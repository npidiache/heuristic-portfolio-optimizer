# Scout-activation telemetry diagnostic (reviewer task 9 follow-up)

Generated 2026-07-20 by `scripts/run_scout_activation_telemetry.py` (20 paired seeds per configuration, identical seeds across configurations; both universes, all four thesis periods).

Reviewer comment 9 established that the thesis's FAEM scout never activates under the calibrated configuration, and [`pfa_sensitivity.md`](pfa_sensitivity.md) §5 committed to a future line: study when elite-guided recovery is worth activating. This diagnostic is the first result of that line, built on two v2 additions (branch `feat/abc-scout-v2`):

- **First-class activation telemetry** (commit `21e7042`): every `optimize()` run reports `scout_activations` and `scout_activation_iterations` on `OptimizationResult`, so activation is now measured, not inferred.
- **`ABCAdaptiveScout`** (commit `c10387a`): a pluggable scout phase — a `ScoutTrigger` decides *who* scouts (budget-proportional trial limits, diversity collapse) and a `ScoutMove` decides *where* the scout goes (corrected-scaling firefly elite move, Lévy flights, Dirichlet elite restarts, canonical random restart). The corrected firefly move normalizes the attraction distance by `sqrt(dim)` — at thesis dimensionality the v1 attraction `exp(-γ·r²)` is ≈ 0.01 at typical inter-bee distances, i.e. the elite move degenerated to noise; normalized, it retains ≈ 0.85 attraction at the same distance. v1 classes are byte-stable (Tier-1/2/3 guards green).

> [!IMPORTANT]
> These runs are exploratory diagnostics, not replacement thesis results. Frozen thesis artifacts are untouched. Runs use identical seeds across configurations (paired Wilcoxon), not the engine's per-model seed offsets, so values differ from the canonical tables by construction. Adaptive configurations run uncalibrated policy defaults at ABC-FAEM's calibrated budget (25 bees, 60 iterations).

## 1. Activation telemetry — the mechanism is now observable

Mean scout activations per run (both universes):

| model                            |   covid_2020 |   gfc_2007_2009 |   war_2022 |   2023_stability |
|:---------------------------------|-------------:|----------------:|-----------:|-----------------:|
| ABC original                     |          0.0 |             0.0 |        0.0 |              0.0 |
| ABC-FAEM frozen mt=300           |          0.0 |             0.0 |        0.0 |              0.0 |
| ABC-FAEM active mt=9             |         12.4 |            11.7 |       11.3 |             11.9 |
| Adaptive FF f=0.25               |          2.8 |             1.6 |        1.4 |              2.4 |
| Adaptive FF f=0.25 (v1 roulette) |          2.5 |             1.5 |        1.8 |              2.5 |
| Adaptive FF f=0.15               |         11.7 |            10.7 |       10.1 |             10.7 |
| Adaptive Dirichlet f=0.15        |         12.3 |            13.1 |       10.9 |             12.3 |

ABC original and frozen ABC-FAEM confirm reviewer task 9 exactly: **zero activations in every canonical-configuration cell** — the proposed recovery mechanics never execute. The proportional triggers make the scout phase operational at a controlled, budget-scaled rate instead of the unreachable `max_trials = 0.6 × bees × assets = 300`.

## 2. Effect on the headline metric

Aggregate over all 8 universe-period cells (mean per-seed Sortino, mean Eq. 18 fitness — lower is better, mean activations):

| model                            |   sortino |   fitness |   activations_per_run |
|:---------------------------------|----------:|----------:|----------------------:|
| Adaptive Dirichlet f=0.15        |     2.870 |    -0.003 |                12.137 |
| ABC original                     |     2.145 |    -0.001 |                 0.000 |
| Adaptive FF f=0.25               |     2.026 |    -0.001 |                 2.031 |
| Adaptive FF f=0.25 (v1 roulette) |     1.986 |    -0.001 |                 2.075 |
| ABC-FAEM frozen mt=300           |     1.975 |    -0.001 |                 0.000 |
| ABC-FAEM active mt=9             |     1.964 |    -0.001 |                11.825 |
| Adaptive FF f=0.15               |     1.960 |    -0.001 |                10.775 |

