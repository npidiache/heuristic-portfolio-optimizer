"""Tier-2 reproduction guard: full 20-seed runs vs. the canonical results.

Marked `repro` — excluded from the default suite and executed by the
`reproduction` workflow. Two layers of assertions per (universe, period):

1. Tolerance bands per metric, calibrated from the observed cross-seed
   dispersion of the pinned-seed reproduction (2026-07) and then frozen.
   Bitwise equality with the thesis numbers is impossible by construction:
   the legacy harness drew its seeds from an unseeded `random.randint` and a
   platform-dependent per-class hash, and the frozen ^IXIC benchmark was
   re-downloaded after the thesis runs (small Jensen-alpha shifts).
2. The thesis's headline ordinal claim, which holds in both the canonical
   tables and every pinned reproduction: ABC_Original, ABC_FA_Scout
   (ABC-FAEM), and ABC_Scout_Gravitacional (ABC-GSA) each beat BOTH
   classical benchmarks on Sortino in every regime and universe.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import pytest

from hive_abc.backtest import PERIODS, BacktestConfig, BacktestResult, run_backtest
from hive_abc.reporting.tables import canonical_metrics_frame, load_canonical_results

pytestmark = pytest.mark.repro

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Bands are frozen; loosening them requires maintainer review.
# --------------------------------------------------------------------------------------
STOCHASTIC_MODELS = (
    "ABC_Original",
    "ABC_FA_Bacanin",
    "ABC_FA_Scout",
    "ABC_Scout_Gravitacional",
)
DETERMINISTIC_MODELS = ("PMVG_CVX", "Equally_Weighted")
DOMINANT_FAMILY = ("ABC_Original", "ABC_FA_Scout", "ABC_Scout_Gravitacional")

STOCHASTIC_BANDS = {
    "sortino": 1.0,
    "max_drawdown": 0.10,
    "jensen_alpha": 0.30,
    "omega": 0.15,
}
DETERMINISTIC_BANDS = {
    "sortino": 0.05,
    "max_drawdown": 0.01,
    "jensen_alpha": 0.08,
    "omega": 0.02,
}

CONFIGURATIONS = [
    (universe, period) for universe in ("dynamic", "fixed") for period in PERIODS
]


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def reproductions() -> dict[tuple[str, str], BacktestResult]:
    """Runs all 8 full configurations once for the module."""
    return {
        (universe, period): run_backtest(
            BacktestConfig(period=period, universe=universe)  # type: ignore[arg-type]
        )
        for universe, period in CONFIGURATIONS
    }


@pytest.mark.parametrize(("universe", "period"), CONFIGURATIONS)
def test_metrics_within_frozen_tolerance_bands(
    reproductions: dict[tuple[str, str], BacktestResult],
    universe: str,
    period: str,
) -> None:
    canonical = canonical_metrics_frame(load_canonical_results(), universe, period)
    result = reproductions[(universe, period)]

    failures: list[str] = []
    for model, model_result in result.models.items():
        bands = (
            DETERMINISTIC_BANDS if model in DETERMINISTIC_MODELS else STOCHASTIC_BANDS
        )
        reproduced = {
            "sortino": model_result.sortino,
            "max_drawdown": model_result.max_drawdown,
            "jensen_alpha": model_result.jensen_alpha,
            "omega": model_result.omega,
        }
        for metric, band in bands.items():
            expected = float(canonical[metric].loc[model])
            got = reproduced[metric]
            if abs(got - expected) > band:
                failures.append(
                    f"{model}.{metric}: reproduced {got:.3f} vs canonical "
                    f"{expected:.3f} (band ±{band})"
                )
    assert not failures, f"{universe}/{period}: " + "; ".join(failures)


@pytest.mark.parametrize(("universe", "period"), CONFIGURATIONS)
def test_abc_family_dominates_benchmarks_on_sortino(
    reproductions: dict[tuple[str, str], BacktestResult],
    universe: str,
    period: str,
) -> None:
    result = reproductions[(universe, period)]
    best_benchmark = max(result.models[m].sortino for m in DETERMINISTIC_MODELS)
    for model in DOMINANT_FAMILY:
        assert result.models[model].sortino > best_benchmark, (
            f"{universe}/{period}: {model} Sortino "
            f"{result.models[model].sortino:.3f} does not beat the best "
            f"benchmark ({best_benchmark:.3f}) — the thesis headline claim broke"
        )


def test_canonical_ordinal_claims_hold_in_canonical_tables() -> None:
    # Guards the claim itself: the dominance assertion must be true of the
    # frozen thesis numbers, not just our reproductions.
    canonical = load_canonical_results()
    for universe, period in CONFIGURATIONS:
        frame = canonical_metrics_frame(canonical, universe, period)
        best_benchmark = max(frame.loc[list(DETERMINISTIC_MODELS), "sortino"])
        for model in DOMINANT_FAMILY:
            assert frame.loc[model, "sortino"] > best_benchmark
