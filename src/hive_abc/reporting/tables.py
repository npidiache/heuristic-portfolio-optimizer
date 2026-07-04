"""Result tables in the canonical thesis schema, plus display naming."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import json
from pathlib import Path
from typing import Any

import pandas as pd

from hive_abc.backtest.engine import BacktestResult

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Canonical JSON keeps legacy keys; display names are applied only here.
# --------------------------------------------------------------------------------------
DISPLAY_NAMES: dict[str, str] = {
    "ABC_Original": "ABC (original)",
    "ABC_FA_Bacanin": "ABC-FA (Bacanin)",
    "ABC_FA_Scout": "ABC-FAEM",
    "ABC_Scout_Gravitacional": "ABC-GSA",
    "PMVG_CVX": "PMVG (min-variance)",
    "Equally_Weighted": "1/N",
}

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_RESULTS_FILE = REPO_ROOT / "data" / "canonical" / "thesis_results_v1.json"


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def load_canonical_results(
    canonical_file: Path = CANONICAL_RESULTS_FILE,
) -> dict[str, Any]:
    """
    Loads the frozen thesis results JSON.

    Args:
        canonical_file: The immutable canonical results artifact.

    Returns:
        The `results[universe][metric_type][period]` structure.
    """
    parsed: dict[str, Any] = json.loads(canonical_file.read_text(encoding="utf-8"))
    return parsed


def canonical_metrics_frame(
    canonical: dict[str, Any], universe: str, period: str
) -> pd.DataFrame:
    """
    One canonical performance table as a DataFrame indexed by model key.

    Args:
        canonical: Output of `load_canonical_results`.
        universe: `dynamic` or `fixed`.
        period: Period slug (e.g., `covid_2020`).

    Returns:
        DataFrame with columns `sortino`, `max_drawdown`, `jensen_alpha`,
        `omega` (the thesis `s`/`d`/`a`/`o` keys).
    """
    rows = canonical[universe]["metrics"][period]
    frame = pd.DataFrame(
        {
            "sortino": [row["s"] for row in rows],
            "max_drawdown": [row["d"] for row in rows],
            "jensen_alpha": [row["a"] for row in rows],
            "omega": [row["o"] for row in rows],
        },
        index=[row["A"] for row in rows],
    )
    frame.index.name = "model"
    return frame


def result_metrics_frame(result: BacktestResult) -> pd.DataFrame:
    """
    Performance table of a backtest run in the canonical column schema.

    Args:
        result: Output of `hive_abc.backtest.run_backtest`.

    Returns:
        DataFrame indexed by model key with the four canonical metrics.
    """
    frame = pd.DataFrame(
        {
            "sortino": {m: r.sortino for m, r in result.models.items()},
            "max_drawdown": {m: r.max_drawdown for m, r in result.models.items()},
            "jensen_alpha": {m: r.jensen_alpha for m, r in result.models.items()},
            "omega": {m: r.omega for m, r in result.models.items()},
        }
    )
    frame.index.name = "model"
    return frame


def runtime_frame(result: BacktestResult) -> pd.DataFrame:
    """
    Execution-time table of a backtest run (committee task 14).

    Args:
        result: Output of `hive_abc.backtest.run_backtest`.

    Returns:
        DataFrame indexed by model key with mean/std/total seconds per run.
    """
    frame = pd.DataFrame(
        {
            "mean_seconds": {
                m: r.runtime.mean_seconds for m, r in result.models.items()
            },
            "std_seconds": {m: r.runtime.std_seconds for m, r in result.models.items()},
            "total_seconds": {
                m: r.runtime.total_seconds for m, r in result.models.items()
            },
        }
    )
    frame.index.name = "model"
    return frame


def with_display_names(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Renames a model-indexed table to thesis display names.

    Args:
        frame: Any DataFrame indexed by legacy model keys.

    Returns:
        Copy with the index mapped through `DISPLAY_NAMES` (unknown keys are
        kept as-is).
    """
    renamed = frame.copy()
    renamed.index = pd.Index(
        [DISPLAY_NAMES.get(str(key), str(key)) for key in frame.index],
        name=frame.index.name,
    )
    return renamed
