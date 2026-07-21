"""Tests for ABCAdaptiveScout: the pluggable-scout optimizer (v2 lab)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections import Counter
from collections.abc import Callable

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hive_abc.algorithms.abc_adaptive import ABCAdaptiveScout
from hive_abc.algorithms.base import BeeHive, _ColonyState
from hive_abc.algorithms.scouting import ProportionalTrialLimit, RandomRestart
from hive_abc.core.types import Bounds


def sphere(x: np.ndarray) -> float:
    """Convex test objective with the global minimum at the origin."""
    return float(np.sum(np.square(x)))


def rastrigin(x: np.ndarray) -> float:
    """Multimodal benchmark whose local minima keep bees stagnating."""
    return float(10.0 * x.size + np.sum(np.square(x) - 10.0 * np.cos(2.0 * np.pi * x)))


class _VectorOnlyMove:
    """Move that edits the vector without evaluating (contract stress-test)."""

    def relocate(self, state: _ColonyState, index: int) -> None:
        """Teleports the bee to the origin, leaving `value` stale."""
        state.population[index].vector = np.zeros(state.bounds.dim)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_rejects_non_positive_max_scouts() -> None:
    with pytest.raises(ValueError, match="max_scouts_per_iteration"):
        ABCAdaptiveScout(max_scouts_per_iteration=0)


def test_rejects_objects_without_the_policy_interface() -> None:
    with pytest.raises(TypeError, match="trigger"):
        ABCAdaptiveScout(trigger="not a trigger")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="scout_move"):
        ABCAdaptiveScout(scout_move=42)  # type: ignore[arg-type]


def test_scouts_activate_at_thesis_scale() -> None:
    # The anti-dormancy acceptance test: at the exact scale where the v1
    # scout never fires (see base_test), the default policies must fire.
    # Rastrigin stands in for the rugged portfolio utility surface — on a
    # smooth convex objective the counters hover right at the default limit
    # (int(0.25 * 60) = 15), whereas stagnation-prone landscapes cross it.
    algo = ABCAdaptiveScout(colony_size=25, max_iterations=60)
    result = algo.optimize(rastrigin, Bounds.box(20, -5.12, 5.12), seed=7)

    assert result.scout_activations > 0
    assert len(result.scout_activation_iterations) == result.scout_activations


def test_optimizes_sphere() -> None:
    algo = ABCAdaptiveScout(colony_size=20, max_iterations=60)
    result = algo.optimize(sphere, Bounds.box(4, -5.0, 5.0), seed=7)
    assert result.best_value < 1e-2


def test_opt_out_path_reproduces_beehive_byte_for_byte() -> None:
    # A trigger that can never fire draws no scout-path RNG, and disabling
    # the roulette refresh restores v1's frozen-at-init probabilities, so
    # both optimizers must consume identical RNG streams end to end.
    bounds = Bounds.box(4, -5.0, 5.0)
    baseline = BeeHive(colony_size=10, max_iterations=25, max_trials=10_000)
    adaptive = ABCAdaptiveScout(
        trigger=ProportionalTrialLimit(fraction=10.0),
        refresh_onlooker_probabilities=False,
        colony_size=10,
        max_iterations=25,
        max_trials=10_000,
    )

    expected = baseline.optimize(sphere, bounds, seed=11)
    result = adaptive.optimize(sphere, bounds, seed=11)

    assert result.best_value == expected.best_value
    assert np.array_equal(result.best_vector, expected.best_vector)
    assert result.best_per_iteration == expected.best_per_iteration
    assert result.mean_per_iteration == expected.mean_per_iteration
    assert result.n_evaluations == expected.n_evaluations
    assert result.scout_activations == 0
    assert expected.scout_activations == 0


def test_multi_scout_replaces_several_bees_in_one_iteration() -> None:
    algo = ABCAdaptiveScout(
        trigger=ProportionalTrialLimit(fraction=1e-9),  # limit floors at 1
        scout_move=RandomRestart(),
        max_scouts_per_iteration=3,
        colony_size=6,
        max_iterations=20,
    )
    result = algo.optimize(sphere, Bounds.box(3, -5.0, 5.0), seed=7)

    # Telemetry counts each relocated bee as one activation, so an iteration
    # with several scouts appears several times in the iteration trace.
    per_iteration = Counter(result.scout_activation_iterations)
    assert result.scout_activations == len(result.scout_activation_iterations)
    assert max(per_iteration.values()) > 1


def test_scout_phase_ignores_max_trials_and_reevaluates_stale_moves(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [2.0, 2.0]])
    state.population[1].counter = 50
    algo = ABCAdaptiveScout(
        trigger=ProportionalTrialLimit(fraction=0.25),
        scout_move=_VectorOnlyMove(),
        colony_size=2,
        max_iterations=60,
    )

    # max_trials is deliberately huge: the trigger owns the decision, so the
    # counter-derived argument from the base loop must be ignored.
    relocated = algo._scout_phase(state, max_trials=10_000, iteration=0)

    assert relocated == 1
    assert state.population[1].value == 0.0  # re-evaluated at the new vector
    assert state.population[1].counter == 0
    assert state.n_evaluations == 1


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
def test_best_vector_always_within_bounds(seed: int) -> None:
    algo = ABCAdaptiveScout(colony_size=6, max_iterations=5)
    bounds = Bounds.box(3, -2.0, 2.0)
    result = algo.optimize(sphere, bounds, seed=seed)
    assert np.all(result.best_vector >= bounds.lower)
    assert np.all(result.best_vector <= bounds.upper)
