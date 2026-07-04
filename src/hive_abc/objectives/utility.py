"""The portfolio utility objective actually executed in the thesis backtests.

Committee tasks 4 and 5 are resolved here in code: the *documented* utility
(thesis Eq. 13, written in terms of Sortino/Omega/CVaR/HHI) and the *executed*
fitness (Eq. 18) are related but not identical — the fitness maximized by the
optimizers is

    U(w) = w'mu - lambda_cvar * CVaR_alpha(R w) - eta_l1 * ||w||_1
           - lambda_card * card_penalty(w)

with the exact executed parameter values frozen in `UtilityParams` below.
See `docs/thesis/objective_function.md` for the full Eq. 13 <-> Eq. 18 mapping.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from hive_abc.objectives.penalties import cardinality_penalty, l1_penalty
from hive_abc.objectives.risk import cvar_historical

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
EMPTY_PORTFOLIO_SENTINEL = 1e10
"""Objective value returned when the raw weights sum to (near) zero."""

REFERENCE_UNIVERSE_SIZE = 20
"""Asset count the cardinality weight was calibrated for in the thesis."""


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class UtilityParams:
    """
    Penalty weights of the executed thesis objective (committee task 5).

    The defaults are the values the frozen backtest harness passed for every
    canonical run (`legacy/test_calibrated_crisis_performance_v2.py`,
    `run_backtest_for_period`):

    Attributes:
        lambda_cvar: CVaR aversion (thesis lambda). Executed value: 0.7.
        eta_l1: L1 regularization weight (thesis eta). Executed value: 5e-4.
        lambda_cardinality_base: Cardinality weight calibrated for a
            20-asset universe; the objective scales it by `n / 20`.
            Executed value: 8e-3.
        cvar_alpha: Alpha passed to the riskfolio-style CVaR estimator.
            Executed value: 0.99.
        target_cardinality: Significant holdings tolerated without penalty.
            Executed value: 10 (aligned with ABC-FAEM's elite pool).
        cardinality_threshold: Weight above which a holding counts as
            significant. Executed value: 0.01 (1%).
    """

    lambda_cvar: float = 0.7
    eta_l1: float = 5e-4
    lambda_cardinality_base: float = 8e-3
    cvar_alpha: float = 0.99
    target_cardinality: int = 10
    cardinality_threshold: float = 0.01


class PortfolioUtilityObjective:
    """
    Callable minimization objective over raw (unnormalized) weight vectors.

    Mirrors `utility_objective_with_cardinality` from the frozen harness:
    weights are normalized internally, a near-zero weight sum returns the
    `EMPTY_PORTFOLIO_SENTINEL`, and the returned value is `-U(w)` so that
    minimizers maximize utility.

    Args:
        returns: Daily (log) return matrix, shape (n_days, n_assets).
        mu: Expected daily returns per asset, shape (n_assets,).
        params: Penalty weights; defaults are the frozen executed values.

    Raises:
        ValueError: If `returns` and `mu` disagree on the asset count.
    """

    def __init__(
        self,
        returns: NDArray[np.float64],
        mu: NDArray[np.float64],
        params: UtilityParams | None = None,
    ) -> None:
        returns = np.asarray(returns, dtype=float)
        mu = np.asarray(mu, dtype=float)
        if returns.ndim != 2:
            raise ValueError(f"returns must be 2-D; got shape {returns.shape}")
        if mu.ndim != 1 or mu.shape[0] != returns.shape[1]:
            raise ValueError(
                f"mu must have one entry per asset; got {mu.shape[0]} for "
                f"{returns.shape[1]} assets"
            )
        self._returns = returns
        self._mu = mu
        self._params = params if params is not None else UtilityParams()
        # The thesis calibrated the cardinality weight on 20 assets and scaled
        # it linearly with the universe size (0.008 * n / 20 in the harness).
        self._lambda_cardinality = self._params.lambda_cardinality_base * (
            mu.shape[0] / REFERENCE_UNIVERSE_SIZE
        )

    @property
    def params(self) -> UtilityParams:
        """The penalty configuration in force."""
        return self._params

    def __call__(self, weights: NDArray[np.float64]) -> float:
        """
        Evaluates `-U(w)` for a raw candidate vector.

        Args:
            weights: Raw weight vector from an optimizer (not normalized).

        Returns:
            Negative utility, or `EMPTY_PORTFOLIO_SENTINEL` when the raw
            weights sum to less than 1e-9.
        """
        weights = np.asarray(weights, dtype=float)
        total = float(np.sum(weights))
        if total <= 1e-9:
            return EMPTY_PORTFOLIO_SENTINEL
        normalized = weights / total

        portfolio_return = float(np.dot(normalized, self._mu))
        portfolio_returns = self._returns @ normalized
        cvar = cvar_historical(portfolio_returns, alpha=self._params.cvar_alpha)
        utility = (
            portfolio_return
            - self._params.lambda_cvar * cvar
            - self._params.eta_l1 * l1_penalty(normalized)
            - self._lambda_cardinality
            * cardinality_penalty(
                normalized,
                target_cardinality=self._params.target_cardinality,
                threshold=self._params.cardinality_threshold,
            )
        )
        return float(-utility)
