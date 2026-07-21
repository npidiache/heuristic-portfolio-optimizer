"""Pluggable scout policies: stagnation triggers and recovery moves.

The v1 scout subsystem is dormant at thesis scale — the dimension-scaled
`max_trials` (0.6 x 25 bees x 20 assets = 300) is unreachable within 60
iterations — and its firefly recovery collapses at portfolio dimensionality
because `exp(-gamma * r**2)` vanishes at typical inter-bee distances. This
module isolates the redesigned policies behind two small protocols: a
`ScoutTrigger` decides WHO scouts each iteration and a `ScoutMove` decides
WHERE a scout goes. `ABCAdaptiveScout` composes them; the frozen v1 variants
import nothing from here.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from hive_abc.algorithms.base import _ColonyState


# --------------------------------------------------------------------------------------
# Protocols
# - Note1: Moves must leave the bee at `index` with a fresh in-bounds vector and,
#   when they evaluate it, an up-to-date `value`; the caller resets the trial
#   counter and re-evaluates any move that skipped evaluation.
# --------------------------------------------------------------------------------------
@runtime_checkable
class ScoutTrigger(Protocol):
    """Decides which bees abandon their food source at a given iteration."""

    def select_scouts(
        self,
        state: _ColonyState,
        iteration: int,
        max_iterations: int,
        max_scouts: int,
    ) -> tuple[int, ...]:
        """
        Returns the population indices to relocate, worst-first.

        Args:
            state: The run's colony state.
            iteration: Current iteration index (0-based).
            max_iterations: Total iteration budget of the run.
            max_scouts: Maximum number of indices to return.

        Returns:
            Selected indices, at most `max_scouts`, or empty when the
            trigger does not fire.
        """
        ...


@runtime_checkable
class ScoutMove(Protocol):
    """Relocates one abandoned bee to a new candidate solution."""

    def relocate(self, state: _ColonyState, index: int) -> None:
        """
        Replaces or mutates the bee at `index` with a recovery candidate.

        Args:
            state: The run's colony state.
            index: Population index of the bee being relocated.
        """
        ...


# --------------------------------------------------------------------------------------
# Trigger policies
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ProportionalTrialLimit:
    """
    Scouts every bee whose trial counter exceeds a budget-proportional limit.

    The limit is `max(1, int(fraction * max_iterations))`, so it scales with
    the run budget instead of v1's dimension-scaled `max_trials` (300 at
    thesis scale, unreachable in 60 iterations). The strict `>` comparison
    preserves v1 trigger semantics.

    Attributes:
        fraction: Fraction of `max_iterations` a bee may stall before it
            scouts.

    Raises:
        ValueError: If `fraction` is not positive.
    """

    fraction: float = 0.25

    def __post_init__(self) -> None:
        if self.fraction <= 0:
            raise ValueError(f"fraction must be positive; got {self.fraction}")

    def select_scouts(
        self,
        state: _ColonyState,
        iteration: int,
        max_iterations: int,
        max_scouts: int,
    ) -> tuple[int, ...]:
        """Returns stalled-bee indices, most-stalled first, up to the quota."""
        limit = max(1, int(self.fraction * max_iterations))
        stalled = [
            index for index, bee in enumerate(state.population) if bee.counter > limit
        ]
        stalled.sort(key=lambda index: (-state.population[index].counter, index))
        return tuple(stalled[:max_scouts])


@dataclass
class DiversityCollapseTrigger:
    """
    Scouts the worst bees when the colony collapses onto one region.

    Normalized dispersion is the mean pairwise Euclidean distance divided by
    `sqrt(dim)` times the mean bound span, making the threshold comparable
    across dimensionalities and box sizes. Firing is rate-limited: after a
    firing iteration, the trigger stays silent for `cooldown` iterations.
    The `_last_fired` field is run-scoped mutable state, mirroring
    `_ColonyState`'s precedent, so this dataclass is deliberately not frozen.

    Attributes:
        threshold: Dispersion level below which the colony counts as
            collapsed.
        cooldown: Iterations to wait after firing before firing again.

    Raises:
        ValueError: If `threshold` is not positive or `cooldown` is negative.
    """

    threshold: float = 0.05
    cooldown: int = 5
    _last_fired: int | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.threshold <= 0:
            raise ValueError(f"threshold must be positive; got {self.threshold}")
        if self.cooldown < 0:
            raise ValueError(f"cooldown must be non-negative; got {self.cooldown}")

    def select_scouts(
        self,
        state: _ColonyState,
        iteration: int,
        max_iterations: int,
        max_scouts: int,
    ) -> tuple[int, ...]:
        """Returns the worst-fitness indices when dispersion collapses."""
        recently_fired = (
            self._last_fired is not None
            and iteration - self._last_fired <= self.cooldown
        )
        if recently_fired or self._normalized_dispersion(state) >= self.threshold:
            return ()
        self._last_fired = iteration
        ranked = sorted(
            range(len(state.population)),
            key=lambda index: (state.population[index].fitness, index),
        )
        return tuple(ranked[:max_scouts])

    def _normalized_dispersion(self, state: _ColonyState) -> float:
        """Mean pairwise distance scaled by dimension and mean bound span."""
        vectors = np.stack([bee.vector for bee in state.population])
        n = vectors.shape[0]
        span = float(np.mean(state.bounds.upper - state.bounds.lower))
        denominator = math.sqrt(state.bounds.dim) * span
        if n < 2 or denominator <= 0:
            return 0.0  # a lone or unscalable colony counts as collapsed
        deltas = vectors[:, None, :] - vectors[None, :, :]
        distances = np.sqrt(np.sum(deltas**2, axis=-1))
        mean_distance = float(np.sum(distances) / (n * (n - 1)))
        return mean_distance / denominator


# --------------------------------------------------------------------------------------
# Move policies
# - Note1: The corrected firefly scaling lives ONLY here; the frozen v1 employed
#   move in `abc_fa_bacanin.py` and the v1 FAEM scout keep the legacy formula.
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CorrectedFireflyElite:
    """
    Firefly move toward a softmax-sampled elite with dimension-safe scaling.

    Two corrections over the v1 FAEM move: the attraction distance is
    normalized by `sqrt(dim)` before `exp(-gamma * r_norm**2)` (the raw
    distance makes attraction vanish at portfolio dimensionality), and the
    random term scales with each dimension's bound span instead of being an
    absolute offset. Degenerate softmax weights (all-equal or non-finite)
    fall back to a uniform elite choice instead of raising.

    Attributes:
        b0: Attractiveness at distance zero.
        gamma: Light-absorption coefficient over the normalized distance.
        alpha: Randomization factor, as a fraction of each bound span.
        k_top: Elite pool size for leader sampling.
        softmax_tau: Softmax temperature over elite fitness.

    Raises:
        ValueError: If `gamma` is negative, `k_top < 1`, or
            `softmax_tau <= 0`.
    """

    b0: float = 1.0
    gamma: float = 1.0
    alpha: float = 0.2
    k_top: int = 3
    softmax_tau: float = 1.0

    def __post_init__(self) -> None:
        if self.gamma < 0:
            raise ValueError(f"gamma must be non-negative; got {self.gamma}")
        if self.k_top < 1:
            raise ValueError(f"k_top must be >= 1; got {self.k_top}")
        if self.softmax_tau <= 0:
            raise ValueError(f"softmax_tau must be positive; got {self.softmax_tau}")

    def relocate(self, state: _ColonyState, index: int) -> None:
        """Moves the scout toward a sampled elite and re-evaluates it."""
        scout = state.population[index]
        target = self._sample_elite_target(state)
        r_norm = float(np.linalg.norm(scout.vector - target)) / math.sqrt(
            state.bounds.dim
        )
        attraction = self.b0 * math.exp(-self.gamma * r_norm**2)
        span = state.bounds.upper - state.bounds.lower
        noise = self.alpha * (state.rng.random(state.bounds.dim) - 0.5) * span
        new_vector = scout.vector + attraction * (target - scout.vector) + noise
        scout.vector = state.clip(new_vector)
        scout.value = state.evaluate(scout.vector)

    def _sample_elite_target(self, state: _ColonyState) -> NDArray[np.float64]:
        """Softmax-samples a top-k leader, uniform on degenerate weights."""
        ranked = sorted(state.population, key=lambda bee: bee.fitness, reverse=True)
        candidates = ranked[: max(1, min(self.k_top, len(ranked)))]

        max_fitness = candidates[0].fitness
        weights = [
            math.exp((bee.fitness - max_fitness) / self.softmax_tau)
            for bee in candidates
        ]
        total = sum(weights)
        if total <= 0 or not math.isfinite(total):
            probs = [1.0 / len(candidates)] * len(candidates)
        else:
            probs = [weight / total for weight in weights]

        u = state.rng.random()
        cumulative = 0.0
        selected = candidates[-1]
        for candidate, probability in zip(candidates, probs, strict=True):
            cumulative += probability
            if u <= cumulative:
                selected = candidate
                break
        return selected.vector


@dataclass(frozen=True)
class LevyFlightFromBest:
    """
    Levy flight from the best-known solution via Mantegna's algorithm.

    Steps are `u / |v| ** (1 / exponent)` with `u ~ N(0, sigma_u**2)` and
    `v ~ N(0, 1)`, where the closed-form `sigma_u` yields the standard
    Levy-stable approximation: mostly local steps with occasional long
    jumps. Steps scale with each dimension's bound span. When no best
    vector exists yet, the scout's own position seeds the flight.

    Attributes:
        exponent: Levy stability exponent (beta), in `(0, 2]`.
        scale: Step size as a fraction of each bound span.

    Raises:
        ValueError: If `exponent` is outside `(0, 2]` or `scale` is not
            positive.
    """

    exponent: float = 1.5
    scale: float = 0.1

    def __post_init__(self) -> None:
        if not 0.0 < self.exponent <= 2.0:
            raise ValueError(f"exponent must be in (0, 2]; got {self.exponent}")
        if self.scale <= 0:
            raise ValueError(f"scale must be positive; got {self.scale}")

    def relocate(self, state: _ColonyState, index: int) -> None:
        """Jumps from the best vector with a Levy step and re-evaluates."""
        scout = state.population[index]
        origin = state.best_vector if state.best_vector.size else scout.vector
        span = state.bounds.upper - state.bounds.lower
        step = self._mantegna_steps(state.rng, state.bounds.dim)
        scout.vector = state.clip(origin + self.scale * span * step)
        scout.value = state.evaluate(scout.vector)

    def _mantegna_steps(
        self, rng: np.random.Generator, dim: int
    ) -> NDArray[np.float64]:
        """Draws `dim` Levy-stable steps with Mantegna's closed-form sigma."""
        beta = self.exponent
        sigma_u = (
            math.gamma(1 + beta)
            * math.sin(math.pi * beta / 2)
            / (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))
        ) ** (1 / beta)
        u = rng.normal(0.0, sigma_u, size=dim)
        v = rng.normal(0.0, 1.0, size=dim)
        return np.asarray(u / np.abs(v) ** (1 / beta), dtype=np.float64)


