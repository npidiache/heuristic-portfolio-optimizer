"""Canonical result tables and Obsidian Aqua HTML reports."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.reporting.html import frame_to_html, notice, render_report
from hive_abc.reporting.tables import (
    CANONICAL_RESULTS_FILE,
    DISPLAY_NAMES,
    canonical_metrics_frame,
    load_canonical_results,
    result_metrics_frame,
    runtime_frame,
    with_display_names,
)

__all__ = [
    "CANONICAL_RESULTS_FILE",
    "DISPLAY_NAMES",
    "canonical_metrics_frame",
    "frame_to_html",
    "load_canonical_results",
    "notice",
    "render_report",
    "result_metrics_frame",
    "runtime_frame",
    "with_display_names",
]
