"""Tests for the significance and selection-integrity statistics."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math
from itertools import pairwise

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from scipy.stats import norm

from hive_abc import metrics
from hive_abc.metrics.stats import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    holm_bonferroni,
    probabilistic_sharpe_ratio,
    wilcoxon_sortino_matrix,
)


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


def test_psr_matches_hand_derived_normal_cdf_value() -> None:
    # Normal returns (skew 0, excess kurtosis 0 -> kurt 3) reduce the PSR
    # denominator to sqrt(1 + SR^2 / 2) = sqrt(1.005) for SR = 0.1.
    hand_z = 0.1 * math.sqrt(249.0) / math.sqrt(1.005)
    result = probabilistic_sharpe_ratio(
        observed=0.1, benchmark=0.0, n_obs=250, skew=0.0, excess_kurtosis=0.0
    )
    assert result == pytest.approx(float(norm.cdf(hand_z)), abs=1e-12)
    assert result == pytest.approx(0.9423, abs=1e-3)


def test_psr_converts_excess_kurtosis_to_fourth_moment_kurtosis() -> None:
    # skew -1, excess kurtosis 3 (kurt 6): denominator is
    # 1 - (-1)(0.1) + ((6 - 1) / 4)(0.1^2) = 1.1125. Feeding the excess value
    # into the (kurt - 1)/4 term instead would give 1.105 — this pins the
    # `kurt = excess_kurtosis + 3` conversion.
    hand_z = 0.1 * math.sqrt(249.0) / math.sqrt(1.1125)
    result = probabilistic_sharpe_ratio(
        observed=0.1, benchmark=0.0, n_obs=250, skew=-1.0, excess_kurtosis=3.0
    )
    assert result == pytest.approx(float(norm.cdf(hand_z)), abs=1e-12)


def test_psr_is_one_half_when_observed_equals_benchmark() -> None:
    result = probabilistic_sharpe_ratio(
        observed=0.7, benchmark=0.7, n_obs=100, skew=0.0, excess_kurtosis=0.0
    )
    assert result == pytest.approx(0.5)


def test_psr_increases_with_sample_length() -> None:
    values = [
        probabilistic_sharpe_ratio(
            observed=0.1, benchmark=0.0, n_obs=n, skew=0.0, excess_kurtosis=0.0
        )
        for n in (10, 50, 250, 1000)
    ]
    assert all(lo < hi for lo, hi in pairwise(values))


def test_psr_rejects_short_samples() -> None:
    with pytest.raises(ValueError, match="n_obs"):
        probabilistic_sharpe_ratio(
            observed=0.1, benchmark=0.0, n_obs=1, skew=0.0, excess_kurtosis=0.0
        )


def test_psr_rejects_non_positive_variance_term() -> None:
    # 1 - 4.0 * 1.0 + (2 / 4) * 1.0 = -2.5 under the square root.
    with pytest.raises(ValueError, match="variance"):
        probabilistic_sharpe_ratio(
            observed=1.0, benchmark=0.0, n_obs=250, skew=4.0, excess_kurtosis=0.0
        )


def test_expected_max_sharpe_matches_hand_value_for_ten_trials() -> None:
    gamma = 0.5772156649015329
    hand = (1.0 - gamma) * float(norm.ppf(1.0 - 1.0 / 10.0)) + gamma * float(
        norm.ppf(1.0 - 1.0 / (10.0 * math.e))
    )
    result = expected_max_sharpe(n_trials=10, sr_variance=1.0)
    assert result == pytest.approx(hand, abs=1e-12)
    assert result == pytest.approx(1.5746, abs=1e-3)


def test_expected_max_sharpe_increases_with_trials() -> None:
    values = [expected_max_sharpe(n_trials=n, sr_variance=1.0) for n in (2, 5, 10, 100)]
    assert all(lo < hi for lo, hi in pairwise(values))


def test_expected_max_sharpe_scales_with_sqrt_of_variance() -> None:
    quadrupled = expected_max_sharpe(n_trials=10, sr_variance=4.0)
    assert quadrupled == pytest.approx(2.0 * expected_max_sharpe(10, 1.0))


def test_expected_max_sharpe_is_zero_for_zero_variance() -> None:
    assert expected_max_sharpe(n_trials=10, sr_variance=0.0) == 0.0


def test_expected_max_sharpe_rejects_fewer_than_two_trials() -> None:
    # At n_trials=1 the Phi^-1(1 - 1/N) quantile degenerates to -inf, and
    # deflating a discovery against a single trial is meaningless.
    for n_trials in (1, 0, -3):
        with pytest.raises(ValueError, match="n_trials"):
            expected_max_sharpe(n_trials=n_trials, sr_variance=1.0)


def test_expected_max_sharpe_rejects_negative_variance() -> None:
    with pytest.raises(ValueError, match="sr_variance"):
        expected_max_sharpe(n_trials=10, sr_variance=-0.5)


def test_dsr_equals_psr_against_expected_max_benchmark() -> None:
    trial_srs = [0.5, 0.8, 1.1, 0.2, 0.9]
    benchmark = expected_max_sharpe(len(trial_srs), float(np.var(trial_srs)))
    expected = probabilistic_sharpe_ratio(
        observed=1.1, benchmark=benchmark, n_obs=250, skew=-0.3, excess_kurtosis=1.5
    )
    result = deflated_sharpe_ratio(
        observed_sr=1.1, trial_srs=trial_srs, n_obs=250, skew=-0.3, excess_kurtosis=1.5
    )
    assert result == pytest.approx(expected, abs=1e-15)


def test_dsr_decreases_as_trials_multiply() -> None:
    # Duplicating the trial set keeps the population variance identical but
    # doubles the trial count, so the deflation benchmark strictly rises.
    trials = [0.2, 0.6, 1.0]
    base = deflated_sharpe_ratio(1.0, trials, n_obs=250, skew=0.0, excess_kurtosis=0.0)
    doubled = deflated_sharpe_ratio(
        1.0, trials * 2, n_obs=250, skew=0.0, excess_kurtosis=0.0
    )
    assert doubled < base


def test_dsr_rejects_short_samples() -> None:
    with pytest.raises(ValueError, match="n_obs"):
        deflated_sharpe_ratio(1.0, [0.2, 0.6], n_obs=1, skew=0.0, excess_kurtosis=0.0)


def test_dsr_rejects_fewer_than_two_trials() -> None:
    for trial_srs in ([], [0.5]):
        with pytest.raises(ValueError, match="trial_srs"):
            deflated_sharpe_ratio(
                1.0, trial_srs, n_obs=250, skew=0.0, excess_kurtosis=0.0
            )


@given(
    observed_sr=st.floats(min_value=-3.0, max_value=3.0),
    trial_srs=st.lists(
        st.floats(min_value=-3.0, max_value=3.0), min_size=2, max_size=20
    ),
    n_obs=st.integers(min_value=2, max_value=5000),
)
def test_dsr_is_a_probability(
    observed_sr: float, trial_srs: list[float], n_obs: int
) -> None:
    result = deflated_sharpe_ratio(
        observed_sr, trial_srs, n_obs=n_obs, skew=0.0, excess_kurtosis=0.0
    )
    assert 0.0 <= result <= 1.0


def test_holm_rejects_more_than_plain_bonferroni() -> None:
    # Plain Bonferroni at alpha=0.05 compares every p against 0.0125 and
    # rejects only "a". Holm's step-down thresholds are 0.0125, 0.0167, 0.025,
    # then 0.05, so it also rejects "b" and "c".
    p_values = {"a": 0.01, "b": 0.015, "c": 0.02, "d": 0.5}
    assert holm_bonferroni(p_values) == {
        "a": True,
        "b": True,
        "c": True,
        "d": False,
    }


def test_holm_stops_at_first_non_rejection() -> None:
    # "c" (0.04) is below its own step threshold (0.05) but must stay
    # unrejected because "b" (0.03 > 0.025) already stopped the step-down.
    p_values = {"a": 0.01, "b": 0.03, "c": 0.04}
    assert holm_bonferroni(p_values) == {"a": True, "b": False, "c": False}


def test_holm_all_rejected_and_none_rejected_edges() -> None:
    assert holm_bonferroni({"a": 0.001, "b": 0.002, "c": 0.003}) == {
        "a": True,
        "b": True,
        "c": True,
    }
    assert holm_bonferroni({"a": 0.9, "b": 0.5}) == {"a": False, "b": False}


def test_holm_empty_mapping_returns_empty_dict() -> None:
    assert holm_bonferroni({}) == {}


def test_holm_rejects_invalid_p_values() -> None:
    for bad in (-0.1, 1.5):
        with pytest.raises(ValueError, match="p-value"):
            holm_bonferroni({"a": bad, "b": 0.5})


@given(
    p_values=st.dictionaries(
        st.text(min_size=1, max_size=8),
        st.floats(min_value=0.0, max_value=1.0),
        max_size=8,
    ),
    alpha_a=st.floats(min_value=0.001, max_value=0.999),
    alpha_b=st.floats(min_value=0.001, max_value=0.999),
)
def test_holm_rejections_are_monotone_in_alpha(
    p_values: dict[str, float], alpha_a: float, alpha_b: float
) -> None:
    low, high = sorted((alpha_a, alpha_b))
    at_low = holm_bonferroni(p_values, alpha=low)
    at_high = holm_bonferroni(p_values, alpha=high)
    assert all(at_high[label] for label, rejected in at_low.items() if rejected)


def test_selection_statistics_are_exported_from_metrics_package() -> None:
    exported = {
        "deflated_sharpe_ratio",
        "expected_max_sharpe",
        "holm_bonferroni",
        "probabilistic_sharpe_ratio",
    }
    assert exported <= set(metrics.__all__)
