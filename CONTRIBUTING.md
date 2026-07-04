# Contributing

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — manages the interpreter, the virtual
  environment, and the lockfile. Python 3.13 is pinned via `.python-version`
  and installed automatically by `uv sync`.

```bash
uv sync --dev
```

## Running tests

```bash
uv run pytest                      # default suite (90% branch coverage gate)
uv run pytest tests/algorithms     # a subset
uv run pytest -m repro             # full thesis reproduction (hours)
uv run pytest -m parity            # metric parity vs quantstats (needs: uv sync --group parity)
```

The default run excludes the `repro`, `slow`, and `parity` markers — those are
long or environment-dependent and run through
[`reproduction.yml`](.github/workflows/reproduction.yml) or on demand.

### Coverage

- Gate: **90% branch coverage** on `src/`, enforced by `--cov-fail-under=90`
  in `pyproject.toml` and re-checked in CI (total + diff coverage on changed
  lines via diff-cover).
- Artifacts land in `coverage/` (git-ignored), never at the repo root.
- Excluded lines: `pragma: no cover`, `__main__` blocks,
  `raise NotImplementedError` stubs, `TYPE_CHECKING` imports.

## Style

- **Ruff** is the single formatter/linter (`E, W, F, I, B, C4, UP`; line
  length 88 for code and docstrings). Run `uv run ruff format . && uv run
  ruff check .` before pushing.
- **Mypy strict** on `src/`, `tests/`, and `scripts/`: every signature typed.
- Google-style docstrings on every public module/class/function — types live
  in the signature, never restated in `Args:`.
- Module section headers (`# ---` rules at column 88) divide every source
  file into Libraries / Global Variables / Exceptions / Classes / Functions.
- Tests mirror `src/` and are named `<module>_test.py`.

## Dependencies

Every dependency uses the compatible-release operator `~=X.Y.Z` (patch
updates only). `uv.lock` pins exact versions; minor/major upgrades are
explicit edits to `pyproject.toml`, never silent.

```bash
uv add "somelib~=1.2.0"
uv add --dev "sometool~=3.4.0"
```

Python is pinned at 3.13 (not newer) because the scientific stack this repo
depends on (cvxpy and its solver wheels) is validated there.

## The frozen-results contract

The thesis results in `data/canonical/thesis_results_v1.json` and the input
data in `data/frozen/` are **immutable** — checksum tests fail if they drift.
Changes to `hive_abc.algorithms`, `hive_abc.objectives`, or
`hive_abc.backtest` must keep:

1. the Tier-3 mini golden test (exact match, runs in every CI job) green, and
2. the Tier-2 reproduction suite (`pytest -m repro`) green.

Never regenerate `tests/golden/mini_backtest_expected.json` to make a failing
test pass — that inverts the regression guard. Regeneration requires an
intentional, documented behavior change approved by the maintainer.

## PR workflow

1. Branch from `master`; never commit to `master` directly.
2. `uv run ruff format . && uv run ruff check . && uv run mypy && uv run pytest`.
3. Open a PR — the `coverage` workflow posts a sticky comment with lint,
   type-check, total coverage, and diff-coverage results; all gates must pass.
4. If optimizer/objective/backtest code changed, dispatch the `reproduction`
   workflow and link the green run in the PR.

## Versioning

- `X.0.0` — result-affecting changes (require a new canonical results file
  and thesis-reviewer awareness).
- `0.X.0` — new features (new algorithms, reports, data loaders).
- `0.0.X` — fixes and docs.
