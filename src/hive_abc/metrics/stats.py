"""Statistical significance tests used in the thesis result analysis."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import math
from collections.abc import Mapping, Sequence
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import norm, wilcoxon


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def wilcoxon_sortino_matrix(sortino_per_seed: pd.DataFrame) -> pd.DataFrame:
    """
    Pairwise Wilcoxon signed-rank tests over per-seed Sortino ratios.

    Replicates the thesis analysis: for every pair of algorithms, test the
    per-seed Sortino samples and report the p-value, significance at 5%, and
    the higher-mean algorithm as the winner. Pairs whose samples are
    identical (zero differences, e.g., two deterministic benchmarks) are
    reported with a NaN p-value.

    Args:
        sortino_per_seed: One column per algorithm, one row per seed.

    Returns:
        DataFrame with columns `a`, `b`, `p_value`, `significant`, `winner`.

    Raises:
        ValueError: If fewer than two algorithm columns are provided.
    """
    algorithms = list(sortino_per_seed.columns)
    if len(algorithms) < 2:
        raise ValueError("need at least two algorithms to compare")

    rows: list[dict[str, object]] = []
    for a, b in combinations(algorithms, 2):
        sample_a = sortino_per_seed[a].to_numpy(dtype=float)
        sample_b = sortino_per_seed[b].to_numpy(dtype=float)
        if np.all(sample_a == sample_b):
            # All differences are zero — identical samples, no test possible.
            # (Older scipy raised ValueError here; newer versions return a
            # degenerate statistic, so the case is detected explicitly.)
            p_value = float("nan")
        else:
            _, raw_p = wilcoxon(sample_a, sample_b)
            p_value = float(raw_p)
        winner = a if np.mean(sample_a) >= np.mean(sample_b) else b
        rows.append(
            {
                "a": a,
                "b": b,
                "p_value": p_value,
                "significant": bool(p_value < 0.05) if p_value == p_value else False,
                "winner": winner,
            }
        )
    return pd.DataFrame(rows)


def probabilistic_sharpe_ratio(
    observed: float,
    benchmark: float,
    n_obs: int,
    skew: float,
    excess_kurtosis: float,
) -> float:
    """
    Probability that the true Sharpe ratio exceeds a benchmark.

    Probabilistic Sharpe Ratio (PSR) of Bailey & López de Prado (2014):
    `Phi(((observed - benchmark) * sqrt(n_obs - 1)) / sigma)` with
    `sigma = sqrt(1 - skew * observed + ((kurt - 1) / 4) * observed^2)`,
    where `kurt` is the fourth-moment kurtosis (3 for Normal returns). This
    function takes EXCESS kurtosis (0 for Normal returns) and converts via
    `kurt = excess_kurtosis + 3`; mixing up the two conventions is the
    classic PSR implementation bug.

    Args:
        observed: Observed Sharpe ratio, in the periodicity of the returns
            it was estimated from (e.g. daily).
        benchmark: Benchmark Sharpe ratio `SR*` to test against.
        n_obs: Number of return observations behind `observed`.
        skew: Sample skewness of the returns (0 for Normal returns).
        excess_kurtosis: Sample excess kurtosis of the returns (0 for
            Normal returns).

    Returns:
        `P[SR_true > benchmark]`, a probability in `[0, 1]`.

    Raises:
        ValueError: If `n_obs < 2`, or if the estimator-variance term under
            the square root is not strictly positive.
    """
    if n_obs < 2:
        raise ValueError(f"n_obs must be at least 2, got {n_obs}")
    kurtosis = excess_kurtosis + 3.0
    variance_term = 1.0 - skew * observed + ((kurtosis - 1.0) / 4.0) * observed**2
    if variance_term <= 0.0:
        raise ValueError(
            f"non-positive Sharpe estimator variance term {variance_term} "
            f"(skew {skew}, excess kurtosis {excess_kurtosis})"
        )
    z_score = (observed - benchmark) * math.sqrt(n_obs - 1.0)
    return float(norm.cdf(z_score / math.sqrt(variance_term)))


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """
    Expected maximum Sharpe ratio across trials under the zero-skill null.

    False Strategy Theorem approximation of Bailey & López de Prado (2014):
    `sqrt(sr_variance) * ((1 - g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(Ne)))`
    with `g` the Euler–Mascheroni constant (~0.5772). The bar rises with both
    the number of trials and their dispersion. At `n_trials == 1` the first
    quantile degenerates (`Phi^-1(0) = -inf`) and deflating against a single
    trial is meaningless, so at least two trials are required.

    Args:
        n_trials: Number of trials behind the discovery.
        sr_variance: Variance of the Sharpe ratios across the trials.

    Returns:
        The expected maximum Sharpe ratio if every trial had zero true skill.

    Raises:
        ValueError: If `n_trials < 2` or `sr_variance < 0`.
    """
    if n_trials < 2:
        raise ValueError(f"n_trials must be at least 2, got {n_trials}")
    if sr_variance < 0.0:
        raise ValueError(f"sr_variance must be non-negative, got {sr_variance}")
    gamma = float(np.euler_gamma)
    high_quantile = float(norm.ppf(1.0 - 1.0 / n_trials))
    tail_quantile = float(norm.ppf(1.0 - 1.0 / (n_trials * math.e)))
    return math.sqrt(sr_variance) * (
        (1.0 - gamma) * high_quantile + gamma * tail_quantile
    )


def deflated_sharpe_ratio(
    observed_sr: float,
    trial_srs: Sequence[float],
    n_obs: int,
    skew: float,
    excess_kurtosis: float,
) -> float:
    """
    Probability the observed Sharpe ratio survives its selection haircut.

    Deflated Sharpe Ratio (DSR) of Bailey & López de Prado (2014): the
    probabilistic Sharpe ratio evaluated against
    `expected_max_sharpe(len(trial_srs), Var[trial_srs])`, so the benchmark
    prices in the multiple testing behind the discovery. The trial dispersion
    uses the population variance (`ddof=0`) of `trial_srs`, the plug-in
    estimator of the original paper.

    Args:
        observed_sr: Observed (selected) Sharpe ratio, in the periodicity of
            the returns it was estimated from.
        trial_srs: Sharpe ratios of all trials in the search that produced
            `observed_sr`, including the selected one.
        n_obs: Number of return observations behind `observed_sr`.
        skew: Sample skewness of the selected strategy's returns.
        excess_kurtosis: Sample excess kurtosis of the selected strategy's
            returns (0 for Normal returns).

    Returns:
        `P[SR_true > E[max SR]]`, a probability in `[0, 1]`.

    Raises:
        ValueError: If `n_obs < 2` or fewer than two trial Sharpe ratios are
            provided (deflation against a single trial is meaningless).
    """
    trials = np.asarray(trial_srs, dtype=float)
    if trials.size < 2:
        raise ValueError(f"trial_srs needs at least two entries, got {trials.size}")
    benchmark = expected_max_sharpe(int(trials.size), float(np.var(trials)))
    return probabilistic_sharpe_ratio(
        observed_sr, benchmark, n_obs, skew, excess_kurtosis
    )


def holm_bonferroni(
    p_values: Mapping[str, float], alpha: float = 0.05
) -> dict[str, bool]:
    """
    Holm's step-down multiple-comparison correction.

    Holm (1979): sort the p-values ascending and compare the i-th smallest
    (1-based) against `alpha / (m - i + 1)`; reject while the comparison
    holds and stop at the first failure, leaving it and every larger p-value
    unrejected. Controls the family-wise error rate at `alpha` and rejects
    at least as much as the plain Bonferroni correction.

    Args:
        p_values: Mapping from hypothesis label to raw (uncorrected) p-value.
        alpha: Family-wise error rate to control.

    Returns:
        Mapping from hypothesis label to whether it is rejected at `alpha`.

    Raises:
        ValueError: If any p-value lies outside `[0, 1]`.
    """
    for label, p_value in p_values.items():
        if not 0.0 <= p_value <= 1.0:
            raise ValueError(f"p-value for {label!r} outside [0, 1]: {p_value}")
    total = len(p_values)
    rejected = dict.fromkeys(p_values, False)
    ascending = sorted(p_values.items(), key=lambda item: item[1])
    for rank, (label, p_value) in enumerate(ascending):
        if p_value > alpha / (total - rank):
            break
        rejected[label] = True
    return rejected
