"""Tests for the backtest engine on synthetic data."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from pathlib import Path

import numpy as np
import pytest

from hive_abc.backtest.engine import BacktestConfig, BacktestResult, run_backtest
from hive_abc.backtest.periods import PERIODS, Period

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Small colonies/iterations via param_overrides keep these tests fast.
# --------------------------------------------------------------------------------------
FAST_OVERRIDES = {
    model: {"colony_size": 6, "max_iterations": 5}
    for model in (
        "ABC_Original",
        "ABC_FA_Bacanin",
        "ABC_FA_Scout",
        "ABC_Scout_Gravitacional",
    )
}


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
@pytest.fixture
def synthetic_period(monkeypatch: pytest.MonkeyPatch) -> str:
    """Registers a backtest period covered by the synthetic price fixture."""
    period = Period(
        slug="synthetic_2021",
        start_date="2021-03-01",
        end_date="2021-05-28",
        regime="CRISIS",
        description="synthetic test window",
    )
    monkeypatch.setitem(PERIODS, period.slug, period)
    return period.slug


def run_synthetic(
    synthetic_period: str,
    synthetic_data_dir: Path,
    **config_kwargs: object,
) -> BacktestResult:
    """Runs a fast synthetic backtest with overridable config fields."""
    defaults: dict[str, object] = {
        "period": synthetic_period,
        "universe": "fixed",
        "seeds": (0, 1),
        "param_overrides": FAST_OVERRIDES,
    }
    defaults.update(config_kwargs)
    return run_backtest(
        BacktestConfig(**defaults),  # type: ignore[arg-type]
        prices_file=synthetic_data_dir / "prices.csv",
        zscore_file=synthetic_data_dir / "z_score.csv",
        benchmark_file=synthetic_data_dir / "benchmark.csv",
    )


def test_full_run_produces_all_models_and_metrics(
    synthetic_period: str, synthetic_data_dir: Path
) -> None:
    result = run_synthetic(synthetic_period, synthetic_data_dir)

    assert set(result.models) == {
        "ABC_Original",
        "ABC_FA_Bacanin",
        "ABC_FA_Scout",
        "ABC_Scout_Gravitacional",
        "PMVG_CVX",
        "Equally_Weighted",
    }
    assert len(result.tickers) == 6
    for model_result in result.models.values():
        assert len(model_result.fitness_per_seed) == 2
        assert len(model_result.sortino_per_seed) == 2
        assert model_result.best_weights.sum() == pytest.approx(1.0)
        assert np.all(model_result.best_weights >= 0)
        assert model_result.runtime.total_seconds >= 0
        assert model_result.cardinality >= 1
        assert -1.0 <= model_result.max_drawdown <= 0.0


def test_run_is_reproducible(synthetic_period: str, synthetic_data_dir: Path) -> None:
    first = run_synthetic(synthetic_period, synthetic_data_dir)
    second = run_synthetic(synthetic_period, synthetic_data_dir)
    for model in first.models:
        assert (
            first.models[model].fitness_per_seed
            == second.models[model].fitness_per_seed
        )


def test_equal_weight_matches_one_over_n(
    synthetic_period: str, synthetic_data_dir: Path
) -> None:
    result = run_synthetic(
        synthetic_period, synthetic_data_dir, models=("Equally_Weighted",)
    )
    assert result.models["Equally_Weighted"].best_weights == pytest.approx(
        np.full(6, 1 / 6)
    )


def test_dynamic_universe_selection_path(
    synthetic_period: str, synthetic_data_dir: Path
) -> None:
    result = run_synthetic(
        synthetic_period,
        synthetic_data_dir,
        universe="dynamic",
        models=("Equally_Weighted",),
    )
    assert len(result.tickers) >= 5


def test_explicit_universe_tickers_skip_selection(
    synthetic_period: str, synthetic_data_dir: Path
) -> None:
    tickers = ("AAA", "BBB", "CCC", "DDD", "EEE")
    result = run_synthetic(
        synthetic_period,
        synthetic_data_dir,
        universe_tickers=tickers,
        models=("Equally_Weighted",),
    )
    assert result.tickers == tickers


def test_param_overrides_change_stochastic_results(
    synthetic_period: str, synthetic_data_dir: Path
) -> None:
    base = run_synthetic(synthetic_period, synthetic_data_dir, models=("ABC_FA_Scout",))
    bigger = run_synthetic(
        synthetic_period,
        synthetic_data_dir,
        models=("ABC_FA_Scout",),
        param_overrides={"ABC_FA_Scout": {"colony_size": 12, "max_iterations": 10}},
    )
    assert (
        base.models["ABC_FA_Scout"].fitness_per_seed
        != bigger.models["ABC_FA_Scout"].fitness_per_seed
    )


def test_unknown_period_raises(synthetic_data_dir: Path) -> None:
    with pytest.raises(ValueError, match="Unknown period"):
        run_backtest(
            BacktestConfig(period="dotcom_2000", universe="fixed"),
            prices_file=synthetic_data_dir / "prices.csv",
        )


def test_unknown_model_raises(synthetic_period: str, synthetic_data_dir: Path) -> None:
    with pytest.raises(ValueError, match="Unknown models"):
        run_synthetic(synthetic_period, synthetic_data_dir, models=("ABC_Quantum",))


def test_too_small_universe_raises(
    synthetic_period: str, synthetic_data_dir: Path
) -> None:
    with pytest.raises(RuntimeError, match="tickers"):
        run_synthetic(
            synthetic_period, synthetic_data_dir, universe_tickers=("AAA", "BBB")
        )
