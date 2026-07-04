"""Runs the full thesis reproduction: every period x universe, all models.

Produces one JSON per (universe, period) with the canonical metric schema,
plus a consolidated `reproduction_summary.json` including execution times
(committee task 14). The Tier-2 pytest suite (`-m repro`) consumes these same
runs through the library API; this script is the human-facing artifact
generator.

Usage:
    uv run python scripts/run_reproduction.py --output outputs/reproduction
    uv run python scripts/run_reproduction.py --seeds 5   # smoke run
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from hive_abc.backtest import (  # noqa: E402
    PERIODS,
    BacktestConfig,
    BacktestResult,
    run_backtest,
)

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
UNIVERSES = ("dynamic", "fixed")


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def serialize_result(result: BacktestResult) -> dict[str, Any]:
    """
    Converts a backtest result to the canonical-schema JSON structure.

    Args:
        result: Output of `run_backtest`.

    Returns:
        Dict with `metrics` (s/d/a/o), `cardinality` (c/mw/hhi), runtimes,
        the universe used, and per-seed fitness/sortino samples.
    """
    return {
        "tickers": list(result.tickers),
        "metrics": [
            {
                "A": m,
                "s": round(r.sortino, 3),
                "d": round(r.max_drawdown, 3),
                "a": round(r.jensen_alpha, 3),
                "o": round(r.omega, 3),
            }
            for m, r in result.models.items()
        ],
        "cardinality": [
            {
                "A": m,
                "c": r.cardinality,
                "mw": round(r.max_weight, 3),
                "hhi": round(r.hhi, 3),
            }
            for m, r in result.models.items()
        ],
        "runtime_seconds": {
            m: {
                "mean": round(r.runtime.mean_seconds, 4),
                "std": round(r.runtime.std_seconds, 4),
                "total": round(r.runtime.total_seconds, 2),
            }
            for m, r in result.models.items()
        },
        "fitness_per_seed": {
            m: list(r.fitness_per_seed) for m, r in result.models.items()
        },
        "sortino_per_seed": {
            m: [round(s, 4) for s in r.sortino_per_seed]
            for m, r in result.models.items()
        },
    }


def main() -> None:
    """Runs all 8 configurations and writes the consolidated summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=REPO_ROOT / "outputs" / "reproduction"
    )
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {"seeds": args.seeds, "runs": {}}
    started = time.perf_counter()
    for universe in UNIVERSES:
        for slug in PERIODS:
            label = f"{universe}/{slug}"
            print(f">> {label} ...", flush=True)
            run_start = time.perf_counter()
            result = run_backtest(
                BacktestConfig(
                    period=slug,
                    universe=universe,  # type: ignore[arg-type]
                    seeds=tuple(range(args.seeds)),
                )
            )
            payload = serialize_result(result)
            payload["wall_seconds"] = round(time.perf_counter() - run_start, 1)
            summary["runs"][label] = payload
            (args.output / f"{universe}_{slug}.json").write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            print(f"   done in {payload['wall_seconds']}s", flush=True)

    summary["total_wall_seconds"] = round(time.perf_counter() - started, 1)
    (args.output / "reproduction_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.output / 'reproduction_summary.json'}")


if __name__ == "__main__":
    main()
