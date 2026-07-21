"""Artificial Bee Colony skeleton shared by every variant in the family.

Faithful refactor of the thesis implementation (`legacy/abc_original.py`),
which follows Karaboga (2005), "An idea based on honey bee swarm for numerical
optimization", Technical Report TR-06, Erciyes University. Variants override
exactly one behavioral hook each (`_neighbor_candidate` or `_scout_move`), so
the employed/onlooker/scout choreography lives in a single place.

Deliberate fidelity notes (behavior preserved from the thesis code, even where
a "cleaner" choice exists, because the frozen results depend on it):

- Onlooker selection probabilities are computed once at initialization and
  never refreshed during the run.
- Exactly one bee (the one with the most trials) can become a scout per
  iteration, and only when its trials strictly exceed `max_trials`.
- Greedy replacement compares transformed fitness, not raw objective values.
- Legacy seeding derived per-class seeds from `hash(cls.__name__)`, which is
  platform-dependent; it is replaced by `numpy.random.default_rng(seed)`.
  Statistical (not bitwise) reproduction is the regression contract.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import time
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from hive_abc.core.optimizer import HeuristicOptimizer
from hive_abc.core.types import Bounds, ObjectiveFn, OptimizationResult


# --------------------------------------------------------------------------------------
# Classes
# - Note1: _Bee and _ColonyState are run-scoped internals; only BeeHive is public.
# --------------------------------------------------------------------------------------
@dataclass
class _Bee:
    """One candidate solution with its objective value and trial counter."""

    vector: NDArray[np.float64]
    value: float
    counter: int = 0

    @property
    def fitness(self) -> float:
        """
        Karaboga's fitness transform of the objective value.

        Non-negative costs map to `1 / (1 + value)`; negative costs (better
        than zero) map to `1 + |value|`, so lower objective values always get
        higher fitness.
        """
        if self.value >= 0:
            return 1.0 / (1.0 + self.value)
        return 1.0 + abs(self.value)


@dataclass
class _ColonyState:
    """
    Mutable state of one `optimize` run, shared with the variant hooks.

    Attributes:
        objective: Objective under minimization.
        bounds: Search-space box constraints.
        rng: The run's random generator (single source of randomness).
        population: Current colony.
        cumulative_probas: Onlooker roulette probabilities (cumulative), frozen
            at initialization to match the thesis implementation.
        best_value: Best objective value observed so far.
        best_vector: Vector achieving `best_value`.
        n_evaluations: Objective calls performed so far.
    """

    objective: ObjectiveFn
    bounds: Bounds
    rng: np.random.Generator
    population: list[_Bee] = field(default_factory=list)
    cumulative_probas: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))
    best_value: float = float("inf")
    best_vector: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))
    n_evaluations: int = 0

    def evaluate(self, vector: NDArray[np.float64]) -> float:
        """Evaluates the objective and counts the call."""
        self.n_evaluations += 1
        return float(self.objective(vector))

    def random_bee(self) -> _Bee:
        """Draws a uniform-random candidate within bounds and evaluates it."""
        span = self.bounds.upper - self.bounds.lower
        vector = self.bounds.lower + self.rng.random(self.bounds.dim) * span
        return _Bee(vector=vector, value=self.evaluate(vector))

    def clip(
        self, vector: NDArray[np.float64], dim: int | None = None
    ) -> NDArray[np.float64]:
        """
        Clamps `vector` into bounds, either fully or on a single dimension.

        Args:
            vector: Candidate to clamp (modified in place and returned).
            dim: When given, only that dimension is checked — the original
                ABC employed move mutates one dimension and validates only it.
        """
        if dim is None:
            np.clip(vector, self.bounds.lower, self.bounds.upper, out=vector)
        else:
            vector[dim] = min(
                max(vector[dim], self.bounds.lower[dim]), self.bounds.upper[dim]
            )
        return vector


class BeeHive(HeuristicOptimizer):
    """
    ABC original (Karaboga, 2005): the base algorithm and template.

    Employed bees mutate one random dimension toward/away from a random
    neighbor; onlookers repeat the employed move on roulette-selected sources;
    the most-stalled bee becomes a scout and is replaced by a uniform-random
    solution once its trials exceed `max_trials`.

    Args:
        colony_size: Requested number of bees; rounded up to an even count
            exactly like the thesis code (`numb_bees + numb_bees % 2`).
        max_iterations: Number of employed/onlooker/scout cycles.
        max_trials: Stagnation threshold before a bee scouts. When `None`,
            it is derived at run time as
            `int(max_trials_factor * colony_size_even * dim)`.
        max_trials_factor: Factor for the derived `max_trials` default.

    Raises:
        ValueError: If `colony_size < 2`, `max_iterations < 1`, or
            `max_trials_factor <= 0`.
    """

    def __init__(
        self,
        *,
        colony_size: int = 50,
        max_iterations: int = 200,
        max_trials: int | None = None,
        max_trials_factor: float = 0.6,
    ) -> None:
        if colony_size < 2:
            raise ValueError(f"colony_size must be >= 2; got {colony_size}")
        if max_iterations < 1:
            raise ValueError(f"max_iterations must be >= 1; got {max_iterations}")
        if max_trials_factor <= 0:
            raise ValueError(
                f"max_trials_factor must be positive; got {max_trials_factor}"
            )
        self._size = int(colony_size + colony_size % 2)
        self._max_iterations = max_iterations
        self._max_trials = max_trials
        self._max_trials_factor = max_trials_factor

    def optimize(
        self,
        objective: ObjectiveFn,
        bounds: Bounds,
        *,
        seed: int | None = None,
    ) -> OptimizationResult:
        """
        Runs the employed → onlooker → scout cycle for `max_iterations`.

        Args:
            objective: Function to minimize over raw candidate vectors.
            bounds: Box constraints; dimension count defines the colony's
                search space.
            seed: Seed for `numpy.random.default_rng`.

        Returns:
            Best solution found with per-iteration convergence history and
            scout-phase activation telemetry.
        """
        start = time.perf_counter()
        state = _ColonyState(
            objective=objective, bounds=bounds, rng=np.random.default_rng(seed)
        )
        state.population = [state.random_bee() for _ in range(self._size)]
        self._update_best(state)
        # Frozen-at-init roulette table: the thesis code never recomputed the
        # onlooker probabilities inside the run loop, so neither do we.
        state.cumulative_probas = self._cumulative_probabilities(state)

        max_trials = self._max_trials
        if max_trials is None:
            max_trials = int(self._max_trials_factor * self._size * bounds.dim)

        best_history: list[float] = []
        mean_history: list[float] = []
        scout_iterations: list[int] = []
        for iteration in range(self._max_iterations):
            for index in range(self._size):
                self._employed_step(state, index)
            self._onlooker_phase(state)
            if self._scout_phase(state, max_trials):
                scout_iterations.append(iteration)
            self._update_best(state)
            best_history.append(state.best_value)
            mean_history.append(sum(bee.value for bee in state.population) / self._size)

        return OptimizationResult(
            best_vector=state.best_vector,
            best_value=state.best_value,
            best_per_iteration=tuple(best_history),
            mean_per_iteration=tuple(mean_history),
            n_evaluations=state.n_evaluations,
            runtime_seconds=time.perf_counter() - start,
            seed=seed,
            scout_activations=len(scout_iterations),
            scout_activation_iterations=tuple(scout_iterations),
        )

    # -- variant hooks -----------------------------------------------------------

    def _neighbor_candidate(
        self, state: _ColonyState, index: int, neighbor: int
    ) -> NDArray[np.float64]:
        """
        Builds the employed/onlooker candidate for bee `index`.

        The original ABC move perturbs ONE random dimension:
        `v_ij = x_ij + phi * (x_ij - x_kj)` with `phi ~ U[-1, 1]`, and clamps
        only that dimension. `ABCFABacanin` overrides this with the firefly
        move over all dimensions.

        Args:
            state: The run's colony state.
            index: Bee being improved.
            neighbor: Random other bee used as the reference solution.

        Returns:
            A new candidate vector, already clamped to bounds.
        """
        candidate = state.population[index].vector.copy()
        d = int(state.rng.integers(0, state.bounds.dim))
        phi = (state.rng.random() - 0.5) * 2.0
        candidate[d] = candidate[d] + phi * (
            candidate[d] - state.population[neighbor].vector[d]
        )
        return state.clip(candidate, dim=d)

    def _scout_move(self, state: _ColonyState, index: int) -> None:
        """
        Replaces the stalled bee `index`; the original ABC restarts randomly.

        Variants override this hook: ABC-FAEM moves toward a softmax-selected
        elite, ABC-GSA follows the swarm's net gravitational force, and the
        epsilon variant mixes restarts with best-guided moves.

        Args:
            state: The run's colony state.
            index: Bee whose trial counter exceeded `max_trials`.
        """
        state.population[index] = state.random_bee()

    # -- phase choreography (shared by all variants) -----------------------------

    def _employed_step(self, state: _ColonyState, index: int) -> None:
        """Applies the neighbor move to bee `index` with greedy replacement."""
        neighbor = index
        while neighbor == index:
            neighbor = int(state.rng.integers(0, self._size))
        candidate = self._neighbor_candidate(state, index, neighbor)
        candidate_bee = _Bee(vector=candidate, value=state.evaluate(candidate))
        if candidate_bee.fitness > state.population[index].fitness:
            state.population[index] = candidate_bee
        else:
            state.population[index].counter += 1

    def _onlooker_phase(self, state: _ColonyState) -> None:
        """
        Runs `colony_size` onlooker moves via the thesis roulette scheme.

        The selector accumulates `phi * max(probas)` modulo `max(probas)` and
        picks the first bee whose cumulative probability exceeds the pointer —
        preserved exactly from the legacy implementation.
        """
        max_proba = float(state.cumulative_probas[-1])
        beta = 0.0
        for _ in range(self._size):
            beta += state.rng.random() * max_proba
            beta %= max_proba
            self._employed_step(state, self._roulette_select(state, beta))

    def _scout_phase(self, state: _ColonyState, max_trials: int) -> bool:
        """
        Sends the single most-stalled bee to scout when it exceeds the cap.

        Returns:
            True when a scout replacement fired, so `optimize` can record the
            activation without altering the trigger semantics.
        """
        trials = [bee.counter for bee in state.population]
        index = trials.index(max(trials))
        if trials[index] > max_trials:
            self._scout_move(state, index)
            state.population[index].counter = 0
            return True
        return False

    def _cumulative_probabilities(self, state: _ColonyState) -> NDArray[np.float64]:
        """Builds the cumulative fitness-proportional roulette table."""
        fitness = np.array([bee.fitness for bee in state.population])
        return np.asarray(np.cumsum(fitness / fitness.sum()), dtype=np.float64)

    def _roulette_select(self, state: _ColonyState, beta: float) -> int:
        """Returns the first index whose cumulative probability exceeds beta."""
        matches = np.nonzero(beta < state.cumulative_probas)[0]
        return int(matches[0]) if matches.size else self._size - 1

    def _update_best(self, state: _ColonyState) -> None:
        """Tracks the strictly-better best solution across the colony."""
        values = [bee.value for bee in state.population]
        index = values.index(min(values))
        if state.population[index].value < state.best_value:
            state.best_value = state.population[index].value
            state.best_vector = state.population[index].vector.copy()
