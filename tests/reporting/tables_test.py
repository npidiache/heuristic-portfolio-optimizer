"""Tests for the canonical result tables and display naming."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pandas as pd
import pytest

from hive_abc.backtest.engine import (
    BacktestConfig,
    BacktestResult,
    ModelBacktestResult,
    RuntimeStats,
)
from hive_abc.reporting.tables import (
    canonical_metrics_frame,
    load_canonical_results,
    result_metrics_frame,
    runtime_frame,
    with_display_names,
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def _stub_result() -> BacktestResult:
    model = ModelBacktestResult(
        model="ABC_FA_Scout",
        fitness_per_seed=(0.1, 0.2),
        sortino_per_seed=(3.0, 2.9),
        best_weights=np.array([0.6, 0.4]),
        sortino=3.0,
        max_drawdown=-0.2,
        jensen_alpha=0.5,
        omega=1.4,
        cardinality=2,
        max_weight=0.6,
        hhi=0.52,
        runtime=RuntimeStats(mean_seconds=1.0, std_seconds=0.1, total_seconds=2.0),
    )
    return BacktestResult(
        config=BacktestConfig(period="covid_2020", universe="fixed"),
        tickers=("AAA", "BBB"),
        models={"ABC_FA_Scout": model},
    )


def test_canonical_frame_reads_the_frozen_json() -> None:
    canonical = load_canonical_results()
    frame = canonical_metrics_frame(canonical, "fixed", "2023_stability")
    assert frame.loc["ABC_Scout_Gravitacional", "sortino"] == pytest.approx(5.011)
    assert list(frame.columns) == [
        "sortino",
        "max_drawdown",
        "jensen_alpha",
        "omega",
    ]


def test_result_frame_uses_canonical_schema() -> None:
    frame = result_metrics_frame(_stub_result())
    assert frame.loc["ABC_FA_Scout", "sortino"] == pytest.approx(3.0)
    assert frame.loc["ABC_FA_Scout", "omega"] == pytest.approx(1.4)


def test_runtime_frame_reports_task_14_columns() -> None:
    frame = runtime_frame(_stub_result())
    assert frame.loc["ABC_FA_Scout", "total_seconds"] == pytest.approx(2.0)
    assert list(frame.columns) == ["mean_seconds", "std_seconds", "total_seconds"]


def test_display_names_are_thesis_names() -> None:
    frame = pd.DataFrame({"x": [1, 2]}, index=["ABC_FA_Scout", "UNKNOWN_MODEL"])
    frame.index.name = "model"
    renamed = with_display_names(frame)
    assert list(renamed.index) == ["ABC-FAEM", "UNKNOWN_MODEL"]
