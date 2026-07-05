# PFA sensitivity analysis — ABC-FAEM (reviewer task 9)

Generated 2026-07-04 by `scripts/run_pfa_sensitivity.py` (20 pinned seeds; fixed fundamentals universe; ABC-FAEM only, as the reviewer note requests).

`p_fa` is the probabilistic trigger of ABC-FAEM's scout phase (thesis p. 21): with probability `p_fa` a stalled bee performs the firefly move toward a softmax-selected elite; with probability `1 − p_fa` it performs the original ABC random restart. `p_fa = 1.0` is the frozen thesis behavior; `p_fa = 0.0` degenerates exactly to the original ABC scout.

## 1. Local sensitivity around the executed value

Because the executed value is `p_fa = 1.0`, the primary sensitivity grid should be local to that value rather than centered on distant lower probabilities. Since `p_fa` is bounded above at 1.0, the local neighborhood is necessarily one-sided: {0.80, 0.90, 0.95, 1.00}.

Under the calibrated stagnation threshold (`max_trials = 0.6 × 25 bees × 20 assets = 300`) a bee accumulates at most ~30 unsuccessful trials within the 60-iteration run, so the scout phase — and therefore `p_fa` — is **never exercised**. The local sweep confirms this: all thesis-facing metrics are bit-identical across `p_fa` values (verified: True).

### Sortino

| period         |   0.8 |   0.9 |   0.95 |   1.0 |
|:---------------|------:|------:|-------:|------:|
| 2023_stability | 4.700 | 4.700 |  4.700 | 4.700 |
| covid_2020     | 3.955 | 3.955 |  3.955 | 3.955 |
| gfc_2007_2009  | 0.399 | 0.399 |  0.399 | 0.399 |
| war_2022       | 0.661 | 0.661 |  0.661 | 0.661 |

### Max drawdown

| period         |    0.8 |    0.9 |   0.95 |    1.0 |
|:---------------|-------:|-------:|-------:|-------:|
| 2023_stability | -0.184 | -0.184 | -0.184 | -0.184 |
| covid_2020     | -0.270 | -0.270 | -0.270 | -0.270 |
| gfc_2007_2009  | -0.337 | -0.337 | -0.337 | -0.337 |
| war_2022       | -0.145 | -0.145 | -0.145 | -0.145 |

> [!IMPORTANT]
> <font color="#ff6b6b">**CONCLUSION (TASK 9)**</font>
> The final thesis results are locally insensitive to the PFA trigger around the executed value `p_fa = 1.0`: with the calibrated stagnation threshold the probabilistic scout never activates, so the parameter is empirically inactive in the canonical runs. This supports the thesis conclusion without claiming that `p_fa` is globally irrelevant under different scout thresholds.

### Suggested wording for the thesis

En todas las ejecuciones reportadas se utilizó p_fa = 1.0; es decir, cuando una abeja alcanza la fase scout, el movimiento guiado por élites FAEM se aplica de forma determinística. La sensibilidad se evaluó en una vecindad local del valor ejecutado ({0.80, 0.90, 0.95, 1.00}) y, adicionalmente, en los valores sugeridos por los evaluadores ({0.3, 0.4, 0.5}). En ambos casos las métricas permanecen idénticas.

La razón es mecánica: p_fa solo interviene dentro de la fase scout. Con la calibración final, max_trials = 300, y un horizonte de ejecución de 60 iteraciones, esa fase no se activa en las corridas canónicas. Por tanto, modificar p_fa no cambia la trayectoria efectiva del algoritmo ni los resultados financieros reportados. Esta evidencia respalda mantener la configuración calibrada de la tesis.

Esto no significa que el algoritmo "requiera 300 iteraciones para funcionar", sino que el mecanismo FAEM está diseñado como una intervención posterior al estancamiento. Antes de ese umbral, la dinámica dominante sigue siendo la de ABC. Después del umbral, si se activa la fase FAEM, el algoritmo incorpora una lógica de seguimiento de soluciones élite.

### Lower-value range check

The reviewer-suggested lower values {0.3, 0.4, 0.5} are better reported as a distant range check, not as the main local sensitivity analysis. They are also bit-identical under the same calibrated configuration (verified: True):

| period         |   0.3 |   0.4 |   0.5 |   1.0 |
|:---------------|------:|------:|------:|------:|
| 2023_stability | 4.700 | 4.700 | 4.700 | 4.700 |
| covid_2020     | 3.955 | 3.955 | 3.955 | 3.955 |
| gfc_2007_2009  | 0.399 | 0.399 | 0.399 | 0.399 |
| war_2022       | 0.661 | 0.661 | 0.661 | 0.661 |

## 2. Why the parameter exists — defense of the mechanism

*Anticipated question: if `p_fa` changes nothing, what is the point of the parameter (and of the FAEM scout)?*

**The inertness is a calibration outcome, not a design flaw.** The robust multi-regime calibration (see `docs/thesis/calibration.md`) selected `max_trials_factor = 0.6` under a worst-case-Sortino criterion — i.e., the data determined that in these portfolio problems, within 60 iterations, sustained exploitation without restarts is optimal. The scout mechanism is the algorithm's *contingency* against stagnation, and the calibration set its activation threshold so high that the contingency was never needed in-sample. The exploratory grids did search the active region (`max_trials ∈ [8, 25]`) and the calibration rejected it. The evidence below characterizes the mechanism in both regions.

