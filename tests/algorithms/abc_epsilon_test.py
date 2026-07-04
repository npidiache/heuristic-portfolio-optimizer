"""Tests for the epsilon-greedy scout variant."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Callable

import numpy as np
import pytest

from hive_abc.algorithms.abc_epsilon import ABCEpsilonScout
from hive_abc.algorithms.base import _ColonyState
from hive_abc.core.types import Bounds


def sphere(x: np.ndarray) -> float:
    """Convex test objective with the global minimum at the origin."""
    return float(np.sum(np.square(x)))


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_epsilon_one_always_restarts(make_state: Callable[..., _ColonyState]) -> None:
    state = make_state([[2.0, 2.0], [0.0, 0.0]])
    state.best_vector = np.array([0.0, 0.0])
    scout_before = state.population[0]

    algo = ABCEpsilonScout(colony_size=2, max_iterations=1, epsilon=1.0)
    algo._scout_move(state, 0)
    assert state.population[0] is not scout_before  # replaced, not moved


def test_epsilon_zero_moves_toward_best(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[2.0, 2.0], [0.0, 0.0]])
    state.best_vector = np.array([0.0, 0.0])
    scout_before = state.population[0]

    algo = ABCEpsilonScout(colony_size=2, max_iterations=1, epsilon=0.0)
    algo._scout_move(state, 0)

    assert state.population[0] is scout_before  # moved in place
    # x_new = x + phi * (best - x) with phi in [0, 1): strictly closer or equal.
    assert float(np.linalg.norm(state.population[0].vector)) <= float(
        np.linalg.norm([2.0, 2.0])
    )


def test_missing_best_falls_back_to_restart(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[2.0, 2.0], [0.0, 0.0]])
    assert state.best_vector.size == 0  # never ran _update_best
    scout_before = state.population[0]

    algo = ABCEpsilonScout(colony_size=2, max_iterations=1, epsilon=0.0)
    algo._scout_move(state, 0)
    assert state.population[0] is not scout_before


@pytest.mark.parametrize("epsilon", [-0.1, 1.1])
def test_rejects_out_of_range_epsilon(epsilon: float) -> None:
    with pytest.raises(ValueError, match="epsilon"):
        ABCEpsilonScout(epsilon=epsilon)


def test_optimizes_sphere() -> None:
    algo = ABCEpsilonScout(colony_size=20, max_iterations=60)
    result = algo.optimize(sphere, Bounds.box(4, -5.0, 5.0), seed=7)
    assert result.best_value < 1e-2
