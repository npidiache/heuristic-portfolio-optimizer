"""Generates the branded thesis figures (committee comment 15).

Produces print-ready PNGs (300 dpi, Obsidian Aqua palette, Spanish labels —
they are destined for the Word document) under `docs/figures/`. Every figure
is derived from the frozen data or the pinned-seed reproduction engine, so
nothing here can contradict the canonical tables.

Requires the optional dependency group:  uv sync --group figures
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# noqa comments: imports must follow the sys.path bootstrap in scripts.
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from hive_abc.backtest import (  # noqa: E402
    PERIODS,
    BacktestConfig,
    BacktestResult,
    load_regime_parameters,
    run_backtest,
)
from hive_abc.backtest.params import build_abc_model  # noqa: E402
from hive_abc.core.types import Bounds  # noqa: E402
from hive_abc.data import (  # noqa: E402
    compute_log_returns,
    compute_moments,
    load_fixed_zscore_universe,
    load_prices,
)
from hive_abc.objectives import PortfolioUtilityObjective  # noqa: E402
from hive_abc.reporting.tables import load_canonical_results  # noqa: E402

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Cool tones = bio-inspired family; warm/neutral tones = benchmarks.
# --------------------------------------------------------------------------------------
FIGURES_DIR = REPO_ROOT / "docs" / "figures"
SEEDS = tuple(range(20))

MODEL_COLORS = {
    "ABC_Original": "#1A1A2E",
    "ABC_FA_Bacanin": "#64748B",
    "ABC_FA_Scout": "#00E5FF",
    "ABC_Scout_Gravitacional": "#10B981",
    "PMVG_CVX": "#F59E0B",
    "Equally_Weighted": "#FF6B6B",
}
MODEL_LABELS = {
    "ABC_Original": "ABC (original)",
    "ABC_FA_Bacanin": "ABC-FA",
    "ABC_FA_Scout": "ABC-FAEM",
    "ABC_Scout_Gravitacional": "ABC-GSA",
    "PMVG_CVX": "PMVG",
    "Equally_Weighted": "1/N",
}
PERIOD_LABELS = {
    "covid_2020": "COVID-19 (2020)",
    "gfc_2007_2009": "GFC (2007–2009)",
    "war_2022": "Guerra (2022)",
    "2023_stability": "Estabilidad (2023–2024)",
}
PERIOD_ORDER = ["covid_2020", "gfc_2007_2009", "war_2022", "2023_stability"]


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def apply_brand_style() -> None:
    """Applies the Obsidian Aqua look to matplotlib."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Outfit", "Segoe UI", "Helvetica Neue", "Arial"],
            "text.color": "#1E293B",
            "axes.edgecolor": "#E2E8F0",
            "axes.labelcolor": "#1E293B",
            "axes.titlecolor": "#1A1A2E",
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.color": "#E2E8F0",
            "grid.linewidth": 0.6,
            "xtick.color": "#64748B",
            "ytick.color": "#64748B",
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "legend.frameon": False,
        }
    )


def save(fig: Figure, name: str) -> None:
    """Writes a figure as PNG and reports it."""
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"   wrote {path.relative_to(REPO_ROOT)}")


def fig_sortino_bars() -> None:
    """Fig. 1 — canonical Sortino by model and regime (fixed universe)."""
    canonical = load_canonical_results()
    models = list(MODEL_COLORS)
    x = np.arange(len(PERIOD_ORDER))
    width = 0.13

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, model in enumerate(models):
        values = [
            next(r["s"] for r in canonical["fixed"]["metrics"][p] if r["A"] == model)
            for p in PERIOD_ORDER
        ]
        ax.bar(
            x + (i - 2.5) * width,
            values,
            width,
            label=MODEL_LABELS[model],
            color=MODEL_COLORS[model],
        )
    ax.axhline(0, color="#1A1A2E", linewidth=0.8)
    ax.set_xticks(x, [PERIOD_LABELS[p] for p in PERIOD_ORDER])
    ax.set_ylabel("Ratio de Sortino")
    ax.set_title(
        "Ratio de Sortino por algoritmo y régimen de volatilidad "
        "(universo fundamental, resultados de la tesis)"
    )
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    save(fig, "fig1_sortino_por_regimen")


