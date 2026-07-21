"""Tests for calibration selection with multiple-testing accounting."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from collections.abc import Mapping
from statistics import fmean

import pandas as pd
import pytest

from hive_abc.calibration.runner import CalibrationStudy, TrialResult
from hive_abc.calibration.selection import select_configuration
from hive_abc.calibration.splits import WalkForwardSplit
from hive_abc.metrics import deflated_sharpe_ratio

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Per-candidate OOS Sortino samples are split-major: one tuple per split,
#   one entry per seed, mirroring the runner's trial layout.
# --------------------------------------------------------------------------------------
BASELINE = (1.00, 1.10, 0.90, 1.05, 0.95, 1.02)

WINNER = tuple(
    base + delta
    for base, delta in zip(BASELINE, (0.40, 0.45, 0.50, 0.55, 0.60, 0.65), strict=True)
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def _split(offset_days: int) -> WalkForwardSplit:
    base = pd.Timestamp("2021-01-04") + pd.Timedelta(days=offset_days)
    return WalkForwardSplit(
        train_start=base,
        train_end=base + pd.Timedelta(days=60),
        test_start=base + pd.Timedelta(days=66),
        test_end=base + pd.Timedelta(days=90),
    )


def _candidate_trials(
    label: str,
    params: Mapping[str, object],
    sortinos: tuple[float, ...],
    n_splits: int = 2,
    oos_n_obs: int = 21,
) -> tuple[TrialResult, ...]:
    """Distributes a flat per-seed sample over `n_splits` equal trials."""
    seeds_per_split = len(sortinos) // n_splits
    return tuple(
        TrialResult(
            candidate=params,
            label=label,
            split=_split(offset_days=100 * split_index),
            in_sample_fitness=tuple(0.0 for _ in range(seeds_per_split)),
            oos_sortino=sortinos[
                split_index * seeds_per_split : (split_index + 1) * seeds_per_split
            ],
            scout_activations=tuple(0 for _ in range(seeds_per_split)),
            oos_n_obs=oos_n_obs,
        )
        for split_index in range(n_splits)
    )


def _study(*trial_groups: tuple[TrialResult, ...]) -> CalibrationStudy:
    trials = tuple(trial for group in trial_groups for trial in group)
    return CalibrationStudy(trials=trials, seeds=(0, 1, 2))


def test_clear_winner_is_recommended_significant_and_deflated() -> None:
    study = _study(
        _candidate_trials("colony_size=6", {"colony_size": 6}, BASELINE),
        _candidate_trials("colony_size=8", {"colony_size": 8}, WINNER),
    )
    report = select_configuration(study, baseline="colony_size=6")

    assert report.recommended == "colony_size=8"
    assert report.recommended_params == {"colony_size": 8}
    assert report.baseline == "colony_size=6"
    assert report.significant is True
    assert report.mean_oos_sortino["colony_size=6"] == pytest.approx(fmean(BASELINE))
    assert report.mean_oos_sortino["colony_size=8"] == pytest.approx(fmean(WINNER))
    assert set(report.p_values) == {"colony_size=8"}
    assert 0.0 < report.p_values["colony_size=8"] < 0.05
    assert report.rejected == {"colony_size=8": True}
    # The report is a frozen dataclass.
    dataclass_params = getattr(type(report), "__dataclass_params__", None)
    assert dataclass_params is not None and dataclass_params.frozen


def test_deflated_sharpe_matches_the_metrics_api_recomputation() -> None:
    study = _study(
        _candidate_trials("colony_size=6", {"colony_size": 6}, BASELINE),
        _candidate_trials("colony_size=8", {"colony_size": 8}, WINNER),
    )
    report = select_configuration(study, baseline="colony_size=6")

    # One trial SR per candidate; the winner's estimate spans 2 x 21 OOS days.
    expected = deflated_sharpe_ratio(
        observed_sr=fmean(WINNER),
        trial_srs=[fmean(BASELINE), fmean(WINNER)],
        n_obs=42,
        skew=0.0,
        excess_kurtosis=0.0,
    )
    assert report.deflated_sharpe == pytest.approx(expected)


def test_no_candidate_beating_baseline_is_an_honest_negative() -> None:
    worse = tuple(
        base - delta
        for base, delta in zip(
            BASELINE, (0.40, 0.45, 0.50, 0.55, 0.60, 0.65), strict=True
        )
    )
    study = _study(
        _candidate_trials("colony_size=6", {"colony_size": 6}, BASELINE),
        _candidate_trials("colony_size=8", {"colony_size": 8}, worse),
    )
    report = select_configuration(study, baseline="colony_size=6")

    assert report.recommended == "colony_size=6"
    assert report.recommended_params == {"colony_size": 6}
    assert report.significant is False
    assert report.deflated_sharpe is not None


def test_holm_step_down_is_applied_across_candidates() -> None:
    baseline = (1.00, 1.10, 0.90, 1.05, 0.95, 1.02, 1.08, 1.01)
    winner = tuple(
        base + delta
        for base, delta in zip(
            baseline,
            (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
            strict=True,
        )
    )
    noise = tuple(
        base + delta
        for base, delta in zip(
            baseline,
            (0.10, -0.11, 0.12, -0.13, 0.14, -0.15, 0.16, -0.17),
            strict=True,
        )
    )
    study = _study(
        _candidate_trials("colony_size=6", {"colony_size": 6}, baseline),
        _candidate_trials("colony_size=8", {"colony_size": 8}, winner),
        _candidate_trials("colony_size=10", {"colony_size": 10}, noise),
    )
    report = select_configuration(study, baseline="colony_size=6")

    assert report.recommended == "colony_size=8"
    assert report.significant is True
    assert report.rejected == {"colony_size=8": True, "colony_size=10": False}


def test_candidate_identical_to_baseline_gets_p_value_one() -> None:
    study = _study(
        _candidate_trials("colony_size=6", {"colony_size": 6}, BASELINE),
        _candidate_trials("colony_size=8", {"colony_size": 8}, BASELINE),
    )
    report = select_configuration(study, baseline="colony_size=6")

    # Identical samples make Wilcoxon undefined (NaN); the report treats that
    # as "no evidence of a difference" rather than crashing Holm.
    assert report.p_values == {"colony_size=8": 1.0}
    assert report.rejected == {"colony_size=8": False}
    assert report.recommended == "colony_size=6"
    assert report.significant is False
    assert report.deflated_sharpe is not None


def test_single_candidate_study_reports_gracefully() -> None:
    study = _study(_candidate_trials("colony_size=6", {"colony_size": 6}, BASELINE))
    report = select_configuration(study, baseline="colony_size=6")

    assert report.recommended == "colony_size=6"
    assert report.recommended_params == {"colony_size": 6}
    assert report.significant is False
    assert report.p_values == {}
    assert report.rejected == {}
    assert report.deflated_sharpe is None


def test_unknown_baseline_rejected() -> None:
    study = _study(_candidate_trials("colony_size=6", {"colony_size": 6}, BASELINE))
    with pytest.raises(ValueError, match="baseline"):
        select_configuration(study, baseline="colony_size=99")


def test_inconsistent_sample_counts_rejected() -> None:
    study = _study(
        _candidate_trials("colony_size=6", {"colony_size": 6}, BASELINE),
        _candidate_trials("colony_size=8", {"colony_size": 8}, WINNER[:3], n_splits=1),
    )
    with pytest.raises(ValueError, match="sample"):
        select_configuration(study, baseline="colony_size=6")


def test_deflated_sharpe_is_none_without_enough_oos_observations() -> None:
    study = _study(
        _candidate_trials("colony_size=6", {"colony_size": 6}, BASELINE, oos_n_obs=0),
        _candidate_trials("colony_size=8", {"colony_size": 8}, WINNER, oos_n_obs=0),
    )
    report = select_configuration(study, baseline="colony_size=6")

    assert report.recommended == "colony_size=8"
    assert report.deflated_sharpe is None
