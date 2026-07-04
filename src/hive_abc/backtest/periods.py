"""Registry of the four thesis backtest periods and their regimes."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from dataclasses import dataclass


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Period:
    """
    One thesis backtest window.

    Attributes:
        slug: Identifier used in the canonical results and output paths.
        start_date: Inclusive window start (`YYYY-MM-DD`).
        end_date: Inclusive window end (`YYYY-MM-DD`).
        regime: Calibration regime key in `regime_parameters.json`.
        description: Human-readable characterization from the thesis.
    """

    slug: str
    start_date: str
    end_date: str
    regime: str
    description: str


# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Slugs, dates, and regimes are frozen thesis facts — never edit them.
# --------------------------------------------------------------------------------------
PERIODS: dict[str, Period] = {
    "covid_2020": Period(
        slug="covid_2020",
        start_date="2020-02-01",
        end_date="2020-07-30",
        regime="CRISIS",
        description="COVID-19 crash and rebound; abrupt systemic shock",
    ),
    "gfc_2007_2009": Period(
        slug="gfc_2007_2009",
        start_date="2007-10-01",
        end_date="2009-03-30",
        regime="CRISIS",
        description="Global Financial Crisis; prolonged systemic collapse",
    ),
    "war_2022": Period(
        slug="war_2022",
        start_date="2022-02-01",
        end_date="2022-08-01",
        regime="UNCERTAINTY",
        description="Russia-Ukraine invasion; elevated geopolitical volatility",
    ),
    "2023_stability": Period(
        slug="2023_stability",
        start_date="2023-01-01",
        end_date="2024-12-31",
        regime="STABLE_GROWTH",
        description="Post-2022 normalization; stable growth conditions",
    ),
}
