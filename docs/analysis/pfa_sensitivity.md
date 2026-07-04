# PFA sensitivity analysis — ABC-FAEM (committee task 9)

Generated 2026-07-04 by `scripts/run_pfa_sensitivity.py` (20 pinned seeds; fixed fundamentals universe; ABC-FAEM only, as the committee note requests).

`p_fa` is the probabilistic trigger of ABC-FAEM's scout phase (thesis p. 21): with probability `p_fa` a stalled bee performs the firefly move toward a softmax-selected elite; with probability `1 − p_fa` it performs the original ABC random restart. `p_fa = 1.0` is the frozen thesis behavior; `p_fa = 0.0` degenerates exactly to the original ABC scout.

## 1. The committee's sweep, calibrated configuration

Under the calibrated stagnation threshold (`max_trials = 0.6 × 25 bees × 20 assets = 300`) a bee accumulates at most ~30 unsuccessful trials within the 60-iteration budget, so the scout phase — and therefore `p_fa` — is **never exercised**. The sweep confirms this: all metrics are bit-identical across `p_fa` values (verified: True).

### Sortino

| period         |   0.3 |   0.4 |   0.5 |   1.0 |
|:---------------|------:|------:|------:|------:|
| 2023_stability | 4.700 | 4.700 | 4.700 | 4.700 |
| covid_2020     | 3.955 | 3.955 | 3.955 | 3.955 |
| gfc_2007_2009  | 0.399 | 0.399 | 0.399 | 0.399 |
| war_2022       | 0.661 | 0.661 | 0.661 | 0.661 |

### Max drawdown

| period         |    0.3 |    0.4 |    0.5 |    1.0 |
|:---------------|-------:|-------:|-------:|-------:|
| 2023_stability | -0.184 | -0.184 | -0.184 | -0.184 |
| covid_2020     | -0.270 | -0.270 | -0.270 | -0.270 |
| gfc_2007_2009  | -0.337 | -0.337 | -0.337 | -0.337 |
| war_2022       | -0.145 | -0.145 | -0.145 | -0.145 |

> [!IMPORTANT]
> <font color="#ff6b6b">**CONCLUSION (TASK 9)**</font>
> The final thesis results are insensitive to the PFA trigger by construction: with the calibrated stagnation threshold the probabilistic scout never activates, so any value in {0.3, 0.4, 0.5, 1.0} leaves every reported number unchanged. This formally satisfies the committee's requirement that the sensitivity analysis must not affect the final results.

## 2. Why the parameter exists — defense of the mechanism

*Anticipated question: if `p_fa` changes nothing, what is the point of the parameter (and of the FAEM scout)?*

**The inertness is a calibration outcome, not a design flaw.** The robust multi-regime calibration (see `docs/thesis/calibration.md`) selected `max_trials_factor = 0.6` under a worst-case-Sortino criterion — i.e., the data determined that in these portfolio problems, within a 60-iteration budget, sustained exploitation without restarts is optimal. The scout mechanism is the algorithm's *contingency* against stagnation, and the calibration set its activation threshold so high that the contingency was never needed in-sample. The exploratory grids did search the active region (`max_trials ∈ [8, 25]`) and the calibration rejected it. The evidence below characterizes the mechanism in both regions.

### 2a. When does the scout wake up? (activation frequency)

Mean scout activations per run (calibrated FAEM parameters, only `max_trials` varies; the calibrated value is 300):

| period         |   10 |   15 |   25 |   50 |   100 |   200 |   300 |
|:---------------|-----:|-----:|-----:|-----:|------:|------:|------:|
| covid_2020     |  9.4 |  2.7 |  0.2 |    0 |     0 |     0 |     0 |
| gfc_2007_2009  |  8.3 |  1.6 |  0.1 |    0 |     0 |     0 |     0 |
| war_2022       |  8.1 |  1.8 |  0.1 |    0 |     0 |     0 |     0 |
| 2023_stability |  7.5 |  2.2 |  0.2 |    0 |     0 |     0 |     0 |

The calibrated threshold sits far inside the never-fires region; the mechanism becomes operative roughly below `max_trials ≈ 50`.

### 2b. Ablation while active: FAEM elite move vs. ABC restart

With `max_trials = 15` the scout fires regularly, and `p_fa` spans a clean ablation: `0.0` = pure original-ABC random restart, `1.0` = pure FAEM elite move. **These runs are diagnostics, not thesis results.**

#### Optimization quality (mean best fitness per seed; lower is better)

