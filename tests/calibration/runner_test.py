"""Tests for the direct calibration runner (grid x split x seed studies)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math
from collections.abc import Mapping
from typing import Any, cast

import numpy as np
import pandas as pd
import pytest

from hive_abc import ABCOriginal, Bounds, HeuristicOptimizer, OptimizationResult
from hive_abc.calibration.runner import (
    CalibrationStudy,
    TrialResult,
    run_calibration,
)
from hive_abc.calibration.splits import WalkForwardSplit, walk_forward_splits
from hive_abc.core.types import ObjectiveFn
from hive_abc.objectives import PortfolioUtilityObjective, UtilityParams

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
TICKERS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]

CANDIDATES = ({"colony_size": 6}, {"colony_size": 8})

SEEDS = (0, 1, 2)


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class _RecordingOptimizer(HeuristicOptimizer):
    """Deterministic double that records every `optimize` call it receives."""

    def __init__(self, activations_by_seed: Mapping[int, int] | None = None) -> None:
        self.objectives: list[PortfolioUtilityObjective] = []
        self.seeds: list[int | None] = []
        self._activations_by_seed = dict(activations_by_seed or {})

    def optimize(
        self,
        objective: ObjectiveFn,
        bounds: Bounds,
        *,
        seed: int | None = None,
    ) -> OptimizationResult:
        """Returns an equal-weight solution and a seed-derived fitness."""
        self.objectives.append(cast(PortfolioUtilityObjective, objective))
        self.seeds.append(seed)
        run_seed = 0 if seed is None else seed
        return OptimizationResult(
            best_vector=np.full(bounds.dim, 1.0 / bounds.dim),
            best_value=float(run_seed),
            best_per_iteration=(float(run_seed),),
            mean_per_iteration=(float(run_seed),),
            n_evaluations=1,
            runtime_seconds=0.0,
            seed=seed,
            scout_activations=self._activations_by_seed.get(run_seed, 0),
        )


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
@pytest.fixture(scope="session")
def synthetic_price_panel() -> pd.DataFrame:
    """Six-ticker synthetic price panel (mirrors the root conftest pattern)."""
    rng = np.random.default_rng(2024)
    dates = pd.bdate_range("2021-01-04", periods=160)
    drifts = np.linspace(0.0003, 0.001, num=len(TICKERS))
    vols = np.linspace(0.01, 0.02, num=len(TICKERS))
    return pd.DataFrame(
        {
            ticker: 100.0 * np.cumprod(1 + rng.normal(drift, vol, size=len(dates)))
            for ticker, drift, vol in zip(TICKERS, drifts, vols, strict=True)
        },
        index=dates,
    )


@pytest.fixture(scope="session")
def two_splits(synthetic_price_panel: pd.DataFrame) -> tuple[WalkForwardSplit, ...]:
    """First two walk-forward splits over the synthetic panel."""
    splits = walk_forward_splits(
        pd.DatetimeIndex(synthetic_price_panel.index),
        train_days=60,
        test_days=20,
        step_days=20,
        embargo_days=3,
    )
    return splits[:2]


def test_study_has_one_trial_per_candidate_split_with_per_seed_tuples(
    synthetic_price_panel: pd.DataFrame, two_splits: tuple[WalkForwardSplit, ...]
) -> None:
    spies: list[_RecordingOptimizer] = []

    def factory(candidate: Mapping[str, Any]) -> HeuristicOptimizer:
        spies.append(_RecordingOptimizer())
        return spies[-1]

    study = run_calibration(
        factory, synthetic_price_panel, CANDIDATES, two_splits, SEEDS
    )

    assert isinstance(study, CalibrationStudy)
    assert len(study.trials) == len(CANDIDATES) * len(two_splits)
    assert study.seeds == SEEDS
    assert [trial.split for trial in study.trials] == [*two_splits, *two_splits]
    for trial in study.trials:
        assert len(trial.in_sample_fitness) == len(SEEDS)
        assert len(trial.oos_sortino) == len(SEEDS)
        assert all(math.isfinite(value) for value in trial.oos_sortino)
        # The spy's fitness equals the seed, so seeds are applied as given.
        assert trial.in_sample_fitness == (0.0, 1.0, 2.0)
        # 20 test prices yield 19 pct-change observations.
        assert trial.oos_n_obs == 19
    labels = [trial.label for trial in study.trials]
    assert labels == [
        "colony_size=6",
        "colony_size=6",
        "colony_size=8",
        "colony_size=8",
    ]
    assert set(study.oos_sortino_by_label()) == {"colony_size=6", "colony_size=8"}


def test_factory_builds_one_optimizer_per_candidate() -> None:
    built: list[Mapping[str, Any]] = []
    prices = _tiny_panel()
    splits = walk_forward_splits(
        pd.DatetimeIndex(prices.index),
        train_days=30,
        test_days=10,
        step_days=10,
        embargo_days=2,
    )

    def factory(candidate: Mapping[str, Any]) -> HeuristicOptimizer:
        built.append(candidate)
        return _RecordingOptimizer()

    run_calibration(factory, prices, CANDIDATES, splits[:1], seeds=(0,))
    assert built == list(CANDIDATES)


def test_only_the_train_window_feeds_the_objective(
    synthetic_price_panel: pd.DataFrame, two_splits: tuple[WalkForwardSplit, ...]
) -> None:
    spies: list[_RecordingOptimizer] = []

    def factory(candidate: Mapping[str, Any]) -> HeuristicOptimizer:
        spies.append(_RecordingOptimizer())
        return spies[-1]

    run_calibration(factory, synthetic_price_panel, CANDIDATES, two_splits, SEEDS)

    full_panel_rows = len(synthetic_price_panel)
    for spy in spies:
        # One objective per (split, seed), in split-major order.
        assert len(spy.objectives) == len(two_splits) * len(SEEDS)
        for split_index, split in enumerate(two_splits):
            window = synthetic_price_panel.loc[split.train_start : split.train_end]
            # compute_log_returns drops the first (all-NaN) row.
            expected_rows = len(window) - 1
            for seed_index in range(len(SEEDS)):
                objective = spy.objectives[split_index * len(SEEDS) + seed_index]
                assert objective._returns.shape[0] == expected_rows
                assert objective._returns.shape[0] < full_panel_rows - 1


def test_runs_are_reproducible_under_the_same_seeds(
    synthetic_price_panel: pd.DataFrame, two_splits: tuple[WalkForwardSplit, ...]
) -> None:
    def factory(candidate: Mapping[str, Any]) -> HeuristicOptimizer:
        return ABCOriginal(colony_size=int(candidate["colony_size"]), max_iterations=5)

    first = run_calibration(
        factory, synthetic_price_panel, CANDIDATES, two_splits, SEEDS
    )
    second = run_calibration(
        factory, synthetic_price_panel, CANDIDATES, two_splits, SEEDS
    )
    for trial_a, trial_b in zip(first.trials, second.trials, strict=True):
        assert trial_a.in_sample_fitness == trial_b.in_sample_fitness
        assert trial_a.oos_sortino == trial_b.oos_sortino
        assert all(math.isfinite(value) for value in trial_a.oos_sortino)


def test_scout_activation_telemetry_is_collected_per_run(
    synthetic_price_panel: pd.DataFrame, two_splits: tuple[WalkForwardSplit, ...]
) -> None:
    def factory(candidate: Mapping[str, Any]) -> HeuristicOptimizer:
        return _RecordingOptimizer(activations_by_seed={1: 2})

    study = run_calibration(
        factory, synthetic_price_panel, CANDIDATES, two_splits, SEEDS
    )
    for trial in study.trials:
        assert trial.scout_activations == (0, 2, 0)
    # 1 activating run out of 3 seeds, in every one of the 4 trials.
    assert study.scout_activation_rate == pytest.approx(1.0 / 3.0)


def test_utility_params_reach_the_objective(
    synthetic_price_panel: pd.DataFrame, two_splits: tuple[WalkForwardSplit, ...]
) -> None:
    spies: list[_RecordingOptimizer] = []

    def factory(candidate: Mapping[str, Any]) -> HeuristicOptimizer:
        spies.append(_RecordingOptimizer())
        return spies[-1]

    custom = UtilityParams(lambda_cvar=0.5)
    run_calibration(
        factory,
        synthetic_price_panel,
        CANDIDATES[:1],
        two_splits[:1],
        seeds=(0,),
        utility=custom,
    )
    assert spies[0].objectives[0].params == custom

    run_calibration(
        factory, synthetic_price_panel, CANDIDATES[:1], two_splits[:1], seeds=(0,)
    )
    assert spies[1].objectives[0].params == UtilityParams()


def test_empty_inputs_rejected(
    synthetic_price_panel: pd.DataFrame, two_splits: tuple[WalkForwardSplit, ...]
) -> None:
    def factory(candidate: Mapping[str, Any]) -> HeuristicOptimizer:
        return _RecordingOptimizer()

    with pytest.raises(ValueError, match="candidates"):
        run_calibration(factory, synthetic_price_panel, (), two_splits, SEEDS)
    with pytest.raises(ValueError, match="splits"):
        run_calibration(factory, synthetic_price_panel, CANDIDATES, (), SEEDS)
    with pytest.raises(ValueError, match="seeds"):
        run_calibration(factory, synthetic_price_panel, CANDIDATES, two_splits, ())


def test_windows_without_enough_prices_rejected(
    synthetic_price_panel: pd.DataFrame,
) -> None:
    index = synthetic_price_panel.index

    def factory(candidate: Mapping[str, Any]) -> HeuristicOptimizer:
        return _RecordingOptimizer()

    single_day_test = WalkForwardSplit(
        train_start=index[0],
        train_end=index[59],
        test_start=index[63],
        test_end=index[63],
    )
    with pytest.raises(ValueError, match="test window"):
        run_calibration(
            factory, synthetic_price_panel, CANDIDATES, (single_day_test,), SEEDS
        )

    single_day_train = WalkForwardSplit(
        train_start=index[0],
        train_end=index[0],
        test_start=index[5],
        test_end=index[30],
    )
    with pytest.raises(ValueError, match="train window"):
        run_calibration(
            factory, synthetic_price_panel, CANDIDATES, (single_day_train,), SEEDS
        )


def test_trial_result_rejects_mismatched_per_seed_tuples() -> None:
    split = WalkForwardSplit(
        train_start=pd.Timestamp("2021-01-04"),
        train_end=pd.Timestamp("2021-03-31"),
        test_start=pd.Timestamp("2021-04-08"),
        test_end=pd.Timestamp("2021-05-07"),
    )
    with pytest.raises(ValueError, match="per-seed"):
        TrialResult(
            candidate={"colony_size": 6},
            label="colony_size=6",
            split=split,
            in_sample_fitness=(0.1, 0.2),
            oos_sortino=(1.0,),
            scout_activations=(0, 0),
            oos_n_obs=19,
        )


def test_empty_study_reports_zero_activation_rate() -> None:
    assert CalibrationStudy(trials=(), seeds=()).scout_activation_rate == 0.0


def _tiny_panel() -> pd.DataFrame:
    """Small independent panel for tests that do not share the fixture."""
    rng = np.random.default_rng(11)
    dates = pd.bdate_range("2022-01-03", periods=60)
    return pd.DataFrame(
        {
            ticker: 50.0 * np.cumprod(1 + rng.normal(0.0005, 0.015, size=len(dates)))
            for ticker in TICKERS[:4]
        },
        index=dates,
    )
