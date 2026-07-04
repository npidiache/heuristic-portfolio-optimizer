# Parameter provenance: the regime calibration (reviewer task 3)

The reviewers noted (task 3) that the comparative table on p. 15 mentions
parameters such as `b0` and `max_trials` that *"are never defined or
explained in the later formulation"*. This note is the missing section: it
defines every algorithm parameter and documents where the executed values
come from — the multi-regime robust calibration pipeline
(`legacy/robust_calibration_pipeline.py`, methodology in
`legacy/robust_calibration_pipeline.md`, exploratory grids in
`legacy/refined_grid_search.py` and `legacy/run_calibration_multi_regime.py`).

## 1. Parameter definitions

| Parameter (thesis / legacy) | `hive_abc` name | Meaning | Applies to |
| --- | --- | --- | --- |
| `numb_bees` | `colony_size` | Colony size; rounded up to an even count. Employed and onlooker phases each perform one move per bee per iteration | all ABC variants |
| `max_itrs` | `max_iterations` | Employed → onlooker → scout cycles per run | all ABC variants |
| `max_trials` | `max_trials` | Stagnation threshold: a bee whose trial counter *strictly exceeds* it becomes a scout. Derived in the backtests as `int(max_trials_factor · numb_bees · n_assets)` | all ABC variants |
| `max_trials_factor` | `max_trials_factor` | Factor of that derivation; calibrated at **0.6** (→ `max_trials = 300` at 25 bees × 20 assets) | all ABC variants |
| `b0` (β₀) | `b0` | Firefly attractiveness at distance zero — the pull strength toward the reference solution | ABC-FA, ABC-FAEM |
| `gamma` (γ) | `gamma` | Firefly light-absorption coefficient — how fast attraction decays with distance (`exp(−γr²)`) | ABC-FA, ABC-FAEM |
| `alpha` (α) | `alpha` | Randomization amplitude of the move (`α·(u−0.5)` per dimension) | ABC-FA, ABC-FAEM, ABC-GSA |
| `k_top` | `k_top` | Elite pool size for the FAEM scout's leader sampling (fixed at 3 in the thesis runs) | ABC-FAEM |
| `softmax_tau` (τ) | `softmax_tau` | Softmax temperature over elite fitness (fixed at 1.0) | ABC-FAEM |
| `p_fa` (PFA) | `p_fa` | Probability that the FA elite move fires instead of a random restart (task 9; 1.0 in the frozen runs) | ABC-FAEM |
| `G` | `g_constant` | Gravitational constant scaling pairwise attraction between bees | ABC-GSA |
| `epsilon` (ε) | `epsilon` | Numeric guard for near-zero distances in the force computation | ABC-GSA |

## 2. How the values were chosen — the calibration pipeline

The calibrated values were **not** hand-picked; they are the output of the
robust multi-regime calibration framework (four methodological pillars, full
description in [`legacy/robust_calibration_pipeline.md`](../../legacy/robust_calibration_pipeline.md)):

1. **Calibration per theoretical regime type** — separate grids are solved
   for `CRISIS`, `STABLE_GROWTH`, and `UNCERTAINTY`, producing an adaptive
   "playbook" rather than one-size-fits-all parameters.
2. **Synthetic regime generation (antifragility)** — each candidate
   parameter set is evaluated on 5 synthetic scenarios per regime type
   (volatility multipliers up to ×5–6, correlation shocks up to 0.9,
   bearish/bullish trend injections), generated from historical base
   returns, so the algorithms never memorize a specific historical crisis.
3. **Cross-validation over seed periods (anti-bias)** — the synthetic
   calibration is repeated from three non-overlapping historical bases
   (`PRE_GFC`, `POST_GFC`, `PRE_COVID`), with survivorship-aware dynamic
   data loading.
4. **Consensus aggregation** — the winner per regime is the parameter set
   that wins most often across the three seed periods; each evaluation
   scores a candidate by its **worst** synthetic scenario (conservative
   min-max criterion on Sortino).

The output is `final_adaptive_parameters.json`, committed verbatim at
[`src/hive_abc/backtest/regime_parameters.json`](../../src/hive_abc/backtest/regime_parameters.json)
(and as provenance in [`legacy/`](../../legacy)) and loaded by
`hive_abc.backtest.load_regime_parameters` — the exact values behind every
canonical run.

## 3. The frozen calibrated values

| Regime | Model | Calibrated parameters |
| --- | --- | --- |
| CRISIS | ABC (original) | bees 20, iters 70, trials factor 0.6 |
| CRISIS | ABC-FA (Bacanin) | bees 25, iters 60, b0 1.0, γ 1.6, α 0.025 |
| CRISIS | ABC-FAEM | bees 25, iters 60, b0 1.4, γ 1.4, α 0.05, factor 0.6 |
| CRISIS | ABC-GSA | bees 25, iters 60, G 0.3, ε 1e−10, α 0.05, factor 0.6 |
| STABLE_GROWTH | ABC (original) | bees 25, iters 70, factor 0.6 |
| STABLE_GROWTH | ABC-FA (Bacanin) | bees 25, iters 60, b0 1.0, γ 1.4, α 0.025 |
| STABLE_GROWTH | ABC-FAEM | bees 25, iters 60, b0 0.95, γ 1.4, α 0.05, factor 0.6 |
| STABLE_GROWTH | ABC-GSA | bees 25, iters 60, G 0.3, ε 1e−12, α 0.05, factor 0.6 |
| UNCERTAINTY | ABC (original) | bees 30, iters 70, factor 0.6 |
| UNCERTAINTY | ABC-FA (Bacanin) | bees 25, iters 60, b0 1.2, γ 1.2, α 0.03 |
| UNCERTAINTY | ABC-FAEM | bees 25, iters 60, b0 1.25, γ 1.2, α 0.05, factor 0.6 |
| UNCERTAINTY | ABC-GSA | bees 25, iters 60, G 0.7, ε 1e−10, α 0.05, factor 0.6 |

Period → regime mapping: `covid_2020`, `gfc_2007_2009` → CRISIS;
`war_2022` → UNCERTAINTY; `2023_stability` → STABLE_GROWTH
(`hive_abc.backtest.PERIODS`).

## 4. A consequence worth stating in the thesis

The calibration selected `max_trials_factor = 0.6`, which at the thesis's
scale (25 bees × 20 assets) yields `max_trials = 300` — while a bee
accumulates at most ~30 unsuccessful trials within the 60-iteration budget.
The consequence, measured in this repo: **the scout phase never activates in
the canonical runs**, so the calibrated configurations effectively favor
pure employed/onlooker exploitation, and the performance differences between
ABC, ABC-FAEM, and ABC-GSA in the result tables stem from their distinct
random streams rather than their scout mechanics. This is also why the PFA
trigger is provably inert in the final results (reviewer task 9 —
[`docs/analysis/pfa_sensitivity.md`](../analysis/pfa_sensitivity.md), whose
stressed annex shows the mechanisms at work when `max_trials` is small, as
in the exploratory grids that searched `max_trials ∈ [8, 25]`).
