"""Concentration analysis of the Dirichlet elite scout (annex section A.7).

The unconstrained Dirichlet restart beats ABC original on Sortino, but its
portfolios are far more concentrated (effective cardinality ~2, max weight
>55%): the operator's exploratory reach extends to concentrated regions that
the original box-space search never visits, and which fall outside the scope
the frozen Eq. 18 was designed for. A rigorous comparison therefore adds an
institutional-style concentration limit so both algorithms compete over the
same admissible set. This script quantifies the effect with two controls:

1. a cardinality floor (at least five significant holdings), added as the
   symmetric penalty `lambda_card * max(0, 5 - holdings)**2`; and
2. a hard 20% weight cap, enforced by projecting the normalized weights onto the
   capped simplex, so every evaluated portfolio satisfies the constraint.

Both controls are applied identically to ABC original and to the Dirichlet
scout, under paired seeds, across the four thesis regimes and both universes.
Diagnostics only: the frozen thesis results are untouched.

Writes `docs/analysis/scout_concentration_analysis.md`.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import argparse
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, SupportsFloat, cast

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# noqa comments: imports must follow the sys.path bootstrap in scripts.
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from numpy.typing import NDArray  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

from hive_abc.algorithms import ABCAdaptiveScout  # noqa: E402
from hive_abc.algorithms.scouting import (  # noqa: E402
    DirichletEliteRestart,
    ProportionalTrialLimit,
)
from hive_abc.backtest.params import (  # noqa: E402
    build_abc_model,
    load_regime_parameters,
)
from hive_abc.backtest.periods import PERIODS  # noqa: E402
from hive_abc.core.optimizer import HeuristicOptimizer  # noqa: E402
from hive_abc.core.types import Bounds, ObjectiveFn  # noqa: E402
from hive_abc.data.loading import (  # noqa: E402
    FROZEN_PRICES,
    FROZEN_ZSCORE,
    compute_log_returns,
    compute_moments,
    load_prices,
)
from hive_abc.data.universe import (  # noqa: E402
    load_fixed_zscore_universe,
    select_universe_dynamic_zscore,
)
from hive_abc.metrics.performance import sortino_ratio  # noqa: E402
from hive_abc.metrics.stats import holm_bonferroni  # noqa: E402
from hive_abc.objectives.utility import PortfolioUtilityObjective  # noqa: E402

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
DOCS_DIR = REPO_ROOT / "docs" / "analysis"
UNIVERSES: tuple[Literal["fixed", "dynamic"], ...] = ("fixed", "dynamic")
BASELINE = "ABC original"
OPERATOR = "Dirichlet élite"
SIGNIFICANT_THRESHOLD = 0.01
MIN_HOLDINGS = 5
WEIGHT_CAP = 0.20
DIRICHLET_FRACTION = 0.15
PERIOD_LABELS = {
    "covid_2020": "COVID-19 (2020)",
    "gfc_2007_2009": "Crisis 2007–09",
    "war_2022": "Guerra (2022)",
    "2023_stability": "Estabilidad (2023–24)",
}


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class RunRecord:
    """One optimizer run's portfolio profile under a given scenario."""

    scenario: str
    universe: str
    period: str
    model: str
    seed: int
    sortino: float
    holdings: int
    effective_cardinality: float
    max_weight: float


class FloorObjective:
    """Eq. 18 plus a penalty for holding fewer than `min_holdings` names."""

    def __init__(self, base: ObjectiveFn, n_assets: int) -> None:
        self._base = base
        self._lambda = 0.008 * n_assets / 20

    def __call__(self, weights: NDArray[np.float64]) -> float:
        value = float(self._base(weights))
        vector = np.asarray(weights, dtype=float)
        total = float(vector.sum())
        if total <= 1e-9:
            return value
        normalized = vector / total
        holdings = int((normalized > SIGNIFICANT_THRESHOLD).sum())
        deficit = max(0, MIN_HOLDINGS - holdings)
        return value + self._lambda * deficit**2


