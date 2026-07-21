"""ABC with a pluggable, adaptive scout phase (the v2 scout lab optimizer)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.algorithms.base import BeeHive, _ColonyState
from hive_abc.algorithms.scouting import (
    CorrectedFireflyElite,
    ProportionalTrialLimit,
    ScoutMove,
    ScoutTrigger,
)


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class ABCAdaptiveScout(BeeHive):
    """
    ABC whose scout phase is a pluggable trigger x move policy pair.

    The v1 scout subsystem is dormant at thesis scale: the dimension-scaled
    `max_trials` (300) is unreachable within 60 iterations, so the proposed
    recovery moves never execute. This class replaces the counter-versus-
    `max_trials` decision with a `ScoutTrigger` (who scouts — possibly
    several bees per iteration) and the relocation with a `ScoutMove`, both
    from `hive_abc.algorithms.scouting`. Employed and onlooker choreography
    are inherited unchanged; optionally the onlooker roulette table is
    recomputed every iteration instead of v1's frozen-at-init table. Like
    `ABCEpsilonScout`, this class is exercised directly and is deliberately
    absent from the backtest engine's default model registry.

    Args:
        trigger: Scout-selection policy; defaults to
            `ProportionalTrialLimit()`.
        scout_move: Relocation policy; defaults to
            `CorrectedFireflyElite()`.
        max_scouts_per_iteration: Upper bound on relocations per iteration.
        refresh_onlooker_probabilities: When True, recompute the onlooker
            roulette at every onlooker phase; when False, keep v1's
            frozen-at-init table (byte-identical to `BeeHive` when the
            trigger never fires).
        colony_size: Requested number of bees (rounded up to even).
        max_iterations: Number of employed/onlooker/scout cycles.
        max_trials: v1 stagnation cap — accepted for constructor parity but
            ignored by the scout phase, which delegates to `trigger`.
        max_trials_factor: Factor for the derived `max_trials` default.

    Raises:
        ValueError: If `max_scouts_per_iteration < 1` or a base-constructor
            constraint is violated.
        TypeError: If `trigger` or `scout_move` does not implement its
            policy protocol.
    """

    def __init__(
        self,
        *,
        trigger: ScoutTrigger | None = None,
        scout_move: ScoutMove | None = None,
        max_scouts_per_iteration: int = 1,
        refresh_onlooker_probabilities: bool = True,
        colony_size: int = 50,
        max_iterations: int = 200,
        max_trials: int | None = None,
        max_trials_factor: float = 0.6,
    ) -> None:
        if max_scouts_per_iteration < 1:
            raise ValueError(
                f"max_scouts_per_iteration must be >= 1; got {max_scouts_per_iteration}"
            )
        resolved_trigger = ProportionalTrialLimit() if trigger is None else trigger
        if not isinstance(resolved_trigger, ScoutTrigger):
            raise TypeError(
                f"trigger must implement ScoutTrigger; got {resolved_trigger!r}"
            )
        resolved_move = CorrectedFireflyElite() if scout_move is None else scout_move
        if not isinstance(resolved_move, ScoutMove):
            raise TypeError(
                f"scout_move must implement ScoutMove; got {resolved_move!r}"
            )
        super().__init__(
            colony_size=colony_size,
            max_iterations=max_iterations,
            max_trials=max_trials,
            max_trials_factor=max_trials_factor,
        )
        self._trigger = resolved_trigger
        self._move = resolved_move
        self._max_scouts = max_scouts_per_iteration
        self._refresh_onlookers = refresh_onlooker_probabilities

    def _scout_phase(self, state: _ColonyState, max_trials: int, iteration: int) -> int:
        """
        Relocates every trigger-selected bee, ignoring the v1 counter cap.

        Args:
            state: The run's colony state.
            max_trials: Ignored — the trigger owns the scouting decision.
            iteration: Current iteration, forwarded to the trigger.

        Returns:
            Number of relocated bees; each one counts as one activation in
            the run telemetry.
        """
        selected = self._trigger.select_scouts(
            state, iteration, self._max_iterations, self._max_scouts
        )
        for index in selected:
            evaluations_before = state.n_evaluations
            self._move.relocate(state, index)
            bee = state.population[index]
            if state.n_evaluations == evaluations_before:
                bee.value = state.evaluate(bee.vector)  # move skipped it
            bee.counter = 0
        return len(selected)

    def _onlooker_phase(self, state: _ColonyState) -> None:
        """Optionally refreshes the roulette table, then runs v1 onlookers."""
        if self._refresh_onlookers:
            state.cumulative_probas = self._cumulative_probabilities(state)
        super()._onlooker_phase(state)
