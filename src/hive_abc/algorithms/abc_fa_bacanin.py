"""ABC-FA hybrid (Tuba & Bacanin, 2014): firefly moves in the employed phase."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math

import numpy as np
from numpy.typing import NDArray

from hive_abc.algorithms.base import BeeHive, _ColonyState


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class ABCFABacanin(BeeHive):
    """
    ABC hybridized with the Firefly Algorithm in the employed/onlooker move.

    Reference: M. Tuba and N. Bacanin, "Artificial bee colony algorithm
    hybridized with firefly algorithm for cardinality constrained
    mean-variance portfolio selection", Applied Mathematics & Information
    Sciences 8(6), 2014 — the original implementation of the hybridization is
    theirs (legacy class `ABC_FA_Bacanin`). Firefly movement follows Yang
    (2009). Instead of mutating one dimension, the candidate moves toward a
    random neighbor on EVERY dimension:

        x_i^new = x_i + b0 * exp(-gamma * r^2) * (x_k - x_i) + alpha * (u - 0.5)

    where `r` is the Euclidean distance to the neighbor. The scout phase stays
    the classic random restart.

    Args:
        b0: Attractiveness at distance zero (paper default 1.1).
        gamma: Light-absorption coefficient (paper default 1.4).
        alpha: Randomization factor (paper default 0.025).

    Raises:
        ValueError: If `gamma` is negative (attraction must decay).
    """

    def __init__(
        self,
        *,
        b0: float = 1.1,
        gamma: float = 1.4,
        alpha: float = 0.025,
        colony_size: int = 50,
        max_iterations: int = 200,
        max_trials: int | None = None,
        max_trials_factor: float = 0.6,
    ) -> None:
        if gamma < 0:
            raise ValueError(f"gamma must be non-negative; got {gamma}")
        super().__init__(
            colony_size=colony_size,
            max_iterations=max_iterations,
            max_trials=max_trials,
            max_trials_factor=max_trials_factor,
        )
        self._b0 = b0
        self._gamma = gamma
        self._alpha = alpha

    def _neighbor_candidate(
        self, state: _ColonyState, index: int, neighbor: int
    ) -> NDArray[np.float64]:
        """Applies the firefly attraction move on all dimensions."""
        current = state.population[index].vector
        other = state.population[neighbor].vector
        r = float(np.linalg.norm(current - other))
        attraction = self._b0 * math.exp(-self._gamma * r**2)

        candidate = current.copy()
        for d in range(state.bounds.dim):
            random_term = self._alpha * (state.rng.random() - 0.5)
            candidate[d] = (
                current[d] + attraction * (other[d] - current[d]) + random_term
            )
        return state.clip(candidate)
