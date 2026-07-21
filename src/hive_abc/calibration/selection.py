"""Configuration selection that prices in the multiple testing behind it.

Candidates are ranked by mean out-of-sample Sortino; each challenger is
tested against the baseline with a paired Wilcoxon signed-rank test, the
family of p-values is corrected with Holm's step-down, and the winner's
estimate is deflated against the whole candidate set (Bailey & Lopez de
Prado's DSR). A study where nothing beats the baseline is a valid result:
the report still names the best candidate but flags it as not significant.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from hive_abc.calibration.runner import CalibrationStudy
from hive_abc.metrics import (
    deflated_sharpe_ratio,
    holm_bonferroni,
    wilcoxon_sortino_matrix,
)


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SelectionReport:
    """
    Outcome of selecting a configuration from a calibration study.

    Attributes:
        recommended: Label of the candidate with the highest mean OOS
            Sortino (ties resolve to the earliest-seen candidate).
        recommended_params: Parameter mapping of the recommended candidate.
        baseline: Label the challengers were tested against.
        significant: Whether the recommendation is a non-baseline candidate
            whose Wilcoxon-vs-baseline test survives the Holm correction.
            `False` whenever the baseline itself wins (honest negative).
        deflated_sharpe: Deflated ratio of the winner against the whole
            candidate set, or `None` when the study cannot support it
            (fewer than two candidates, or fewer than two OOS observations).
        mean_oos_sortino: Mean OOS Sortino per candidate label.
        p_values: Raw Wilcoxon-vs-baseline p-value per challenger label;
            undefined tests (identical samples) are reported as 1.0.
        rejected: Holm step-down rejection decision per challenger label.
    """

    recommended: str
    recommended_params: Mapping[str, object]
    baseline: str
    significant: bool
    deflated_sharpe: float | None
    mean_oos_sortino: Mapping[str, float]
    p_values: Mapping[str, float]
    rejected: Mapping[str, bool]


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def select_configuration(
    study: CalibrationStudy, baseline: str, alpha: float = 0.05
) -> SelectionReport:
    """
    Ranks a study's candidates and tests the family against a baseline.

    Args:
        study: Calibration study to select from.
        baseline: Label of the incumbent candidate (must be in the study).
        alpha: Family-wise error rate for the Holm correction.

    Returns:
        The frozen selection report.

    Raises:
        ValueError: If `baseline` is not a candidate of the study, or the
            candidates carry unequal OOS sample counts (the paired tests
            need aligned samples).
    """
    samples = study.oos_sortino_by_label()
    if baseline not in samples:
        raise ValueError(
            f"baseline {baseline!r} is not in the study; candidates are "
            f"{sorted(samples)}"
        )
    sample_sizes = {label: len(values) for label, values in samples.items()}
    if len(set(sample_sizes.values())) != 1:
        raise ValueError(f"candidates carry unequal sample counts: {sample_sizes}")

    means = {label: float(np.mean(values)) for label, values in samples.items()}
    recommended = max(means, key=lambda label: means[label])
    p_values = _wilcoxon_versus_baseline(samples, baseline)
    rejected = holm_bonferroni(p_values, alpha=alpha)
    significant = recommended != baseline and rejected[recommended]
    recommended_params = next(
        trial.candidate for trial in study.trials if trial.label == recommended
    )
    return SelectionReport(
        recommended=recommended,
        recommended_params=recommended_params,
        baseline=baseline,
        significant=significant,
        deflated_sharpe=_deflated_sharpe_of(recommended, means, study),
        mean_oos_sortino=means,
        p_values=p_values,
        rejected=rejected,
    )


def _wilcoxon_versus_baseline(
    samples: Mapping[str, tuple[float, ...]], baseline: str
) -> dict[str, float]:
    """
    Paired Wilcoxon p-values of every challenger against the baseline.

    Reuses `hive_abc.metrics.wilcoxon_sortino_matrix`; undefined tests
    (identical samples, NaN p-value) are mapped to 1.0 — no evidence of a
    difference — so the Holm correction stays well-defined.

    Args:
        samples: Aligned OOS Sortino samples per candidate label.
        baseline: Label to test the other candidates against.

    Returns:
        Mapping from challenger label to its raw p-value; empty when the
        study only contains the baseline.
    """
    if len(samples) < 2:
        return {}
    frame = pd.DataFrame({label: list(values) for label, values in samples.items()})
    matrix = wilcoxon_sortino_matrix(frame)
    subset = matrix[(matrix["a"] == baseline) | (matrix["b"] == baseline)]
    p_values: dict[str, float] = {}
    for a, b, p_value in zip(subset["a"], subset["b"], subset["p_value"], strict=True):
        challenger = str(b if a == baseline else a)
        raw_p = float(p_value)
        p_values[challenger] = 1.0 if math.isnan(raw_p) else raw_p
    return p_values


def _deflated_sharpe_of(
    winner: str, means: Mapping[str, float], study: CalibrationStudy
) -> float | None:
    """
    Deflates the winner's mean OOS Sortino against the candidate set.

    Each candidate's mean OOS Sortino counts as one trial (selection happens
    across candidates), and the winner's observation count is the total of
    its distinct OOS days across splits. Higher return moments are not
    tracked per trial, so the PSR inside the deflation assumes Gaussian OOS
    returns (skew 0, excess kurtosis 0) — the multiplicity haircut, not the
    moment adjustment, is the term calibration must price in.

    Args:
        winner: Label of the recommended candidate.
        means: Mean OOS Sortino per candidate label.
        study: The study the means were computed from.

    Returns:
        The deflated ratio, or `None` when the study has fewer than two
        candidates or the winner has fewer than two OOS observations —
        `deflated_sharpe_ratio` rejects both degenerate cases by design.
    """
    if len(means) < 2:
        return None
    n_obs = sum(trial.oos_n_obs for trial in study.trials if trial.label == winner)
    if n_obs < 2:
        return None
    return deflated_sharpe_ratio(
        observed_sr=means[winner],
        trial_srs=tuple(means.values()),
        n_obs=n_obs,
        skew=0.0,
        excess_kurtosis=0.0,
    )