Mean per-seed Sortino by period — fixed fundamentals universe:

| model                            |   covid_2020 |   gfc_2007_2009 |   war_2022 |   2023_stability |
|:---------------------------------|-------------:|----------------:|-----------:|-----------------:|
| ABC original                     |        4.194 |           0.237 |      0.482 |            4.476 |
| ABC-FAEM frozen mt=300           |        3.826 |           0.185 |      0.301 |            4.239 |
| ABC-FAEM active mt=9             |        3.954 |           0.207 |      0.175 |            4.270 |
| Adaptive FF f=0.25               |        3.933 |           0.221 |      0.280 |            4.369 |
| Adaptive FF f=0.25 (v1 roulette) |        3.887 |           0.207 |      0.228 |            4.299 |
| Adaptive FF f=0.15               |        3.965 |           0.192 |      0.199 |            4.270 |
| Adaptive Dirichlet f=0.15        |        5.581 |           0.536 |      1.220 |            4.828 |

Mean per-seed Sortino by period — dynamic z-score universe:

| model                            |   covid_2020 |   gfc_2007_2009 |   war_2022 |   2023_stability |
|:---------------------------------|-------------:|----------------:|-----------:|-----------------:|
| ABC original                     |        3.539 |          -0.289 |      0.593 |            3.927 |
| ABC-FAEM frozen mt=300           |        3.486 |          -0.334 |      0.357 |            3.740 |
| ABC-FAEM active mt=9             |        3.414 |          -0.295 |      0.343 |            3.643 |
| Adaptive FF f=0.25               |        3.495 |          -0.314 |      0.389 |            3.832 |
| Adaptive FF f=0.25 (v1 roulette) |        3.488 |          -0.328 |      0.350 |            3.758 |
| Adaptive FF f=0.15               |        3.333 |          -0.370 |      0.469 |            3.626 |
| Adaptive Dirichlet f=0.15        |        5.205 |           0.140 |      1.250 |            4.202 |

## 3. Paired significance vs. ABC original

Wilcoxon signed-rank over the paired per-seed Sortino samples (20 seeds). Note the baselines keep their own calibrated budgets: ABC original runs 20-30 bees for 70 iterations while every FAEM-derived and adaptive row runs 25 bees for 60 iterations — so ABC original's edge over the frozen-FAEM row partly reflects its larger iteration budget, and the adaptive rows compete with a ~14% smaller budget than the baseline they are tested against:

