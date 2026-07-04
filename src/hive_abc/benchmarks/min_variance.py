"""Deterministic minimum-variance benchmark solved with cvxpy."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import time

import cvxpy as cp
import numpy as np
from numpy.typing import NDArray

from hive_abc.core.optimizer import HeuristicOptimizer
from hive_abc.core.types import Bounds, ObjectiveFn, OptimizationResult


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class MinVarianceCVX(HeuristicOptimizer):
    """
    Global minimum-variance portfolio (legacy `PMVG_CVX`, thesis "PMVG").

    Solves the convex program

        minimize    w' Sigma w
        subject to  sum(w) = 1,  lower <= w <= upper

    and evaluates the supplied objective on the solved weights so the value
    is comparable with the ABC family in the backtest. The solve is
    deterministic — `seed` is accepted for interface compatibility and
    recorded in the result, but has no effect.

    The legacy code solved with ECOS and fell back to SCS; cvxpy >= 1.6
    deprecates ECOS, so this implementation uses Clarabel with an SCS
    fallback. If the solver output is unusable, it falls back to clipped
    equal weights exactly like the legacy code.

    Args:
        cov: Asset-return covariance matrix (n x n, symmetric).

    Raises:
        ValueError: If `cov` is not a square 2-D matrix.
    """

    def __init__(self, cov: NDArray[np.float64]) -> None:
        cov = np.asarray(cov, dtype=float)
        if cov.ndim != 2 or cov.shape[0] != cov.shape[1]:
            raise ValueError(f"cov must be a square matrix; got shape {cov.shape}")
        self._cov = cov

    def optimize(
        self,
        objective: ObjectiveFn,
        bounds: Bounds,
        *,
        seed: int | None = None,
    ) -> OptimizationResult:
        """
        Solves the minimum-variance program within `bounds`.

        Args:
            objective: Evaluated once on the solved weights for
                comparability with stochastic optimizers.
            bounds: Box constraints; its dimension must match `cov`.
            seed: Ignored (deterministic solve); recorded in the result.

        Returns:
            The solved (clipped, normalized) weights and their objective
            value; convergence histories contain the single solve.

        Raises:
            ValueError: If `bounds.dim` does not match the covariance size.
        """
        if bounds.dim != self._cov.shape[0]:
            raise ValueError(
                f"bounds dimension {bounds.dim} does not match covariance "
                f"size {self._cov.shape[0]}"
            )
        start = time.perf_counter()
        weights = self._solve(bounds)
        value = float(objective(weights))
        return OptimizationResult(
            best_vector=weights,
            best_value=value,
            best_per_iteration=(value,),
            mean_per_iteration=(value,),
            n_evaluations=1,
            runtime_seconds=time.perf_counter() - start,
            seed=seed,
        )

    def _solve(self, bounds: Bounds) -> NDArray[np.float64]:
        """Runs the convex solve with fallbacks preserved from the legacy code."""
        n = bounds.dim
        w = cp.Variable(n)
        covariance = cp.psd_wrap(self._cov)  # type: ignore[attr-defined]
        problem = cp.Problem(
            cp.Minimize(cp.quad_form(w, covariance)),  # type: ignore[attr-defined]
            [
                cp.sum(w) == 1,  # type: ignore[attr-defined]
                w >= bounds.lower,
                w <= bounds.upper,
            ],
        )
        try:
            problem.solve(solver=cp.CLARABEL, verbose=False)  # type: ignore[no-untyped-call]
        except cp.SolverError:
            problem.solve(solver=cp.SCS, verbose=False)  # type: ignore[no-untyped-call]

        solution = None if w.value is None else np.asarray(w.value, dtype=float)
        if solution is None or not np.isfinite(solution).all() or solution.sum() <= 0:
            solution = np.clip(np.ones(n) / n, bounds.lower, bounds.upper)
            total = solution.sum()
            if total > 0:
                solution = solution / total

        solution = np.clip(solution.flatten(), bounds.lower, bounds.upper)
        total = solution.sum()
        if total > 0:
            solution = solution / total
        return np.asarray(solution, dtype=np.float64)
