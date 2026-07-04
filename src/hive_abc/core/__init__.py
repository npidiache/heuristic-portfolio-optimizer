"""Problem-agnostic optimizer contract — the seam for future metaheuristics.

Every optimizer in this package (the ABC family today; PSO/GA on the v2
roadmap) implements `HeuristicOptimizer.optimize` over a box-constrained
search space, so portfolio code never depends on a concrete algorithm.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.core.optimizer import HeuristicOptimizer
from hive_abc.core.types import Bounds, ObjectiveFn, OptimizationResult

__all__ = ["Bounds", "HeuristicOptimizer", "ObjectiveFn", "OptimizationResult"]
