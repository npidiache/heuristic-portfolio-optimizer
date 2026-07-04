"""
PMVG_CVX: Mean-Variance (Minimum Variance) Portfolio via CVX
============================================================

Wrapper compatible with the ABC algorithm interface to act as a deterministic
benchmark. It ignores the ABC search and solves a convex optimization:

    minimize     w^T Σ w
    subject to   sum(w) = 1,  w >= 0,  lower_i <= w_i <= upper_i

Then it returns weights and, if a fitness function was provided (the same
objective used for ABCs), it evaluates it on the solved weights so results are
comparable in the backtest pipeline.
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Callable, List, Tuple

try:
    import cvxpy as cp
except Exception as _:
    cp = None  # Will raise at runtime with a clear error


class PMVG_CVX:
    def __init__(self,
                 lower: List[float],
                 upper: List[float],
                 fun: Optional[Callable] = None,
                 mu: Optional[np.ndarray] = None,
                 cov: Optional[np.ndarray] = None,
                 seed: Optional[int] = None,
                 verbose: bool = False,
                 **kwargs):
        assert len(upper) == len(lower), "'lower' and 'upper' must be same length."
        if cp is None:
            raise ImportError("cvxpy is required for PMVG_CVX. Please install 'cvxpy'.")

        self.dim = len(lower)
        self.lower = np.asarray(lower, dtype=float)
        self.upper = np.asarray(upper, dtype=float)
        self.fun = fun
        self.mu = np.asarray(mu, dtype=float) if mu is not None else None
        self.cov = np.asarray(cov, dtype=float) if cov is not None else None
        self.verbose = verbose

        if self.cov is None:
            raise ValueError("PMVG_CVX requires 'cov' (covariance matrix).")

        # Solution placeholders
        self.solution: Optional[np.ndarray] = None
        self.best: float = float('inf')

    def run(self) -> None:
        n = self.dim
        w = cp.Variable(n)
        cov_param = cp.atoms.affine.wraps.psd_wrap(self.cov)
        objective = cp.Minimize(cp.quad_form(w, cov_param))
        constraints = [cp.sum(w) == 1, w >= self.lower, w <= self.upper]
        problem = cp.Problem(objective, constraints)
        try:
            problem.solve(solver=cp.ECOS, verbose=False)
        except Exception:
            problem.solve(solver=cp.SCS, verbose=False)

        weights = np.asarray(w.value, dtype=float).flatten()
        if not np.isfinite(weights).all() or weights.sum() <= 0:
            # Fallback to equal weights within bounds
            weights = np.clip(np.ones(n) / n, self.lower, self.upper)
            s = weights.sum()
            weights = weights / s if s > 0 else weights

        # Ensure feasibility and normalization
        weights = np.clip(weights, self.lower, self.upper)
        s = weights.sum()
        if s > 0:
            weights = weights / s

        self.solution = weights
        # Compute comparable fitness if a function is provided
        if self.fun is not None:
            try:
                self.best = float(self.fun(self.solution))
            except Exception:
                self.best = float('inf')
        else:
            # If no objective provided, use negative expected return as placeholder
            if self.mu is not None:
                self.best = float(-np.dot(self.solution, self.mu))
            else:
                self.best = float('inf')

    def get_best_solution(self) -> Tuple[np.ndarray, float]:
        if self.solution is None:
            raise RuntimeError("PMVG_CVX.run() must be called before get_best_solution().")
        return self.solution, self.best


