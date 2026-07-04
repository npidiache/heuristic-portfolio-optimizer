"""Heuristic portfolio optimizer — ABC variants for portfolio selection.

Formalizes the Master in Finance thesis "Optimización de portafolios mediante
variantes del algoritmo Artificial Bee Colony" (Pidiache, 2026). The public
API re-exports the optimizer family, the portfolio objective, and the metric
suite; import from this package root, never from submodules.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.algorithms import (
    ABCFAEM,
    ABCGSA,
    ABCEpsilonScout,
    ABCFABacanin,
    ABCOriginal,
    BeeHive,
)
from hive_abc.benchmarks import EqualWeight, MinVarianceCVX
from hive_abc.core import Bounds, HeuristicOptimizer, ObjectiveFn, OptimizationResult
from hive_abc.objectives import PortfolioUtilityObjective, UtilityParams

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
__version__ = "1.0.0"

__all__ = [
    "ABCEpsilonScout",
    "ABCFABacanin",
    "ABCFAEM",
    "ABCGSA",
    "ABCOriginal",
    "BeeHive",
    "Bounds",
    "EqualWeight",
    "HeuristicOptimizer",
    "MinVarianceCVX",
    "ObjectiveFn",
    "OptimizationResult",
    "PortfolioUtilityObjective",
    "UtilityParams",
    "__version__",
]
