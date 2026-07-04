"""Frozen per-regime calibration and optimizer factory.

`regime_parameters.json` is the committed copy of the thesis's
`final_adaptive_parameters.json` (the calibrated parameters behind every
canonical run). This module translates its legacy keys to the refactored
constructor arguments and builds ready-to-run optimizer instances.
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from hive_abc.algorithms import ABCFAEM, ABCGSA, ABCFABacanin, ABCOriginal
from hive_abc.core.optimizer import HeuristicOptimizer

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Model keys are the legacy names used in the canonical results JSON.
# --------------------------------------------------------------------------------------
REGIME_PARAMETERS_FILE = Path(__file__).resolve().parent / "regime_parameters.json"

ABC_MODEL_CLASSES: dict[str, type[HeuristicOptimizer]] = {
    "ABC_Original": ABCOriginal,
    "ABC_FA_Bacanin": ABCFABacanin,
    "ABC_FA_Scout": ABCFAEM,
    "ABC_Scout_Gravitacional": ABCGSA,
}

_LEGACY_KEY_MAP = {
    "numb_bees": "colony_size",
    "max_itrs": "max_iterations",
    "G": "g_constant",
}


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def load_regime_parameters(
    regime: str, parameters_file: Path = REGIME_PARAMETERS_FILE
) -> dict[str, dict[str, float]]:
    """
    Loads the calibrated parameters of one regime, keyed by legacy model name.

    Args:
        regime: `CRISIS`, `STABLE_GROWTH`, or `UNCERTAINTY`.
        parameters_file: The frozen calibration JSON.

    Returns:
        Mapping of legacy model name to its raw legacy parameter dict.

    Raises:
        ValueError: If the regime is not present in the file.
    """
    data = json.loads(parameters_file.read_text(encoding="utf-8"))
    if regime not in data:
        raise ValueError(
            f"Regime '{regime}' not found in {parameters_file.name}; "
            f"available: {sorted(data)}"
        )
    regime_params: dict[str, dict[str, float]] = data[regime]
    return regime_params


def build_abc_model(
    model: str,
    legacy_params: Mapping[str, float],
    n_assets: int,
    overrides: Mapping[str, float] | None = None,
) -> HeuristicOptimizer:
    """
    Instantiates an ABC-family optimizer from legacy-format parameters.

    Translates legacy keys (`numb_bees`, `max_itrs`, `G`) to the refactored
    constructor names and resolves `max_trials_factor` into the explicit
    `max_trials = int(max(1, factor * numb_bees * n_assets))` the frozen
    harness used (note: the factor multiplies the REQUESTED colony size, not
    the evened one).

    Args:
        model: Legacy model key (e.g., `ABC_FA_Scout`).
        legacy_params: Raw parameter dict from `regime_parameters.json`.
        n_assets: Universe size for the `max_trials` derivation.
        overrides: Constructor-name overrides applied last — the hook the
            PFA sensitivity analysis uses (e.g., `{"p_fa": 0.4}`).

    Returns:
        A configured optimizer instance.

    Raises:
        ValueError: If `model` is not a known ABC model key.
    """
    if model not in ABC_MODEL_CLASSES:
        raise ValueError(
            f"Unknown ABC model '{model}'; expected one of {sorted(ABC_MODEL_CLASSES)}"
        )

    kwargs: dict[str, Any] = {}
    factor: float | None = None
    for key, value in legacy_params.items():
        if key == "max_trials_factor":
            factor = float(value)
        else:
            kwargs[_LEGACY_KEY_MAP.get(key, key)] = value
    if factor is not None:
        requested_bees = int(legacy_params.get("numb_bees", 20))
        kwargs["max_trials"] = int(max(1, factor * requested_bees * n_assets))
    if overrides:
        kwargs.update(overrides)

    if "colony_size" in kwargs:
        kwargs["colony_size"] = int(kwargs["colony_size"])
    if "max_iterations" in kwargs:
        kwargs["max_iterations"] = int(kwargs["max_iterations"])

    return ABC_MODEL_CLASSES[model](**kwargs)
