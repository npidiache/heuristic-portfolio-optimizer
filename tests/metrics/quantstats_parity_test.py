"""One-off parity checks of the native metrics against quantstats.

The thesis computed its reported metrics with quantstats; these tests lock
the native reimplementations to those estimators. They only run with the
`parity` marker and require the optional dependency group:

    uv sync --group parity && uv run pytest -m parity
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pandas as pd
import pytest

from hive_abc.metrics.performance import (
    jensen_alpha,
    max_drawdown,
    omega_ratio,
    sortino_ratio,
)

qs = pytest.importorskip("quantstats")

pytestmark = pytest.mark.parity

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
RNG = np.random.default_rng(42)
DATES = pd.bdate_range("2020-01-01", periods=300)
PORTFOLIO = pd.Series(RNG.normal(0.0008, 0.015, size=300), index=DATES)
BENCHMARK = pd.Series(
    0.8 * np.asarray(PORTFOLIO, dtype=np.float64) + RNG.normal(0.0, 0.005, size=300),
    index=DATES,
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_sortino_parity() -> None:
    assert sortino_ratio(np.asarray(PORTFOLIO, dtype=np.float64)) == pytest.approx(
        float(qs.stats.sortino(PORTFOLIO)), rel=1e-9
    )


def test_max_drawdown_parity() -> None:
    assert max_drawdown(np.asarray(PORTFOLIO, dtype=np.float64)) == pytest.approx(
        float(qs.stats.max_drawdown(PORTFOLIO)), rel=1e-9
    )


def test_omega_parity() -> None:
    assert omega_ratio(np.asarray(PORTFOLIO, dtype=np.float64)) == pytest.approx(
        float(qs.stats.omega(PORTFOLIO)), rel=1e-9
    )


def test_jensen_alpha_parity() -> None:
    greeks = qs.stats.greeks(PORTFOLIO, benchmark=BENCHMARK)
    assert jensen_alpha(
        np.asarray(PORTFOLIO, dtype=np.float64), np.asarray(BENCHMARK, dtype=np.float64)
    ) == pytest.approx(float(greeks["alpha"]), rel=1e-6)
