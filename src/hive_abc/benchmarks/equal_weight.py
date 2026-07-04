"""Naive 1/N benchmark."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import time

import numpy as np

from hive_abc.core.optimizer import HeuristicOptimizer
from hive_abc.core.types import Bounds, ObjectiveFn, OptimizationResult


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class EqualWeight(HeuristicOptimizer):
    """
    Equally weighted (1/N) portfolio — the thesis's naive benchmark.

    Ignores the search entirely and returns `1/n` per asset, evaluated with
    the shared objective for comparability.
    """

    def optimize(
        self,
        objective: ObjectiveFn,
        bounds: Bounds,
        *,
        seed: int | None = None,
    ) -> OptimizationResult:
        """
        Returns the 1/N portfolio for the given dimensionality.

        Args:
            objective: Evaluated once on the equal weights.
            bounds: Only `bounds.dim` is used.
            seed: Ignored (deterministic); recorded in the result.

        Returns:
            The equal-weight vector and its objective value.
        """
        start = time.perf_counter()
        weights = np.full(bounds.dim, 1.0 / bounds.dim)
        value = float(objective(weights))
        return OptimizationResult(
            best_vector=weights,
            best_value=value,
            best_per_iteration=(value,),
            mean_per_iteration=(value,),
            n_evaluations=1,
            runtime_seconds=time.perf_counter() - start,
            seed=seed,
        )
