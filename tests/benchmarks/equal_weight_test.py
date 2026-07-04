"""Tests for the 1/N benchmark."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import numpy as np
import pytest

from hive_abc.benchmarks.equal_weight import EqualWeight
from hive_abc.core.types import Bounds


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_returns_equal_weights_and_objective_value() -> None:
    result = EqualWeight().optimize(
        lambda w: float(np.sum(w**2)), Bounds.box(4), seed=None
    )
    assert result.best_vector == pytest.approx([0.25] * 4)
    assert result.best_value == pytest.approx(0.25)
    assert result.n_evaluations == 1
    assert result.best_per_iteration == (result.best_value,)
