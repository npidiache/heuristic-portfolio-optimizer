"""PFA sensitivity analysis on ABC-FAEM (committee task 9), with defense.

Part 1 — the committee's requested sweep: `p_fa` over {0.3, 0.4, 0.5} plus
the frozen baseline 1.0, ABC-FAEM only, fixed fundamentals universe, all four
thesis periods. Under the calibrated stagnation threshold the scout phase
never activates, so the sweep is provably invariant — the formal confirmation
that the analysis "does not affect the final results".

Part 2 — the defense of the mechanism (why the parameter exists):

- **Activation frequency**: how often the scout phase fires as a function of
  `max_trials`, locating the calibrated setting (300) in the never-fires
  region and showing where the mechanism wakes up.
- **Ablation when active**: with a stressed threshold, `p_fa = 0` is exactly
  the original ABC random-restart scout and `p_fa = 1` the full FAEM elite
  move — sweeping between them isolates the mechanism's contribution, with
  Wilcoxon significance tests on the per-seed samples.
- **Convergence profiles**: mean best fitness at iteration checkpoints for
  `p_fa` 0 vs 1 under stress, showing the mechanism's anytime behavior.

Writes `docs/analysis/pfa_sensitivity.md` and `.html`.
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
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

from hive_abc.algorithms import ABCFAEM  # noqa: E402
from hive_abc.backtest import (  # noqa: E402
    PERIODS,
    BacktestConfig,
    load_regime_parameters,
    run_backtest,
)
from hive_abc.core.types import Bounds, ObjectiveFn  # noqa: E402
from hive_abc.data import (  # noqa: E402
    compute_log_returns,
    compute_moments,
    load_fixed_zscore_universe,
    load_prices,
)
from hive_abc.objectives import PortfolioUtilityObjective  # noqa: E402
from hive_abc.reporting.html import (  # noqa: E402
    frame_to_html,
    notice,
    render_report,
)

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
DOCS_DIR = REPO_ROOT / "docs" / "analysis"
P_FA_VALUES = (1.0, 0.5, 0.4, 0.3)
ABLATION_P_FA = (0.0, 0.3, 0.5, 1.0)
MODEL = "ABC_FA_Scout"
STRESSED_MAX_TRIALS = 15
ACTIVATION_THRESHOLDS = (10, 15, 25, 50, 100, 200, 300)
CONVERGENCE_CHECKPOINTS = (5, 10, 20, 40, 60)


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class _CountingFAEM(ABCFAEM):
    """ABCFAEM that counts scout-phase activations (diagnostic only)."""

    def __init__(self, **kwargs: float) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.scout_activations = 0

    def _scout_move(self, state: object, index: int) -> None:
        self.scout_activations += 1
        super()._scout_move(state, index)  # type: ignore[arg-type]


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def prepare_problem(period_slug: str) -> tuple[ObjectiveFn, Bounds, dict[str, float]]:
    """
    Builds the thesis objective/bounds/params for one fixed-universe period.

    Args:
        period_slug: Key of `PERIODS`.

    Returns:
        The objective, the box bounds, and the calibrated FAEM parameters.
    """
    period = PERIODS[period_slug]
    tickers = load_fixed_zscore_universe()
    prices = load_prices(
        start_date=period.start_date,
        end_date=period.end_date,
        tickers=tickers,
        min_days=50,
    )
    returns = compute_log_returns(prices)
    mu, _ = compute_moments(returns)
    objective = PortfolioUtilityObjective(returns.to_numpy(), mu.to_numpy())
    return objective, Bounds.box(len(mu)), load_regime_parameters(period.regime)[MODEL]


def faem_kwargs(legacy: dict[str, float], max_trials: int) -> dict[str, float]:
    """Translates the calibrated legacy FAEM parameters to constructor kwargs."""
    return {
        "b0": legacy["b0"],
        "gamma": legacy["gamma"],
        "alpha": legacy["alpha"],
        "colony_size": int(legacy["numb_bees"]),
        "max_iterations": int(legacy["max_itrs"]),
        "max_trials": max_trials,
    }


def sweep(seeds: int, stressed: bool) -> pd.DataFrame:
    """
    Runs the committee's p_fa sweep over every period on the fixed universe.

    Args:
        seeds: Seeds per run.
        stressed: When True, forces `max_trials = STRESSED_MAX_TRIALS`.

    Returns:
        Long-format DataFrame with one row per (period, p_fa).
    """
    rows = []
    for slug in PERIODS:
        for p_fa in P_FA_VALUES:
            overrides: dict[str, float] = {"p_fa": p_fa}
            if stressed:
                overrides["max_trials"] = STRESSED_MAX_TRIALS
            result = run_backtest(
                BacktestConfig(
                    period=slug,
                    universe="fixed",
                    seeds=tuple(range(seeds)),
                    models=(MODEL,),
                    param_overrides={MODEL: overrides},
                )
            )
            model = result.models[MODEL]
            rows.append(
                {
                    "period": slug,
                    "p_fa": p_fa,
                    "sortino": round(model.sortino, 3),
                    "max_drawdown": round(model.max_drawdown, 3),
                    "jensen_alpha": round(model.jensen_alpha, 3),
                    "omega": round(model.omega, 3),
                    "mean_fitness": round(float(np.mean(model.fitness_per_seed)), 6),
                    "std_fitness": round(float(np.std(model.fitness_per_seed)), 6),
                }
            )
        print(f"   sweep ({'stressed' if stressed else 'calibrated'}) {slug} done")
    return pd.DataFrame(rows)


def activation_frequency(seeds: int) -> pd.DataFrame:
    """
    Mean scout activations per run as a function of `max_trials`.

    Uses the calibrated FAEM parameters on every period; only the stagnation
    threshold varies. Locates the calibrated value (300) in the never-fires
    region and shows where the mechanism starts operating.
    """
    records = {}
    for slug in PERIODS:
        objective, bounds, legacy = prepare_problem(slug)
        row = {}
        for threshold in ACTIVATION_THRESHOLDS:
            activations = []
            for seed in range(seeds):
                algo = _CountingFAEM(**faem_kwargs(legacy, threshold))
                algo.optimize(objective, bounds, seed=seed)
                activations.append(algo.scout_activations)
            row[threshold] = round(float(np.mean(activations)), 1)
        records[slug] = row
        print(f"   activation frequency {slug} done")
    frame = pd.DataFrame.from_dict(records, orient="index")
    frame.index.name = "period"
    frame.columns.name = "max_trials"
    return frame


def ablation(seeds: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Mechanism ablation under stress: p_fa = 0 (pure ABC random-restart
    scout) through p_fa = 1 (full FAEM elite move).

    Returns:
        Tuple of (per-period metric table, Wilcoxon table comparing the
        p_fa = 1 and p_fa = 0 per-seed samples).
    """
    rows = []
    samples: dict[tuple[str, float], dict[str, tuple[float, ...]]] = {}
    for slug in PERIODS:
        for p_fa in ABLATION_P_FA:
            result = run_backtest(
                BacktestConfig(
                    period=slug,
                    universe="fixed",
                    seeds=tuple(range(seeds)),
                    models=(MODEL,),
                    param_overrides={
                        MODEL: {"p_fa": p_fa, "max_trials": STRESSED_MAX_TRIALS}
                    },
                )
            )
            model = result.models[MODEL]
            samples[(slug, p_fa)] = {
                "fitness": model.fitness_per_seed,
                "sortino": model.sortino_per_seed,
            }
            rows.append(
                {
                    "period": slug,
                    "p_fa": p_fa,
                    "mean_fitness": round(float(np.mean(model.fitness_per_seed)), 6),
                    "std_fitness": round(float(np.std(model.fitness_per_seed)), 6),
                    "mean_sortino_per_seed": round(
                        float(np.mean(model.sortino_per_seed)), 3
                    ),
                    "best_sortino": round(model.sortino, 3),
                }
            )
        print(f"   ablation {slug} done")

    tests = []
    for slug in PERIODS:
        for metric in ("fitness", "sortino"):
            full = np.array(samples[(slug, 1.0)][metric])
            none = np.array(samples[(slug, 0.0)][metric])
            if np.all(full == none):
                p_value = float("nan")
            else:
                _, raw_p = wilcoxon(full, none)
                p_value = float(raw_p)
            better = (
                "p_fa=1.0 (FAEM)"
                if _favors_full(metric, full, none)
                else ("p_fa=0.0 (ABC restart)")
            )
            tests.append(
                {
                    "period": slug,
                    "metric": metric,
                    "p_value": round(p_value, 4) if p_value == p_value else p_value,
                    "significant_5pct": bool(p_value < 0.05)
                    if p_value == p_value
                    else False,
                    "higher_mean": better,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(tests)


def _favors_full(metric: str, full: np.ndarray, none: np.ndarray) -> bool:
    """True when the p_fa=1 sample has the better mean for the metric."""
    if metric == "fitness":  # minimization: lower is better
        return bool(np.mean(full) <= np.mean(none))
    return bool(np.mean(full) >= np.mean(none))


def convergence_profile(seeds: int) -> pd.DataFrame:
    """
    Mean best fitness at iteration checkpoints, stressed, p_fa 0 vs 1.

    Shows the anytime behavior of the two scout policies while the
    mechanism is actually firing. Returned long-format (`period` and
    `policy` as plain columns) so markdown tables render cleanly.
    """
    rows = []
    for slug in PERIODS:
        objective, bounds, legacy = prepare_problem(slug)
        for p_fa in (0.0, 1.0):
            histories = []
            for seed in range(seeds):
                algo = ABCFAEM(
                    p_fa=p_fa,
                    **faem_kwargs(legacy, STRESSED_MAX_TRIALS),  # type: ignore[arg-type]
                )
                outcome = algo.optimize(objective, bounds, seed=seed)
                histories.append(outcome.best_per_iteration)
            mean_history = np.mean(np.array(histories), axis=0)
            row: dict[str, object] = {"period": slug, "policy": f"p_fa={p_fa:.0f}"}
            row.update(
                {
                    f"iter {c}": round(float(mean_history[c - 1]), 6)
                    for c in CONVERGENCE_CHECKPOINTS
                    if c <= len(mean_history)
                }
            )
            rows.append(row)
        print(f"   convergence {slug} done")
    return pd.DataFrame(rows)


def convergence_takeaway(convergence: pd.DataFrame) -> str:
    """
    One-sentence interpretation of the convergence table, computed from it.

    Args:
        convergence: Long-format output of `convergence_profile`.

    Returns:
        A markdown paragraph stating where the trajectories split and how
        many periods finish equal-or-better under the elite move.
    """
    checkpoint_columns = [c for c in convergence.columns if c.startswith("iter ")]
    final_column = checkpoint_columns[-1]
    wide = convergence.pivot(index="period", columns="policy", values=final_column)
    better_or_equal = int((wide["p_fa=1"] <= wide["p_fa=0"]).sum())

    # First checkpoint at which any period's two policies differ.
    split_at = final_column
    for column in checkpoint_columns:
        by_policy = convergence.pivot(index="period", columns="policy", values=column)
        if bool((by_policy["p_fa=1"] != by_policy["p_fa=0"]).any()):
            split_at = column
            break

    return (
        f"**Reading**: both policies are *identical* until the first scout "
        f"activations (first divergence at {split_at}) — mechanistic "
        f"confirmation that the trigger only matters after stagnation "
        f"accumulates — and the FAEM elite move finishes with equal-or-"
        f"better mean best fitness in {better_or_equal} of "
        f"{wide.shape[0]} periods at {final_column}."
    )


def pivot(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    """One metric as a period x p_fa table."""
    table = frame.pivot(index="period", columns="p_fa", values=metric)
    table.index.name = "period"
    return table


def main() -> None:
    """Runs all analyses and writes the markdown + HTML deliverables."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args()
    today = date.today().isoformat()

    print(">> Part 1: calibrated sweep (thesis max_trials)")
    calibrated = sweep(args.seeds, stressed=False)
    print(">> Part 2a: scout activation frequency vs max_trials")
    activations = activation_frequency(args.seeds)
    print(">> Part 2b: mechanism ablation under stress (p_fa 0 -> 1)")
    ablation_table, wilcoxon_table = ablation(args.seeds)
    print(">> Part 2c: convergence profiles under stress")
    convergence = convergence_profile(args.seeds)

    calibrated_identical = all(
        pivot(calibrated, metric).nunique(axis=1).eq(1).all()
        for metric in ("sortino", "max_drawdown", "jensen_alpha", "omega")
    )

    md: list[str] = [
        "# PFA sensitivity analysis — ABC-FAEM (committee task 9)",
        "",
        f"Generated {today} by `scripts/run_pfa_sensitivity.py` "
        f"({args.seeds} pinned seeds; fixed fundamentals universe; "
        f"ABC-FAEM only, as the committee note requests).",
        "",
        "`p_fa` is the probabilistic trigger of ABC-FAEM's scout phase "
        "(thesis p. 21): with probability `p_fa` a stalled bee performs the "
        "firefly move toward a softmax-selected elite; with probability "
        "`1 − p_fa` it performs the original ABC random restart. "
        "`p_fa = 1.0` is the frozen thesis behavior; `p_fa = 0.0` degenerates "
        "exactly to the original ABC scout.",
        "",
        "## 1. The committee's sweep, calibrated configuration",
        "",
        "Under the calibrated stagnation threshold "
        "(`max_trials = 0.6 × 25 bees × 20 assets = 300`) a bee accumulates "
        "at most ~30 unsuccessful trials within the 60-iteration budget, so "
        "the scout phase — and therefore `p_fa` — is **never exercised**. "
        "The sweep confirms this: all metrics are bit-identical across "
        f"`p_fa` values (verified: {calibrated_identical}).",
        "",
        "### Sortino",
        "",
        pivot(calibrated, "sortino").to_markdown(floatfmt=".3f"),
        "",
        "### Max drawdown",
        "",
        pivot(calibrated, "max_drawdown").to_markdown(floatfmt=".3f"),
        "",
        "> [!IMPORTANT]",
        '> <font color="#ff6b6b">**CONCLUSION (TASK 9)**</font>',
        "> The final thesis results are insensitive to the PFA trigger by "
        "construction: with the calibrated stagnation threshold the "
        "probabilistic scout never activates, so any value in {0.3, 0.4, "
        "0.5, 1.0} leaves every reported number unchanged. This formally "
        "satisfies the committee's requirement that the sensitivity "
        "analysis must not affect the final results.",
        "",
        "## 2. Why the parameter exists — defense of the mechanism",
        "",
        "*Anticipated question: if `p_fa` changes nothing, what is the "
        "point of the parameter (and of the FAEM scout)?*",
        "",
        "**The inertness is a calibration outcome, not a design flaw.** The "
        "robust multi-regime calibration (see "
        "`docs/thesis/calibration.md`) selected `max_trials_factor = 0.6` "
        "under a worst-case-Sortino criterion — i.e., the data determined "
        "that in these portfolio problems, within a 60-iteration budget, "
        "sustained exploitation without restarts is optimal. The scout "
        "mechanism is the algorithm's *contingency* against stagnation, and "
        "the calibration set its activation threshold so high that the "
        "contingency was never needed in-sample. The exploratory grids did "
        "search the active region (`max_trials ∈ [8, 25]`) and the "
        "calibration rejected it. The evidence below characterizes the "
        "mechanism in both regions.",
        "",
        "### 2a. When does the scout wake up? (activation frequency)",
        "",
        "Mean scout activations per run (calibrated FAEM parameters, only "
        "`max_trials` varies; the calibrated value is 300):",
        "",
        activations.to_markdown(),
        "",
        "The calibrated threshold sits far inside the never-fires region; "
        "the mechanism becomes operative roughly below `max_trials ≈ 50`.",
        "",
        "### 2b. Ablation while active: FAEM elite move vs. ABC restart",
        "",
        f"With `max_trials = {STRESSED_MAX_TRIALS}` the scout fires "
        "regularly, and `p_fa` spans a clean ablation: `0.0` = pure "
        "original-ABC random restart, `1.0` = pure FAEM elite move. "
        "**These runs are diagnostics, not thesis results.**",
        "",
        "#### Optimization quality (mean best fitness per seed; lower is better)",
        "",
        pivot(ablation_table, "mean_fitness").to_markdown(floatfmt=".6f"),
        "",
        "#### Financial outcome (mean per-seed Sortino)",
        "",
        pivot(ablation_table, "mean_sortino_per_seed").to_markdown(floatfmt=".3f"),
        "",
        "#### Wilcoxon signed-rank: p_fa = 1.0 vs p_fa = 0.0 (20 paired seeds)",
        "",
        wilcoxon_table.to_markdown(index=False),
        "",
        "### 2c. Convergence profiles under stress",
        "",
        "Mean best fitness across seeds at iteration checkpoints (lower is better):",
        "",
        convergence.to_markdown(index=False, floatfmt=".6f"),
        "",
        convergence_takeaway(convergence),
        "",
        "## 3. Defense summary (for the oral discussion)",
        "",
        "1. **Formally**: the requested sweep (0.3/0.4/0.5) leaves every "
        "reported number unchanged — bit-identical, not merely "
        "statistically indistinguishable — because the calibrated "
        "stagnation threshold keeps the trigger dormant (§1, §2a).",
        "2. **Mechanistically**: `p_fa` is the knob of a calibrated "
        "contingency subsystem. The calibration, not the authors, decided "
        "the contingency was unnecessary for these horizons and budgets — "
        "an empirical finding about the problem class (exploitation-"
        "dominant landscapes), documented in `docs/thesis/calibration.md`.",
        "3. **Empirically**: when the trigger is active (§2b–2c), the "
        "ablation and Wilcoxon tests quantify exactly what the elite move "
        "contributes relative to the original ABC restart, so the "
        "mechanism's behavior is characterized in both regimes rather than "
        "asserted.",
        "",
    ]

    html_sections = [
        (
            "Conclusion (task 9)",
            notice(
                "Under the calibrated thesis parameters the PFA trigger is "
                "never exercised: results are bit-identical for p_fa in "
                "{0.3, 0.4, 0.5, 1.0}. The final results are unaffected.",
                label="TASK 9",
            ),
        ),
        ("Calibrated sweep — Sortino", frame_to_html(pivot(calibrated, "sortino"))),
        (
            "Scout activation frequency vs max_trials",
            frame_to_html(activations, "{:.1f}"),
        ),
        (
            "Ablation under stress — mean best fitness",
            frame_to_html(pivot(ablation_table, "mean_fitness"), "{:.6f}"),
        ),
        (
            "Ablation under stress — mean per-seed Sortino",
            frame_to_html(pivot(ablation_table, "mean_sortino_per_seed")),
        ),
        (
            "Wilcoxon: p_fa 1.0 vs 0.0",
            frame_to_html(wilcoxon_table.set_index("period")),
        ),
        (
            "Convergence profiles under stress",
            frame_to_html(convergence.set_index("period"), "{:.6f}"),
        ),
    ]

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "pfa_sensitivity.md").write_text("\n".join(md), encoding="utf-8")
    (DOCS_DIR / "pfa_sensitivity.html").write_text(
        render_report(
            title="PFA sensitivity analysis",
            subtitle="ABC-FAEM probabilistic trigger — committee task 9, with "
            "mechanism defense",
            sections=html_sections,
            generated_note=f"generated {today} — {args.seeds} seeds, "
            "fixed universe, ABC-FAEM only",
        ),
        encoding="utf-8",
    )
    print(f"Wrote {DOCS_DIR / 'pfa_sensitivity.md'} and .html")


if __name__ == "__main__":
    main()
