"""Direct calibration runner: candidate x split x seed optimizer studies.

For every (candidate, split) pair the runner builds the thesis utility
objective from the TRAIN window's log-returns and moments, runs one optimize
per seed over long-only box bounds, and scores the normalized best weights by
out-of-sample Sortino on the TEST window's pct-change returns — the same
metric-input convention as `hive_abc.backtest.engine`. It deliberately does
NOT import the backtest engine: no `DEFAULT_MODELS` table, no per-model seed
offsets — seeds are applied exactly as given, and callers own any offset
scheme. That keeps calibration studies structurally unable to disturb the
frozen thesis reproduction path.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from hive_abc.calibration.grid import candidate_label
from hive_abc.calibration.splits import WalkForwardSplit
from hive_abc.core.optimizer import HeuristicOptimizer
from hive_abc.core.types import Bounds
from hive_abc.data.loading import compute_log_returns, compute_moments
from hive_abc.metrics.performance import sortino_ratio
from hive_abc.objectives.utility import PortfolioUtilityObjective, UtilityParams


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class TrialResult:
    """
    Outcome of one (candidate, split) cell across every seed.

    Attributes:
        candidate: Parameter mapping the optimizer was built from.
        label: Canonical candidate label (`grid.candidate_label`).
        split: The walk-forward window pair the cell ran on.
        in_sample_fitness: Best objective value per seed (train window).
        oos_sortino: Out-of-sample Sortino per seed (test window).
        scout_activations: Scout-phase activations per seed's run.
        oos_n_obs: Out-of-sample return observations behind each Sortino.

    Raises:
        ValueError: If the per-seed tuples disagree in length.
    """

    candidate: Mapping[str, object]
    label: str
    split: WalkForwardSplit
    in_sample_fitness: tuple[float, ...]
    oos_sortino: tuple[float, ...]
    scout_activations: tuple[int, ...]
    oos_n_obs: int

    def __post_init__(self) -> None:
        """Validates that the per-seed tuples are aligned."""
        lengths = {
            len(self.in_sample_fitness),
            len(self.oos_sortino),
            len(self.scout_activations),
        }
        if len(lengths) != 1:
            raise ValueError(
                "per-seed tuples must have equal lengths; got "
                f"{len(self.in_sample_fitness)} fitness, "
                f"{len(self.oos_sortino)} sortino, "
                f"{len(self.scout_activations)} activation entries"
            )


@dataclass(frozen=True)
class CalibrationStudy:
    """
    Full result of a calibration run: one trial per (candidate, split).

    Attributes:
        trials: Candidate-major, then split-major trial results.
        seeds: Seeds every trial was run with, in run order.
    """

    trials: tuple[TrialResult, ...]
    seeds: tuple[int, ...]

    @property
    def scout_activation_rate(self) -> float:
        """Share of individual runs in which the scout phase fired."""
        total = sum(len(trial.scout_activations) for trial in self.trials)
        if total == 0:
            return 0.0
        active = sum(
            1
            for trial in self.trials
            for activations in trial.scout_activations
            if activations > 0
        )
        return active / total

    def oos_sortino_by_label(self) -> dict[str, tuple[float, ...]]:
        """
        Per-candidate OOS Sortino samples, concatenated in trial order.

        Returns:
            Mapping from candidate label to its flattened (split-major,
            seed-minor) Sortino sample — the Wilcoxon input for selection.
        """
        grouped: dict[str, list[float]] = {}
        for trial in self.trials:
            grouped.setdefault(trial.label, []).extend(trial.oos_sortino)
        return {label: tuple(values) for label, values in grouped.items()}


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def run_calibration(
    build_optimizer: Callable[[Mapping[str, Any]], HeuristicOptimizer],
    prices: pd.DataFrame,
    candidates: Sequence[Mapping[str, Any]],
    splits: Sequence[WalkForwardSplit],
    seeds: Sequence[int],
    utility: UtilityParams | None = None,
) -> CalibrationStudy:
    """
    Runs every candidate over every split and seed.

    One optimizer instance is built per candidate through `build_optimizer`
    (the `HeuristicOptimizer` contract keeps instances stateless across
    `optimize` calls), and only the train window of each split ever feeds
    the objective.

    Args:
        build_optimizer: Factory turning a candidate mapping into a
            configured optimizer.
        prices: Price panel covering every split window (forward-filled
            internally, as in the backtest engine).
        candidates: Candidate parameter mappings to evaluate.
        splits: Walk-forward windows, e.g. from `walk_forward_splits`.
        seeds: Seeds for the per-cell runs, applied exactly as given.
        utility: Objective parameters; `None` uses the frozen thesis values.

    Returns:
        The study, with one `TrialResult` per (candidate, split).

    Raises:
        ValueError: If `candidates`, `splits`, or `seeds` is empty, or a
            split window covers fewer than two price rows.
    """
    if not candidates:
        raise ValueError("candidates must not be empty")
    if not splits:
        raise ValueError("splits must not be empty")
    if not seeds:
        raise ValueError("seeds must not be empty")

    panel = prices.ffill()
    bounds = Bounds.box(panel.shape[1])
    # Window inputs are candidate-independent; preparing them once up front
    # also fail-fasts on windows the panel cannot support.
    windows = [_window_inputs(panel, split, utility) for split in splits]

    trials: list[TrialResult] = []
    for candidate in candidates:
        optimizer = build_optimizer(candidate)
        label = candidate_label(candidate)
        for split, (objective, oos_matrix) in zip(splits, windows, strict=True):
            fitness: list[float] = []
            sortinos: list[float] = []
            activations: list[int] = []
            for seed in seeds:
                outcome = optimizer.optimize(objective, bounds, seed=seed)
                weights = np.asarray(outcome.best_vector, dtype=np.float64)
                normalized = weights / np.sum(weights)
                oos_returns = np.asarray(oos_matrix @ normalized, dtype=np.float64)
                fitness.append(float(outcome.best_value))
                sortinos.append(sortino_ratio(oos_returns))
                activations.append(outcome.scout_activations)
            trials.append(
                TrialResult(
                    candidate=dict(candidate),
                    label=label,
                    split=split,
                    in_sample_fitness=tuple(fitness),
                    oos_sortino=tuple(sortinos),
                    scout_activations=tuple(activations),
                    oos_n_obs=int(oos_matrix.shape[0]),
                )
            )
    return CalibrationStudy(trials=tuple(trials), seeds=tuple(seeds))


def _window_inputs(
    panel: pd.DataFrame,
    split: WalkForwardSplit,
    utility: UtilityParams | None,
) -> tuple[PortfolioUtilityObjective, NDArray[np.float64]]:
    """
    Builds one split's train objective and test return matrix.

    The objective sees ONLY the train window (log returns and their moments,
    per `hive_abc.data.loading`); the returned matrix holds the test window's
    simple pct-change returns, the engine's Sortino input convention.

    Args:
        panel: Forward-filled price panel.
        split: Window pair to prepare.
        utility: Objective parameters; `None` uses the frozen thesis values.

    Returns:
        Tuple of (train-window objective, test-window return matrix).

    Raises:
        ValueError: If either window covers fewer than two price rows.
    """
    train = panel.loc[split.train_start : split.train_end]
    if len(train) < 2:
        raise ValueError(
            f"train window {split.train_start}..{split.train_end} needs at "
            f"least 2 price rows; got {len(train)}"
        )
    test = panel.loc[split.test_start : split.test_end]
    if len(test) < 2:
        raise ValueError(
            f"test window {split.test_start}..{split.test_end} needs at "
            f"least 2 price rows; got {len(test)}"
        )
    log_returns = compute_log_returns(train)
    mu, _ = compute_moments(log_returns)
    objective = PortfolioUtilityObjective(
        log_returns.to_numpy(), mu.to_numpy(), utility
    )
    oos_matrix = test.pct_change().dropna().to_numpy(dtype=np.float64)
    return objective, oos_matrix
