"""Tier-3 golden regression: exact-match mini backtest, runs in every CI job.

The golden file freezes the numeric output of a small covid_2020/fixed
configuration. Any change to the algorithms, objective, data loaders, or
engine that alters numbers breaks this test — which is the point. Never
regenerate `tests/golden/mini_backtest_expected.json` just to make it pass
(see CONTRIBUTING.md); use `scripts/generate_mini_golden.py` only for
intentional, reviewed behavior changes.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import json
from pathlib import Path

import pytest

from hive_abc.backtest import BacktestConfig, run_backtest

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Must stay in sync with scripts/generate_mini_golden.py.
# --------------------------------------------------------------------------------------
GOLDEN_FILE = Path(__file__).resolve().parent / "golden" / "mini_backtest_expected.json"
MINI_CONFIG = BacktestConfig(
    period="covid_2020",
    universe="fixed",
    seeds=(0, 1, 2),
    param_overrides={
        model: {"colony_size": 10, "max_iterations": 15}
        for model in (
            "ABC_Original",
            "ABC_FA_Bacanin",
            "ABC_FA_Scout",
            "ABC_Scout_Gravitacional",
        )
    },
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_mini_backtest_matches_golden_exactly() -> None:
    expected = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    result = run_backtest(MINI_CONFIG)

    assert list(result.tickers) == expected["tickers"]
    assert set(result.models) == set(expected["models"])
    for model, model_result in result.models.items():
        frozen = expected["models"][model]
        assert list(model_result.fitness_per_seed) == pytest.approx(
            frozen["fitness_per_seed"], rel=1e-9
        ), f"{model}: per-seed fitness drifted from the golden file"
        assert model_result.sortino == pytest.approx(frozen["sortino"], rel=1e-9)
        assert model_result.max_drawdown == pytest.approx(
            frozen["max_drawdown"], rel=1e-9
        )
        assert model_result.jensen_alpha == pytest.approx(
            frozen["jensen_alpha"], rel=1e-9
        )
        assert model_result.omega == pytest.approx(frozen["omega"], rel=1e-9)
        assert model_result.cardinality == frozen["cardinality"]
        assert list(model_result.best_weights) == pytest.approx(
            frozen["best_weights"], rel=1e-9
        )
