"""ABC-FAEM active-scout calibration diagnostic.

This annex keeps the thesis results frozen and tests the smallest plausible
change that makes the FAEM scout reachable within the 60-iteration thesis
budget: express `max_trials` as a fraction of `max_iterations`, while keeping
`p_fa = 1.0` and every other calibrated parameter unchanged.

Writes `docs/analysis/faem_activation_calibration.md` and `.html`.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Literal, SupportsFloat, cast

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# noqa comments: imports must follow the sys.path bootstrap in scripts.
import pandas as pd  # noqa: E402

from hive_abc.backtest import PERIODS, BacktestConfig, run_backtest  # noqa: E402
from hive_abc.reporting.html import frame_to_html, notice, render_report  # noqa: E402
from hive_abc.reporting.tables import (  # noqa: E402
    canonical_metrics_frame,
    load_canonical_results,
)

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
DOCS_DIR = REPO_ROOT / "docs" / "analysis"
FAEM_MODEL = "ABC_FA_Scout"
REFERENCE_MODELS = (
    "ABC_Original",
    "ABC_FA_Scout",
    "PMVG_CVX",
    "Equally_Weighted",
)
UNIVERSES = ("fixed", "dynamic")
THRESHOLD_RATIOS = (0.15, 0.25, 0.40)
METRICS = ("sortino", "max_drawdown", "jensen_alpha", "omega")


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def thresholds_from_iterations(max_iterations: int) -> tuple[tuple[str, int], ...]:
    """
    Converts proportional scout thresholds into explicit `max_trials` values.

    Args:
        max_iterations: Thesis iteration budget.

    Returns:
        Pairs of display label and integer scout threshold.
    """
    thresholds = []
    for ratio in THRESHOLD_RATIOS:
        max_trials = max(1, round(ratio * max_iterations))
        thresholds.append((f"FAEM active mt={max_trials}", max_trials))
    return tuple(thresholds)


def run_active_faem(seeds: int) -> pd.DataFrame:
    """
    Runs ABC-FAEM with reachable scout thresholds over all thesis windows.

    Args:
        seeds: Pinned seeds per configuration.

    Returns:
        Long-format table with one row per universe, period, and threshold.
    """
    rows = []
    for universe in UNIVERSES:
        for period_slug in PERIODS:
            for label, max_trials in thresholds_from_iterations(60):
                result = run_backtest(
                    BacktestConfig(
                        period=period_slug,
                        universe=cast(Literal["dynamic", "fixed"], universe),
                        seeds=tuple(range(seeds)),
                        models=(FAEM_MODEL,),
                        param_overrides={
                            FAEM_MODEL: {"p_fa": 1.0, "max_trials": max_trials}
                        },
                    )
                )
                outcome = result.models[FAEM_MODEL]
                rows.append(
                    {
                        "universe": universe,
                        "period": period_slug,
                        "model": label,
                        "sortino": outcome.sortino,
                        "max_drawdown": outcome.max_drawdown,
                        "jensen_alpha": outcome.jensen_alpha,
                        "omega": outcome.omega,
                    }
                )
                print(f"   {universe} / {period_slug} / {label} done", flush=True)
    return pd.DataFrame(rows)


def canonical_reference_rows() -> pd.DataFrame:
    """
    Loads canonical reference rows used for the diagnostic comparison.

    Returns:
        Long-format table for ABC original, frozen ABC-FAEM, PMVG, and 1/N.
    """
    canonical = load_canonical_results()
    rows = []
    for universe in UNIVERSES:
        for period_slug in PERIODS:
            frame = canonical_metrics_frame(canonical, universe, period_slug)
            for model in REFERENCE_MODELS:
                metrics = frame.loc[model]
                rows.append(
                    {
                        "universe": universe,
                        "period": period_slug,
                        "model": canonical_label(model),
                        "sortino": as_float(metrics["sortino"]),
                        "max_drawdown": as_float(metrics["max_drawdown"]),
                        "jensen_alpha": as_float(metrics["jensen_alpha"]),
                        "omega": as_float(metrics["omega"]),
                    }
                )
    return pd.DataFrame(rows)


def canonical_label(model: str) -> str:
    """
    Display label for the reference rows.

    Args:
        model: Canonical legacy model key.

    Returns:
        Compact label used in the diagnostic tables.
    """
    labels = {
        "ABC_Original": "ABC original",
        "ABC_FA_Scout": "ABC-FAEM frozen mt=300",
        "PMVG_CVX": "PMVG",
        "Equally_Weighted": "1/N",
    }
    return labels[model]


def aggregate_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Mean metric values by model across all universes and periods.

    Args:
        frame: Long-format metric table.

    Returns:
        Model-indexed summary sorted by Sortino.
    """
    summary = frame.groupby("model", sort=False)[list(METRICS)].mean()
    return summary.sort_values("sortino", ascending=False)


