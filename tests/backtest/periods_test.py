"""Tests for the frozen period registry."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.backtest.periods import PERIODS


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_registry_holds_the_four_thesis_periods() -> None:
    assert set(PERIODS) == {
        "covid_2020",
        "gfc_2007_2009",
        "war_2022",
        "2023_stability",
    }


def test_frozen_dates_and_regimes() -> None:
    covid = PERIODS["covid_2020"]
    assert (covid.start_date, covid.end_date) == ("2020-02-01", "2020-07-30")
    assert covid.regime == "CRISIS"
    assert PERIODS["gfc_2007_2009"].regime == "CRISIS"
    assert PERIODS["war_2022"].regime == "UNCERTAINTY"
    assert PERIODS["2023_stability"].regime == "STABLE_GROWTH"
