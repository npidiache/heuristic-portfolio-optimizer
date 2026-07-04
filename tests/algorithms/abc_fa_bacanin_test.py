"""Tests for the ABC-FA (Tuba & Bacanin) employed-phase hybrid."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math
from collections.abc import Callable

import numpy as np
import pytest

from hive_abc.algorithms.abc_fa_bacanin import ABCFABacanin
from hive_abc.algorithms.base import _ColonyState
from hive_abc.core.types import Bounds


def sphere(x: np.ndarray) -> float:
    """Convex test objective with the global minimum at the origin."""
    return float(np.sum(np.square(x)))


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_firefly_move_updates_every_dimension(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 2.0, 3.0], [-1.0, 0.5, 2.0]])
    algo = ABCFABacanin(colony_size=2, max_iterations=1, alpha=0.5)
    candidate = algo._neighbor_candidate(state, 0, 1)

    assert np.all(candidate != state.population[0].vector)
    assert np.all(candidate >= state.bounds.lower)
    assert np.all(candidate <= state.bounds.upper)


def test_firefly_attraction_scale_matches_formula(
    make_state: Callable[..., _ColonyState],
) -> None:
    # With alpha=0 the move is purely deterministic attraction, so each
    # dimension must land exactly at x_i + b0*exp(-gamma*r^2)*(x_k - x_i).
    state = make_state([[1.0, 1.0], [0.0, 0.0]])
    b0, gamma = 1.1, 1.4
    algo = ABCFABacanin(colony_size=2, max_iterations=1, b0=b0, gamma=gamma, alpha=0.0)
    candidate = algo._neighbor_candidate(state, 0, 1)

    r = math.sqrt(2.0)
    expected = 1.0 + b0 * math.exp(-gamma * r**2) * (0.0 - 1.0)
    assert candidate == pytest.approx([expected, expected])


def test_rejects_negative_gamma() -> None:
    with pytest.raises(ValueError, match="gamma"):
        ABCFABacanin(gamma=-0.1)


def test_optimizes_sphere() -> None:
    algo = ABCFABacanin(colony_size=20, max_iterations=80, alpha=0.2)
    result = algo.optimize(sphere, Bounds.box(3, -5.0, 5.0), seed=11)
    assert result.best_value < 5.0  # FA attraction converges slowly on sphere
    assert result.best_value < sphere(np.full(3, 5.0))
