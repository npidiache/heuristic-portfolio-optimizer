"""Historical tail-risk measures."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
from numpy.typing import NDArray


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def cvar_historical(returns: NDArray[np.float64], alpha: float = 0.05) -> float:
    """
    Historical CVaR with riskfolio-lib's `CVaR_Hist` semantics.

    The thesis objective evaluated CVaR through riskfolio-lib; this native
    implementation replicates that exact estimator so results are unchanged:
    returns are sorted ascending, the VaR index is `ceil(alpha * n) - 1`, and

        CVaR = -VaR - (1 / (alpha * n)) * sum_{i <= index}(r_i - VaR_r)

    Note that the thesis calls this with `alpha = 0.99` (as executed in the
    frozen backtest harness), which averages essentially the whole return
    distribution below its 99th percentile — see
    `docs/thesis/objective_function.md` for the discussion.

    Args:
        returns: One-dimensional array of portfolio returns.
        alpha: Tail probability parameter of the riskfolio estimator.

    Returns:
        The CVaR estimate (positive for losses).

    Raises:
        ValueError: If `returns` is empty or `alpha` is outside (0, 1].
    """
    if returns.size == 0:
        raise ValueError("returns must not be empty")
    if not 0.0 < alpha <= 1.0:
        raise ValueError(f"alpha must be in (0, 1]; got {alpha}")

    sorted_returns = np.sort(returns.flatten())
    n = sorted_returns.size
    index = int(np.ceil(alpha * n) - 1)
    var_return = sorted_returns[index]
    tail_excess = float(np.sum(sorted_returns[: index + 1] - var_return))
    return float(-var_return - tail_excess / (alpha * n))
