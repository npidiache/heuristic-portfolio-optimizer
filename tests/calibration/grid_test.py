"""Tests for the calibration parameter grids and candidate sampling."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import pytest

from hive_abc.calibration.grid import (
    ParameterGrid,
    candidate_label,
    sample_candidates,
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_candidates_is_the_cartesian_product_in_deterministic_order() -> None:
    grid = ParameterGrid({"colony_size": (15, 25), "fraction": (0.15, 0.25)})
    assert grid.candidates() == (
        {"colony_size": 15, "fraction": 0.15},
        {"colony_size": 15, "fraction": 0.25},
        {"colony_size": 25, "fraction": 0.15},
        {"colony_size": 25, "fraction": 0.25},
    )
    # Two calls must yield the exact same ordering (deterministic enumeration).
    assert grid.candidates() == grid.candidates()


def test_single_axis_grid_yields_one_candidate_per_value() -> None:
    grid = ParameterGrid({"colony_size": (10, 20, 30)})
    assert grid.candidates() == (
        {"colony_size": 10},
        {"colony_size": 20},
        {"colony_size": 30},
    )


def test_empty_grid_rejected() -> None:
    with pytest.raises(ValueError, match="at least one parameter"):
        ParameterGrid({})


def test_empty_axis_rejected() -> None:
    with pytest.raises(ValueError, match="colony_size"):
        ParameterGrid({"colony_size": ()})


def test_duplicate_axis_values_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ParameterGrid({"fraction": (0.15, 0.15)})


def test_sample_candidates_is_reproducible_under_the_same_seed() -> None:
    grid = ParameterGrid({"colony_size": (15, 25), "fraction": (0.15, 0.25)})
    first = sample_candidates(grid, n=3, seed=0)
    second = sample_candidates(grid, n=3, seed=0)
    assert first == second
    assert len(first) == 3


def test_sample_candidates_has_no_duplicates_and_is_a_subset() -> None:
    grid = ParameterGrid({"colony_size": (15, 25, 35), "fraction": (0.15, 0.25)})
    sample = sample_candidates(grid, n=4, seed=7)
    keys = [tuple(sorted(candidate.items())) for candidate in sample]
    assert len(set(keys)) == len(sample)
    full_product = grid.candidates()
    assert all(candidate in full_product for candidate in sample)


def test_sampling_every_candidate_returns_the_full_grid_in_order() -> None:
    grid = ParameterGrid({"colony_size": (15, 25), "fraction": (0.15, 0.25)})
    assert sample_candidates(grid, n=4, seed=3) == grid.candidates()


def test_sample_candidates_rejects_invalid_sizes() -> None:
    grid = ParameterGrid({"colony_size": (15, 25)})
    with pytest.raises(ValueError, match="n must be"):
        sample_candidates(grid, n=0, seed=0)
    with pytest.raises(ValueError, match="n must be"):
        sample_candidates(grid, n=3, seed=0)


def test_candidate_label_is_canonical_and_key_order_independent() -> None:
    label = candidate_label({"fraction": 0.15, "colony_size": 15})
    assert label == "colony_size=15,fraction=0.15"
    assert label == candidate_label({"colony_size": 15, "fraction": 0.15})