| universe   | period         | model                            |   p_value | significant   | winner                    |
|:-----------|:---------------|:---------------------------------|----------:|:--------------|:--------------------------|
| fixed      | covid_2020     | ABC-FAEM active mt=9             |    0.0192 | True          | ABC original              |
| fixed      | covid_2020     | ABC-FAEM frozen mt=300           |    0.0017 | True          | ABC original              |
| fixed      | covid_2020     | Adaptive Dirichlet f=0.15        |    0.0000 | True          | Adaptive Dirichlet f=0.15 |
| fixed      | covid_2020     | Adaptive FF f=0.15               |    0.0696 | False         | ABC original              |
| fixed      | covid_2020     | Adaptive FF f=0.25               |    0.0362 | True          | ABC original              |
| fixed      | covid_2020     | Adaptive FF f=0.25 (v1 roulette) |    0.0215 | True          | ABC original              |
| fixed      | gfc_2007_2009  | ABC-FAEM active mt=9             |    0.0897 | False         | ABC original              |
| fixed      | gfc_2007_2009  | ABC-FAEM frozen mt=300           |    0.0192 | True          | ABC original              |
| fixed      | gfc_2007_2009  | Adaptive Dirichlet f=0.15        |    0.0000 | True          | Adaptive Dirichlet f=0.15 |
| fixed      | gfc_2007_2009  | Adaptive FF f=0.15               |    0.0826 | False         | ABC original              |
| fixed      | gfc_2007_2009  | Adaptive FF f=0.25               |    0.3884 | False         | ABC original              |
| fixed      | gfc_2007_2009  | Adaptive FF f=0.25 (v1 roulette) |    0.1140 | False         | ABC original              |
| fixed      | war_2022       | ABC-FAEM active mt=9             |    0.0001 | True          | ABC original              |
| fixed      | war_2022       | ABC-FAEM frozen mt=300           |    0.0002 | True          | ABC original              |
| fixed      | war_2022       | Adaptive Dirichlet f=0.15        |    0.0000 | True          | Adaptive Dirichlet f=0.15 |
| fixed      | war_2022       | Adaptive FF f=0.15               |    0.0000 | True          | ABC original              |
| fixed      | war_2022       | Adaptive FF f=0.25               |    0.0073 | True          | ABC original              |
| fixed      | war_2022       | Adaptive FF f=0.25 (v1 roulette) |    0.0000 | True          | ABC original              |
| fixed      | 2023_stability | ABC-FAEM active mt=9             |    0.0094 | True          | ABC original              |
| fixed      | 2023_stability | ABC-FAEM frozen mt=300           |    0.0004 | True          | ABC original              |
| fixed      | 2023_stability | Adaptive Dirichlet f=0.15        |    0.0010 | True          | Adaptive Dirichlet f=0.15 |
| fixed      | 2023_stability | Adaptive FF f=0.15               |    0.0897 | False         | ABC original              |
| fixed      | 2023_stability | Adaptive FF f=0.25               |    0.4091 | False         | ABC original              |
| fixed      | 2023_stability | Adaptive FF f=0.25 (v1 roulette) |    0.0532 | False         | ABC original              |
| dynamic    | covid_2020     | ABC-FAEM active mt=9             |    0.2774 | False         | ABC original              |
| dynamic    | covid_2020     | ABC-FAEM frozen mt=300           |    0.5459 | False         | ABC original              |
| dynamic    | covid_2020     | Adaptive Dirichlet f=0.15        |    0.0000 | True          | Adaptive Dirichlet f=0.15 |
| dynamic    | covid_2020     | Adaptive FF f=0.15               |    0.0441 | True          | ABC original              |
| dynamic    | covid_2020     | Adaptive FF f=0.25               |    0.8408 | False         | ABC original              |
| dynamic    | covid_2020     | Adaptive FF f=0.25 (v1 roulette) |    0.7841 | False         | ABC original              |
| dynamic    | gfc_2007_2009  | ABC-FAEM active mt=9             |    0.7285 | False         | ABC original              |
| dynamic    | gfc_2007_2009  | ABC-FAEM frozen mt=300           |    0.2943 | False         | ABC original              |
| dynamic    | gfc_2007_2009  | Adaptive Dirichlet f=0.15        |    0.0000 | True          | Adaptive Dirichlet f=0.15 |
| dynamic    | gfc_2007_2009  | Adaptive FF f=0.15               |    0.0637 | False         | ABC original              |
| dynamic    | gfc_2007_2009  | Adaptive FF f=0.25               |    0.4980 | False         | ABC original              |
| dynamic    | gfc_2007_2009  | Adaptive FF f=0.25 (v1 roulette) |    0.3488 | False         | ABC original              |
| dynamic    | war_2022       | ABC-FAEM active mt=9             |    0.0017 | True          | ABC original              |
| dynamic    | war_2022       | ABC-FAEM frozen mt=300           |    0.0000 | True          | ABC original              |
| dynamic    | war_2022       | Adaptive Dirichlet f=0.15        |    0.0000 | True          | Adaptive Dirichlet f=0.15 |
| dynamic    | war_2022       | Adaptive FF f=0.15               |    0.0532 | False         | ABC original              |
| dynamic    | war_2022       | Adaptive FF f=0.25               |    0.0073 | True          | ABC original              |
| dynamic    | war_2022       | Adaptive FF f=0.25 (v1 roulette) |    0.0002 | True          | ABC original              |
| dynamic    | 2023_stability | ABC-FAEM active mt=9             |    0.0107 | True          | ABC original              |
| dynamic    | 2023_stability | ABC-FAEM frozen mt=300           |    0.0002 | True          | ABC original              |
| dynamic    | 2023_stability | Adaptive Dirichlet f=0.15        |    0.0037 | True          | Adaptive Dirichlet f=0.15 |
| dynamic    | 2023_stability | Adaptive FF f=0.15               |    0.0172 | True          | ABC original              |
| dynamic    | 2023_stability | Adaptive FF f=0.25               |    0.2774 | False         | ABC original              |
| dynamic    | 2023_stability | Adaptive FF f=0.25 (v1 roulette) |    0.0192 | True          | ABC original              |

