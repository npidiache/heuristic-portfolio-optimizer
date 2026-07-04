"""Asset-universe selection: dynamic market z-score and fixed fundamentals.

Both selectors reproduce the thesis's stock-picking stage exactly
(`select_universe_by_zscores` / `select_universe_from_zscore_file` in the
frozen harness): a dynamic ex-ante screen over the pre-period window, and a
static top-N read from the fundamentals z-score file.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from hive_abc.data.loading import (
    FROZEN_PRICES,
    FROZEN_ZSCORE,
    compute_log_returns,
    load_prices,
)
from hive_abc.metrics.performance import max_drawdown


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def _zscore(series: pd.Series) -> pd.Series:
    """Population z-score; zeros when the dispersion is degenerate."""
    mean, std = series.mean(), series.std(ddof=0)
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - mean) / std


def select_universe_dynamic_zscore(
    start_date: str,
    prices_file: Path = FROZEN_PRICES,
    lookback_days: int = 252,
    gap_days: int = 21,
    min_days_pre: int = 180,
    target_n: int = 20,
    corr_threshold: float = 0.8,
) -> list[str]:
    """
    Ex-ante dynamic selection on the window preceding the backtest.

    Scores each ticker with `0.5 * z(momentum 12-1) + 0.3 * z(-volatility)
    + 0.2 * z(-max drawdown)` over the lookback window ending the day before
    `start_date`, then greedily diversifies by rejecting candidates whose
    absolute correlation with any already-selected ticker reaches
    `corr_threshold` (topping up ignoring correlation if fewer than
    `target_n` survive). No test-window data is used — this is the
    look-ahead-bias control of the thesis.

    Args:
        start_date: First day of the backtest window (`YYYY-MM-DD`).
        prices_file: Price panel to screen.
        lookback_days: Calendar days of pre-window history.
        gap_days: Recent rows excluded from momentum (the "-1" in 12-1).
        min_days_pre: Minimum observations per ticker in the pre-window
            (relaxed to 120 once if the screen comes back empty).
        target_n: Universe size.
        corr_threshold: Greedy diversification cutoff.

    Returns:
        The selected tickers, at most `target_n`.

    Raises:
        RuntimeError: If no tickers survive even the relaxed screen.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end_pre = (start - timedelta(days=1)).strftime("%Y-%m-%d")
    start_pre = (start - timedelta(days=1 + lookback_days)).strftime("%Y-%m-%d")

    prices_pre = load_prices(prices_file, start_pre, end_pre, min_days=min_days_pre)
    returns_pre = compute_log_returns(prices_pre)
    if returns_pre.shape[1] == 0:
        prices_pre = load_prices(prices_file, start_pre, end_pre, min_days=120)
        returns_pre = compute_log_returns(prices_pre)
    if returns_pre.shape[1] == 0:
        raise RuntimeError(
            f"No tickers with enough pre-window history before {start_date}"
        )

    if returns_pre.shape[0] <= gap_days:
        gap_days = max(1, returns_pre.shape[0] // 10)
    momentum = (
        returns_pre.iloc[:-gap_days].sum()
        if returns_pre.shape[0] > gap_days
        else returns_pre.sum()
    )
    volatility = returns_pre.std()
    drawdown = returns_pre.apply(
        lambda column: max_drawdown(column.to_numpy(dtype=np.float64)), axis=0
    )

    score = (
        0.5 * _zscore(momentum) + 0.3 * _zscore(-volatility) + 0.2 * _zscore(-drawdown)
    )
    rank = score.dropna().sort_values(ascending=False)
    if rank.empty:
        rank = momentum.dropna().sort_values(ascending=False)

    correlation = returns_pre.corr().fillna(0)
    selected: list[str] = []
    for ticker in rank.index:
        if len(selected) >= target_n:
            break
        if not selected:
            selected.append(str(ticker))
            continue
        max_corr = max(abs(float(correlation.loc[ticker, other])) for other in selected)
        if max_corr < corr_threshold:
            selected.append(str(ticker))
    if len(selected) < target_n:
        for ticker in rank.index:
            if str(ticker) not in selected:
                selected.append(str(ticker))
            if len(selected) >= target_n:
                break
    return list(dict.fromkeys(selected))[:target_n]


def load_fixed_zscore_universe(
    zscore_file: Path = FROZEN_ZSCORE, top_n: int = 20
) -> list[str]:
    """
    Static top-N universe from the fundamentals z-score file.

    Args:
        zscore_file: Semicolon-delimited CSV with `Ticker` and `Z_Score`
            columns (decimal commas), as produced for the thesis.
        top_n: Number of tickers to keep.

    Returns:
        Top-`top_n` tickers by fundamentals z-score, excluding the index row.

    Raises:
        ValueError: If the file lacks the required columns.
    """
    frame = pd.read_csv(zscore_file, sep=";", decimal=",")
    if "Ticker" not in frame.columns or "Z_Score" not in frame.columns:
        raise ValueError("z-score file must contain 'Ticker' and 'Z_Score' columns")
    frame = frame[frame["Ticker"] != "NASDAQ_100"].dropna(subset=["Z_Score"])
    ranked = frame.sort_values(by="Z_Score", ascending=False).head(top_n)
    return [str(t) for t in ranked["Ticker"]]