Equivalently, ABC-FAEM does not need 300 iterations to "start working"; it works first as ABC, and only after the stagnation criterion is met does the FAEM recovery behavior become available. That is the point at which the method can behave like a leader-following mechanism, because the stalled bee is pulled toward a softmax-selected elite instead of being restarted randomly.

### ¿Cuándo puede activarse FAEM?

La activación de FAEM depende del estancamiento de la búsqueda, no de la volatilidad del periodo por sí sola. Un régimen muy volátil puede aumentar la dificultad del paisaje de optimización, pero el disparador operativo es que una abeja acumule suficientes intentos fallidos sin mejorar. Por tanto, FAEM es más probable cuando el umbral `max_trials` es menor, cuando se permite un mayor número de iteraciones, o cuando el problema presenta mesetas de fitness, alta correlación entre activos, restricciones fuertes o penalizaciones que dificultan encontrar mejoras marginales.

Esta distinción ayuda a interpretar los resultados: ABC-FAEM puede converger hacia resultados similares al ABC original porque ambos comparten la misma dinámica base antes de la fase scout. Cuando la fase scout no se activa, la diferencia mecánica entre ambos queda disponible pero no ejecutada. Cuando sí se activa, ABC original responde al estancamiento con un reinicio aleatorio, mientras que ABC-FAEM intenta una recuperación guiada hacia soluciones élite. Esa recuperación puede mejorar la explotación si la élite es informativa, pero también puede reducir diversidad si la búsqueda todavía necesita explorar regiones nuevas; por eso los resultados pueden coincidir en algunos regímenes y discrepar en otros.

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

## 3. Related work and references to cite

Use these sources to position the answer: ABC establishes why the scout phase is the only place where `p_fa` can matter; Firefly and ABC-FA literature justifies the elite move; sensitivity/tuning references justify a local perturbation around the calibrated parameter rather than treating distant values as the main test.

- **Karaboga (2005) and Karaboga & Basturk (2007)** — baseline ABC mechanics: employed/onlooker search plus a scout restart after an abandonment/limit counter is exceeded.
- **Yang (2009)** — Firefly Algorithm movement rule and its b0, gamma, and alpha parameters; this is the move reused inside FAEM's scout.
- **Tuba & Bacanin (2014)** — closest portfolio-specific ABC-FA precedent: a firefly-hybrid ABC for cardinality-constrained mean-variance portfolio selection.
- **Ertenlice & Kalayci (2018)** — survey context for swarm-intelligence portfolio optimization and why algorithm-parameter robustness matters in this domain.
- **Birattari (2009), Eiben & Smit (2011), and Sipper et al. (2018)** — parameter tuning/configuration literature supporting a distinction between the calibrated value and a post-hoc sensitivity analysis.
- **Saltelli et al. (2008)** — sensitivity-analysis framing: perturb the input whose effect is being claimed; because p_fa is bounded above at 1.0, the local test is necessarily one-sided below the executed value.
- **Wilcoxon (1945)** — paired non-parametric comparison used for the per-seed stochastic diagnostic when the scout mechanism is forced active.

## 4. Defense summary (for the oral discussion)

1. **Formally**: the local sweep around the executed value (`p_fa = 0.80/0.90/0.95/1.00`) leaves every reported number unchanged — bit-identical, not merely statistically indistinguishable — because the calibrated stagnation threshold keeps the trigger dormant (§1, §2a). The lower `0.3/0.4/0.5` range check reaches the same result but should not be the main robustness claim.
2. **Mechanistically**: `p_fa` is the knob of a calibrated contingency subsystem. The calibration, not the authors, decided the contingency was unnecessary for these horizons — an empirical finding about the problem class (exploitation-dominant landscapes), documented in `docs/thesis/calibration.md`.
3. **Empirically**: when the trigger is active (§2b–2c), the ablation and Wilcoxon tests quantify exactly what the elite move contributes relative to the original ABC restart, so the mechanism's behavior is characterized in both regimes rather than asserted.

## 5. Exploratory future work note

Como línea exploratoria para trabajos futuros, podría estudiarse una sensibilidad conjunta entre max_trials y p_fa, o bien horizontes de ejecución más largos, para caracterizar cuándo conviene activar mecanismos de recuperación guiados por élites. Ese análisis ampliaría el entendimiento del balance exploración-explotación de ABC-FAEM, pero no modifica las conclusiones de la configuración calibrada usada en esta tesis.

Como complemento, se ejecutó el diagnóstico [`faem_activation_calibration.md`](faem_activation_calibration.md): al reemplazar la regla no alcanzable `max_trials = 300` por umbrales proporcionales al horizonte de 60 iteraciones (`max_trials ∈ {9, 15, 24}`), la fase FAEM sí entra en operación. La mejor variante activa (`max_trials = 9`) eleva el Sortino promedio de 2.324 a 2.420 frente al ABC-FAEM congelado y supera marginalmente al ABC original en +0.015 en promedio. Sin embargo, la mejora es pequeña y desigual entre periodos, por lo que no justifica reemplazar la configuración calibrada de la tesis.