## 4. Interpretation

The strongest adaptive configuration is `Adaptive Dirichlet f=0.15` with mean per-seed Sortino 2.870 across the 8 universe-period cells: +0.726 versus ABC original and +0.906 versus the prior diagnostic's best (`ABC-FAEM active mt=9`). Of its 8 paired Wilcoxon tests against ABC original, 8 are significant at 5% (8 in its favor). Under the uncalibrated default policies this is a directional, not yet conclusive, result — the calibrated study (plan SG-3/SG-4/SG-5) owns the final claim with Holm-corrected significance and deflated-Sharpe selection.

Three structural observations stand alongside the numbers. First, activation without a better move is not enough — that was already the mt=9 lesson in [`faem_activation_calibration.md`](faem_activation_calibration.md), and the corrected-firefly rows repeat it here — but telemetry now separates the two questions cleanly: the tables above report *how often* recovery ran next to *what it earned*. Second, the winning configuration also wins on the Eq. 18 fitness itself, i.e. it finds better optima of the executed objective rather than exploiting the evaluation metric, and it does so despite running ~14% fewer iterations than ABC original's calibrated budget — a simplex-native restart matches the geometry of long-only weight vectors in a way box-space moves do not. Third, the `(v1 roulette)` twin isolates the onlooker-refresh effect from the scout policies, so the two v2 changes are attributable independently.

## 5. Metrics used (and why)

- **Mean per-seed Sortino** — the thesis's headline risk-adjusted metric, computed with the frozen conventions (daily simple returns of the window, annualized); per-seed means support paired tests, unlike best-of-seeds alone.
- **Eq. 18 fitness** — the executed objective (`wᵀμ − 0.7·CVaR₀.₉₉ − η‖w‖₁ − λ_card·card`), the optimizer's own currency; separates search quality from financial outcome.
- **Scout activations per run** — the new telemetry; the quantity reviewer task 9 could only tabulate indirectly is now a first-class run diagnostic.
- **Wilcoxon signed-rank (paired seeds)** — the thesis's own significance methodology (comment 10). Multiple-testing control (Holm) and deflated-Sharpe selection arrive with plan SG-3 and gate any final configuration claim.
- Max drawdown / Jensen α / Omega are deliberately deferred to the calibrated study — the full canonical metric set belongs with the engine-integrated comparison, not this direct-run diagnostic.

## 6. Recommendation for the thesis document

**Yes — add a short activation-analysis subsection, but as an annex extension, not a results-chapter change.** Concretely:

1. Keep the frozen results and their conclusions exactly as they are (the calibration legitimately preferred pure exploitation at these horizons; task 9's defense stands).
2. Extend the existing comment-9 annex with «Análisis de activación del mecanismo scout»: the activation table above (or its `fig6_pfa_activacion` counterpart), one paragraph stating that activation is governed by search stagnation rather than market volatility, and the observation that recovery quality — not just activation frequency — determines value (the mt=9 vs. corrected-move contrast).
3. Cite the v2 line as future work exactly as `pfa_sensitivity.md` §5 already frames it: a joint `max_trials`-and-move calibration with honest multiple-testing control, now implemented in the repository (`ABCAdaptiveScout`, telemetry, and the upcoming calibration framework).

This keeps the document's claims conservative while showing the committee that the observed limitation became a designed, measured, and reproducible research line.
