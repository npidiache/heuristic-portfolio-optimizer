"""Portfolio concentration and cardinality metrics from the thesis tables."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
from numpy.typing import NDArray

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: The thesis counts holdings above 0.5% as "significant" in its tables.
# --------------------------------------------------------------------------------------
SIGNIFICANT_WEIGHT_THRESHOLD = 0.005


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def effective_cardinality(
    weights: NDArray[np.float64],
    threshold: float = SIGNIFICANT_WEIGHT_THRESHOLD,
) -> int:
    """
    Number of holdings whose weight exceeds the significance threshold.

    Args:
        weights: Normalized portfolio weights.
        threshold: Significance cutoff (thesis tables use 0.5%).

    Returns:
        Count of significant holdings.
    """
    return int(np.sum(weights > threshold))


def max_weight(weights: NDArray[np.float64]) -> float:
    """
    Largest single-asset weight.

    Args:
        weights: Normalized portfolio weights.

    Returns:
        `max(w)`.

    Raises:
        ValueError: If `weights` is empty.
    """
    if weights.size == 0:
        raise ValueError("weights must not be empty")
    return float(np.max(weights))


def concentration_hhi(weights: NDArray[np.float64]) -> float:
    """
    Herfindahl-Hirschman index of the portfolio.

    Args:
        weights: Normalized portfolio weights.

    Returns:
        `sum(w_i^2)`.
    """
    return float(np.sum(np.square(weights)))
