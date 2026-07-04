"""Tests for the minimum-variance CVX benchmark."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from typing import Any

import cvxpy as cp
import numpy as np
import pytest

from hive_abc.benchmarks.min_variance import MinVarianceCVX
from hive_abc.core.types import Bounds


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def variance_objective(cov: np.ndarray) -> Any:
    """Portfolio variance evaluated on normalized weights."""

    def _objective(w: np.ndarray) -> float:
        w = w / np.sum(w)
        return float(w @ cov @ w)

    return _objective


def test_uncorrelated_two_asset_solution_is_inverse_variance() -> None:
    # Analytic min-variance with diagonal covariance: w_i proportional to
    # 1/sigma_i^2 -> (0.2, 0.8) for variances (0.04, 0.01).
    cov = np.diag([0.04, 0.01])
    result = MinVarianceCVX(cov).optimize(
        variance_objective(cov), Bounds.box(2), seed=None
    )
    assert result.best_vector == pytest.approx([0.2, 0.8], abs=1e-4)
    assert result.best_vector.sum() == pytest.approx(1.0)
    assert result.n_evaluations == 1


def test_solution_respects_upper_bounds() -> None:
    cov = np.diag([0.04, 0.01])
    bounds = Bounds(lower=np.zeros(2), upper=np.array([1.0, 0.6]))
    result = MinVarianceCVX(cov).optimize(variance_objective(cov), bounds, seed=None)
    assert result.best_vector[1] <= 0.6 + 1e-6
    assert result.best_vector.sum() == pytest.approx(1.0)


def test_rejects_non_square_covariance() -> None:
    with pytest.raises(ValueError, match="square"):
        MinVarianceCVX(np.zeros((2, 3)))


def test_rejects_dimension_mismatch() -> None:
    solver = MinVarianceCVX(np.eye(3))
    with pytest.raises(ValueError, match="dimension"):
        solver.optimize(lambda w: 0.0, Bounds.box(2), seed=None)


def test_clarabel_failure_falls_back_to_scs(monkeypatch: pytest.MonkeyPatch) -> None:
    cov = np.diag([0.04, 0.01])
    original_solve = cp.Problem.solve
    calls: list[str] = []

    def flaky_solve(self: cp.Problem, *args: Any, **kwargs: Any) -> Any:
        calls.append(str(kwargs.get("solver")))
        if kwargs.get("solver") == cp.CLARABEL:
            raise cp.SolverError("forced failure")
        return original_solve(self, *args, **kwargs)  # type: ignore[no-untyped-call]

    monkeypatch.setattr(cp.Problem, "solve", flaky_solve)
    result = MinVarianceCVX(cov).optimize(
        variance_objective(cov), Bounds.box(2), seed=None
    )
    assert calls == [str(cp.CLARABEL), str(cp.SCS)]
    assert result.best_vector == pytest.approx([0.2, 0.8], abs=1e-3)


def test_unusable_solver_output_falls_back_to_equal_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cov = np.eye(2)

    def dead_solve(self: cp.Problem, *args: Any, **kwargs: Any) -> None:
        return None  # leaves every variable's .value as None

    monkeypatch.setattr(cp.Problem, "solve", dead_solve)
    result = MinVarianceCVX(cov).optimize(
        variance_objective(cov), Bounds.box(2), seed=None
    )
    assert result.best_vector == pytest.approx([0.5, 0.5])
