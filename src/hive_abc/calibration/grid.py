"""Parameter grids and candidate sampling for calibration studies.

A `ParameterGrid` names each tunable constructor argument and the values it may
take; `candidates()` enumerates the full cartesian product in a deterministic
order so studies are reproducible, and `sample_candidates` draws a seeded
random subset when the full product is too expensive to run.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product

import numpy as np


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ParameterGrid:
    """
    Cartesian grid over named parameter axes.

    Attributes:
        parameters: Mapping from parameter name to the tuple of values that
            axis may take. Axis order follows the mapping's iteration order;
            within an axis, values keep the order they were given in.

    Raises:
        ValueError: If the grid has no axes, an axis has no values, or an
            axis repeats a value.
    """

    parameters: Mapping[str, tuple[float | int, ...]]

    def __post_init__(self) -> None:
        """Validates that every axis is non-empty and duplicate-free."""
        if not self.parameters:
            raise ValueError("grid needs at least one parameter axis")
        for name, values in self.parameters.items():
            if not values:
                raise ValueError(f"axis {name!r} has no values")
            if len(set(values)) != len(values):
                raise ValueError(f"axis {name!r} has duplicate values: {values}")

    def candidates(self) -> tuple[dict[str, float | int], ...]:
        """
        Enumerates the full cartesian product as candidate mappings.

        The last axis varies fastest (`itertools.product` order), so the
        enumeration is deterministic for a given `parameters` mapping.

        Returns:
            One dict per grid point, in deterministic order.
        """
        names = tuple(self.parameters)
        return tuple(
            dict(zip(names, combo, strict=True))
            for combo in product(*self.parameters.values())
        )


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def candidate_label(candidate: Mapping[str, object]) -> str:
    """
    Canonical string identity of a candidate mapping.

    Keys are sorted so two mappings with the same items always produce the
    same label; `select_configuration` addresses candidates (e.g. the
    baseline) through these labels.

    Args:
        candidate: Parameter mapping of one candidate configuration.

    Returns:
        Comma-joined `key=value` pairs in sorted key order.
    """
    return ",".join(f"{name}={candidate[name]!r}" for name in sorted(candidate))


def sample_candidates(
    grid: ParameterGrid, n: int, seed: int
) -> tuple[dict[str, float | int], ...]:
    """
    Draws a reproducible, duplicate-free subset of the grid's candidates.

    Args:
        grid: Grid to sample from.
        n: Number of candidates to draw (without replacement).
        seed: Seed for the sampling generator.

    Returns:
        `n` distinct candidates, in grid-enumeration order.

    Raises:
        ValueError: If `n` is not in `[1, len(grid.candidates())]`.
    """
    full_product = grid.candidates()
    if not 1 <= n <= len(full_product):
        raise ValueError(
            f"n must be between 1 and {len(full_product)} candidates; got {n}"
        )
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(full_product), size=n, replace=False)
    return tuple(full_product[index] for index in sorted(int(i) for i in chosen))
