# Committee tasks — Assignee: Norbey

Exported from `ABC Comments.xlsx` (2026-06-27). Only the rows assigned to
Norbey are tracked here; the repo produces the annex-ready material, and the
Word document itself is edited outside this repository.

| # | Type | Comment (summary) | Resolution in this repo | Status |
| --- | --- | --- | --- | --- |
| 3* | Form/substance | (Assignee: Luisa) The p. 15 comparative table mentions parameters like `b0` and `max_trials` that are never defined or explained later; "define them in some section". | The repo supplies that section: [`docs/thesis/calibration.md`](../docs/thesis/calibration.md) defines every parameter and documents its provenance — the multi-regime robust calibration pipeline (synthetic regimes, worst-case Sortino, 3-seed-period consensus) whose scripts live in [`legacy/`](../legacy) and whose output is the frozen [`regime_parameters.json`](../src/hive_abc/backtest/regime_parameters.json). | **Material provided** — Luisa/Norbey to transcribe |
| 4 | Form/substance | Is the multi-objective utility (Eq. 13) the same as the fitness function (Eq. 18)? Validate whether they must be equal. | [`docs/thesis/objective_function.md`](../docs/thesis/objective_function.md) documents the Eq. 13 ↔ Eq. 18 mapping (related but intentionally distinct: preference vs. executable scalarization); `hive_abc.objectives.utility` docstrings cross-reference it. | **Done** — pending docx wording |
| 5 | Substance | Eq. 13 (p. 18) integrates Sortino, Omega, CVaR and HHI, but the penalty weights λ and η are never defined. | Executed values extracted from the frozen harness: λ = 0.7 (CVaR, α = 0.99), η = 5·10⁻⁴ (L1), λ_card = 0.008·n/20 (target 10 holdings @1%). Frozen in `hive_abc.objectives.UtilityParams` and documented with task 4. | **Done** — pending docx wording |
| 9 | Substance | p. 21 mentions a probabilistic trigger PFA without a value or a sensitivity analysis. Note: test 0.3 / 0.4 / 0.5 on ABC-FAEM only; backtest only that model; must not affect final results. | `p_fa` added to `ABCFAEM` (default 1.0 = frozen behavior); [`docs/analysis/pfa_sensitivity.md`](../docs/analysis/pfa_sensitivity.md) shows the calibrated sweep is bit-identical across {0.3, 0.4, 0.5, 1.0} (the trigger never activates under the thesis's `max_trials`), plus a stressed annex diagnostic. Canonical results untouched (checksum green). | **Done** — pending docx annex |
| 12 | Form/substance | Compare the best model's performance with and without the (z-score) filter. Brief mention in results; detail in annexes. | [`docs/analysis/filter_comparison.md`](../docs/analysis/filter_comparison.md): the filter adds +2.35 / +0.57 Sortino in the COVID / GFC crises but costs −1.37 / −0.45 in stability / war-2022 — a crisis-defense mechanism. Annex-ready tables included. | **Done** — pending docx annex |
| 14 | Form (easy) | Include algorithm execution times. | Execution-times table (mean s/run per model × configuration) in [`docs/analysis/reproduction_report.md`](../docs/analysis/reproduction_report.md), captured by `RuntimeStats` in the engine. | **Done** — pending docx table |

All repo artifacts are complete; the remaining step for each task is
transcribing the annex material into the Word document, which is handled
outside this repository (see CLAUDE.md).

\* Task 3 is assigned to Luisa in the Excel, but its substance — where the
model parameters come from — is Norbey's calibration work, so the repo
provides the ready-made section.