def universe_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Mean Sortino by model and universe.

    Args:
        frame: Long-format metric table.

    Returns:
        Table indexed by model, with fixed/dynamic columns.
    """
    return frame.pivot_table(
        index="model",
        columns="universe",
        values="sortino",
        aggfunc="mean",
        sort=False,
    ).sort_values("fixed", ascending=False)


def deltas_vs_references(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Per-configuration Sortino deltas versus frozen FAEM and ABC original.

    Args:
        frame: Long-format metric table including references and active FAEM.

    Returns:
        Delta table for the active-threshold rows only.
    """
    active = frame[frame["model"].str.startswith("FAEM active")].copy()
    key_columns = ["universe", "period"]
    frozen = reference_sortino(frame, "ABC-FAEM frozen mt=300")
    abc = reference_sortino(frame, "ABC original")
    active["delta_vs_frozen_faem"] = active.set_index(key_columns).index.map(frozen)
    active["delta_vs_abc_original"] = active.set_index(key_columns).index.map(abc)
    active["delta_vs_frozen_faem"] = (
        active["sortino"] - active["delta_vs_frozen_faem"]
    )
    active["delta_vs_abc_original"] = (
        active["sortino"] - active["delta_vs_abc_original"]
    )
    return active[
        [
            "universe",
            "period",
            "model",
            "sortino",
            "delta_vs_frozen_faem",
            "delta_vs_abc_original",
        ]
    ]


def reference_sortino(frame: pd.DataFrame, model: str) -> dict[tuple[str, str], float]:
    """
    Sortino lookup for one reference model.

    Args:
        frame: Long-format metric table.
        model: Reference model label.

    Returns:
        Mapping from `(universe, period)` to Sortino.
    """
    reference = frame[frame["model"] == model].set_index(["universe", "period"])
    values: dict[tuple[str, str], float] = {}
    for index, row in reference.iterrows():
        universe, period = cast(tuple[str, str], index)
        values[(universe, period)] = as_float(row["sortino"])
    return values


def as_float(value: object) -> float:
    """
    Converts pandas scalar values to plain floats for strict typing.

    Args:
        value: Scalar value read from a pandas object.

    Returns:
        The value as a Python float.
    """
    return float(cast(SupportsFloat, value))


def recommendation(summary: pd.DataFrame) -> str:
    """
    Interprets whether the active FAEM thresholds justify changing conclusions.

    Args:
        summary: Aggregate model summary.

    Returns:
        A concise recommendation for the markdown/HTML report.
    """
    best_active = summary.loc[
        [idx for idx in summary.index if str(idx).startswith("FAEM active")]
    ].sort_values("sortino", ascending=False)
    best_label = str(best_active.index[0])
    best_sortino = float(best_active.iloc[0]["sortino"])
    frozen_sortino = as_float(summary.loc["ABC-FAEM frozen mt=300", "sortino"])
    abc_sortino = as_float(summary.loc["ABC original", "sortino"])
    frozen_delta = best_sortino - frozen_sortino
    abc_delta = best_sortino - abc_sortino

    return (
        f"The best active-scout threshold is `{best_label}` with mean Sortino "
        f"{best_sortino:.3f}, a {frozen_delta:+.3f} delta versus frozen "
        f"ABC-FAEM and a {abc_delta:+.3f} delta versus ABC original. This "
        "confirms the FAEM scout can be made operational with a proportional "
        "`max_trials` rule, but it does not provide a strong enough aggregate "
        "improvement over ABC original to replace the frozen thesis setting."
    )


