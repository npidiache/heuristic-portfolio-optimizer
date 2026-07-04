"""Tests for the frozen-data loaders (on synthetic fixtures)."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hive_abc.data.loading import (
    compute_log_returns,
    compute_moments,
    load_benchmark_returns,
    load_prices,
)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_load_prices_filters_dates_and_tickers(synthetic_prices_file: Path) -> None:
    prices = load_prices(
        synthetic_prices_file,
        start_date="2020-06-01",
        end_date="2020-12-31",
        tickers=["AAA", "BBB", "ZZZ"],  # ZZZ silently dropped (legacy behavior)
        min_days=10,
    )
    assert list(prices.columns) == ["AAA", "BBB"]
    assert prices.index.min() >= pd.Timestamp("2020-06-01")
    assert prices.index.max() <= pd.Timestamp("2020-12-31")


def test_load_prices_min_days_drops_sparse_tickers(
    synthetic_prices_file: Path, tmp_path: Path
) -> None:
    prices = pd.read_csv(synthetic_prices_file, index_col=0)
    prices.loc[prices.index[30:], "FFF"] = np.nan  # only 30 observations left
    sparse_file = tmp_path / "sparse.csv"
    prices.to_csv(sparse_file)

    loaded = load_prices(sparse_file, min_days=100)
    assert "FFF" not in loaded.columns
    assert "AAA" in loaded.columns


def test_load_prices_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_prices(Path("does/not/exist.csv"))


def test_log_returns_and_moments(synthetic_prices_file: Path) -> None:
    prices = load_prices(synthetic_prices_file, min_days=10)
    returns = compute_log_returns(prices)

    assert len(returns) == len(prices) - 1
    manual = np.log(prices["AAA"].iloc[1] / prices["AAA"].iloc[0])
    assert returns["AAA"].iloc[0] == pytest.approx(manual)

    mu, cov = compute_moments(returns)
    assert mu.shape == (6,)
    assert cov.shape == (6, 6)
    assert np.allclose(cov, cov.T)


def test_benchmark_returns_are_log_returns(synthetic_benchmark_file: Path) -> None:
    returns = load_benchmark_returns(
        synthetic_benchmark_file, start_date="2020-06-01", end_date="2020-12-31"
    )
    closes = pd.read_csv(synthetic_benchmark_file, index_col=0, parse_dates=True)[
        "IXIC"
    ]
    closes = closes[(closes.index >= "2020-06-01") & (closes.index <= "2020-12-31")]
    assert returns.iloc[0] == pytest.approx(
        float(np.log(closes.iloc[1] / closes.iloc[0]))
    )


def test_benchmark_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_benchmark_returns(Path("missing.csv"))
