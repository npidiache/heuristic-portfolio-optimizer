"""Performance metrics replicating the quantstats estimators the thesis used.

The frozen harness computed every reported metric through quantstats
(`qs.stats.sortino/max_drawdown/omega/greeks`). These native implementations
replicate those exact estimators — the `parity`-marked tests compare them
against quantstats to lock the formulas.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math

import numpy as np
from numpy.typing import NDArray

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
TRADING_DAYS_PER_YEAR = 252


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def sortino_ratio(
    returns: NDArray[np.float64], periods: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Annualized Sortino ratio with quantstats semantics.

    Downside deviation divides the squared negative returns by the FULL
    sample length (not just the count of negative days), matching
    `qs.stats.sortino(returns, annualize=True)`.

    Args:
        returns: Daily portfolio returns.
        periods: Annualization factor.

    Returns:
        `mean(r) / sqrt(mean(min(r, 0)^2)) * sqrt(periods)`; NaN when the
        downside deviation is zero.

    Raises:
        ValueError: If `returns` is empty.
    """
    if returns.size == 0:
        raise ValueError("returns must not be empty")
    downside = math.sqrt(float(np.mean(np.square(np.minimum(returns, 0.0)))))
    if downside == 0:
        return float("nan")
    return float(np.mean(returns) / downside * math.sqrt(periods))


def max_drawdown(returns: NDArray[np.float64]) -> float:
    """
    Maximum drawdown of the compounded return path.

    Args:
        returns: Daily portfolio returns.

    Returns:
        The minimum of `wealth / running_max - 1` (a non-positive number).

    Raises:
        ValueError: If `returns` is empty.
    """
    if returns.size == 0:
        raise ValueError("returns must not be empty")
    wealth = np.cumprod(1.0 + returns)
    running_max = np.maximum.accumulate(np.maximum(wealth, 1.0e-12))
    # quantstats compounds from an initial price point, so the running max
    # never drops below the starting capital (1.0).
    running_max = np.maximum(running_max, 1.0)
    return float(np.min(wealth / running_max - 1.0))


def omega_ratio(returns: NDArray[np.float64], required_return: float = 0.0) -> float:
    """
    Omega ratio versus a required threshold, as in `qs.stats.omega`.

    Args:
        returns: Daily portfolio returns.
        required_return: Daily return threshold (0 in every thesis run).

    Returns:
        Sum of gains above the threshold divided by the absolute sum of
        shortfalls below it; NaN when there are no shortfalls.

    Raises:
        ValueError: If `returns` is empty.
    """
    if returns.size == 0:
        raise ValueError("returns must not be empty")
    excess = returns - required_return
    gains = float(excess[excess > 0].sum())
    losses = float(-excess[excess < 0].sum())
    if losses == 0:
        return float("nan")
    return gains / losses


def jensen_alpha(
    returns: NDArray[np.float64],
    benchmark_returns: NDArray[np.float64],
    periods: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """
    Annualized Jensen alpha versus a benchmark, as in `qs.stats.greeks`.

    Beta is the OLS slope of portfolio on benchmark returns; alpha is the
    daily intercept scaled by `periods`. The thesis benchmark is the NASDAQ
    Composite (^IXIC) in daily log returns.

    Args:
        returns: Daily portfolio returns.
        benchmark_returns: Benchmark returns aligned to the same dates.
        periods: Annualization factor.

    Returns:
        Annualized Jensen alpha.

    Raises:
        ValueError: If the series lengths differ or have fewer than 2 points.
    """
    if returns.shape != benchmark_returns.shape:
        raise ValueError(
            f"returns and benchmark must align; got {returns.shape} vs "
            f"{benchmark_returns.shape}"
        )
    if returns.size < 2:
        raise ValueError("need at least 2 observations for beta")
    matrix = np.cov(returns, benchmark_returns, ddof=1)
    benchmark_variance = matrix[1, 1]
    if benchmark_variance == 0:
        return float("nan")
    beta = matrix[0, 1] / benchmark_variance
    alpha_daily = float(np.mean(returns) - beta * np.mean(benchmark_returns))
    return alpha_daily * periods
