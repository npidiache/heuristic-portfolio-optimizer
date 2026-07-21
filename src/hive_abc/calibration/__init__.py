"""Calibration framework: grids, leak-free splits, runner, and selection.

The production path for tuning optimizer hyper-parameters (replacing the
unrunnable `legacy/` tuners): enumerate candidates with `ParameterGrid`,
cut leak-free windows with `walk_forward_splits`, evaluate every candidate
with `run_calibration`, and pick a configuration with
`select_configuration`, which prices in the multiple testing behind the
search. Deliberately independent of `hive_abc.backtest` — studies can never
disturb the frozen thesis reproduction path.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.calibration.grid import ParameterGrid, candidate_label, sample_candidates
from hive_abc.calibration.runner import CalibrationStudy, TrialResult, run_calibration
from hive_abc.calibration.selection import SelectionReport, select_configuration
from hive_abc.calibration.splits import WalkForwardSplit, walk_forward_splits

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
__all__ = [
    "CalibrationStudy",
    "ParameterGrid",
    "SelectionReport",
    "TrialResult",
    "WalkForwardSplit",
    "candidate_label",
    "run_calibration",
    "sample_candidates",
    "select_configuration",
    "walk_forward_splits",
]
