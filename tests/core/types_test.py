"""Tests for the optimizer value types."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pytest

from hive_abc.core.types import Bounds, OptimizationResult


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


def test_optimization_result_scout_telemetry_defaults() -> None:
    # The pre-telemetry 7-keyword construction (all existing call sites) must
    # keep working and yield inert scout telemetry.
    result = OptimizationResult(
        best_vector=np.zeros(2),
        best_value=0.0,
        best_per_iteration=(1.0, 0.0),
        mean_per_iteration=(2.0, 1.0),
        n_evaluations=10,
        runtime_seconds=0.5,
        seed=7,
    )
    assert result.scout_activations == 0
    assert result.scout_activation_iterations == ()


def test_optimization_result_scout_telemetry_explicit() -> None:
    result = OptimizationResult(
        best_vector=np.zeros(2),
        best_value=0.0,
        best_per_iteration=(1.0, 0.0),
        mean_per_iteration=(2.0, 1.0),
        n_evaluations=10,
        runtime_seconds=0.5,
        seed=7,
        scout_activations=2,
        scout_activation_iterations=(3, 8),
    )
    assert result.scout_activations == 2
    assert result.scout_activation_iterations == (3, 8)