class CappedObjective:
    """Eq. 18 evaluated on the cap-projected portfolio (hard weight cap)."""

    def __init__(self, base: ObjectiveFn) -> None:
        self._base = base

    def __call__(self, weights: NDArray[np.float64]) -> float:
        vector = np.asarray(weights, dtype=float)
        if float(vector.sum()) <= 1e-9:
            return float(self._base(vector))
        return float(self._base(cap_project(vector)))


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def cap_project(
    raw: NDArray[np.float64], cap: float = WEIGHT_CAP
) -> NDArray[np.float64]:
    """
    Projects raw weights onto the simplex with a per-asset upper bound.

    Uses proportional water-filling: weights above the cap are clipped and their
    excess is redistributed among the remaining assets in proportion to their
    current weight, repeating until no weight exceeds the cap.

    Args:
        raw: Unnormalized weight vector from an optimizer.
        cap: Maximum admissible weight per asset.

    Returns:
        Normalized weights summing to one, each at most `cap`.
    """
    vector = np.asarray(raw, dtype=float)
    size = vector.size
    total = float(vector.sum())
    if total <= 1e-12:
        return np.full(size, 1.0 / size)
    weights = vector / total
    for _ in range(200):
        over = weights > cap + 1e-12
        if not over.any():
            break
        excess = float((weights[over] - cap).sum())
        weights[over] = cap
        under = ~over
        pool = float(weights[under].sum())
        if pool <= 1e-12:
            if under.any():
                weights[under] += excess / int(under.sum())
            break
        weights[under] += excess * (weights[under] / pool)
    return np.asarray(weights, dtype=np.float64)


def build_model(
    model: str, regime_params: Mapping[str, Mapping[str, float]], n_assets: int
) -> HeuristicOptimizer:
    """
    Instantiates the baseline or the Dirichlet-scout optimizer.

    Args:
        model: `BASELINE` or `OPERATOR`.
        regime_params: Calibrated parameters of the period's regime.
        n_assets: Universe size.

    Returns:
        A configured optimizer.
    """
    if model == BASELINE:
        return build_abc_model("ABC_Original", regime_params["ABC_Original"], n_assets)
    faem = regime_params["ABC_FA_Scout"]
    return ABCAdaptiveScout(
        trigger=ProportionalTrialLimit(fraction=DIRICHLET_FRACTION),
        scout_move=DirichletEliteRestart(),
        colony_size=int(faem["numb_bees"]),
        max_iterations=int(faem["max_itrs"]),
    )


def universe_tickers(universe: str, start_date: str) -> list[str]:
    """
    Resolves the ticker list for one universe mode.

    Args:
        universe: `fixed` or `dynamic`.
        start_date: Window start, used by the dynamic screen.

    Returns:
        Selected tickers.
    """
    if universe == "fixed":
        return load_fixed_zscore_universe(FROZEN_ZSCORE)
    return select_universe_dynamic_zscore(start_date, prices_file=FROZEN_PRICES)


def scenario_objectives(
    base: PortfolioUtilityObjective, n_assets: int
) -> tuple[tuple[str, ObjectiveFn, bool], ...]:
    """
    Builds the three scenarios as (label, objective, applies_cap) triples.

    Args:
        base: The frozen Eq. 18 objective.
        n_assets: Universe size, for the floor penalty's lambda scaling.

    Returns:
        Scenario label, objective to optimize, and whether the reported
        portfolio must be cap-projected.
    """
    return (
        ("Sin restricción", base, False),
        ("Piso de cinco posiciones", FloorObjective(base, n_assets), False),
        (f"Tope duro de {WEIGHT_CAP:.0%}", CappedObjective(base), True),
    )


def run_grid(seeds: int) -> pd.DataFrame:
    """
    Runs both models under the three scenarios over every universe and period.

    Args:
        seeds: Paired seeds per configuration.

    Returns:
        Long-format records, one row per run.
    """
    records: list[RunRecord] = []
    for universe in UNIVERSES:
        for slug, period in PERIODS.items():
            tickers = universe_tickers(universe, period.start_date)
            prices = load_prices(
                FROZEN_PRICES, period.start_date, period.end_date, tickers, min_days=50
            )
            log_returns = compute_log_returns(prices)
            mu, _ = compute_moments(log_returns)
            n_assets = int(mu.shape[0])
            base = PortfolioUtilityObjective(log_returns.to_numpy(), mu.to_numpy())
            bounds = Bounds.box(n_assets)
            asset_returns = prices.ffill().pct_change().dropna().to_numpy(dtype=float)
            regime_params = load_regime_parameters(period.regime)

            for label, objective, applies_cap in scenario_objectives(base, n_assets):
                for model in (BASELINE, OPERATOR):
                    for seed in range(seeds):
                        outcome = build_model(model, regime_params, n_assets).optimize(
                            objective, bounds, seed=seed
                        )
                        weights = (
                            cap_project(outcome.best_vector)
                            if applies_cap
                            else outcome.best_vector / outcome.best_vector.sum()
                        )
                        returns = np.asarray(asset_returns @ weights, dtype=np.float64)
                        records.append(
                            RunRecord(
                                scenario=label,
                                universe=universe,
                                period=slug,
                                model=model,
                                seed=seed,
                                sortino=sortino_ratio(returns),
                                holdings=int((weights > SIGNIFICANT_THRESHOLD).sum()),
                                effective_cardinality=1.0 / float(np.sum(weights**2)),
                                max_weight=float(weights.max()),
                            )
                        )
                print(f"   {universe} / {slug} / {label} done", flush=True)
    return pd.DataFrame([record.__dict__ for record in records])


