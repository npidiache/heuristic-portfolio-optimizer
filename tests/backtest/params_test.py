"""Tests for the frozen calibration loader and optimizer factory."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import pytest

from hive_abc.algorithms import ABCFAEM, ABCGSA
from hive_abc.backtest.params import build_abc_model, load_regime_parameters


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_loads_frozen_crisis_parameters() -> None:
    params = load_regime_parameters("CRISIS")
    assert params["ABC_FA_Scout"]["b0"] == 1.4
    assert params["ABC_Scout_Gravitacional"]["G"] == 0.3
    assert params["ABC_Original"]["numb_bees"] == 20


def test_unknown_regime_raises() -> None:
    with pytest.raises(ValueError, match="Regime 'BULL'"):
        load_regime_parameters("BULL")


def test_build_translates_legacy_keys_and_max_trials() -> None:
    legacy = {
        "numb_bees": 25,
        "max_itrs": 60,
        "max_trials_factor": 0.6,
        "b0": 1.4,
        "gamma": 1.4,
        "alpha": 0.05,
    }
    model = build_abc_model("ABC_FA_Scout", legacy, n_assets=20)
    assert isinstance(model, ABCFAEM)
    # Legacy derivation multiplies the REQUESTED colony size (25), not the
    # evened one (26): 0.6 * 25 * 20 = 300.
    assert model._max_trials == 300
    assert model._size == 26
    assert model._b0 == 1.4


def test_build_translates_gravitational_constant() -> None:
    legacy = {"numb_bees": 25, "max_itrs": 60, "G": 0.7, "epsilon": 1e-10}
    model = build_abc_model("ABC_Scout_Gravitacional", legacy, n_assets=10)
    assert isinstance(model, ABCGSA)
    assert model._g == 0.7


def test_overrides_apply_last() -> None:
    legacy = {"numb_bees": 25, "max_itrs": 60}
    model = build_abc_model(
        "ABC_FA_Scout", legacy, n_assets=10, overrides={"p_fa": 0.4}
    )
    assert isinstance(model, ABCFAEM)
    assert model._p_fa == 0.4


def test_unknown_model_raises() -> None:
    with pytest.raises(ValueError, match="Unknown ABC model"):
        build_abc_model("ABC_Quantum", {}, n_assets=10)
