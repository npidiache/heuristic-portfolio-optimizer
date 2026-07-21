"""Tests for the pluggable scout policies (triggers and moves)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math
from collections.abc import Callable

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hive_abc.algorithms.base import _ColonyState
from hive_abc.algorithms.scouting import (
    CorrectedFireflyElite,
    DirichletEliteRestart,
    DiversityCollapseTrigger,
    LevyFlightFromBest,
    ProportionalTrialLimit,
    RandomRestart,
    ScoutMove,
)
from hive_abc.core.types import Bounds


def sphere(x: np.ndarray) -> float:
    """Convex test objective with the global minimum at the origin."""
    return float(np.sum(np.square(x)))


def _seeded_state(seed: int, dim: int = 20) -> _ColonyState:
    """Builds a random unit-box colony with `best_vector` populated."""
    state = _ColonyState(
        objective=sphere,
        bounds=Bounds.box(dim),
        rng=np.random.default_rng(seed),
    )
    state.population = [state.random_bee() for _ in range(6)]
    best = min(state.population, key=lambda bee: bee.value)
    state.best_vector = best.vector.copy()
    state.best_value = best.value
    return state


# --------------------------------------------------------------------------------------
# Functions
# - Note1: `make_state` (tests/algorithms/conftest.py) seeds every state RNG with
#   `np.random.default_rng`, so all policy behavior below is reproducible.
# --------------------------------------------------------------------------------------
def test_proportional_limit_selects_worst_first_with_strict_semantics(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]])
    for bee, counter in zip(state.population, [16, 10, 20, 15], strict=True):
        bee.counter = counter
    trigger = ProportionalTrialLimit(fraction=0.25)

    selected = trigger.select_scouts(
        state, iteration=0, max_iterations=60, max_scouts=4
    )

    # limit = int(0.25 * 60) = 15: counters 20 and 16 exceed it (worst first);
    # 15 is excluded by the strict `>` and 10 is far below.
    assert selected == (2, 0)


def test_proportional_limit_caps_selection_at_max_scouts(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    for bee, counter in zip(state.population, [16, 10, 20], strict=True):
        bee.counter = counter
    trigger = ProportionalTrialLimit(fraction=0.25)

    selected = trigger.select_scouts(
        state, iteration=0, max_iterations=60, max_scouts=1
    )
    assert selected == (2,)


def test_proportional_limit_floors_the_limit_at_one_trial(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [2.0, 2.0]])
    state.population[0].counter = 2
    state.population[1].counter = 1
    trigger = ProportionalTrialLimit(fraction=1e-9)

    selected = trigger.select_scouts(
        state, iteration=0, max_iterations=60, max_scouts=2
    )

    # A vanishing fraction still yields limit 1: counter 2 scouts, 1 does not.
    assert selected == (0,)


@pytest.mark.parametrize("fraction", [0.0, -0.25])
def test_proportional_limit_rejects_non_positive_fraction(fraction: float) -> None:
    with pytest.raises(ValueError, match="fraction"):
        ProportionalTrialLimit(fraction=fraction)


def test_diversity_collapse_fires_on_clustered_population_worst_first(
    make_state: Callable[..., _ColonyState],
) -> None:
    positions = [[1.0, 1.0], [1.001, 1.001], [0.999, 0.999], [1.002, 1.002]]
    state = make_state(positions)
    trigger = DiversityCollapseTrigger(threshold=0.05, cooldown=5)

    selected = trigger.select_scouts(
        state, iteration=0, max_iterations=60, max_scouts=2
    )

    # The two worst-fitness bees (largest sphere values) leave first.
    assert selected == (3, 1)


def test_diversity_collapse_ignores_spread_population(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[4.0, 4.0], [-4.0, -4.0], [4.0, -4.0], [-4.0, 4.0]])
    trigger = DiversityCollapseTrigger(threshold=0.05, cooldown=5)

    selected = trigger.select_scouts(
        state, iteration=0, max_iterations=60, max_scouts=2
    )
    assert selected == ()


def test_diversity_collapse_respects_cooldown(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]])
    trigger = DiversityCollapseTrigger(threshold=0.05, cooldown=5)

    fired = trigger.select_scouts(state, iteration=3, max_iterations=60, max_scouts=1)
    assert fired != ()

    for iteration in range(4, 9):  # still inside the cooldown window
        selected = trigger.select_scouts(
            state, iteration=iteration, max_iterations=60, max_scouts=1
        )
        assert selected == ()

    refired = trigger.select_scouts(state, iteration=9, max_iterations=60, max_scouts=1)
    assert refired != ()


def test_diversity_collapse_treats_single_bee_as_collapsed(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[2.0, 2.0]])
    trigger = DiversityCollapseTrigger()

    selected = trigger.select_scouts(
        state, iteration=0, max_iterations=60, max_scouts=1
    )
    assert selected == (0,)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"threshold": 0.0}, "threshold"),
        ({"cooldown": -1}, "cooldown"),
    ],
)
def test_diversity_collapse_validates_parameters(
    kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        DiversityCollapseTrigger(**kwargs)  # type: ignore[arg-type]


def test_corrected_firefly_moves_where_legacy_attraction_vanishes(
    make_state: Callable[..., _ColonyState],
) -> None:
    dim = 20
    scout, elite = [0.4] * dim, [0.0] * dim
    state = make_state([scout, elite], low=0.0, high=1.0)
    move = CorrectedFireflyElite(b0=1.0, gamma=1.0, alpha=0.0, k_top=1)

    distance_before = float(np.linalg.norm(np.array(scout)))
    # The v1 scaling degenerates at portfolio dimensionality: exp(-gamma*r^2)
    # at r ~ 1.8 attracts by less than 5%, so the legacy scout barely moves.
    legacy_attraction = math.exp(-1.0 * distance_before**2)
    assert legacy_attraction < 0.05

    move.relocate(state, 0)
    distance_after = float(np.linalg.norm(state.population[0].vector))

    # The corrected move must close a material fraction of the gap.
    assert distance_after <= 0.75 * distance_before
    assert state.n_evaluations == 1


def test_corrected_firefly_noise_scales_with_bounds_span(
    make_state: Callable[..., _ColonyState],
) -> None:
    # The scout sits exactly on the elite target, isolating the noise term.
    positions = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    wide = make_state(positions, low=-5.0, high=5.0, seed=99)
    narrow = make_state(positions, low=-0.5, high=0.5, seed=99)
    move = CorrectedFireflyElite()

    move.relocate(wide, 0)
    move.relocate(narrow, 0)

    assert not np.allclose(narrow.population[0].vector, 0.0)
    assert np.allclose(wide.population[0].vector, narrow.population[0].vector * 10.0)


def test_corrected_firefly_uniform_fallback_on_degenerate_weights(
    make_state: Callable[..., _ColonyState],
) -> None:
    # Non-finite objective values poison every softmax weight; the fallback
    # must select uniformly instead of raising (v1 FAEM's untested branch).
    def poisoned(x: np.ndarray) -> float:
        return float("nan")

    state = make_state([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]], objective=poisoned)
    move = CorrectedFireflyElite(k_top=3)

    move.relocate(state, 0)

    vector = state.population[0].vector
    assert np.all(np.isfinite(vector))
    assert np.all(vector >= state.bounds.lower)
    assert np.all(vector <= state.bounds.upper)
    assert state.n_evaluations == 1


def test_corrected_firefly_handles_all_equal_elite_weights(
    make_state: Callable[..., _ColonyState],
) -> None:
    # Identical elite fitness is uniform by construction and must not raise.
    state = make_state([[1.0, 1.0], [-1.0, 1.0], [1.0, -1.0]])
    move = CorrectedFireflyElite(k_top=3)

    move.relocate(state, 0)
    assert state.n_evaluations == 1


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"gamma": -0.1}, "gamma"),
        ({"k_top": 0}, "k_top"),
        ({"softmax_tau": 0.0}, "softmax_tau"),
    ],
)
def test_corrected_firefly_validates_parameters(
    kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        CorrectedFireflyElite(**kwargs)  # type: ignore[arg-type]


def test_levy_flight_is_deterministic_per_seed(
    make_state: Callable[..., _ColonyState],
) -> None:
    draws = []
    for _ in range(2):
        state = make_state([[2.0, 2.0], [1.0, 1.0]], seed=5)
        state.best_vector = np.array([1.0, 1.0])
        LevyFlightFromBest().relocate(state, 0)
        draws.append(state.population[0].vector.copy())
    assert np.array_equal(draws[0], draws[1])


def test_levy_flight_produces_occasional_large_steps() -> None:
    move = LevyFlightFromBest(exponent=1.5)
    rng = np.random.default_rng(42)

    magnitudes = [abs(float(move._mantegna_steps(rng, 1)[0])) for _ in range(200)]

    # Mantegna steps are heavy-tailed: rare jumps dwarf the typical step.
    assert max(magnitudes) > 5.0 * float(np.median(magnitudes))


def test_levy_flight_steps_from_the_best_vector(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[4.0, 4.0], [0.5, 0.5]], seed=3)
    state.best_vector = np.array([0.5, 0.5])
    move = LevyFlightFromBest(scale=1e-9)

    move.relocate(state, 0)

    # A vanishing scale collapses the flight onto its origin, proving the
    # step starts at the best vector rather than the scout's old position.
    assert np.allclose(state.population[0].vector, [0.5, 0.5], atol=1e-3)
    assert state.n_evaluations == 1


def test_levy_flight_falls_back_to_the_scout_without_a_best(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[2.0, 2.0], [1.0, 1.0]], seed=5)
    assert state.best_vector.size == 0  # never ran _update_best
    move = LevyFlightFromBest(scale=1e-9)

    move.relocate(state, 0)
    assert np.allclose(state.population[0].vector, [2.0, 2.0], atol=1e-3)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"exponent": 0.0}, "exponent"),
        ({"exponent": 2.5}, "exponent"),
        ({"scale": 0.0}, "scale"),
    ],
)
def test_levy_flight_validates_parameters(
    kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        LevyFlightFromBest(**kwargs)


def test_dirichlet_restart_lands_on_the_simplex(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state(
        [[0.2, 0.3, 0.5], [0.1, 0.1, 0.8], [0.6, 0.2, 0.2]], low=0.0, high=1.0
    )
    DirichletEliteRestart().relocate(state, 0)

    vector = state.population[0].vector
    assert np.all(vector >= 0.0)
    assert float(np.sum(vector)) == pytest.approx(1.0)
    assert state.n_evaluations == 1


def test_dirichlet_restart_concentrates_around_the_elite_mean(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state(
        [[0.9, 0.9, 0.9], [0.1, 0.2, 0.3], [0.3, 0.2, 0.1]], low=0.0, high=1.0
    )
    move = DirichletEliteRestart(concentration=1e7, k_top=2)

    move.relocate(state, 0)

    # Elite mean of the two fittest bees is (0.2, 0.2, 0.2) -> uniform third.
    assert np.allclose(state.population[0].vector, 1.0 / 3.0, atol=1e-3)


def test_dirichlet_restart_is_deterministic_per_seed(
    make_state: Callable[..., _ColonyState],
) -> None:
    draws = []
    for _ in range(2):
        state = make_state([[0.2, 0.8], [0.5, 0.5]], low=0.0, high=1.0, seed=11)
        DirichletEliteRestart().relocate(state, 0)
        draws.append(state.population[0].vector.copy())
    assert np.array_equal(draws[0], draws[1])


def test_dirichlet_restart_recovers_from_all_lower_bound_elites(
    make_state: Callable[..., _ColonyState],
) -> None:
    # An elite mean sitting exactly on the lower bound encodes no direction;
    # the policy must fall back to a uniform concentration, not raise.
    state = make_state([[0.0, 0.0], [0.0, 0.0]], low=0.0, high=1.0)
    DirichletEliteRestart().relocate(state, 0)

    vector = state.population[0].vector
    assert np.all(vector >= 0.0)
    assert float(np.sum(vector)) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"concentration": 0.0}, "concentration"),
        ({"k_top": 0}, "k_top"),
    ],
)
def test_dirichlet_restart_validates_parameters(
    kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        DirichletEliteRestart(**kwargs)  # type: ignore[arg-type]


def test_random_restart_matches_uniform_box_semantics(
    make_state: Callable[..., _ColonyState],
) -> None:
    state = make_state([[2.0, 2.0], [1.0, 1.0]], seed=123)
    scout_before = state.population[0]

    RandomRestart().relocate(state, 0)

    reference = np.random.default_rng(123)
    span = state.bounds.upper - state.bounds.lower
    expected = state.bounds.lower + reference.random(2) * span
    assert state.population[0] is not scout_before  # replaced, not moved
    assert np.array_equal(state.population[0].vector, expected)
    assert state.population[0].counter == 0
    assert state.n_evaluations == 1


@pytest.mark.parametrize(
    "move",
    [
        CorrectedFireflyElite(alpha=5.0),
        LevyFlightFromBest(scale=5.0),
        DirichletEliteRestart(),
        RandomRestart(),
    ],
)
@settings(max_examples=25, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
def test_relocated_bee_always_within_bounds(move: ScoutMove, seed: int) -> None:
    state = _seeded_state(seed)
    move.relocate(state, 0)

    vector = state.population[0].vector
    assert np.all(vector >= state.bounds.lower)
    assert np.all(vector <= state.bounds.upper)
