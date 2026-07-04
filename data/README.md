# Data — frozen research inputs and canonical results

> [!IMPORTANT]
> <font color="#ff6b6b">**IMMUTABLE ARTIFACTS**</font>
> Everything in this folder is frozen. The thesis results were produced from
> these exact bytes; `tests/frozen_artifacts_test.py` fails if any file drifts
> from the SHA-256 checksums in [`checksums.json`](checksums.json).

## `frozen/` — input data

| File | Contents | Provenance |
| --- | --- | --- |
| `nasdaq_prices_2000_2025.csv` | Daily close prices for the NASDAQ-100 constituents, 2000-01-03 → 2024-12-31 | Downloaded once for the thesis experiments (`Hive ABC/data/raw`) |
| `nasdaq_metadata.csv` | Per-ticker coverage: start/end date, day counts, price stats, missing days | Derived from the price file |
| `z_score.csv` | Fixed top-20 universe ranked by financial-fundamentals z-score (semicolon-delimited) | Fundamentals screen described in thesis §Metodología |

## `canonical/` — frozen thesis results

`thesis_results_v1.json` is extracted from the approved thesis presentation
(`thesis/ABC_Thesis_Presentation.html`) by
[`scripts/extract_canonical_results.py`](../scripts/extract_canonical_results.py)
— the extraction is deterministic and idempotent.

Schema: `results[universe][metric_type][period]` → list of six records, one
per algorithm.

- `universe`: `dynamic` (market z-score screen) | `fixed` (fundamentals top-20)
- `metric_type`: `metrics` (`A` algorithm, `s` Sortino, `d` max drawdown,
  `a` Jensen alpha, `o` Omega) | `cardinality` (`c` holdings count, `mw` max
  weight, `hhi` concentration, plus `s`/`d`)
- `period`: `covid_2020`, `gfc_2007_2009`, `war_2022`, `2023_stability`
- Algorithm keys keep the legacy thesis-code names (`ABC_Original`,
  `ABC_FA_Bacanin`, `ABC_FA_Scout`, `ABC_Scout_Gravitacional`, `PMVG_CVX`,
  `Equally_Weighted`) so the file matches the presentation byte-for-byte;
  display names live in `hive_abc.reporting`.

## Updating checksums

Only when an artifact is *intentionally* replaced (new thesis version):

```bash
uv run python - <<'PY'
import hashlib, json, pathlib
files = sorted(pathlib.Path("data").rglob("*.csv")) + sorted(pathlib.Path("data").rglob("*.json"))
sums = {f.as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in files if f.name != "checksums.json"}
pathlib.Path("data/checksums.json").write_text(json.dumps(sums, indent=2, sort_keys=True) + "\n")
PY
```
