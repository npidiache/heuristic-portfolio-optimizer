"""ABC epsilon-greedy scout (legacy `ABC_Probabilistic_Scout`)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.algorithms.base import BeeHive, _ColonyState


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class ABCEpsilonScout(BeeHive):
    """
    ABC with an epsilon-greedy scout decision.

    With probability `epsilon` the stalled bee restarts randomly (pure
    exploration, the original ABC behavior); otherwise it moves toward the
    best solution found so far with a single scalar step:

        x_new = x + phi * (best - x),  phi ~ U[0, 1)

    This variant is not part of the thesis's headline result tables; it is
    kept as the annex companion of the PFA discussion (reviewer task 9).

    Args:
        epsilon: Probability of a pure random restart.

    Raises:
        ValueError: If `epsilon` is outside `[0, 1]`.
    """

    def __init__(
        self,
        *,
        epsilon: float = 0.1,
        colony_size: int = 50,
        max_iterations: int = 200,
        max_trials: int | None = None,
        max_trials_factor: float = 0.6,
    ) -> None:
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError(f"epsilon must be in [0, 1]; got {epsilon}")
        super().__init__(
            colony_size=colony_size,
            max_iterations=max_iterations,
            max_trials=max_trials,
            max_trials_factor=max_trials_factor,
        )
        self._epsilon = epsilon

    def _scout_move(self, state: _ColonyState, index: int) -> None:
        """Random restart with probability epsilon; best-guided move otherwise."""
        if state.rng.random() < self._epsilon or state.best_vector.size == 0:
            state.population[index] = state.random_bee()
            return

        scout = state.population[index]
        phi = state.rng.random()
        new_vector = scout.vector + phi * (state.best_vector - scout.vector)
        scout.vector = state.clip(new_vector)
        scout.value = state.evaluate(scout.vector)
