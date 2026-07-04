# CLAUDE.md — agent instructions

## What this repo is

`heuristic-portfolio-optimizer` formalizes Norbey Pidiache's Master in Finance
thesis: Artificial Bee Colony (ABC) variants for portfolio optimization over
the NASDAQ-100 across four volatility regimes. The installable package is
`hive_abc` (`from hive_abc import ABCFAEM`). v1.x is the academic release; the
v2 roadmap generalizes to other metaheuristics (PSO, GA) behind the
`hive_abc.core.HeuristicOptimizer` seam.

## The prime directive: thesis results are frozen

`data/canonical/thesis_results_v1.json` holds the approved thesis results and
must never change — a checksum test guards it. Any code change to algorithms,
objectives, or the backtest engine must keep the Tier-2 reproduction tests
(`pytest -m repro`) and the Tier-3 mini golden test green. If a change breaks
Tier-3, the change is wrong — do not regenerate the golden file without
explicit maintainer approval.

## Layout

- `src/hive_abc/` — the package (core, algorithms, benchmarks, objectives,
  data, backtest, metrics, reporting). Public API exported from `__init__.py`.
- `tests/` — mirrors `src/hive_abc/`; files named `<module>_test.py`.
- `data/frozen/` — committed input data (checksummed, immutable).
- `data/canonical/` — frozen thesis results (checksummed, immutable).
- `thesis/` — frozen thesis document artifacts (never edited here).
- `legacy/` — verbatim pre-refactor code, provenance only. Excluded from
  ruff/mypy/coverage. Never import from it.
- `docs/thesis/`, `docs/analysis/` — committed deliverables.
- `scripts/` — thin entry points; logic lives in the package.

## Workflow

- `uv run pytest` — default suite (excludes `repro`/`slow`/`parity` markers),
  90% branch coverage gate.
- `uv run ruff format . && uv run ruff check . && uv run mypy` — style gates.
- `uv run pytest -m repro` — full thesis reproduction (hours; usually CI-only
  via `.github/workflows/reproduction.yml`).
- Google-style docstrings, 88-char lines, `# ---` module section headers,
  `~=` dependency pins. See CONTRIBUTING.md.

## Domain naming

Public API uses thesis names; legacy code used different class names:
ABCOriginal (=ABC_BeeHive), ABCFABacanin (=ABC_FA_Bacanin),
ABCFAEM (=ABC_FA_Scout), ABCGSA (=ABC_Scout_Gravitacional),
ABCEpsilonScout (=ABC_Probabilistic_Scout), MinVarianceCVX (=PMVG_CVX).
Canonical JSON keeps the legacy string keys so it matches the thesis
presentation HTML byte-for-byte; `hive_abc.reporting` owns display names.
