# Committee tasks — Assignee: Norbey

Exported from `ABC Comments.xlsx` (2026-06-27). Only the rows assigned to
Norbey are tracked here; the repo produces the annex-ready material, and the
Word document itself is edited outside this repository.

| # | Type | Comment (summary) | Resolution in this repo | Status |
| --- | --- | --- | --- | --- |
| 4 | Form/substance | Is the multi-objective utility (Eq. 13) the same as the fitness function (Eq. 18)? Validate whether they must be equal. | [`docs/thesis/objective_function.md`](../docs/thesis/objective_function.md) documents the Eq. 13 ↔ Eq. 18 mapping; `hive_abc.objectives.utility` docstrings cross-reference it. | Pending |
| 5 | Substance | Eq. 13 (p. 18) integrates Sortino, Omega, CVaR and HHI, but the penalty weights λ and η are never defined. | Executed values extracted from the frozen harness and made explicit in `hive_abc.objectives.UtilityParams`; documented in the same doc as task 4. | Pending |
| 9 | Substance | p. 21 mentions a probabilistic trigger PFA without a value or a sensitivity analysis. Note: test 0.3 / 0.4 / 0.5 on ABC-FAEM only; backtest only that model; must not affect final results. | `p_fa` parameter added to `ABCFAEM` (default 1.0 = frozen behavior); [`scripts/run_pfa_sensitivity.py`](../scripts/run_pfa_sensitivity.py) sweeps 0.3/0.4/0.5 → [`docs/analysis/pfa_sensitivity.md`](../docs/analysis/pfa_sensitivity.md). Canonical results guarded by checksum test. | Pending |
| 12 | Form/substance | Compare the best model's performance with and without the (z-score) filter. Brief mention in results; detail in annexes. | [`scripts/run_filter_comparison.py`](../scripts/run_filter_comparison.py) → [`docs/analysis/filter_comparison.md`](../docs/analysis/filter_comparison.md) (annex-ready). | Pending |
| 14 | Form (easy) | Include algorithm execution times. | `RuntimeStats` captured per model by `hive_abc.backtest.engine`; execution-times table included in [`docs/analysis/reproduction_report.md`](../docs/analysis/reproduction_report.md). | Pending |

Statuses flip to **Done** as each Phase 4 artifact lands (see repo plan).
