"""Tests for the universe-selection stage."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from pathlib import Path

import pandas as pd
import pytest

from hive_abc.data.universe import (
    load_fixed_zscore_universe,
    select_universe_dynamic_zscore,
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_fixed_universe_ranks_by_zscore_and_drops_index_row(
    synthetic_zscore_file: Path,
) -> None:
    selected = load_fixed_zscore_universe(synthetic_zscore_file, top_n=3)
    assert selected == ["AAA", "BBB", "CCC"]
    assert "NASDAQ_100" not in load_fixed_zscore_universe(synthetic_zscore_file)


def test_fixed_universe_requires_expected_columns(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"Symbol": ["A"], "Score": [1.0]}).to_csv(bad, sep=";", index=False)
    with pytest.raises(ValueError, match="Ticker"):
        load_fixed_zscore_universe(bad)


def test_dynamic_selection_uses_only_pre_window(
    synthetic_prices_file: Path,
) -> None:
    selected = select_universe_dynamic_zscore(
        "2021-03-01",
        prices_file=synthetic_prices_file,
        min_days_pre=100,
        target_n=4,
    )
    assert len(selected) == 4
    assert len(set(selected)) == 4


def test_dynamic_selection_tops_up_when_correlation_rejects(
    synthetic_prices_file: Path,
) -> None:
    # A correlation threshold of 0 rejects every candidate after the first,
    # so the top-up loop must fill the remaining slots ignoring correlation.
    selected = select_universe_dynamic_zscore(
        "2021-03-01",
        prices_file=synthetic_prices_file,
        min_days_pre=100,
        target_n=5,
        corr_threshold=0.0,
    )
    assert len(selected) == 5


def test_dynamic_selection_without_history_raises(
    synthetic_prices_file: Path,
) -> None:
    with pytest.raises(RuntimeError, match="pre-window history"):
        select_universe_dynamic_zscore("2020-03-05", prices_file=synthetic_prices_file)
