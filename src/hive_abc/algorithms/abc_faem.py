"""ABC-FAEM (thesis proposal): firefly scout guided toward a softmax elite."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math

import numpy as np

from hive_abc.algorithms.base import BeeHive, _ColonyState


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class ABCFAEM(BeeHive):
    """
    ABC-FAEM — the thesis's main proposed variant (legacy `ABC_FA_Scout`).

    The random scout restart of the original ABC is replaced by a firefly
    move (Yang, 2009) toward a leader sampled from the top-`k_top` bees with
    a temperature-`softmax_tau` softmax over their fitness. This keeps
    exploration guided by elite information without collapsing onto a single
    leader. Hybridization concept follows Tuba & Bacanin (2014).

    The probabilistic trigger `p_fa` (thesis p. 21, reviewer task 9)
    gates the mechanism: with probability `p_fa` the stalled bee performs the
    FA elite move; otherwise it falls back to the classic random restart.
    The frozen thesis runs fired the FA move unconditionally, so the default
    `p_fa=1.0` reproduces them exactly; the sensitivity analysis sweeps
    a local one-sided grid below 1.0, with lower values as a range check.

    Args:
        b0: Attractiveness at distance zero.
        gamma: Light-absorption coefficient.
        alpha: Randomization factor of the FA move.
        k_top: Elite pool size for leader sampling.
        softmax_tau: Softmax temperature over elite fitness.
        p_fa: Probability that the FA elite move fires instead of a random
            restart.

    Raises:
        ValueError: If `k_top < 1`, `softmax_tau <= 0`, or `p_fa` is outside
            `[0, 1]`.
    """

    def __init__(
        self,
        *,
        b0: float = 1.0,
        gamma: float = 1.0,
        alpha: float = 0.2,
        k_top: int = 3,
        softmax_tau: float = 1.0,
        p_fa: float = 1.0,
        colony_size: int = 50,
        max_iterations: int = 200,
        max_trials: int | None = None,
        max_trials_factor: float = 0.6,
    ) -> None:
        if k_top < 1:
            raise ValueError(f"k_top must be >= 1; got {k_top}")
        if softmax_tau <= 0:
            raise ValueError(f"softmax_tau must be positive; got {softmax_tau}")
        if not 0.0 <= p_fa <= 1.0:
            raise ValueError(f"p_fa must be in [0, 1]; got {p_fa}")
        super().__init__(
            colony_size=colony_size,
            max_iterations=max_iterations,
            max_trials=max_trials,
            max_trials_factor=max_trials_factor,
        )
        self._b0 = b0
        self._gamma = gamma
        self._alpha = alpha
        self._k_top = k_top
        self._softmax_tau = softmax_tau
        self._p_fa = p_fa

    def _scout_move(self, state: _ColonyState, index: int) -> None:
        """FA elite move with probability `p_fa`; random restart otherwise."""
        if state.rng.random() >= self._p_fa:
            state.population[index] = state.random_bee()
            return

        scout = state.population[index]
        target = self._select_elite_target(state)
        r = float(np.linalg.norm(scout.vector - target))
        attraction_scale = self._b0 * math.exp(-self._gamma * r**2)

        new_vector = scout.vector.copy()
        for d in range(state.bounds.dim):
            random_term = self._alpha * (state.rng.random() - 0.5)
            new_vector[d] = (
                scout.vector[d]
                + attraction_scale * (target[d] - scout.vector[d])
                + random_term
            )
        scout.vector = state.clip(new_vector)
        scout.value = state.evaluate(scout.vector)

    def _select_elite_target(self, state: _ColonyState) -> np.ndarray:
        """
        Samples the leader among the top-k bees via a stable softmax.

        The softmax subtracts the maximum fitness before exponentiating and
        falls back to a uniform distribution if the weights degenerate,
        mirroring the legacy implementation's numeric guards.
        """
        ranked = sorted(state.population, key=lambda bee: bee.fitness, reverse=True)
        k = max(1, min(self._k_top, len(ranked)))
        candidates = ranked[:k]

        max_fitness = candidates[0].fitness
        weights = [
            math.exp((bee.fitness - max_fitness) / self._softmax_tau)
            for bee in candidates
        ]
        total = sum(weights)
        if total <= 0 or not math.isfinite(total):
            probs = [1.0 / k] * k
        else:
            probs = [w / total for w in weights]

        u = state.rng.random()
        cumulative = 0.0
        selected = candidates[-1]
        for candidate, p in zip(candidates, probs, strict=True):
            cumulative += p
            if u <= cumulative:
                selected = candidate
                break
        return selected.vector
