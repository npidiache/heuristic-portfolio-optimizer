"""Statistical significance tests used in the thesis result analysis."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


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
