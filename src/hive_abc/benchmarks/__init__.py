"""Deterministic benchmark portfolios the thesis compares the ABC family to."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.benchmarks.equal_weight import EqualWeight
from hive_abc.benchmarks.min_variance import MinVarianceCVX

__all__ = ["EqualWeight", "MinVarianceCVX"]
