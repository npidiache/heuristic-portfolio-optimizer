"""Leak-free walk-forward splits over a trading-day index.

Windows are measured in index positions (trading days, not calendar days) and
generated left to right: `train_days` of history, an `embargo_days` gap that
absorbs serial correlation at the boundary, then `test_days` of out-of-sample
data. Hand-rolled on purpose — the package keeps its cvxpy/numpy/pandas/scipy
dependency set instead of pulling in sklearn for one splitter.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from dataclasses import dataclass

import pandas as pd


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class WalkForwardSplit:
    """
    One train/test window pair with inclusive timestamp endpoints.

    Attributes:
        train_start: First trading day of the training window.
        train_end: Last trading day of the training window.
        test_start: First trading day of the test window.
        test_end: Last trading day of the test window.

    Raises:
        ValueError: If the endpoints are not chronological, i.e. not
            `train_start <= train_end < test_start <= test_end` (the strict
            middle inequality is the no-look-ahead invariant).
    """

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp

    def __post_init__(self) -> None:
        """Validates the chronological ordering of the window endpoints."""
        ordered = self.train_start <= self.train_end < self.test_start <= self.test_end
        if not ordered:
            raise ValueError(
                "split endpoints must be chronological "
                "(train_start <= train_end < test_start <= test_end); got "
                f"{self.train_start} / {self.train_end} / "
                f"{self.test_start} / {self.test_end}"
            )


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def walk_forward_splits(
    index: pd.DatetimeIndex,
    train_days: int = 252,
    test_days: int = 63,
    step_days: int = 63,
    embargo_days: int = 5,
) -> tuple[WalkForwardSplit, ...]:
    """
    Generates chronological walk-forward splits over a trading-day index.

    Each split trains on `train_days` positions, skips `embargo_days`
    positions, and tests on the next `test_days` positions; successive splits
    advance by `step_days`. No split reaches past the end of the index, and
    every train day strictly precedes every test day of its split.

    Args:
        index: Sorted, duplicate-free trading-day index to split.
        train_days: Training-window length in index positions.
        test_days: Test-window length in index positions.
        step_days: Advance between consecutive splits, in index positions.
        embargo_days: Positions skipped between train end and test start.

    Returns:
        The splits, oldest first.

    Raises:
        ValueError: If a window parameter is out of range, the index is not
            sorted or has duplicates, or the index is too short for even one
            split.
    """
    if train_days < 1:
        raise ValueError(f"train_days must be >= 1; got {train_days}")
    if test_days < 1:
        raise ValueError(f"test_days must be >= 1; got {test_days}")
    if step_days < 1:
        raise ValueError(f"step_days must be >= 1; got {step_days}")
    if embargo_days < 0:
        raise ValueError(f"embargo_days must be >= 0; got {embargo_days}")
    if not index.is_monotonic_increasing:
        raise ValueError("index must be monotonic increasing")
    if index.has_duplicates:
        raise ValueError("index must not contain duplicate timestamps")

    window = train_days + embargo_days + test_days
    if len(index) < window:
        raise ValueError(
            f"index too short for one split: {len(index)} days < "
            f"{train_days} train + {embargo_days} embargo + {test_days} test"
        )

    splits: list[WalkForwardSplit] = []
    for start in range(0, len(index) - window + 1, step_days):
        test_start = start + train_days + embargo_days
        splits.append(
            WalkForwardSplit(
                train_start=index[start],
                train_end=index[start + train_days - 1],
                test_start=index[test_start],
                test_end=index[test_start + test_days - 1],
            )
        )
    return tuple(splits)
