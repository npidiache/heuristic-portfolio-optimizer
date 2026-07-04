"""Checksum guard for the frozen research data and canonical thesis results.

These tests are the Tier-1 regression layer: the thesis results are approved
and immutable, so any byte-level drift in `data/` is a failure by definition —
including "improvements". Replacing an artifact intentionally requires
regenerating `data/checksums.json` (see `data/README.md`) in the same commit.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import hashlib
import json
from pathlib import Path

import pytest

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKSUMS = json.loads((REPO_ROOT / "data" / "checksums.json").read_text())


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("relative_path", sorted(CHECKSUMS))
def test_frozen_artifact_is_unchanged(relative_path: str) -> None:
    digest = hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()
    assert digest == CHECKSUMS[relative_path], (
        f"{relative_path} drifted from its frozen checksum. Thesis artifacts are "
        "immutable; see data/README.md before regenerating checksums."
    )


def test_checksums_cover_all_data_files() -> None:
    data_dir = REPO_ROOT / "data"
    tracked = {
        f.relative_to(REPO_ROOT).as_posix()
        for pattern in ("*.csv", "*.json")
        for f in data_dir.rglob(pattern)
        if f.name != "checksums.json"
    }
    assert tracked == set(CHECKSUMS), (
        "data/ contains files not covered by checksums.json (or vice versa)"
    )