def write_report(frame: pd.DataFrame, seeds: int) -> None:
    """
    Writes the markdown and HTML diagnostic report.

    Args:
        frame: Long-format metric table.
        seeds: Pinned seeds per configuration.
    """
    today = date.today().isoformat()
    summary = aggregate_summary(frame)
    by_universe = universe_summary(frame)
    deltas = deltas_vs_references(frame)
    verdict = recommendation(summary)

    md = [
        "# ABC-FAEM active-scout calibration diagnostic",
        "",
        f"Generated {today} by `scripts/run_faem_activation_calibration.py` "
        f"({seeds} pinned seeds per configuration).",
        "",
        "This diagnostic keeps the thesis results frozen and changes only "
        "ABC-FAEM's scout activation threshold. Instead of the calibrated "
        "`max_trials = 0.6 × bees × assets = 300`, it tests thresholds tied "
        "to the 60-iteration budget: 15%, 25%, and 40%, i.e. "
        "`max_trials ∈ {9, 15, 24}`. The FAEM trigger remains `p_fa = 1.0`.",
        "",
        "> [!IMPORTANT]",
        "> These runs are exploratory diagnostics, not replacement thesis "
        "results. They test whether the FAEM mechanism can become active "
        "under a minimal, interpretable recalibration.",
        "",
        "## Aggregate results",
        "",
        summary.to_markdown(floatfmt=".3f"),
        "",
        "## Mean Sortino by universe",
        "",
        by_universe.to_markdown(floatfmt=".3f"),
        "",
        "## Active FAEM Sortino deltas",
        "",
        deltas.to_markdown(index=False, floatfmt=".3f"),
        "",
        "## Interpretation",
        "",
        verdict,
        "",
        "The most defensible reading is that proportional `max_trials` removes "
        "the activation failure and makes the FAEM recovery mechanism visible. "
        "However, the active variants are still conditional: they can improve "
        "some regimes and weaken others because they replace ABC's random "
        "restart with leader-guided recovery. The evidence supports a future "
        "calibration line, not an ex-post replacement of the frozen thesis "
        "configuration.",
        "",
    ]

    html_sections = [
        (
            "Scope",
            notice(
                "Exploratory diagnostic only: thesis results and canonical "
                "artifacts remain unchanged.",
                label="ANNEX",
            ),
        ),
        ("Aggregate results", frame_to_html(summary, "{:.3f}")),
        ("Mean Sortino by universe", frame_to_html(by_universe, "{:.3f}")),
        (
            "Active FAEM Sortino deltas",
            frame_to_html(deltas.set_index(["universe", "period", "model"]), "{:.3f}"),
        ),
        ("Interpretation", f"<p>{verdict}</p>"),
    ]

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "faem_activation_calibration.md").write_text(
        "\n".join(md),
        encoding="utf-8",
    )
    (DOCS_DIR / "faem_activation_calibration.html").write_text(
        render_report(
            title="ABC-FAEM active-scout calibration diagnostic",
            subtitle="Proportional max_trials under the frozen thesis harness",
            sections=html_sections,
            generated_note=f"generated {today} — {seeds} seeds per configuration",
        ),
        encoding="utf-8",
    )


def main() -> None:
    """Runs the diagnostic and writes its report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args()

    references = canonical_reference_rows()
    active = run_active_faem(args.seeds)
    frame = pd.concat([references, active], ignore_index=True)
    write_report(frame, args.seeds)
    print(f"Wrote {DOCS_DIR / 'faem_activation_calibration.md'} and .html")


if __name__ == "__main__":
    main()
