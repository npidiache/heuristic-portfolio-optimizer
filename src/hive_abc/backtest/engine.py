"""Backtest engine reproducing the frozen thesis harness semantics.

One `run_backtest(config)` call replays a thesis experiment: select the
universe (dynamic or fixed z-score), load the period's prices from the frozen
data, optimize every model over `config.seeds`, pick each model's
best-of-seeds portfolio, and compute the canonical metric set. The only
deliberate deviation from the legacy harness is seeding: seeds are pinned in
the config instead of drawn from an unseeded `random.randint`, which is what
makes reruns reproducible.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from hive_abc.backtest.params import (
    ABC_MODEL_CLASSES,
    load_regime_parameters,
)
from hive_abc.backtest.params import (
    build_abc_model as _build_abc_model,
)
from hive_abc.backtest.periods import PERIODS
from hive_abc.benchmarks import EqualWeight, MinVarianceCVX
from hive_abc.core.types import Bounds
from hive_abc.data.loading import (
    FROZEN_BENCHMARK,
    FROZEN_PRICES,
    FROZEN_ZSCORE,
    compute_log_returns,
    compute_moments,
    load_benchmark_returns,
    load_prices,
)
from hive_abc.data.universe import (
    load_fixed_zscore_universe,
    select_universe_dynamic_zscore,
)
from hive_abc.metrics.concentration import (
    concentration_hhi,
    effective_cardinality,
    max_weight,
)
from hive_abc.metrics.performance import (
    jensen_alpha,
    max_drawdown,
    omega_ratio,
    sortino_ratio,
)
from hive_abc.objectives.utility import PortfolioUtilityObjective, UtilityParams

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Model keys are the legacy names so results align with the canonical JSON.
# --------------------------------------------------------------------------------------
DEFAULT_MODELS: tuple[str, ...] = (
    "ABC_Original",
    "ABC_FA_Bacanin",
    "ABC_FA_Scout",
    "ABC_Scout_Gravitacional",
    "PMVG_CVX",
    "Equally_Weighted",
)

# The legacy harness gave every algorithm its own RNG stream by deriving a
# per-class seed from hash(cls.__name__) — platform-dependent, but it means
# the canonical per-model numbers differ by seed noise even where the scout
# mechanics never fire. This stable offset table reproduces that property
# portably: run seed = config_seed * 1000 + offset.
MODEL_SEED_OFFSETS: dict[str, int] = {
    "ABC_Original": 0,
    "ABC_FA_Bacanin": 1,
    "ABC_FA_Scout": 2,
    "ABC_Scout_Gravitacional": 3,
}


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class BacktestConfig:
    """
    Full specification of one reproducible backtest run.

    Attributes:
        period: Key of `hive_abc.backtest.periods.PERIODS`.
        universe: `dynamic` (ex-ante market z-score) or `fixed`
            (fundamentals top-20 file).
        seeds: One optimizer run per seed for the stochastic models.
        utility: Objective parameters (defaults are the frozen values).
        models: Legacy-keyed models to run.
        param_overrides: Per-model constructor overrides — the PFA
            sensitivity hook (e.g., `{"ABC_FA_Scout": {"p_fa": 0.4}}`).
        universe_tickers: When given, skips selection and uses these tickers
            (the with/without-filter comparison hook of reviewer task 12).
    """

    period: str
    universe: Literal["dynamic", "fixed"]
    seeds: tuple[int, ...] = tuple(range(20))
    utility: UtilityParams = field(default_factory=UtilityParams)
    models: tuple[str, ...] = DEFAULT_MODELS
    param_overrides: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    universe_tickers: tuple[str, ...] | None = None


@dataclass(frozen=True)
class RuntimeStats:
    """Wall-clock statistics per model across seeds (reviewer task 14)."""

    mean_seconds: float
    std_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class ModelBacktestResult:
    """
    One model's outcome over all seeds of a backtest run.

    Attributes:
        model: Legacy model key.
        fitness_per_seed: Best objective value of each seed's run.
        sortino_per_seed: Sortino of each seed's best portfolio (Wilcoxon
            input, as in the thesis analysis).
        best_weights: Normalized weights of the best-of-seeds portfolio.
        sortino / max_drawdown / jensen_alpha / omega: Canonical performance
            metrics of the best portfolio (thesis table schema s/d/a/o).
        cardinality / max_weight / hhi: Concentration metrics (c/mw/hhi).
        runtime: Wall-clock statistics across the model's runs.
    """

    model: str
    fitness_per_seed: tuple[float, ...]
    sortino_per_seed: tuple[float, ...]
    best_weights: NDArray[np.float64]
    sortino: float
    max_drawdown: float
    jensen_alpha: float
    omega: float
    cardinality: int
    max_weight: float
    hhi: float
    runtime: RuntimeStats


@dataclass(frozen=True)
class BacktestResult:
    """A full run: per-model results plus the universe that was used."""

    config: BacktestConfig
    tickers: tuple[str, ...]
    models: dict[str, ModelBacktestResult]


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def run_backtest(
    config: BacktestConfig,
    prices_file: Path = FROZEN_PRICES,
    zscore_file: Path = FROZEN_ZSCORE,
    benchmark_file: Path = FROZEN_BENCHMARK,
) -> BacktestResult:
    """
    Replays one thesis backtest experiment end to end.

    Args:
        config: The run specification.
        prices_file: Price panel (defaults to the frozen artifact).
        zscore_file: Fundamentals z-score file for the fixed universe.
        benchmark_file: Frozen ^IXIC closes for Jensen alpha.

    Returns:
        Per-model results with canonical metrics and runtime statistics.

    Raises:
        ValueError: If the period or a model key is unknown.
        RuntimeError: If universe selection yields fewer than 5 tickers.
    """
    if config.period not in PERIODS:
        raise ValueError(
            f"Unknown period '{config.period}'; expected one of {sorted(PERIODS)}"
        )
    unknown = [m for m in config.models if m not in DEFAULT_MODELS]
    if unknown:
        raise ValueError(f"Unknown models {unknown}; expected among {DEFAULT_MODELS}")
    period = PERIODS[config.period]

    if config.universe_tickers is not None:
        tickers = list(config.universe_tickers)
    elif config.universe == "dynamic":
        tickers = select_universe_dynamic_zscore(
            period.start_date, prices_file=prices_file
        )
    else:
        tickers = load_fixed_zscore_universe(zscore_file)
    if len(tickers) < 5:
        raise RuntimeError(f"Universe selection produced only {len(tickers)} tickers")

    prices = load_prices(
        prices_file, period.start_date, period.end_date, tickers, min_days=50
    )
    log_returns = compute_log_returns(prices)
    mu, cov = compute_moments(log_returns)
    prices = prices.ffill()
    tickers = [str(t) for t in mu.index]
    n_assets = len(tickers)

    objective = PortfolioUtilityObjective(
        log_returns.to_numpy(), mu.to_numpy(), config.utility
    )
    bounds = Bounds.box(n_assets)

    # Metric inputs, exactly as the frozen harness: simple pct-change asset
    # returns for portfolio metrics, log-return ^IXIC aligned to them.
    asset_returns = prices.pct_change().dropna()
    benchmark = (
        load_benchmark_returns(benchmark_file, period.start_date, period.end_date)
        .reindex(asset_returns.index)
        .ffill()
        .bfill()
        .to_numpy(dtype=np.float64)
    )

    regime_params = load_regime_parameters(period.regime)
    results: dict[str, ModelBacktestResult] = {}
    for model in config.models:
        runs = _run_model(model, config, regime_params, objective, bounds, cov)
        results[model] = _summarize_model(model, runs, asset_returns, benchmark)

    return BacktestResult(config=config, tickers=tuple(tickers), models=results)


def _run_model(
    model: str,
    config: BacktestConfig,
    regime_params: dict[str, dict[str, float]],
    objective: PortfolioUtilityObjective,
    bounds: Bounds,
    cov: pd.DataFrame,
) -> list[tuple[float, NDArray[np.float64], float]]:
    """Runs one model over every seed; returns (fitness, weights, seconds)."""
    runs: list[tuple[float, NDArray[np.float64], float]] = []
    if model in ABC_MODEL_CLASSES:
        overrides = config.param_overrides.get(model)
        for seed in config.seeds:
            optimizer = _build_abc_model(
                model, regime_params.get(model, {}), bounds.dim, overrides
            )
            run_seed = seed * 1000 + MODEL_SEED_OFFSETS[model]
            outcome = optimizer.optimize(objective, bounds, seed=run_seed)
            runs.append(
                (outcome.best_value, outcome.best_vector, outcome.runtime_seconds)
            )
        return runs

    # Deterministic benchmarks: solved once, replicated per seed exactly like
    # the frozen harness recorded them.
    if model == "PMVG_CVX":
        outcome = MinVarianceCVX(cov.to_numpy()).optimize(objective, bounds)
    else:  # Equally_Weighted
        outcome = EqualWeight().optimize(objective, bounds)
    runs = [
        (outcome.best_value, outcome.best_vector, outcome.runtime_seconds)
        for _ in config.seeds
    ]
    return runs


def _summarize_model(
    model: str,
    runs: list[tuple[float, NDArray[np.float64], float]],
    asset_returns: pd.DataFrame,
    benchmark: NDArray[np.float64],
) -> ModelBacktestResult:
    """Builds the canonical metric set from a model's per-seed runs."""

    def portfolio_returns(weights: NDArray[np.float64]) -> NDArray[np.float64]:
        normalized = weights / np.sum(weights)
        return np.asarray(asset_returns.to_numpy() @ normalized, dtype=np.float64)

    sortino_per_seed = tuple(
        sortino_ratio(portfolio_returns(weights)) for _, weights, _ in runs
    )
    best_fitness, best_raw, _ = min(runs, key=lambda run: run[0])
    best_weights = np.asarray(best_raw / np.sum(best_raw), dtype=np.float64)
    best_returns = portfolio_returns(best_weights)
    durations = np.array([seconds for _, _, seconds in runs])

    return ModelBacktestResult(
        model=model,
        fitness_per_seed=tuple(fitness for fitness, _, _ in runs),
        sortino_per_seed=sortino_per_seed,
        best_weights=best_weights,
        sortino=sortino_ratio(best_returns),
        max_drawdown=max_drawdown(best_returns),
        jensen_alpha=jensen_alpha(best_returns, benchmark),
        omega=omega_ratio(best_returns),
        cardinality=effective_cardinality(best_weights),
        max_weight=max_weight(best_weights),
        hhi=concentration_hhi(best_weights),
        runtime=RuntimeStats(
            mean_seconds=float(durations.mean()),
            std_seconds=float(durations.std()),
            total_seconds=float(durations.sum()),
        ),
    )
