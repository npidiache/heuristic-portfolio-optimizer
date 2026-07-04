"""Abstract optimizer interface implemented by every algorithm in the package."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from abc import ABC, abstractmethod

from hive_abc.core.types import Bounds, ObjectiveFn, OptimizationResult


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class HeuristicOptimizer(ABC):
    """
    Contract for box-constrained minimizers.

    Concrete algorithms are configured through their constructors and remain
    stateless across calls: `optimize` may be invoked repeatedly (e.g., once
    per seed) without leaking state between runs. This interface is the v2
    seam — future metaheuristics (PSO, GA) plug in here without touching the
    portfolio or backtest layers.
    """

    @abstractmethod
    def optimize(
        self,
        objective: ObjectiveFn,
        bounds: Bounds,
        *,
        seed: int | None = None,
    ) -> OptimizationResult:
        """
        Minimizes `objective` over the box defined by `bounds`.

        Args:
            objective: Function to minimize; receives a raw candidate vector.
            bounds: Box constraints for every dimension.
            seed: Seed for the run's random generator. `None` draws entropy
                from the OS, making the run non-reproducible.

        Returns:
            The best solution found and its run diagnostics.
        """
