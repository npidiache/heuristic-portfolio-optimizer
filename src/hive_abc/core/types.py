"""Shared value types for the optimizer contract."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
ObjectiveFn = Callable[[NDArray[np.float64]], float]
"""Objective to MINIMIZE: maps a candidate vector to a scalar cost."""


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Bounds:
    """
    Box constraints for a search space.

    Attributes:
        lower: Per-dimension lower bounds.
        upper: Per-dimension upper bounds.
    """

    lower: NDArray[np.float64]
    upper: NDArray[np.float64]

    def __post_init__(self) -> None:
        """
        Validates shape agreement and ordering.

        Raises:
            ValueError: If the arrays differ in shape, are not 1-D, or any
                lower bound exceeds its upper bound.
        """
        if self.lower.ndim != 1 or self.upper.ndim != 1:
            raise ValueError("Bounds arrays must be one-dimensional")
        if self.lower.shape != self.upper.shape:
            raise ValueError(
                f"lower and upper must have the same shape; got "
                f"{self.lower.shape} and {self.upper.shape}"
            )
        if bool(np.any(self.lower > self.upper)):
            raise ValueError("Every lower bound must be <= its upper bound")

    @classmethod
    def box(cls, n: int, low: float = 0.0, high: float = 1.0) -> "Bounds":
        """
        Builds uniform box bounds, the long-only portfolio default.

        Args:
            n: Number of dimensions (assets).
            low: Lower bound applied to every dimension.
            high: Upper bound applied to every dimension.

        Returns:
            Bounds with `n` copies of `[low, high]`.

        Raises:
            ValueError: If `n` is not positive or `low > high`.
        """
        if n <= 0:
            raise ValueError(f"n must be positive; got {n}")
        return cls(lower=np.full(n, low), upper=np.full(n, high))

    @property
    def dim(self) -> int:
        """Number of dimensions in the search space."""
        return int(self.lower.shape[0])


@dataclass(frozen=True)
class OptimizationResult:
    """
    Outcome of a single optimizer run.

    Attributes:
        best_vector: The best candidate found (raw, not normalized).
        best_value: Objective value of `best_vector` (minimization).
        best_per_iteration: Best objective value after each iteration.
        mean_per_iteration: Population mean objective value per iteration.
        n_evaluations: Total objective-function evaluations performed.
        runtime_seconds: Wall-clock duration of the run (committee task 14).
        seed: Seed the run was started with, if any.
    """

    best_vector: NDArray[np.float64]
    best_value: float
    best_per_iteration: tuple[float, ...]
    mean_per_iteration: tuple[float, ...]
    n_evaluations: int
    runtime_seconds: float
    seed: int | None
