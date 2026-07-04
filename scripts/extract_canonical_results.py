"""Extracts the canonical thesis results from the presentation HTML.

The thesis presentation (`thesis/ABC_Thesis_Presentation.html`) embeds the
approved results as a JavaScript literal (`const DATA = {...};`). This script
converts that literal to JSON and writes `data/canonical/thesis_results_v1.json`,
the immutable source of truth guarded by the checksum regression test. The
conversion is deterministic (sorted keys, fixed indentation), so re-running the
script on the same HTML is idempotent.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import argparse
import json
import re
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HTML = REPO_ROOT / "thesis" / "ABC_Thesis_Presentation.html"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "canonical" / "thesis_results_v1.json"

DATA_BLOCK_PATTERN = re.compile(r"const DATA = (\{.*?\});", re.DOTALL)


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def convert_js_object_to_json(js_literal: str) -> dict[str, Any]:
    """
    Converts the presentation's JavaScript object literal into a Python dict.

    The literal uses unquoted identifier keys (`metrics:`), single-quoted
    string keys (`'2023_stability':`), and single-quoted string values — all
    invalid JSON. Keys and values never contain escaped quotes, so plain
    regex substitution is safe here.

    Args:
        js_literal: The `{...}` object literal captured from the HTML.

    Returns:
        The parsed results structure keyed by universe, metric type, and
        period.

    Raises:
        json.JSONDecodeError: If the literal contains syntax this converter
            does not handle.
    """
    quoted_keys = re.sub(
        r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', js_literal
    )
    json_text = quoted_keys.replace("'", '"')
    parsed: dict[str, Any] = json.loads(json_text)
    return parsed


def extract_canonical_results(html_path: Path, output_path: Path) -> dict[str, Any]:
    """
    Reads the presentation HTML and writes the canonical results JSON.

    Args:
        html_path: Path to the thesis presentation HTML.
        output_path: Destination for the canonical JSON file.

    Returns:
        The extracted results structure that was written.

    Raises:
        ValueError: If the HTML does not contain a `const DATA = {...};` block.
    """
    html = html_path.read_text(encoding="utf-8")
    match = DATA_BLOCK_PATTERN.search(html)
    if match is None:
        raise ValueError(f"No 'const DATA = {{...}};' block found in {html_path}")

    results = convert_js_object_to_json(match.group(1))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return results


def main() -> None:
    """Parses CLI arguments and runs the extraction."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    results = extract_canonical_results(args.html, args.output)
    universes = ", ".join(sorted(results))
    print(f"Wrote {args.output} (universes: {universes})")


if __name__ == "__main__":
    main()
