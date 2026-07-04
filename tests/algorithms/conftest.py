"""Shared helpers for algorithm tests: hand-built colony states."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Callable

import numpy as np
import pytest

from hive_abc.algorithms.base import _Bee, _ColonyState
from hive_abc.core.types import Bounds


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def _sphere(x: np.ndarray) -> float:
    """Convex test objective with the global minimum at the origin."""
    return float(np.sum(np.square(x)))


@pytest.fixture
def make_state() -> Callable[..., _ColonyState]:
    """
    Builds a `_ColonyState` from explicit bee positions.

    The factory evaluates each position with the given objective (default
    sphere) and seeds the state's RNG deterministically so hook tests are
    reproducible.
    """

    def _factory(
        positions: list[list[float]],
        objective: Callable[[np.ndarray], float] = _sphere,
        low: float = -5.0,
        high: float = 5.0,
        seed: int = 123,
    ) -> _ColonyState:
        dim = len(positions[0])
        state = _ColonyState(
            objective=objective,
            bounds=Bounds.box(dim, low, high),
            rng=np.random.default_rng(seed),
        )
        state.population = [
            _Bee(vector=np.array(p, dtype=float), value=objective(np.array(p)))
            for p in positions
        ]
        return state

    return _factory
