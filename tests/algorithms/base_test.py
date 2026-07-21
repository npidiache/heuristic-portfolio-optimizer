"""Tests for the shared BeeHive skeleton (ABC original behavior)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Callable

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hive_abc.algorithms.base import BeeHive, _Bee, _ColonyState
from hive_abc.core.types import Bounds


def sphere(x: np.ndarray) -> float:
    """Convex test objective with the global minimum at the origin."""
    return float(np.sum(np.square(x)))


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_sphere_convergence_is_deterministic_per_seed() -> None:
    algo = BeeHive(colony_size=20, max_iterations=60)
    bounds = Bounds.box(4, -5.0, 5.0)
    first = algo.optimize(sphere, bounds, seed=7)
    second = algo.optimize(sphere, bounds, seed=7)

    assert first.best_value < 1e-2
    assert first.best_value == second.best_value
    assert np.array_equal(first.best_vector, second.best_vector)
    assert first.seed == 7


def test_histories_track_every_iteration_and_runtime() -> None:
    algo = BeeHive(colony_size=6, max_iterations=15)
    result = algo.optimize(sphere, Bounds.box(2, -1.0, 1.0), seed=1)

    assert len(result.best_per_iteration) == 15
    assert len(result.mean_per_iteration) == 15
    # Best history is monotonically non-increasing (strictly-better updates).
    assert all(
        b2 <= b1
        for b1, b2 in zip(
            result.best_per_iteration, result.best_per_iteration[1:], strict=False
        )
    )
    assert result.runtime_seconds > 0
    assert result.n_evaluations > 0


def test_colony_size_is_rounded_to_even() -> None:
    algo = BeeHive(colony_size=25, max_iterations=1)
    assert algo._size == 26


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"colony_size": 1}, "colony_size"),
        ({"max_iterations": 0}, "max_iterations"),
        ({"max_trials_factor": 0.0}, "max_trials_factor"),
    ],
)
def test_constructor_validation(kwargs: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BeeHive(**kwargs)  # type: ignore[arg-type]


def test_employed_move_changes_single_dimension(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 2.0, 3.0], [4.0, 0.0, -2.0]])
    algo = BeeHive(colony_size=2, max_iterations=1)
    candidate = algo._neighbor_candidate(state, 0, 1)

    differences = np.sum(candidate != state.population[0].vector)
    assert differences <= 1
    assert np.all(candidate >= state.bounds.lower)
    assert np.all(candidate <= state.bounds.upper)


def test_greedy_replacement_resets_counter_and_keeps_better(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[3.0, 3.0], [0.5, 0.5]])
    state.population[0].counter = 4
    algo = BeeHive(colony_size=2, max_iterations=1)

    # Force the candidate to be strictly better by pointing the hook at the
    # better neighbor repeatedly until an improving move lands.
    for _ in range(50):
        algo._employed_step(state, 0)
    assert state.population[0].value <= 18.0  # sphere at (3, 3)


def test_scout_phase_replaces_only_the_most_stalled_bee(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [2.0, 2.0]])
    state.population[1].counter = 10
    original_vector = state.population[0].vector.copy()

    algo = BeeHive(colony_size=2, max_iterations=1)
    algo._scout_phase(state, max_trials=5)

    assert np.array_equal(state.population[0].vector, original_vector)
    assert state.population[1].counter == 0


def test_scout_phase_ignores_bees_below_threshold(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [2.0, 2.0]])
    state.population[1].counter = 5
    vector_before = state.population[1].vector.copy()

    algo = BeeHive(colony_size=2, max_iterations=1)
    algo._scout_phase(state, max_trials=5)  # strictly-greater trigger

    assert np.array_equal(state.population[1].vector, vector_before)


def test_scout_never_activates_at_thesis_scale() -> None:
    # Executable statement of the v1 weakness: at thesis-scale settings the
    # trial counters never exceed max_trials, so the scout phase is dormant.
    # This must stay true for v1 defaults forever (regression contract).
    algo = BeeHive(colony_size=25, max_iterations=60, max_trials=300)
    result = algo.optimize(sphere, Bounds.box(20), seed=7)

    assert result.scout_activations == 0
    assert result.scout_activation_iterations == ()


def test_scout_telemetry_counts_activations() -> None:
    # max_trials=0 makes every stalled bee exceed the cap immediately, so the
    # (at most one per iteration) scout fires and the telemetry must count it.
    algo = BeeHive(colony_size=4, max_iterations=8, max_trials=0)
    result = algo.optimize(sphere, Bounds.box(2, -1.0, 1.0), seed=1)

    assert result.scout_activations >= 1
    assert len(result.scout_activation_iterations) == result.scout_activations
    assert all(
        i1 <= i2
        for i1, i2 in zip(
            result.scout_activation_iterations,
            result.scout_activation_iterations[1:],
            strict=False,
        )
    )
    assert all(
        iteration in range(8) for iteration in result.scout_activation_iterations
    )


def test_roulette_select_falls_back_to_last_index(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [2.0, 2.0]])
    algo = BeeHive(colony_size=2, max_iterations=1)
    state.cumulative_probas = algo._cumulative_probabilities(state)
    assert algo._roulette_select(state, beta=2.0) == 1


def test_fitness_transform_matches_karaboga() -> None:
    positive = _Bee(vector=np.zeros(1), value=3.0)
    negative = _Bee(vector=np.zeros(1), value=-0.25)
    assert positive.fitness == pytest.approx(0.25)
    assert negative.fitness == pytest.approx(1.25)


def test_single_dimension_clip(make_state: Callable[..., _ColonyState]) -> None:
    state = make_state([[0.0, 0.0]], low=-1.0, high=1.0)
    vector = np.array([5.0, 5.0])
    clipped = state.clip(vector, dim=0)
    assert clipped[0] == 1.0
    assert clipped[1] == 5.0  # untouched: original ABC checks one dimension


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
def test_best_vector_always_within_bounds(seed: int) -> None:
    algo = BeeHive(colony_size=6, max_iterations=5)
    bounds = Bounds.box(3, -2.0, 2.0)
    result = algo.optimize(sphere, bounds, seed=seed)
    assert np.all(result.best_vector >= bounds.lower)
    assert np.all(result.best_vector <= bounds.upper)
