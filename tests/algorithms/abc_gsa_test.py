"""Tests for ABC-GSA: gravitational scout phase."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Callable

import numpy as np
import pytest

from hive_abc.algorithms.abc_gsa import ABCGSA
from hive_abc.algorithms.base import _ColonyState
from hive_abc.core.types import Bounds


def sphere(x: np.ndarray) -> float:
    """Convex test objective with the global minimum at the origin."""
    return float(np.sum(np.square(x)))


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_two_bee_net_force_matches_hand_computation(
    make_state: Callable[..., _ColonyState],
) -> None:
    # Scout at (3, 4), other bee at origin: distance 5, direction (-0.6, -0.8).
    state = make_state([[3.0, 4.0], [0.0, 0.0]])
    g, epsilon = 0.5, 1e-10
    algo = ABCGSA(colony_size=2, max_iterations=1, g_constant=g, epsilon=epsilon)
    force = algo._net_gravitational_force(state, 0)

    mass_scout = state.population[0].fitness  # 1 / (1 + 25)
    mass_other = state.population[1].fitness  # 1 / (1 + 0)
    magnitude = g * mass_scout * mass_other / (25.0 + epsilon)
    expected = magnitude * np.array([-0.6, -0.8])
    assert force == pytest.approx(expected)


def test_scout_moves_along_unit_force_plus_noise(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[3.0, 4.0], [0.0, 0.0]])
    algo = ABCGSA(colony_size=2, max_iterations=1, g_constant=0.5, alpha=0.0)
    algo._scout_move(state, 0)

    # With alpha=0 the move is exactly one unit step toward the origin.
    expected = np.array([3.0, 4.0]) + np.array([-0.6, -0.8])
    assert state.population[0].vector == pytest.approx(expected)
    assert state.n_evaluations == 1


def test_coincident_bees_produce_zero_force_random_walk(
    make_state: Callable[..., _ColonyState],
) -> None:
    # All bees at the same point: every pairwise distance is below epsilon,
    # so the net force is zero and only the random component moves the scout.
    state = make_state([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]])
    algo = ABCGSA(colony_size=3, max_iterations=1, epsilon=1e-6, alpha=0.5)
    algo._scout_move(state, 0)

    displacement = state.population[0].vector - np.array([1.0, 1.0])
    assert np.all(np.abs(displacement) <= 0.25)  # alpha/2 bound


def test_rejects_non_positive_epsilon() -> None:
    with pytest.raises(ValueError, match="epsilon"):
        ABCGSA(epsilon=0.0)


def test_optimizes_sphere() -> None:
    algo = ABCGSA(colony_size=20, max_iterations=60, g_constant=0.3, alpha=0.05)
    result = algo.optimize(sphere, Bounds.box(4, -5.0, 5.0), seed=7)
    assert result.best_value < 1e-2
