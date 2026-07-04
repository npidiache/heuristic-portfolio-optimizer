"""Tests for the portfolio penalty terms."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from hive_abc.objectives.penalties import cardinality_penalty, hhi, l1_penalty


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_l1_penalty_sums_absolute_weights() -> None:
    assert l1_penalty(np.array([0.5, -0.2, 0.3])) == pytest.approx(1.0)


def test_hhi_bounds() -> None:
    assert hhi(np.full(4, 0.25)) == pytest.approx(0.25)
    assert hhi(np.array([1.0, 0.0, 0.0])) == pytest.approx(1.0)


def test_cardinality_penalty_is_zero_at_or_below_target() -> None:
    weights = np.array([0.4, 0.3, 0.2, 0.1])
    assert cardinality_penalty(weights, target_cardinality=4) == 0.0
    assert cardinality_penalty(weights, target_cardinality=8) == 0.0


def test_cardinality_penalty_grows_quadratically() -> None:
    weights = np.full(10, 0.1)
    assert cardinality_penalty(weights, target_cardinality=8) == pytest.approx(4.0)
    assert cardinality_penalty(weights, target_cardinality=7) == pytest.approx(9.0)


def test_threshold_excludes_dust_positions() -> None:
    weights = np.array([0.5, 0.5, 0.005, 0.001])
    assert cardinality_penalty(weights, target_cardinality=2, threshold=0.01) == 0.0


@given(
    weights=arrays(
        dtype=np.float64,
        shape=st.integers(min_value=1, max_value=30),
        elements=st.floats(min_value=0.0, max_value=1.0),
    ),
    target=st.integers(min_value=1, max_value=10),
)
def test_cardinality_penalty_is_never_negative(
    weights: np.ndarray, target: int
) -> None:
    assert cardinality_penalty(weights, target_cardinality=target) >= 0.0
