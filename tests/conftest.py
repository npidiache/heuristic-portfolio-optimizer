"""Synthetic data fixtures for backtest and data-loading tests."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: 6 tickers, ~320 business days ending mid-2021 so a 2021-06 backtest
#   window has a full 252-day dynamic-selection lookback.
# --------------------------------------------------------------------------------------
TICKERS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
@pytest.fixture(scope="session")
def synthetic_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Writes a synthetic prices/z-score/benchmark trio and returns the dir."""
    data_dir = tmp_path_factory.mktemp("synthetic_frozen")
    rng = np.random.default_rng(2024)
    dates = pd.bdate_range("2020-03-02", periods=320)

    drifts = np.linspace(0.0002, 0.001, num=len(TICKERS))
    vols = np.linspace(0.01, 0.03, num=len(TICKERS))
    prices = pd.DataFrame(
        {
            ticker: 100.0 * np.cumprod(1 + rng.normal(drift, vol, size=len(dates)))
            for ticker, drift, vol in zip(TICKERS, drifts, vols, strict=True)
        },
        index=dates,
    )
    prices.index.name = "date"
    prices.to_csv(data_dir / "prices.csv")

    zscore = pd.DataFrame(
        {
            "Ticker": ["NASDAQ_100", *TICKERS],
            "Z_Score": ["0,0", "1,5", "1,2", "0,9", "0,4", "0,1", "-0,3"],
        }
    )
    zscore.to_csv(data_dir / "z_score.csv", sep=";", index=False)

    benchmark = pd.DataFrame(
        {"IXIC": 10_000.0 * np.cumprod(1 + rng.normal(0.0004, 0.012, len(dates)))},
        index=dates,
    )
    benchmark.index.name = "date"
    benchmark.to_csv(data_dir / "benchmark.csv")
    return data_dir


@pytest.fixture(scope="session")
def synthetic_prices_file(synthetic_data_dir: Path) -> Path:
    """Path of the synthetic price CSV."""
    return synthetic_data_dir / "prices.csv"


@pytest.fixture(scope="session")
def synthetic_zscore_file(synthetic_data_dir: Path) -> Path:
    """Path of the synthetic fundamentals z-score CSV."""
    return synthetic_data_dir / "z_score.csv"


@pytest.fixture(scope="session")
def synthetic_benchmark_file(synthetic_data_dir: Path) -> Path:
    """Path of the synthetic benchmark CSV."""
    return synthetic_data_dir / "benchmark.csv"
