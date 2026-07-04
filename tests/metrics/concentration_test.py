"""Tests for concentration metrics."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pytest

from hive_abc.metrics.concentration import (
    concentration_hhi,
    effective_cardinality,
    max_weight,
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_effective_cardinality_uses_half_percent_threshold() -> None:
    weights = np.array([0.60, 0.394, 0.005, 0.001])
    assert effective_cardinality(weights) == 2  # strict >0.005


def test_max_weight() -> None:
    assert max_weight(np.array([0.2, 0.5, 0.3])) == pytest.approx(0.5)
    with pytest.raises(ValueError, match="empty"):
        max_weight(np.array([]))


def test_hhi_equal_weights() -> None:
    assert concentration_hhi(np.full(20, 0.05)) == pytest.approx(0.05)