def fig_wealth_curves() -> None:
    """Fig. 2 — cumulative wealth of the best portfolios per regime."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    show = [
        "ABC_Original",
        "ABC_FA_Scout",
        "ABC_Scout_Gravitacional",
        "PMVG_CVX",
        "Equally_Weighted",
    ]
    for ax, slug in zip(axes.flat, PERIOD_ORDER, strict=True):
        result: BacktestResult = run_backtest(
            BacktestConfig(period=slug, universe="fixed", seeds=SEEDS)
        )
        period = PERIODS[slug]
        prices = load_prices(
            start_date=period.start_date,
            end_date=period.end_date,
            tickers=list(result.tickers),
            min_days=50,
        ).ffill()
        asset_returns = prices.pct_change().dropna()
        for model in show:
            weights = result.models[model].best_weights
            wealth = np.cumprod(1.0 + asset_returns.to_numpy() @ weights)
            ax.plot(
                asset_returns.index,
                wealth,
                label=MODEL_LABELS[model],
                color=MODEL_COLORS[model],
                linewidth=1.6,
            )
        ax.axhline(1.0, color="#1A1A2E", linewidth=0.8, linestyle="--")
        ax.set_title(PERIOD_LABELS[slug])
        ax.set_ylabel("Riqueza acumulada (base 1)")
        ax.tick_params(axis="x", labelrotation=30)
        print(f"   wealth curves {slug} done")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=5, loc="lower center")
    fig.suptitle(
        "Evolución del mejor portafolio por régimen (universo fundamental)",
        fontweight="bold",
        color="#1A1A2E",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    save(fig, "fig2_riqueza_acumulada_por_regimen")


def fig_convergence() -> None:
    """Fig. 3 — mean convergence of the four ABC variants (COVID, fixed)."""
    period = PERIODS["covid_2020"]
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
    bounds = Bounds.box(len(mu))
    regime_params = load_regime_parameters(period.regime)

    fig, ax = plt.subplots(figsize=(9, 5))
    for model in (
        "ABC_Original",
        "ABC_FA_Bacanin",
        "ABC_FA_Scout",
        "ABC_Scout_Gravitacional",
    ):
        histories = []
        for seed in SEEDS:
            optimizer = build_abc_model(model, regime_params.get(model, {}), bounds.dim)
            outcome = optimizer.optimize(objective, bounds, seed=seed * 1000)
            histories.append(outcome.best_per_iteration)
        length = min(len(h) for h in histories)
        mean_history = np.mean([h[:length] for h in histories], axis=0)
        ax.plot(
            range(1, length + 1),
            mean_history,
            label=MODEL_LABELS[model],
            color=MODEL_COLORS[model],
            linewidth=1.8,
        )
        print(f"   convergence {model} done")
    ax.set_xlabel("Iteración")
    ax.set_ylabel("Mejor aptitud (promedio de 20 semillas; menor es mejor)")
    ax.set_title(
        "Convergencia de las variantes ABC — régimen COVID-19, parámetros calibrados"
    )
    ax.legend()
    save(fig, "fig3_convergencia_abc")


def fig_risk_return() -> None:
    """Fig. 4 — Sortino vs. max drawdown across all regimes (canonical)."""
    canonical = load_canonical_results()
    markers = {
        "covid_2020": "o",
        "gfc_2007_2009": "s",
        "war_2022": "^",
        "2023_stability": "D",
    }
    fig, ax = plt.subplots(figsize=(9, 6))
    for slug in PERIOD_ORDER:
        for row in canonical["fixed"]["metrics"][slug]:
            ax.scatter(
                abs(row["d"]),
                row["s"],
                color=MODEL_COLORS[row["A"]],
                marker=markers[slug],
                s=90,
                edgecolors="#1A1A2E",
                linewidths=0.6,
                zorder=3,
            )
    ax.set_xlabel("Máximo drawdown (valor absoluto)")
    ax.set_ylabel("Ratio de Sortino")
    ax.set_title(
        "Riesgo vs. retorno ajustado por regímenes "
        "(universo fundamental, resultados de la tesis)"
    )
    model_handles = [
        Line2D(
            [],
            [],
            marker="o",
            linestyle="",
            color=MODEL_COLORS[m],
            markersize=9,
            label=MODEL_LABELS[m],
        )
        for m in MODEL_COLORS
    ]
    period_handles = [
        Line2D(
            [],
            [],
            marker=markers[p],
            linestyle="",
            color="#64748B",
            markersize=9,
            label=PERIOD_LABELS[p],
        )
        for p in PERIOD_ORDER
    ]
    # Both legends live outside the axes: the lower-right data cluster (GFC
    # benchmarks) collides with any in-plot placement.
    first = ax.legend(
        handles=model_handles,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        title="Algoritmo",
    )
    ax.add_artist(first)
    ax.legend(
        handles=period_handles,
        loc="lower left",
        bbox_to_anchor=(1.02, 0.0),
        title="Régimen",
    )
    save(fig, "fig4_riesgo_retorno")


def fig_filter_comparison() -> None:
    """Fig. 5 (anexo) — best model with vs. without the z-score filter."""
    best = {
        "covid_2020": "ABC_Original",
        "gfc_2007_2009": "ABC_Original",
        "war_2022": "ABC_FA_Scout",
        "2023_stability": "ABC_Scout_Gravitacional",
    }
    from run_filter_comparison import (  # type: ignore[import-not-found]  # noqa: E402
        unfiltered_universe,
    )

    with_f: list[float] = []
    without_f: list[float] = []
    for slug, model in best.items():
        for target, tickers in ((with_f, None), (without_f, unfiltered_universe(slug))):
            result = run_backtest(
                BacktestConfig(
                    period=slug,
                    universe="fixed",
                    seeds=SEEDS,
                    models=(model,),
                    universe_tickers=tickers,
                )
            )
            target.append(result.models[model].sortino)
        print(f"   filter comparison {slug} done")

    x = np.arange(len(best))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - 0.2, with_f, 0.4, label="Con filtro z-score", color="#00E5FF")
    ax.bar(x + 0.2, without_f, 0.4, label="Sin filtro", color="#64748B")
    ax.axhline(0, color="#1A1A2E", linewidth=0.8)
    ax.set_xticks(
        x,
        [f"{PERIOD_LABELS[s]}\n({MODEL_LABELS[m]})" for s, m in best.items()],
    )
    ax.set_ylabel("Ratio de Sortino")
    ax.set_title("Mejor modelo con y sin el filtro z-score (anexo, comentario 12)")
    ax.legend()
    save(fig, "fig5_filtro_comparacion")


def fig_pfa_activation() -> None:
    """Fig. 6 (anexo) — scout activation frequency vs. max_trials (task 9)."""
    from run_pfa_sensitivity import (  # type: ignore[import-not-found]  # noqa: E402
        activation_frequency,
    )

    frame = activation_frequency(seeds=10)
    thresholds = list(frame.columns)
    fig, ax = plt.subplots(figsize=(9, 5))
    period_colors = ["#00E5FF", "#FF6B6B", "#F59E0B", "#10B981"]
    for color, (slug, row) in zip(period_colors, frame.iterrows(), strict=True):
        ax.plot(
            thresholds,
            row.to_numpy(),
            marker="o",
            color=color,
            label=PERIOD_LABELS[str(slug)],
            linewidth=1.8,
        )
    ax.axvline(300, color="#1A1A2E", linestyle="--", linewidth=1.2)
    ax.annotate(
        "valor calibrado (300)",
        xy=(300, ax.get_ylim()[1] * 0.85),
        xytext=(150, ax.get_ylim()[1] * 0.85),
        color="#1A1A2E",
        ha="right",
        arrowprops={"arrowstyle": "->", "color": "#1A1A2E"},
    )
    ax.set_xlabel("max_trials (umbral de estancamiento)")
    ax.set_ylabel("Activaciones del scout por corrida (promedio)")
    ax.set_title(
        "Frecuencia de activación de la fase scout de ABC-FAEM (anexo, comentario 9)"
    )
    ax.legend()
    save(fig, "fig6_pfa_activacion")


def main() -> None:
    """Generates all six thesis figures."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    apply_brand_style()
    print(">> fig 1: Sortino por régimen")
    fig_sortino_bars()
    print(">> fig 2: riqueza acumulada")
    fig_wealth_curves()
    print(">> fig 3: convergencia")
    fig_convergence()
    print(">> fig 4: riesgo-retorno")
    fig_risk_return()
    print(">> fig 5: filtro con/sin")
    fig_filter_comparison()
    print(">> fig 6: activación PFA")
    fig_pfa_activation()
    print("Done.")


if __name__ == "__main__":
    main()
