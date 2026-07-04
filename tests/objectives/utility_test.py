"""Tests for the executed thesis objective (Eq. 18 semantics)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pytest

from hive_abc.objectives.risk import cvar_historical
from hive_abc.objectives.utility import (
    EMPTY_PORTFOLIO_SENTINEL,
    PortfolioUtilityObjective,
    UtilityParams,
)

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
RETURNS = np.array(
    [
        [0.010, -0.004, 0.002],
        [-0.020, 0.006, -0.001],
        [0.005, 0.003, 0.004],
        [0.012, -0.008, 0.000],
        [-0.007, 0.001, 0.002],
    ]
)
MU = RETURNS.mean(axis=0)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_executed_default_parameters_are_the_frozen_values() -> None:
    params = UtilityParams()
    assert params.lambda_cvar == 0.7
    assert params.eta_l1 == 5e-4
    assert params.lambda_cardinality_base == 8e-3
    assert params.cvar_alpha == 0.99
    assert params.target_cardinality == 10
    assert params.cardinality_threshold == 0.01


def test_empty_portfolio_returns_sentinel() -> None:
    objective = PortfolioUtilityObjective(RETURNS, MU)
    assert objective(np.zeros(3)) == EMPTY_PORTFOLIO_SENTINEL


def test_hand_computed_negative_utility() -> None:
    objective = PortfolioUtilityObjective(RETURNS, MU)
    raw = np.array([2.0, 1.0, 1.0])  # normalizes to (0.5, 0.25, 0.25)
    normalized = raw / raw.sum()

    portfolio_return = float(normalized @ MU)
    portfolio_returns = RETURNS @ normalized
    cvar = cvar_historical(portfolio_returns, alpha=0.99)
    # 3 assets: every weight > 1% but 3 <= target 10 -> no cardinality
    # penalty; L1 of a normalized long-only portfolio is exactly 1.
    expected_utility = portfolio_return - 0.7 * cvar - 5e-4 * 1.0
    assert objective(raw) == pytest.approx(-expected_utility)


def test_normalization_makes_scale_irrelevant() -> None:
    objective = PortfolioUtilityObjective(RETURNS, MU)
    weights = np.array([0.3, 0.5, 0.2])
    assert objective(weights) == pytest.approx(objective(weights * 7.5))


def test_cardinality_weight_scales_with_universe_size() -> None:
    # 40 assets -> effective lambda_card = 0.008 * 40/20 = 0.016. Build a
    # portfolio with 12 significant names (2 above the target of 10).
    rng = np.random.default_rng(3)
    returns = rng.normal(0.0, 0.01, size=(30, 40))
    mu = returns.mean(axis=0)
    objective = PortfolioUtilityObjective(returns, mu)

    weights = np.zeros(40)
    weights[:12] = 1.0 / 12
    dense = objective(weights)

    sparse_weights = np.zeros(40)
    sparse_weights[:10] = 0.1
    # Compare the cardinality contribution directly: 2 excess names squared.
    penalty_gap = 0.016 * 4.0
    utility_gap_without_penalty = float(
        (weights / weights.sum() - sparse_weights / sparse_weights.sum()) @ mu
    )
    assert dense == pytest.approx(
        objective(sparse_weights)
        + penalty_gap
        - utility_gap_without_penalty
        + 0.7
        * (
            cvar_historical(returns @ (weights / weights.sum()), alpha=0.99)
            - cvar_historical(
                returns @ (sparse_weights / sparse_weights.sum()), alpha=0.99
            )
        )
    )


def test_rejects_mismatched_shapes() -> None:
    with pytest.raises(ValueError, match="one entry per asset"):
        PortfolioUtilityObjective(RETURNS, np.zeros(5))
    with pytest.raises(ValueError, match="2-D"):
        PortfolioUtilityObjective(np.zeros(5), np.zeros(5))


def test_params_property_round_trips() -> None:
    params = UtilityParams(lambda_cvar=0.5)
    objective = PortfolioUtilityObjective(RETURNS, MU, params)
    assert objective.params.lambda_cvar == 0.5
