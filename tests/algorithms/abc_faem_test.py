"""Tests for ABC-FAEM: softmax elite scout with the PFA trigger."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Callable

import numpy as np
import pytest

from hive_abc.algorithms.abc_faem import ABCFAEM
from hive_abc.algorithms.base import _ColonyState
from hive_abc.core.types import Bounds


def sphere(x: np.ndarray) -> float:
    """Convex test objective with the global minimum at the origin."""
    return float(np.sum(np.square(x)))


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_fa_move_pulls_scout_toward_elite(
    make_state: Callable[..., _ColonyState],
) -> None:
    # Bee 1 sits at the optimum (fitness 1.0); bee 0 is stalled far away.
    state = make_state([[4.0, 4.0], [0.0, 0.0], [3.0, -3.0]])
    algo = ABCFAEM(
        colony_size=4, max_iterations=1, b0=1.0, gamma=0.01, alpha=0.0, k_top=1
    )
    distance_before = float(np.linalg.norm(state.population[0].vector))
    algo._scout_move(state, 0)
    distance_after = float(np.linalg.norm(state.population[0].vector))

    assert distance_after < distance_before
    assert state.n_evaluations == 1  # scout was re-evaluated


def test_p_fa_zero_always_restarts(make_state: Callable[..., _ColonyState]) -> None:
    state = make_state([[4.0, 4.0], [0.0, 0.0]])
    algo = ABCFAEM(colony_size=2, max_iterations=1, p_fa=0.0)
    algo._scout_move(state, 0)

    # A restart draws a fresh random bee: with p_fa=0 the FA move never fires,
    # so the replacement is a brand-new _Bee object with counter 0.
    assert state.population[0].counter == 0
    assert state.n_evaluations == 1


def test_p_fa_one_reproduces_frozen_behavior(
    make_state: Callable[..., _ColonyState],
) -> None:
    # The frozen thesis code fired the FA scout unconditionally; p_fa=1.0 must
    # never fall back to a random restart regardless of the RNG stream.
    for seed in range(5):
        state = make_state([[4.0, 4.0], [0.0, 0.0]], seed=seed)
        scout_before = state.population[0]
        algo = ABCFAEM(colony_size=2, max_iterations=1, p_fa=1.0, alpha=0.0, k_top=1)
        algo._scout_move(state, 0)
        # The FA move mutates the existing bee in place; a restart would have
        # replaced the object.
        assert state.population[0] is scout_before


def test_softmax_prefers_fitter_elites(
    make_state: Callable[..., _ColonyState],
) -> None:
    # With a tiny temperature the softmax collapses onto the single best bee.
    state = make_state([[4.0, 4.0], [0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
    algo = ABCFAEM(colony_size=4, max_iterations=1, k_top=3, softmax_tau=1e-6)
    target = algo._select_elite_target(state)
    assert np.array_equal(target, np.array([0.0, 0.0]))


def test_k_top_larger_than_population_is_clamped(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [2.0, 2.0]])
    algo = ABCFAEM(colony_size=2, max_iterations=1, k_top=50)
    target = algo._select_elite_target(state)
    assert target.shape == (2,)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"k_top": 0}, "k_top"),
        ({"softmax_tau": 0.0}, "softmax_tau"),
        ({"p_fa": 1.5}, "p_fa"),
        ({"p_fa": -0.1}, "p_fa"),
    ],
)
def test_constructor_validation(kwargs: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ABCFAEM(**kwargs)  # type: ignore[arg-type]


def test_optimizes_sphere() -> None:
    algo = ABCFAEM(colony_size=20, max_iterations=60)
    result = algo.optimize(sphere, Bounds.box(4, -5.0, 5.0), seed=7)
    assert result.best_value < 1e-2
