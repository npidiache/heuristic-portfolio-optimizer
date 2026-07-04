"""Regenerates the Tier-3 mini golden file. MAINTAINER USE ONLY.

The golden file freezes the exact output of a small, fast backtest
configuration. The Tier-3 test compares every run against it bit-for-bit, so
regenerating it silently would disable the regression guard — only do so for
an intentional, reviewed behavior change (see CONTRIBUTING.md).
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from hive_abc.backtest import BacktestConfig, run_backtest  # noqa: E402

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: MINI_CONFIG must stay in sync with tests/golden_backtest_test.py.
# --------------------------------------------------------------------------------------
GOLDEN_FILE = REPO_ROOT / "tests" / "golden" / "mini_backtest_expected.json"
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
def main() -> None:
    """Runs the mini config and freezes its exact numeric output."""
    result = run_backtest(MINI_CONFIG)
    payload = {
        "tickers": list(result.tickers),
        "models": {
            model: {
                "fitness_per_seed": list(r.fitness_per_seed),
                "sortino": r.sortino,
                "max_drawdown": r.max_drawdown,
                "jensen_alpha": r.jensen_alpha,
                "omega": r.omega,
                "cardinality": r.cardinality,
                "max_weight": r.max_weight,
                "hhi": r.hhi,
                "best_weights": list(r.best_weights),
            }
            for model, r in result.models.items()
        },
    }
    GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {GOLDEN_FILE}")


if __name__ == "__main__":
    main()
