<div align="center">

<img src="assets/logo.svg" width="720" alt="heuristic portfolio optimizer — hive_abc, Artificial Bee Colony variants for portfolio selection">

# Heuristic portfolio optimizer

**Artificial Bee Colony variants for portfolio selection — the formalization of a Master in Finance thesis, built to grow into a general metaheuristic optimizer.**

![python](https://img.shields.io/badge/python-3.13-00e5ff?style=flat-square&labelColor=1a1a2e)
![package](https://img.shields.io/badge/uv-managed-00e5ff?style=flat-square&labelColor=1a1a2e)
![lint](https://img.shields.io/badge/ruff-clean-00e5ff?style=flat-square&labelColor=1a1a2e)
![types](https://img.shields.io/badge/mypy-strict-00e5ff?style=flat-square&labelColor=1a1a2e)
![coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-00e5ff?style=flat-square&labelColor=1a1a2e)
![thesis](https://img.shields.io/badge/thesis-v1.0_frozen-ff6b6b?style=flat-square&labelColor=1a1a2e)
![license](https://img.shields.io/badge/license-MIT-00e5ff?style=flat-square&labelColor=1a1a2e)

</div>

## Overview

`hive_abc` formalizes the thesis *"Optimización de portafolios mediante variantes del algoritmo Artificial Bee Colony"* (Pidiache, 2026 — Master in Finance): four ABC-family metaheuristics optimize NASDAQ-100 portfolios under a multi-objective utility (return − CVaR − L1 − cardinality) across four volatility regimes — the COVID-19 crash, the 2008 Global Financial Crisis, the 2022 geopolitical shock, and the 2023–2024 stability window — against classical minimum-variance and 1/N benchmarks.

The repository is built on four properties:

- **Frozen results** — the approved thesis numbers live in [`data/canonical/thesis_results_v1.json`](data/canonical/thesis_results_v1.json) and are guarded by a three-tier regression suite; code evolves, results do not.
- **Reproducible by construction** — pinned seeds, committed input data (including the ^IXIC benchmark), and a one-command reproduction of every thesis table in about a minute.
- **Typed and tested** — mypy strict, ruff, and a 90% branch-coverage gate over 129 unit tests plus property tests.
- **Designed to generalize** — every optimizer implements the small `HeuristicOptimizer` contract, the seam where the v2 roadmap (PSO, GA, …) plugs in without touching the portfolio or backtest layers.

## Contents

- [The ABC family](#the-abc-family)
- [Methodology](#methodology)
- [Canonical results](#canonical-results)
- [Reproducing the thesis](#reproducing-the-thesis)
- [Committee analyses](#committee-analyses)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [References and citation](#references-and-citation)

## The ABC family

| Public class | Thesis name | What changes vs. the original | Reference |
| --- | --- | --- | --- |
| `ABCOriginal` | ABC | — (baseline) | Karaboga (2005), TR-06 |
| `ABCFABacanin` | ABC-FA | Firefly movement in the employed phase | Tuba & Bacanin (2014) — the original implementation of the hybridization is theirs |
| `ABCFAEM` | **ABC-FAEM** (proposed) | Scout replaced by a firefly move toward a softmax-selected elite, gated by the `p_fa` trigger | this thesis |
| `ABCGSA` | **ABC-GSA** (proposed) | Scout follows the swarm's net gravitational force | this thesis; gravity analogy after Rashedi et al. (2009) |
| `ABCEpsilonScout` | (annex) | ε-greedy scout: random restart vs. best-guided move | this thesis (annex) |
| `MinVarianceCVX` | PMVG | Convex global minimum variance (benchmark) | Markowitz (1952) |
| `EqualWeight` | 1/N | Naive equal weights (benchmark) | — |

Full naming and parameter mapping (legacy classes → public API): [`docs/thesis/naming.md`](docs/thesis/naming.md).

## Methodology

```
frozen NASDAQ prices (2000–2025)
        │
        ▼
universe selection (n = 20)
  ├─ dynamic market z-score     0.5·z(momentum 12-1) + 0.3·z(−vol) + 0.2·z(−MDD), ρ < 0.8
  └─ fixed fundamentals top-20  data/frozen/z_score.csv
        │
        ▼
objective  −[ wᵀμ − 0.7·CVaR₀.₉₉(Rw) − 5·10⁻⁴·‖w‖₁ − λc·card(w) ]
        │
        ▼
optimizers × 20 pinned seeds, calibrated per regime
  ABC · ABC-FA · ABC-FAEM · ABC-GSA · PMVG · 1/N
        │
        ▼
4 volatility regimes            covid_2020 · gfc_2007_2009 · war_2022 · 2023_stability
        │
        ▼
metrics + Wilcoxon              Sortino · max drawdown · Jensen α (^IXIC) · Omega · HHI
```

The full stage-by-repo map, including the four documented deviations from the legacy pipeline, is in [`docs/thesis/methodology.md`](docs/thesis/methodology.md); the executed objective and its parameters (committee tasks 4–5) are derived in [`docs/thesis/objective_function.md`](docs/thesis/objective_function.md).

## Canonical results

Sortino ratios of the best-of-seeds portfolios, fixed fundamentals universe (the thesis's headline table):

| model | covid_2020 | gfc_2007_2009 | war_2022 | 2023_stability |
| --- | ---: | ---: | ---: | ---: |
| ABC (original) | **4.648** | **0.361** | 0.744 | 4.896 |
| ABC-FA (Bacanin) | 2.410 | −0.161 | 0.127 | 3.727 |
| ABC-FAEM | 4.290 | 0.342 | **0.811** | 4.888 |
| ABC-GSA | 4.484 | 0.324 | 0.669 | **5.011** |
| PMVG (min-variance) | 3.808 | −0.135 | −0.333 | 1.941 |
| 1/N | 2.079 | −0.513 | −0.466 | 3.305 |

The bio-inspired family (ABC original + the two proposed variants) beats both classical benchmarks on Sortino in **every** regime and universe — the ordinal claim enforced by the reproduction suite.

> [!IMPORTANT]
> <font color="#ff6b6b">**FROZEN THESIS RESULTS**</font>
> These numbers are the approved thesis results, extracted verbatim from the defense presentation and guarded by SHA-256 checksums plus a three-tier regression suite. They must not change. Full tables (both universes, all metrics): [`data/canonical/thesis_results_v1.json`](data/canonical/thesis_results_v1.json); reproduced-vs-canonical comparison: [`docs/analysis/reproduction_report.md`](docs/analysis/reproduction_report.md).

## Reproducing the thesis

```bash
uv sync --dev
uv run python scripts/run_reproduction.py     # all 8 configurations, ~1 minute
uv run pytest -m repro                        # Tier-2 assertions vs. canonical
```

Three regression tiers keep the results frozen:

| Tier | What | When it runs |
| --- | --- | --- |
| 1 | SHA-256 checksums over `data/frozen` and `data/canonical` | every `pytest` run and CI job |
| 2 | Full 20-seed reproduction within frozen tolerance bands + the family-dominance ordinal claim | `pytest -m repro` / [`reproduction.yml`](.github/workflows/reproduction.yml) |
| 3 | Exact-match mini backtest against a committed golden file | every `pytest` run and CI job |

Bitwise equality with the thesis tables is impossible by design — the legacy harness drew unpinned seeds — so Tier 2 asserts calibrated statistical bands instead; the reasoning is documented in [`tests/reproduction_test.py`](tests/reproduction_test.py).

## Committee analyses

Annex-ready material for the committee's review comments (tracker: [`thesis/committee_tasks.md`](thesis/committee_tasks.md)):

| Task | Deliverable | Headline |
| --- | --- | --- |
| 4 + 5 | [`objective_function.md`](docs/thesis/objective_function.md) | Eq. 13 (preference) vs. Eq. 18 (executed scalarization); λ = 0.7, α = 0.99, η = 5·10⁻⁴, λ_card = 0.008·n/20 |
| 9 | [`pfa_sensitivity.md`](docs/analysis/pfa_sensitivity.md) | Under calibrated parameters the PFA trigger never activates — results are provably identical for p_fa ∈ {0.3, 0.4, 0.5, 1.0} |
| 12 | [`filter_comparison.md`](docs/analysis/filter_comparison.md) | The z-score filter is a crisis-defense mechanism: +2.35/+0.57 Sortino in COVID/GFC, −1.37/−0.45 in calm regimes |
| 14 | [`reproduction_report.md`](docs/analysis/reproduction_report.md) | Execution-times table per model × configuration |

## Project structure

```
heuristic-portfolio-optimizer/
├── src/hive_abc/          # the installable package
│   ├── core/              # HeuristicOptimizer contract, Bounds, OptimizationResult (v2 seam)
│   ├── algorithms/        # BeeHive template + the five ABC variants
│   ├── benchmarks/        # MinVarianceCVX, EqualWeight
│   ├── objectives/        # CVaR, penalties, the executed thesis utility
│   ├── data/              # frozen-data loaders + universe selection
│   ├── backtest/          # periods, calibrated parameters, engine
│   ├── metrics/           # quantstats-parity performance + concentration + Wilcoxon
│   └── reporting/         # canonical tables + Obsidian Aqua HTML reports
├── tests/                 # mirrors src/; *_test.py; golden/ Tier-3 file
├── data/frozen/           # committed input data (checksummed, immutable)
├── data/canonical/        # frozen thesis results (checksummed, immutable)
├── thesis/                # frozen thesis document + committee task tracker
├── legacy/                # verbatim pre-refactor code (provenance only)
├── docs/thesis/           # objective function, naming, methodology notes
├── docs/analysis/         # committed analysis deliverables (md + html)
├── scripts/               # thin entry points (reproduction, task 9, task 12)
└── .github/workflows/     # PR coverage gate + dispatchable full reproduction
```

| Layer | Import | Purpose |
| --- | --- | --- |
| `hive_abc.core` | `HeuristicOptimizer`, `Bounds`, `OptimizationResult` | Algorithm-agnostic contract every optimizer implements |
| `hive_abc.algorithms` | `ABCOriginal`, `ABCFABacanin`, `ABCFAEM`, `ABCGSA`, `ABCEpsilonScout` | The ABC family; variants override exactly one hook of the shared `BeeHive` template |
| `hive_abc.objectives` | `PortfolioUtilityObjective`, `UtilityParams` | The executed thesis objective with its frozen parameters |
| `hive_abc.backtest` | `BacktestConfig`, `run_backtest`, `PERIODS` | Replays any thesis experiment end to end |
| `hive_abc.reporting` | `result_metrics_frame`, `render_report` | Canonical-schema tables and branded HTML reports |

## Getting started

Prerequisites: [uv](https://docs.astral.sh/uv/) (installs Python 3.13 automatically).

```bash
git clone <repo-url> && cd heuristic-portfolio-optimizer
uv sync --dev
uv run pytest          # 129 tests, ≥90% branch coverage, Tier-1 + Tier-3 guards
```

## Usage

```python
import numpy as np
from hive_abc import ABCFAEM, Bounds, PortfolioUtilityObjective
from hive_abc.backtest import BacktestConfig, run_backtest
from hive_abc.data import compute_log_returns, compute_moments, load_prices

# Low-level: optimize any objective over a box
prices = load_prices(start_date="2023-01-01", end_date="2024-12-31",
                     tickers=["NVDA", "MSFT", "AAPL", "AMZN", "META"], min_days=50)
returns = compute_log_returns(prices)
mu, _ = compute_moments(returns)
objective = PortfolioUtilityObjective(returns.to_numpy(), mu.to_numpy())

result = ABCFAEM(colony_size=25, max_iterations=60).optimize(
    objective, Bounds.box(len(mu)), seed=42
)
weights = result.best_vector / result.best_vector.sum()

# High-level: replay a thesis experiment
outcome = run_backtest(BacktestConfig(period="covid_2020", universe="fixed"))
print(outcome.models["ABC_FA_Scout"].sortino)
```

## Roadmap

- **v1.x (academic)** — the thesis formalization: frozen results, committee annexes, reproduction suite. *This release.*
- **v2 (heuristic portfolio optimizer)** — additional metaheuristics (PSO, GA, simulated annealing) behind the same `HeuristicOptimizer` contract; rebalancing backtests; a strategy-comparison CLI. The `core/` seam exists so none of this touches the frozen v1 surface.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — uv workflow, ruff/mypy-strict/90%-coverage gates, the frozen-results contract, and the PR checklist. Agent instructions live in [CLAUDE.md](CLAUDE.md).

## References and citation

Key literature (full list in [`docs/thesis/methodology.md`](docs/thesis/methodology.md)):

- Karaboga, D. (2005). *An idea based on honey bee swarm for numerical optimization*. TR-06, Erciyes University.
- Tuba, M., & Bacanin, N. (2014). *Artificial bee colony algorithm hybridized with firefly algorithm for cardinality constrained mean-variance portfolio selection*. Appl. Math. Inf. Sci. 8(6).
- Yang, X.-S. (2009). *Firefly algorithms for multimodal optimization*. SAGA.
- Rashedi, E., Nezamabadi-pour, H., & Saryazdi, S. (2009). *GSA: A gravitational search algorithm*. Information Sciences 179(13).
- Markowitz, H. (1952). *Portfolio selection*. The Journal of Finance 7(1).

To cite this software, use [CITATION.cff](CITATION.cff).
