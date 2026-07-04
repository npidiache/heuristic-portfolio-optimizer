"""Loaders for the frozen thesis data (prices, returns, moments, benchmark).

All defaults point at the committed `data/frozen/` artifacts so every run is
reproducible offline; the legacy pipeline's runtime Yahoo Finance download is
replaced by the frozen ^IXIC file.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Repo-root-relative defaults; pass explicit paths when installed as a wheel.
# --------------------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]
FROZEN_DATA_DIR = REPO_ROOT / "data" / "frozen"
FROZEN_PRICES = FROZEN_DATA_DIR / "nasdaq_prices_2000_2025.csv"
FROZEN_ZSCORE = FROZEN_DATA_DIR / "z_score.csv"
FROZEN_BENCHMARK = FROZEN_DATA_DIR / "benchmark_ixic_2007_2024.csv"


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def load_prices(
    prices_file: Path = FROZEN_PRICES,
    start_date: str | None = None,
    end_date: str | None = None,
    tickers: list[str] | None = None,
    min_days: int = 1000,
) -> pd.DataFrame:
    """
    Loads the NASDAQ price panel with the legacy loader's filters.

    Args:
        prices_file: CSV with a date index column and one column per ticker.
        start_date: Inclusive start (`YYYY-MM-DD`), if any.
        end_date: Inclusive end (`YYYY-MM-DD`), if any.
        tickers: Restrict to these tickers (missing ones are dropped
            silently, as in the legacy loader).
        min_days: Minimum non-null observations a ticker needs to survive.

    Returns:
        Price DataFrame indexed by datetime, filtered like the thesis runs.

    Raises:
        FileNotFoundError: If `prices_file` does not exist.
    """
    if not prices_file.exists():
        raise FileNotFoundError(f"Price file not found: {prices_file}")

    prices = pd.read_csv(prices_file, index_col=0)
    prices.index = pd.to_datetime(prices.index.astype(str).str[:10])

    if start_date is not None:
        prices = prices[prices.index >= pd.to_datetime(start_date)]
    if end_date is not None:
        prices = prices[prices.index <= pd.to_datetime(end_date)]
    if tickers is not None:
        available = [t for t in tickers if t in prices.columns]
        prices = prices[available]
    if min_days > 0:
        keep = [c for c in prices.columns if int(prices[c].notna().sum()) >= min_days]
        prices = prices[keep]
    return prices


def compute_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Daily log returns with forward-filled gaps, as in the thesis pipeline.

    Args:
        prices: Price panel.

    Returns:
        Log-return DataFrame with the first (all-NaN) row dropped.
    """
    filled = prices.ffill()
    returns = pd.DataFrame(
        np.log(filled.to_numpy() / filled.shift(1).to_numpy()),
        index=filled.index,
        columns=filled.columns,
    )
    return returns.dropna()


def compute_moments(returns: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """
    Expected returns and covariance matrix of a return panel.

    Args:
        returns: Daily (log) returns.

    Returns:
        Tuple of per-asset mean returns and the sample covariance matrix.
    """
    return returns.mean(), returns.cov()


def load_benchmark_returns(
    benchmark_file: Path = FROZEN_BENCHMARK,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.Series:
    """
    Daily log returns of the frozen ^IXIC benchmark (Jensen alpha reference).

    Args:
        benchmark_file: CSV with `date` and `IXIC` close columns.
        start_date: Inclusive start (`YYYY-MM-DD`), if any.
        end_date: Inclusive end (`YYYY-MM-DD`), if any.

    Returns:
        Log-return Series indexed by datetime.

    Raises:
        FileNotFoundError: If `benchmark_file` does not exist.
    """
    if not benchmark_file.exists():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_file}")

    closes = pd.read_csv(benchmark_file, index_col=0, parse_dates=True)["IXIC"]
    if start_date is not None:
        closes = closes[closes.index >= pd.to_datetime(start_date)]
    if end_date is not None:
        closes = closes[closes.index <= pd.to_datetime(end_date)]
    returns = pd.Series(
        np.log(closes.to_numpy() / closes.shift(1).to_numpy()), index=closes.index
    )
    return returns.dropna()
