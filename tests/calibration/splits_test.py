"""Tests for the leak-free walk-forward split generator."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from itertools import pairwise

import pandas as pd
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from hive_abc.calibration.splits import WalkForwardSplit, walk_forward_splits

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
INDEX = pd.bdate_range("2018-01-01", periods=700)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_default_windows_are_chronological_and_within_the_index() -> None:
    splits = walk_forward_splits(
        INDEX, train_days=252, test_days=63, step_days=63, embargo_days=5
    )
    # floor((700 - (252 + 5 + 63)) / 63) + 1 anchored windows fit.
    assert len(splits) == 7
    for split in splits:
        assert split.train_start < split.train_end
        assert split.train_end < split.test_start
        assert split.test_start < split.test_end
        assert split.test_end <= INDEX[-1]
    starts = [split.train_start for split in splits]
    assert starts == sorted(starts)


def test_test_segments_do_not_overlap_when_step_matches_test_days() -> None:
    splits = walk_forward_splits(
        INDEX, train_days=252, test_days=63, step_days=63, embargo_days=5
    )
    for previous, current in pairwise(splits):
        assert current.test_start > previous.test_end


def test_embargo_leaves_a_gap_between_train_end_and_test_start() -> None:
    embargo_days = 5
    splits = walk_forward_splits(
        INDEX, train_days=252, test_days=63, step_days=63, embargo_days=embargo_days
    )
    for split in splits:
        assert split.test_start > split.train_end
        skipped = INDEX[(INDEX > split.train_end) & (INDEX < split.test_start)]
        assert len(skipped) == embargo_days


def test_window_day_counts_match_the_requested_sizes() -> None:
    splits = walk_forward_splits(
        INDEX, train_days=60, test_days=20, step_days=20, embargo_days=3
    )
    for split in splits:
        train = INDEX[(INDEX >= split.train_start) & (INDEX <= split.train_end)]
        test = INDEX[(INDEX >= split.test_start) & (INDEX <= split.test_end)]
        assert len(train) == 60
        assert len(test) == 20


def test_too_short_index_rejected() -> None:
    short = pd.bdate_range("2018-01-01", periods=100)
    with pytest.raises(ValueError, match="too short"):
        walk_forward_splits(
            short, train_days=252, test_days=63, step_days=63, embargo_days=5
        )


def test_non_positive_window_parameters_rejected() -> None:
    for override in (
        {"train_days": 0},
        {"test_days": 0},
        {"step_days": 0},
        {"embargo_days": -1},
    ):
        params = {
            "train_days": 60,
            "test_days": 20,
            "step_days": 20,
            "embargo_days": 0,
        } | override
        with pytest.raises(ValueError, match=next(iter(override))):
            walk_forward_splits(INDEX, **params)


def test_unsorted_or_duplicated_index_rejected() -> None:
    backwards = INDEX[::-1]
    with pytest.raises(ValueError, match="monotonic"):
        walk_forward_splits(backwards, train_days=60, test_days=20, step_days=20)
    duplicated = pd.DatetimeIndex(INDEX[:100].append(INDEX[99:100]))
    with pytest.raises(ValueError, match="duplicate"):
        walk_forward_splits(duplicated, train_days=60, test_days=20, step_days=20)


def test_split_dataclass_rejects_non_chronological_windows() -> None:
    with pytest.raises(ValueError, match="chronological"):
        WalkForwardSplit(
            train_start=pd.Timestamp("2020-01-01"),
            train_end=pd.Timestamp("2020-06-01"),
            test_start=pd.Timestamp("2020-06-01"),
            test_end=pd.Timestamp("2020-09-01"),
        )


@given(
    n_days=st.integers(min_value=10, max_value=400),
    train_days=st.integers(min_value=1, max_value=120),
    test_days=st.integers(min_value=1, max_value=60),
    step_days=st.integers(min_value=1, max_value=60),
    embargo_days=st.integers(min_value=0, max_value=10),
)
def test_property_every_train_day_precedes_every_test_day(
    n_days: int, train_days: int, test_days: int, step_days: int, embargo_days: int
) -> None:
    # The no-look-ahead invariant, matching data/universe.py's discipline.
    assume(n_days >= train_days + embargo_days + test_days)
    index = pd.bdate_range("2015-01-05", periods=n_days)
    for split in walk_forward_splits(
        index,
        train_days=train_days,
        test_days=test_days,
        step_days=step_days,
        embargo_days=embargo_days,
    ):
        train = index[(index >= split.train_start) & (index <= split.train_end)]
        test = index[(index >= split.test_start) & (index <= split.test_end)]
        assert train.max() < test.min()
