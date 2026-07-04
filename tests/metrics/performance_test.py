"""Tests for the quantstats-parity performance metrics."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math

import numpy as np
import pytest

from hive_abc.metrics.performance import (
    jensen_alpha,
    max_drawdown,
    omega_ratio,
    sortino_ratio,
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_sortino_matches_hand_computation() -> None:
    returns = np.array([0.02, -0.01, 0.03, -0.02, 0.01])
    downside = math.sqrt((0.01**2 + 0.02**2) / 5)
    expected = returns.mean() / downside * math.sqrt(252)
    assert sortino_ratio(returns) == pytest.approx(expected)


def test_sortino_without_losses_is_nan() -> None:
    assert math.isnan(sortino_ratio(np.array([0.01, 0.02])))


def test_max_drawdown_matches_hand_computation() -> None:
    # Wealth path: 1.10 -> 0.55 -> 0.6875; running max 1.10 -> dd min = -0.5.
    returns = np.array([0.10, -0.50, 0.25])
    assert max_drawdown(returns) == pytest.approx(-0.5)


def test_max_drawdown_measures_from_initial_capital() -> None:
    # A first-day loss counts against the starting capital of 1.0.
    returns = np.array([-0.10, 0.05])
    assert max_drawdown(returns) == pytest.approx(-0.10)


def test_omega_matches_hand_computation() -> None:
    returns = np.array([0.02, -0.01, 0.03, -0.02])
    assert omega_ratio(returns) == pytest.approx(0.05 / 0.03)


def test_omega_without_losses_is_nan() -> None:
    assert math.isnan(omega_ratio(np.array([0.01, 0.02])))


def test_jensen_alpha_of_scaled_benchmark_is_zero() -> None:
    rng = np.random.default_rng(5)
    benchmark = rng.normal(0.0005, 0.01, size=200)
    portfolio = 1.5 * benchmark  # beta 1.5, alpha exactly 0
    assert jensen_alpha(portfolio, benchmark) == pytest.approx(0.0, abs=1e-12)


def test_jensen_alpha_detects_constant_excess() -> None:
    rng = np.random.default_rng(6)
    benchmark = rng.normal(0.0, 0.01, size=500)
    portfolio = benchmark + 0.001  # beta 1, daily alpha 0.001
    assert jensen_alpha(portfolio, benchmark) == pytest.approx(0.252, abs=1e-9)


def test_jensen_alpha_nan_for_flat_benchmark() -> None:
    assert math.isnan(jensen_alpha(np.array([0.01, 0.02]), np.array([0.0, 0.0])))


def test_input_validation() -> None:
    with pytest.raises(ValueError, match="empty"):
        sortino_ratio(np.array([]))
    with pytest.raises(ValueError, match="empty"):
        max_drawdown(np.array([]))
    with pytest.raises(ValueError, match="empty"):
        omega_ratio(np.array([]))
    with pytest.raises(ValueError, match="align"):
        jensen_alpha(np.array([0.01]), np.array([0.01, 0.02]))
    with pytest.raises(ValueError, match="at least 2"):
        jensen_alpha(np.array([0.01]), np.array([0.01]))