| period         |       0.0 |       0.3 |       0.5 |       1.0 |
|:---------------|----------:|----------:|----------:|----------:|
| 2023_stability | -0.002338 | -0.002379 | -0.002392 | -0.002418 |
| covid_2020     | -0.005360 | -0.005402 | -0.005405 | -0.005421 |
| gfc_2007_2009  |  0.001541 |  0.001542 |  0.001542 |  0.001543 |
| war_2022       |  0.000958 |  0.000984 |  0.000898 |  0.000910 |

#### Financial outcome (mean per-seed Sortino)

| period         |   0.0 |   0.3 |   0.5 |   1.0 |
|:---------------|------:|------:|------:|------:|
| 2023_stability | 4.326 | 4.340 | 4.354 | 4.403 |
| covid_2020     | 3.936 | 3.994 | 3.933 | 3.920 |
| gfc_2007_2009  | 0.196 | 0.194 | 0.194 | 0.184 |
| war_2022       | 0.278 | 0.271 | 0.324 | 0.311 |

#### Wilcoxon signed-rank: p_fa = 1.0 vs p_fa = 0.0 (20 paired seeds)

| period         | metric   |   p_value | significant_5pct   | higher_mean            |
|:---------------|:---------|----------:|:-------------------|:-----------------------|
| covid_2020     | fitness  |    0.8983 | False              | p_fa=1.0 (FAEM)        |
| covid_2020     | sortino  |    0.7012 | False              | p_fa=0.0 (ABC restart) |
| gfc_2007_2009  | fitness  |    0.9165 | False              | p_fa=0.0 (ABC restart) |
| gfc_2007_2009  | sortino  |    0.4631 | False              | p_fa=0.0 (ABC restart) |
| war_2022       | fitness  |    0.5277 | False              | p_fa=1.0 (FAEM)        |
| war_2022       | sortino  |    0.286  | False              | p_fa=1.0 (FAEM)        |
| 2023_stability | fitness  |    0.5067 | False              | p_fa=1.0 (FAEM)        |
| 2023_stability | sortino  |    0.1159 | False              | p_fa=1.0 (FAEM)        |

### 2c. Convergence profiles under stress

Mean best fitness across seeds at iteration checkpoints (lower is better):

| period         | policy   |   iter 5 |   iter 10 |   iter 20 |   iter 40 |   iter 60 |
|:---------------|:---------|---------:|----------:|----------:|----------:|----------:|
| covid_2020     | p_fa=0   | 0.165249 |  0.113003 |  0.044713 | -0.000288 | -0.005403 |
| covid_2020     | p_fa=1   | 0.165249 |  0.113003 |  0.043141 |  0.000215 | -0.005467 |
| gfc_2007_2009  | p_fa=0   | 0.019079 |  0.010759 |  0.002547 |  0.001900 |  0.001538 |
| gfc_2007_2009  | p_fa=1   | 0.019079 |  0.010759 |  0.002547 |  0.001902 |  0.001559 |
| war_2022       | p_fa=0   | 0.166980 |  0.122502 |  0.063575 |  0.017409 |  0.002529 |
| war_2022       | p_fa=1   | 0.166980 |  0.122502 |  0.063575 |  0.016152 |  0.001019 |
| 2023_stability | p_fa=0   | 0.159236 |  0.123407 |  0.062741 |  0.008018 | -0.002162 |
| 2023_stability | p_fa=1   | 0.159236 |  0.123407 |  0.062741 |  0.007581 | -0.002268 |

**Reading**: both policies are *identical* until the first scout activations (first divergence at iter 20) — mechanistic confirmation that the trigger only matters after stagnation accumulates — and the FAEM elite move finishes with equal-or-better mean best fitness in 3 of 4 periods at iter 60.

## 3. Defense summary (for the oral discussion)

1. **Formally**: the requested sweep (0.3/0.4/0.5) leaves every reported number unchanged — bit-identical, not merely statistically indistinguishable — because the calibrated stagnation threshold keeps the trigger dormant (§1, §2a).
2. **Mechanistically**: `p_fa` is the knob of a calibrated contingency subsystem. The calibration, not the authors, decided the contingency was unnecessary for these horizons and budgets — an empirical finding about the problem class (exploitation-dominant landscapes), documented in `docs/thesis/calibration.md`.
3. **Empirically**: when the trigger is active (§2b–2c), the ablation and Wilcoxon tests quantify exactly what the elite move contributes relative to the original ABC restart, so the mechanism's behavior is characterized in both regimes rather than asserted.
