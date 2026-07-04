"""Portfolio penalty terms used by the thesis utility function.

The legacy harness contained two cardinality-penalty variants; the one used
by the frozen final runs (`utility_objective_with_cardinality` in
`legacy/test_calibrated_crisis_performance_v2.py`) is the single definition
kept here.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
from numpy.typing import NDArray


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def l1_penalty(weights: NDArray[np.float64]) -> float:
    """
    L1 norm of the weights (the eta-weighted diversification term).

    For a normalized long-only portfolio this equals 1, so the term acts as a
    constant regularizer in the frozen runs; it is kept for fidelity and for
    future short-enabled extensions.

    Args:
        weights: Portfolio weight vector.

    Returns:
        `sum(|w_i|)`.
    """
    return float(np.sum(np.abs(weights)))


def hhi(weights: NDArray[np.float64]) -> float:
    """
    Herfindahl-Hirschman concentration index of a weight vector.

    Args:
        weights: Portfolio weight vector (normalized).

    Returns:
        `sum(w_i^2)` — 1/n for equal weights, 1.0 for a single asset.
    """
    return float(np.sum(np.square(weights)))


def cardinality_penalty(
    weights: NDArray[np.float64],
    target_cardinality: int = 8,
    threshold: float = 0.01,
) -> float:
    """
    Quadratic penalty on the number of significant holdings above a target.

    Args:
        weights: Portfolio weight vector (normalized).
        target_cardinality: Number of significant assets tolerated for free.
        threshold: Minimum weight for an asset to count as significant.

    Returns:
        0 when at most `target_cardinality` weights exceed `threshold`;
        `excess^2` otherwise.
    """
    significant = int(np.sum(weights > threshold))
    if significant <= target_cardinality:
        return 0.0
    return float((significant - target_cardinality) ** 2)