@dataclass(frozen=True)
class DirichletEliteRestart:
    """
    Restarts the scout on the simplex around the elite mean direction.

    The elite mean (top-`k_top` bees by fitness) is normalized into a
    direction on the simplex; a Dirichlet draw concentrated around that
    direction is mapped onto the bounds box. Natural for long-only
    portfolio weights, whose candidates live on a scaled simplex.

    Attributes:
        concentration: Total Dirichlet concentration; larger values sample
            closer to the elite mean direction.
        k_top: Elite pool size for the mean.

    Raises:
        ValueError: If `concentration <= 0` or `k_top < 1`.
    """

    concentration: float = 20.0
    k_top: int = 3

    def __post_init__(self) -> None:
        if self.concentration <= 0:
            raise ValueError(
                f"concentration must be positive; got {self.concentration}"
            )
        if self.k_top < 1:
            raise ValueError(f"k_top must be >= 1; got {self.k_top}")

    def relocate(self, state: _ColonyState, index: int) -> None:
        """Replaces the scout with a Dirichlet draw mapped into bounds."""
        ranked = sorted(state.population, key=lambda bee: bee.fitness, reverse=True)
        elite = ranked[: max(1, min(self.k_top, len(ranked)))]
        elite_mean = np.mean(np.stack([bee.vector for bee in elite]), axis=0)

        span = state.bounds.upper - state.bounds.lower
        relative = (elite_mean - state.bounds.lower) / span
        total = float(np.sum(relative))
        if not math.isfinite(total) or total <= 0:
            # An elite mean on the lower bound encodes no direction: sample
            # around the simplex barycenter instead of raising.
            direction = np.full(state.bounds.dim, 1.0 / state.bounds.dim)
        else:
            direction = relative / total
        alpha_vec = self.concentration * direction + 1e-6

        weights = state.rng.dirichlet(alpha_vec)
        scout = state.population[index]
        scout.vector = state.clip(state.bounds.lower + weights * span)
        scout.value = state.evaluate(scout.vector)


@dataclass(frozen=True)
class RandomRestart:
    """
    Canonical ABC restart: a fresh uniform draw inside the bounds box.

    Delegates to `_ColonyState.random_bee`, so the replacement bee is
    evaluated on construction exactly like v1's scout restart.
    """

    def relocate(self, state: _ColonyState, index: int) -> None:
        """Replaces the scout with a uniform-random evaluated bee."""
        state.population[index] = state.random_bee()
