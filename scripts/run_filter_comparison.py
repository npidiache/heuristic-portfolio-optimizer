"""Best model with vs. without the z-score filter (reviewer task 12).

For each thesis period, backtests the best-performing model of the canonical
fixed-universe tables under two universes:

- **With filter**: the thesis's fundamentals z-score top-20 (the canonical
  setting).
- **Without filter**: the 20 largest tickers by data coverage that pass the
  same liquidity/history screen, WITHOUT the z-score ranking — i.e., the
  selection stage is removed but everything else is identical.

Writes `docs/analysis/filter_comparison.md` and `.html` (annex-ready detail;
the thesis body only needs the brief mention, as the reviewers suggested).
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# noqa comments: imports must follow the sys.path bootstrap in scripts.
import pandas as pd  # noqa: E402

from hive_abc.backtest import PERIODS, BacktestConfig, run_backtest  # noqa: E402
from hive_abc.data.loading import FROZEN_PRICES, load_prices  # noqa: E402
from hive_abc.reporting.html import (  # noqa: E402
    frame_to_html,
    notice,
    render_report,
)
from hive_abc.reporting.tables import DISPLAY_NAMES  # noqa: E402

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Best fixed-universe model per period, read from the canonical tables.
# --------------------------------------------------------------------------------------
DOCS_DIR = REPO_ROOT / "docs" / "analysis"
BEST_MODEL_PER_PERIOD = {
    "covid_2020": "ABC_Original",
    "gfc_2007_2009": "ABC_Original",
    "war_2022": "ABC_FA_Scout",
    "2023_stability": "ABC_Scout_Gravitacional",
}


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def unfiltered_universe(period_slug: str, target_n: int = 20) -> tuple[str, ...]:
    """
    Top-N tickers by data coverage in the period, without any z-score screen.

    Args:
        period_slug: Thesis period key.
        target_n: Universe size (20, matching the filtered setting).

    Returns:
        The `target_n` tickers with the most price observations in the
        window (alphabetical tie-break for determinism).
    """
    period = PERIODS[period_slug]
    prices = load_prices(FROZEN_PRICES, period.start_date, period.end_date, min_days=50)
    coverage = prices.notna().sum().sort_values(ascending=False)
    ordered = sorted(coverage.index, key=lambda t: (-int(coverage[t]), str(t)))
    return tuple(str(t) for t in ordered[:target_n])


def main() -> None:
    """Runs both universes per period and writes the deliverables."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args()
    today = date.today().isoformat()

    rows = []
    for slug, model in BEST_MODEL_PER_PERIOD.items():
        for label, tickers in (
            ("with z-score filter", None),
            ("without filter", unfiltered_universe(slug)),
        ):
            result = run_backtest(
                BacktestConfig(
                    period=slug,
                    universe="fixed",
                    seeds=tuple(range(args.seeds)),
                    models=(model,),
                    universe_tickers=tickers,
                )
            )
            outcome = result.models[model]
            rows.append(
                {
                    "period": slug,
                    "model": DISPLAY_NAMES[model],
                    "universe": label,
                    "sortino": round(outcome.sortino, 3),
                    "max_drawdown": round(outcome.max_drawdown, 3),
                    "jensen_alpha": round(outcome.jensen_alpha, 3),
                    "omega": round(outcome.omega, 3),
                    "cardinality": outcome.cardinality,
                }
            )
            print(f"   {slug} / {label} done", flush=True)

    frame = pd.DataFrame(rows).set_index(["period", "model", "universe"])

    # Brief-mention summary: Sortino advantage of the filtered universe.
    sortino = frame["sortino"].unstack("universe")
    sortino["filter advantage"] = (
        sortino["with z-score filter"] - sortino["without filter"]
    )
    sortino.index = pd.Index(
        [f"{period} — {model}" for period, model in sortino.index],
        name="period — model",
    )

    md = [
        "# Best model with vs. without the z-score filter (reviewer task 12)",
        "",
        f"Generated {today} by `scripts/run_filter_comparison.py` "
        f"({args.seeds} pinned seeds per configuration).",
        "",
        "Per period, the best fixed-universe model from the canonical tables "
        "is re-run on (a) the thesis's fundamentals z-score top-20 and "
        "(b) an unfiltered top-20 by data coverage under the same "
        "liquidity/history screen — isolating the contribution of the "
        "selection stage.",
        "",
        "## Summary (for the results-section mention)",
        "",
        sortino.round(3).to_markdown(floatfmt=".3f"),
        "",
        "## Full annex detail",
        "",
        frame.reset_index().to_markdown(index=False, floatfmt=".3f"),
        "",
    ]

    html_sections = [
        (
            "Scope",
            notice(
                "Annex material for reviewer task 12. The canonical thesis "
                "tables are unchanged; this compares the selection stage "
                "only.",
                label="TASK 12",
            ),
        ),
        ("Sortino summary", frame_to_html(sortino.round(3))),
        ("Full detail", frame_to_html(frame.reset_index().set_index("period"))),
    ]

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "filter_comparison.md").write_text("\n".join(md), encoding="utf-8")
    (DOCS_DIR / "filter_comparison.html").write_text(
        render_report(
            title="Z-score filter comparison",
            subtitle="Best model with vs. without the selection stage — task 12",
            sections=html_sections,
            generated_note=f"generated {today} — {args.seeds} seeds per run",
        ),
        encoding="utf-8",
    )
    print(f"Wrote {DOCS_DIR / 'filter_comparison.md'} and .html")


if __name__ == "__main__":
    main()
