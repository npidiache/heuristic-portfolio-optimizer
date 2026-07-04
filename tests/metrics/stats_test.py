"""Tests for the Wilcoxon significance matrix."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math

import numpy as np
import pandas as pd
import pytest

from hive_abc.metrics.stats import wilcoxon_sortino_matrix


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_pairwise_matrix_covers_all_combinations() -> None:
    rng = np.random.default_rng(1)
    frame = pd.DataFrame(
        {
            "A": rng.normal(2.0, 0.1, size=20),
            "B": rng.normal(1.0, 0.1, size=20),
            "C": rng.normal(1.5, 0.1, size=20),
        }
    )
    result = wilcoxon_sortino_matrix(frame)
    assert len(result) == 3  # C(3, 2)
    ab = result[(result["a"] == "A") & (result["b"] == "B")].iloc[0]
    assert bool(ab["significant"])
    assert ab["winner"] == "A"


def test_identical_columns_yield_nan_pvalue() -> None:
    frame = pd.DataFrame({"X": [1.0, 2.0, 3.0], "Y": [1.0, 2.0, 3.0]})
    row = wilcoxon_sortino_matrix(frame).iloc[0]
    assert math.isnan(row["p_value"])
    assert not bool(row["significant"])


def test_requires_two_algorithms() -> None:
    with pytest.raises(ValueError, match="two algorithms"):
        wilcoxon_sortino_matrix(pd.DataFrame({"A": [1.0, 2.0]}))
