"""ABC-GSA (thesis proposal): gravitational-search scout phase."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np

from hive_abc.algorithms.base import BeeHive, _ColonyState


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class ABCGSA(BeeHive):
    """
    ABC-GSA — thesis variant with a gravitational scout (legacy
    `ABC_Scout_Gravitacional`).

    Instead of restarting randomly, the stalled bee moves along the net
    gravitational force exerted by the whole swarm, following the analogy of
    Rashedi, Nezamabadi-pour & Saryazdi (2009), "GSA: A Gravitational Search
    Algorithm", Information Sciences 179(13). Pairwise forces use the bees'
    fitness as mass:

        F = G * (m_scout * m_other) / (r^2 + epsilon)

    the net force is normalized to a unit step, and a small random component
    preserves diversity. The scout therefore drifts toward the swarm's
    fitness-weighted center of mass rather than a single leader.

    Args:
        g_constant: Gravitational constant `G` scaling pairwise forces.
        epsilon: Numeric guard for near-zero distances.
        alpha: Randomization factor of the final move.

    Raises:
        ValueError: If `epsilon` is not positive.
    """

    def __init__(
        self,
        *,
        g_constant: float = 1.0,
        epsilon: float = 1e-10,
        alpha: float = 0.1,
        colony_size: int = 50,
        max_iterations: int = 200,
        max_trials: int | None = None,
        max_trials_factor: float = 0.6,
    ) -> None:
        if epsilon <= 0:
            raise ValueError(f"epsilon must be positive; got {epsilon}")
        super().__init__(
            colony_size=colony_size,
            max_iterations=max_iterations,
            max_trials=max_trials,
            max_trials_factor=max_trials_factor,
        )
        self._g = g_constant
        self._epsilon = epsilon
        self._alpha = alpha

    def _scout_move(self, state: _ColonyState, index: int) -> None:
        """Moves the stalled bee along the swarm's normalized net force."""
        scout = state.population[index]
        net_force = self._net_gravitational_force(state, index)

        magnitude = float(np.linalg.norm(net_force))
        if magnitude > 0:
            net_force = net_force / magnitude
        else:
            net_force = np.zeros(state.bounds.dim)

        random_component = self._alpha * (state.rng.random(state.bounds.dim) - 0.5)
        new_vector = scout.vector + net_force + random_component
        scout.vector = state.clip(new_vector)
        scout.value = state.evaluate(scout.vector)

    def _net_gravitational_force(self, state: _ColonyState, index: int) -> np.ndarray:
        """Sums the pairwise gravitational pull of every other bee."""
        scout = state.population[index]
        net_force = np.zeros(state.bounds.dim)
        for position, other in enumerate(state.population):
            if position == index:
                continue
            offset = other.vector - scout.vector
            distance = float(np.linalg.norm(offset))
            if distance < self._epsilon:
                continue
            magnitude = (
                self._g
                * (scout.fitness * other.fitness)
                / (distance**2 + self._epsilon)
            )
            net_force += magnitude * (offset / distance)
        return net_force
