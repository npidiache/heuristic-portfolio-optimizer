# Committee review tracker — all 15 comments

Exported from `ABC Comments.xlsx` (2026-06-27) and validated against this
repository on 2026-07-04. The repo produces annex-ready material; the Word
document itself is edited outside this repository (see CLAUDE.md).

Legend — **Repo: done** = the analytical/technical substance exists here and
only needs transcription; **Repo: supports** = the repo provides the source
material for a document edit; **Docx only** = pure document/wording work with
no repo counterpart.

## Norbey's tasks

| # | Comment (summary) | Repo resolution | Status |
| --- | --- | --- | --- |
| 4 | Is the multi-objective utility (Eq. 13) the same as the fitness function (Eq. 18)? | [`docs/thesis/objective_function.md`](../docs/thesis/objective_function.md): related but intentionally distinct — Eq. 13 is the preference, Eq. 18 its executable scalarization; term-by-term mapping table provided. | **Repo: done** |
| 5 | Penalty weights λ and η of Eq. 13 are never defined. | Executed values extracted from the frozen harness: λ = 0.7 (CVaR, α = 0.99), η = 5·10⁻⁴ (L1), λ_card = 0.008·n/20 (target 10 holdings @1%). Frozen in `hive_abc.objectives.UtilityParams`; documented with task 4. | **Repo: done** |
| 9 | PFA probabilistic trigger: no value given, no sensitivity analysis. Sweep 0.3/0.4/0.5, ABC-FAEM only, must not affect final results. | [`docs/analysis/pfa_sensitivity.md`](../docs/analysis/pfa_sensitivity.md): (§1) calibrated sweep bit-identical across {0.3, 0.4, 0.5, 1.0}; (§2) mechanism defense — activation-frequency diagnostic (scout dormant above `max_trials ≈ 50`; calibrated value 300), p_fa 0→1 ablation with Wilcoxon (FAEM elite move directionally better mean fitness in 3/4 periods, not significant at 20 seeds), convergence profiles; (§3) prepared oral-defense summary. | **Repo: done** |
| 12 | Compare best model with vs. without the z-score filter; brief mention + annex detail. | [`docs/analysis/filter_comparison.md`](../docs/analysis/filter_comparison.md): the filter is a crisis-defense mechanism (+2.35/+0.57 Sortino in COVID/GFC; −1.37/−0.45 in stability/war). Annex tables ready. | **Repo: done** |
| 14 | Include algorithm execution times. | Execution-times table (mean s/run per model × configuration) in [`docs/analysis/reproduction_report.md`](../docs/analysis/reproduction_report.md). | **Repo: done** |

## Luisa's tasks (repo support where applicable)

| # | Comment (summary) | Repo support | Status |
| --- | --- | --- | --- |
| 1 | Include an abstract. | The README [Overview](../README.md#overview) paragraph is a ready first draft (EN; needs ES translation). | Docx only — draft available |
| 2 | Standardize model names (ABC-FAEM vs "ABC-FA-EM") and fix typos. | [`docs/thesis/naming.md`](../docs/thesis/naming.md) is the canonical naming table to standardize against. | **Repo: supports** |
| 3 | Parameters like `b0` and `max_trials` appear on p. 15 but are never defined; "define them in some section". | [`docs/thesis/calibration.md`](../docs/thesis/calibration.md): full parameter-definition table + calibration provenance (four-pillar pipeline) + frozen per-regime values. Ready to transcribe as the missing section. | **Repo: done** — transcription pending |
| 6 | Detail the z-score filters: exact windows, aggregation weights, selection thresholds (pp. 16–17). | [`docs/thesis/methodology.md`](../docs/thesis/methodology.md) § "The z-score selection stage, exactly": 252-day ex-ante window (≥180 obs), weights 0.5/0.3/0.2 on z(momentum 12-1)/z(−vol)/z(−MDD), ρ < 0.8 greedy diversification, n = 20; fixed-universe top-20 rule. Both filters covered (the comment's note asks to check both). | **Repo: done** — transcription pending |
| 7 | CVaR vs. Expected Shortfall used inconsistently. | [`docs/thesis/objective_function.md`](../docs/thesis/objective_function.md): equivalence note (CVaR ≡ Expected Shortfall, Rockafellar & Uryasev 2000) with the recommendation to state it once and standardize on one term. | **Repo: supports** |
| 8 | Eq. 20 (p. 23) looks truncated (ends in "+"). | — (typography in the Word document; the note says it may actually be fine). | Docx only |
| 10 | Include p-values / Wilcoxon tests in the result tables. | [`docs/analysis/reproduction_report.md`](../docs/analysis/reproduction_report.md) § "Wilcoxon significance": full pairwise signed-rank tests on per-seed Sortino for all 8 configurations, coherent with the dominance discourse (ABC-family-vs-benchmark pairs are the significant ones). | **Repo: done** — transcription pending |
| 11 | Report the number of assets per portfolio. | Same report, § "Portfolio cardinality": holdings count (weight > 0.5%) per model × configuration; also in the canonical JSON (`cardinality` block, keys `c`/`mw`/`hhi`). | **Repo: done** — transcription pending |
| 13 | Wrong claim on p. 31: PMVG's COVID Sortino (2.67) is *not* below every ABC algorithm (ABC-FA reports 2.10). | Confirmed by the canonical data — the repo's headline dominance claim deliberately **excludes ABC-FA (Bacanin)** for exactly this reason (see README "Canonical results" and `tests/reproduction_test.py::DOMINANT_FAMILY`). Suggested wording: "below the ABC original and the two proposed variants". | **Repo: supports** |
| 15 | The document has no figures; add some, "dejarlos bonitos". | Source material ready: the Mermaid methodology diagram (README / methodology.md), the branded HTML reports in `docs/analysis/`, and the presentation visualizer in `thesis/`. Any table in the reports can be exported as a styled figure. | **Repo: supports** |

## Summary

- **10 of 15 comments** have their full analytical substance or source
  material in this repository (3, 4, 5, 6, 9, 10, 11, 12, 14 done; 2, 7,
  13, 15 supported).
- **All remaining work is transcription/wording** in the Word document
  (handled outside the repo), plus the two purely editorial items (1, 8).
- The frozen canonical results were never touched: the checksum and golden
  tests stayed green through every analysis added for these comments.
