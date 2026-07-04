"""Heuristic portfolio optimizer — ABC variants for portfolio selection.

Formalizes the Master in Finance thesis "Optimización de portafolios mediante
variantes del algoritmo Artificial Bee Colony" (Pidiache, 2026). The public
API re-exports the optimizer family, the portfolio objective, and the backtest
entry point; import from this package root, never from submodules.
"""

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
__version__ = "1.0.0"

__all__ = ["__version__"]
