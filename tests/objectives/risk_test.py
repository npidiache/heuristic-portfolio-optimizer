"""Tests for the historical CVaR estimator (riskfolio parity)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pytest

from hive_abc.objectives.risk import cvar_historical


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_hand_computed_cvar() -> None:
    # n=5, alpha=0.4: index = ceil(2) - 1 = 1; sorted returns
    # [-0.05, -0.03, 0.0, 0.01, 0.02] -> VaR return -0.03,
    # tail excess = (-0.05 - -0.03) = -0.02,
    # CVaR = 0.03 - (-0.02) / (0.4 * 5) = 0.04.
    returns = np.array([-0.05, 0.01, 0.02, -0.03, 0.0])
    assert cvar_historical(returns, alpha=0.4) == pytest.approx(0.04)


def test_alpha_one_covers_whole_distribution() -> None:
    returns = np.array([-0.02, 0.01, 0.03])
    # index = n-1: VaR return is the max; CVaR = -max - sum(r_i - max)/n.
    expected = -0.03 - float(np.sum(returns - 0.03)) / 3.0
    assert cvar_historical(returns, alpha=1.0) == pytest.approx(expected)


def test_all_positive_returns_give_negative_cvar() -> None:
    # No losses in the tail: the "shortfall" is a gain, CVaR goes negative.
    returns = np.array([0.01, 0.02, 0.03, 0.04])
    assert cvar_historical(returns, alpha=0.5) < 0


def test_rejects_empty_returns() -> None:
    with pytest.raises(ValueError, match="empty"):
        cvar_historical(np.array([]))


@pytest.mark.parametrize("alpha", [0.0, 1.5])
def test_rejects_out_of_range_alpha(alpha: float) -> None:
    with pytest.raises(ValueError, match="alpha"):
        cvar_historical(np.array([0.01]), alpha=alpha)