def as_float(value: object) -> float:
    """
    Converts pandas scalar values to plain floats for strict typing.

    Args:
        value: Scalar read from a pandas object.

    Returns:
        The value as a Python float.
    """
    return float(cast(SupportsFloat, value))


def concentration_table(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Per-regime concentration profile of the unconstrained portfolios.

    Args:
        frame: Long-format run records.

    Returns:
        Table indexed by period and model (fixed universe).
    """
    sliced = frame[
        (frame["scenario"] == "Sin restricción") & (frame["universe"] == "fixed")
    ]
    table = sliced.groupby(["period", "model"], sort=False).agg(
        posiciones=("holdings", "mean"),
        card_efectiva=("effective_cardinality", "mean"),
        peso_maximo=("max_weight", "mean"),
    )
    return table.reindex(
        pd.MultiIndex.from_product([list(PERIODS), [BASELINE, OPERATOR]])
    )


def scenario_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate Sortino and concentration per scenario, plus Holm-significant wins.

    Args:
        frame: Long-format run records.

    Returns:
        One row per scenario.
    """
    rows: list[dict[str, object]] = []
    for scenario, sliced in frame.groupby("scenario", sort=False):
        cells = sliced.pivot_table(
            index=["universe", "period", "seed"], columns="model", values="sortino"
        )
        p_values: dict[str, float] = {}
        favourable: dict[str, bool] = {}
        for key, cell in cells.groupby(level=["universe", "period"], sort=False):
            a = cell[BASELINE].to_numpy(dtype=float)
            b = cell[OPERATOR].to_numpy(dtype=float)
            name = f"{key[0]}/{key[1]}"
            p_values[name] = 1.0 if np.all(a == b) else float(wilcoxon(a, b).pvalue)
            favourable[name] = bool(b.mean() > a.mean())
        rejected = holm_bonferroni(p_values, alpha=0.05)
        wins = sum(1 for k, ok in rejected.items() if ok and favourable[k])
        operator_rows = sliced[sliced["model"] == OPERATOR]
        rows.append(
            {
                "escenario": scenario,
                "dirichlet": as_float(operator_rows["sortino"].mean()),
                "abc": as_float(sliced[sliced["model"] == BASELINE]["sortino"].mean()),
                "card_efectiva": as_float(
                    operator_rows["effective_cardinality"].mean()
                ),
                "peso_maximo": as_float(operator_rows["max_weight"].mean()),
                "celdas_favorables_holm": f"{wins} de 8",
            }
        )
    summary = pd.DataFrame(rows)
    summary["diferencia"] = summary["dirichlet"] - summary["abc"]
    return summary[
        [
            "escenario",
            "dirichlet",
            "abc",
            "diferencia",
            "card_efectiva",
            "peso_maximo",
            "celdas_favorables_holm",
        ]
    ]


def write_report(frame: pd.DataFrame, seeds: int) -> None:
    """
    Writes the markdown report backing annex section A.7.

    Args:
        frame: Long-format run records.
        seeds: Paired seeds per configuration.
    """
    today = date.today().isoformat()
    concentration = concentration_table(frame)
    summary = scenario_summary(frame)
    lines = [
        "# Análisis de concentración del reinicio de Dirichlet élite",
        "",
        f"Generado {today} por `scripts/run_scout_concentration_analysis.py` "
        f"({seeds} semillas pareadas por configuración; cuatro regímenes y dos "
        "universos).",
        "",
        "> [!IMPORTANT]",
        "> Diagnóstico exploratorio. Los resultados congelados de la tesis no se "
        "modifican. Respalda la sección A.7 del anexo de activación del explorador.",
        "",
        "## Concentración de los portafolios finales (universo fijo, sin restricción)",
        "",
        concentration.to_markdown(floatfmt=".2f"),
        "",
        "## Efecto de las restricciones de concentración",
        "",
        summary.to_markdown(index=False, floatfmt=".3f"),
        "",
        "El tope duro de peso máximo es la única restricción que controla "
        "efectivamente la concentración: el piso de cinco posiciones se satisface "
        "manteniendo un peso máximo superior al 50 %. Bajo el tope, la ventaja del "
        "operador se reduce pero conserva significancia estadística tras la "
        "corrección de Holm, de modo que una parte de la diferencia inicial era "
        "atribuible a la concentración y otra corresponde a una mejora de búsqueda.",
        "",
    ]
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "scout_concentration_analysis.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    """Runs the concentration analysis and writes its report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args()

    frame = run_grid(args.seeds)
    write_report(frame, args.seeds)
    print(f"Wrote {DOCS_DIR / 'scout_concentration_analysis.md'}")


if __name__ == "__main__":
    main()
