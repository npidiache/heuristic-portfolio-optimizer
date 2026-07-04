"""Tests for the optimizer value types."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pytest

from hive_abc.core.types import Bounds


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_box_builds_uniform_bounds() -> None:
    bounds = Bounds.box(3, low=-1.0, high=2.0)
    assert bounds.dim == 3
    assert np.array_equal(bounds.lower, np.full(3, -1.0))
    assert np.array_equal(bounds.upper, np.full(3, 2.0))


def test_box_rejects_non_positive_dimension() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        Bounds.box(0)


def test_bounds_reject_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="same shape"):
        Bounds(lower=np.zeros(2), upper=np.ones(3))


def test_bounds_reject_multidimensional_arrays() -> None:
    with pytest.raises(ValueError, match="one-dimensional"):
        Bounds(lower=np.zeros((2, 2)), upper=np.ones((2, 2)))


def test_bounds_reject_inverted_interval() -> None:
    with pytest.raises(ValueError, match="lower bound"):
        Bounds(lower=np.array([0.0, 1.0]), upper=np.array([1.0, 0.5]))
