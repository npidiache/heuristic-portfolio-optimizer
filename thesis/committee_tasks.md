# Reviewer comments — all 15 comments, answers included

Exported from `ABC Comments.xlsx` (2026-06-27), validated against this
repository on 2026-07-04. **This document is self-contained**: every
comment's answer (or source material) is summarized inline, so it can be
reviewed top-to-bottom without navigating the repository. Links point to
the full detail for anyone who wants to go deeper.

## Status at a glance

| # | Assignee | Comment (short) | Status |
| --- | --- | --- | --- |
| 1 | Luisa | Include an abstract | Docx only — draft available below |
| 2 | Luisa | Standardize model names, fix typos | Supported — naming table below |
| 3 | Luisa | Define `b0`, `max_trials`, etc. somewhere | **Answered below** |
| 4 | Norbey | Is Eq. 13 the same as Eq. 18? | **Answered below** |
| 5 | Norbey | λ and η never defined | **Answered below** |
| 6 | Luisa | Detail the z-score filters exactly | **Answered below** |
| 7 | Luisa | CVaR vs Expected Shortfall inconsistency | **Answered below** |
| 8 | Luisa | Eq. 20 looks truncated | Docx only (note says it may be fine) |
| 9 | Norbey | PFA value + sensitivity analysis | **Answered below** |
| 10 | Luisa | Include Wilcoxon p-values in results | **Answered below** |
| 11 | Luisa | Number of assets per portfolio | **Answered below** |
| 12 | Norbey | Best model with vs. without the filter | **Answered below** |
| 13 | Luisa | Wrong PMVG-vs-ABC claim on p. 31 | **Corrected wording below** |
| 14 | Norbey | Include execution times | **Answered below** |
| 15 | Luisa | Add figures to the document | Supported — sources listed below |

Everything below only needs transcription into the Word document (handled
outside this repository). The frozen thesis results were never touched:
checksum and regression tests stayed green through every analysis.

---

## Detailed answers

### 1 — Abstract (docx only)

The README [Overview](../README.md#overview) paragraph is a ready first
draft in English (four ABC-family metaheuristics, NASDAQ-100, four
volatility regimes, benchmarks, frozen results); it needs translation to
Spanish and a results sentence (e.g., the family-dominance finding from
comment 13's corrected wording).

### 2 — Naming consistency

Standardize on these names everywhere in the document (full mapping in
[`docs/thesis/naming.md`](../docs/thesis/naming.md)):

**ABC** (original, Karaboga 2005) · **ABC-FA** (Bacanin) · **ABC-FAEM**
(proposed — never "ABC-FA-EM") · **ABC-GSA** (proposed) · **PMVG** ·
**1/N**.

### 3 — Where `b0` and `max_trials` are defined (parameter provenance)

The missing section exists now
([`docs/thesis/calibration.md`](../docs/thesis/calibration.md)). Essentials:

| Parameter | Meaning |
| --- | --- |
| `numb_bees` | Colony size (evened up); one employed + one onlooker move per bee per iteration |
| `max_itrs` | Iterations (employed → onlooker → scout cycles) |
| `max_trials` | Stagnation threshold: a bee scouts when its unsuccessful-trial counter exceeds it; derived as `0.6 · numb_bees · n_assets` (= 300 at 25 bees × 20 assets) |
| `b0` / `gamma` / `alpha` | Firefly attraction at distance zero / attraction decay `exp(−γr²)` / randomization amplitude |
| `k_top`, `softmax_tau` | FAEM elite pool size (3) and softmax temperature (1.0) |
| `p_fa` | PFA trigger — probability the FAEM scout uses the elite move vs. a random restart (1.0 in all thesis runs) |
| `G`, `epsilon` | ABC-GSA gravitational constant and numeric guard |

The values were **not hand-picked**: they come from the multi-regime robust
calibration (per-regime grids → 5 synthetic stress scenarios each →
worst-case-Sortino scoring → consensus across 3 historical seed periods).
Calibrated values per regime (CRISIS / STABLE_GROWTH / UNCERTAINTY): e.g.,
ABC-FAEM uses b0 = 1.4/0.95/1.25, γ = 1.4/1.4/1.2, α = 0.05, 25 bees, 60
iterations; full table in the calibration doc.

### 4 — Eq. 13 vs. Eq. 18

**They are related but intentionally not identical, and they should not
be.** Eq. 13 states the investor *preference* (Sortino, Omega, CVaR, HHI);
Eq. 18 is its *executable scalarization* inside the metaheuristic:

`U(w) = wᵀμ − λ·CVaR_α(Rw) − η·‖w‖₁ − λ_card·card(w)`, minimized as `−U(w)`.

Sortino/Omega/HHI re-enter as *evaluation metrics* on the optimized
portfolios (the results tables). Suggested thesis fix: state this
relationship explicitly and cross-reference the two equations. Full
term-by-term mapping:
[`docs/thesis/objective_function.md`](../docs/thesis/objective_function.md).

### 5 — The λ and η values

As executed in every canonical run (frozen in code as
`hive_abc.objectives.UtilityParams`):

| Symbol | Meaning | Executed value |
| --- | --- | --- |
| λ | CVaR aversion | **0.7** |
| α | CVaR tail parameter (riskfolio convention) | **0.99** |
| η | L1 regularization | **5·10⁻⁴** (constant ≡ η for long-only normalized weights) |
| λ_card | Cardinality penalty weight | **0.008 · n/20**, target 10 holdings, threshold 1% |

### 6 — The z-score filters, exactly

**Dynamic (market) filter**, recomputed ex-ante per backtest window:
252-calendar-day window ending the day before the backtest start (≥ 180
observations per ticker, relaxed once to 120); factors on daily log
returns — momentum 12-1 (cumulative return excluding the last 21 rows),
volatility (std), max drawdown; aggregation
`0.5·z(momentum) + 0.3·z(−vol) + 0.2·z(−MDD)` (population z-scores);
selection: rank descending, greedy diversification rejecting |ρ| ≥ 0.8
against already-selected names, top-up ignoring correlation if fewer than
20 survive; final n = 20.

**Fixed (fundamentals) filter**: top-20 by `Z_Score` in the frozen
fundamentals file, excluding the index row.

(Also in [`docs/thesis/methodology.md`](../docs/thesis/methodology.md).)

### 7 — CVaR vs. Expected Shortfall

They are **the same measure**: Conditional Value-at-Risk ≡ Expected
Shortfall ≡ Average VaR (Rockafellar & Uryasev, 2000). Suggested fix:
state the equivalence once and use one term (the code standardizes on
CVaR) consistently thereafter.

### 9 — PFA sensitivity (the sensitive one)

**Direct answer to the comment**: the value used in every thesis run is
`p_fa = 1.0` (the FA elite move fires unconditionally). The main sensitivity
check should therefore be local to the executed value, not centered on
distant lower probabilities. Because `p_fa` is bounded above at 1.0, the
local grid is one-sided: {0.80, 0.90, 0.95, 1.00}. Every reported metric is
**bit-identical** across that grid — e.g., Sortino by period:

| period | Sortino (any p_fa) |
| --- | ---: |
| covid_2020 | 3.955 |
| gfc_2007_2009 | 0.399 |
| war_2022 | 0.661 |
| 2023_stability | 4.700 |

The reviewer-suggested lower values {0.3, 0.4, 0.5} are still useful as a
distant range check, but they should not be presented as the main robustness
claim. They also leave every reported metric bit-identical for the same
mechanical reason.

**Why (and the defense against "then what is the parameter for?")**: the
calibrated stagnation threshold (`max_trials = 300`) is never reached
within the 60-iteration budget — mean scout activations per run:

| max_trials → | 10 | 15 | 25 | 50–300 |
| --- | ---: | ---: | ---: | ---: |
| activations/run (avg across periods) | ~8.3 | ~2.1 | ~0.2 | 0 |

So the PFA governs a *calibrated contingency* that the calibration itself
(worst-case-Sortino criterion) deemed unnecessary for these horizons. When
the mechanism IS forced active (diagnostic with `max_trials = 15`), the
elite move shows directionally better mean fitness in 3 of 4 periods and
equal-or-better convergence endpoints in 3 of 4 — but not statistically
significant at 20 seeds. **Defensible claim**: "a mild, never-harmful
guided-recovery mechanism whose calibrated configuration never needs it;
therefore the final results are locally insensitive to PFA around the
executed value, while active-mechanism diagnostics show how it behaves when
the scout phase is forced on."

References to cite in the written answer: Karaboga (2005) and Karaboga &
Basturk (2007) for ABC/scout mechanics; Yang (2009) for Firefly movement;
Tuba & Bacanin (2014) for ABC-FA in cardinality-constrained portfolio
selection; Ertenlice & Kalayci (2018) for swarm-intelligence portfolio
optimization context; Birattari (2009), Eiben & Smit (2011), Sipper et al.
(2018), and Saltelli et al. (2008) for parameter tuning/sensitivity logic;
Wilcoxon (1945) for the paired seed-level diagnostic.

Suggested thesis wording:

> En todas las ejecuciones reportadas se utilizó p_fa = 1.0; es decir,
> cuando una abeja alcanza la fase scout, el movimiento guiado por élites
> FAEM se aplica de forma determinística. La sensibilidad se evaluó en una
> vecindad local del valor ejecutado ({0.80, 0.90, 0.95, 1.00}) y,
> adicionalmente en valores extremos ({0.3, 0.4, 0.5}).
> En ambos casos las métricas permanecen idénticas.
>
> La razón es mecánica: p_fa solo interviene dentro de la fase scout. Con la
> calibración final, max_trials = 300, y con un total de 60 iteraciones,
> esa fase no se activa en las corridas canónicas. Por tanto, modificar p_fa
> no cambia la trayectoria efectiva del algoritmo ni los resultados
> reportados. Esta evidencia respalda mantener la configuración
> calibrada de la tesis.

Optional future-work note:

> Como línea exploratoria para trabajos futuros, podría estudiarse una
> sensibilidad conjunta entre max_trials y p_fa, o bien niveles de
> iteración más altos, para determinar cuándo conviene activar mecanismos
> de recuperación guiados por élites. Ese análisis ampliaría el entendimiento
> del balance exploración-explotación de ABC-FAEM, pero no modifica las
> conclusiones de la configuración calibrada usada en esta tesis.

Full evidence + oral-defense summary:
[`docs/analysis/pfa_sensitivity.md`](../docs/analysis/pfa_sensitivity.md).

### 10 — Wilcoxon p-values

Computed for all 8 configurations (2 universes × 4 periods), pairwise over
the 20 per-seed Sortino samples: **75% of all pairs are significant at
5%**, and the significant pairs are exactly the ones our discourse needs
(ABC-family vs. benchmarks); the ABC-FAEM vs. ABC-GSA pairs are generally
not significant, consistent with the seed-noise interpretation. Full
tables ready to transcribe:
[`docs/analysis/reproduction_report.md`](../docs/analysis/reproduction_report.md)
§ "Wilcoxon significance".

### 11 — Number of assets per portfolio

Holdings with weight > 0.5% per best portfolio (fixed universe shown;
full table incl. dynamic in the reproduction report):

| model | covid | gfc | war | 2023 |
| --- | ---: | ---: | ---: | ---: |
| ABC (original) | 7 | 6 | 10 | 9 |
| ABC-FA (Bacanin) | 17 | 15 | 19 | 18 |
| ABC-FAEM | 11 | 5 | 9 | 10 |
| ABC-GSA | 9 | 4 | 9 | 10 |
| PMVG | 6 | 5 | 7 | 14 |
| 1/N | 20 | 16 | 20 | 20 |

Reading: the ABC family (except Bacanin) concentrates in 4–11 names —
the cardinality penalty at work — vs. 1/N's 20.

### 12 — Best model with vs. without the filter

| period — best model | with filter | without | advantage |
| --- | ---: | ---: | ---: |
| covid_2020 — ABC (original) | 4.822 | 2.475 | **+2.347** |
| gfc_2007_2009 — ABC (original) | 0.439 | −0.131 | **+0.570** |
| war_2022 — ABC-FAEM | 0.661 | 1.110 | −0.449 |
| 2023_stability — ABC-GSA | 4.379 | 5.751 | −1.372 |

(Sortino; "without" = top-20 by data coverage under the same
liquidity/history screen.) **Suggested results-section mention**: the
z-score filter behaves as a crisis-defense mechanism — it adds large
value precisely in the systemic-crisis regimes and cedes ground in calm
ones. Full annex tables:
[`docs/analysis/filter_comparison.md`](../docs/analysis/filter_comparison.md).

### 13 — The erroneous p. 31 claim

Confirmed against the canonical data: PMVG's COVID Sortino (2.67) beats
ABC-FA's (2.10), so "inferior to the ABC-based algorithms" is false as
written. **Suggested corrected wording**: *"…es inferior al del ABC
original y al de las dos variantes propuestas (ABC-FAEM y ABC-GSA),
aunque supera al ABC-FA."* (The repo's formal dominance claim already
excludes ABC-FA for exactly this reason.)

### 14 — Execution times

Mean seconds per optimizer run (one seed, averaged over the 8
configurations): ABC (original) **0.076 s**, ABC-FA (Bacanin) **0.112 s**,
ABC-FAEM **0.072 s**, ABC-GSA **0.070 s**; PMVG solves once in ~0.004 s
and 1/N is instantaneous. A full 20-seed × 6-model × 8-configuration
reproduction completes in ≈ 1 minute. Per-configuration breakdown in the
reproduction report.

### 15 — Figures for the document

**Six print-ready branded figures** (300 dpi PNG, Spanish labels, Obsidian
Aqua palette) are committed under [`docs/figures/`](../docs/figures) —
generated from the frozen data by `scripts/generate_thesis_figures.py`, so
they cannot contradict the tables:

| Figure | Content | Thesis placement |
| --- | --- | --- |
| `fig1_sortino_por_regimen` | Sortino by algorithm × regime (canonical, fixed universe) | Resultados — opening of the comparative analysis |
| `fig2_riqueza_acumulada_por_regimen` | Cumulative wealth of the best portfolios, 4 regimes | Resultados — per-regime subsections |
| `fig3_convergencia_abc` | Mean convergence of the 4 ABC variants (COVID) | Metodología — after the algorithm descriptions |
| `fig4_riesgo_retorno` | Sortino vs. max drawdown scatter, all regimes | Resultados — cross-regime discussion |
| `fig5_filtro_comparacion` | Best model with vs. without the z-score filter | Anexo (comentario 12) |
| `fig6_pfa_activacion` | Scout activation frequency vs. `max_trials` | Anexo (comentario 9) |

The Mermaid methodology flowchart (README) and the interactive visualizer
(`thesis/ABC_Thesis_Presentation.html`) remain additional sources.

---

*Assignee note: comments 1–3, 6–8, 10–11, 13, 15 are Luisa's in the
Excel; where their substance is parameter/results material, this repo
provides it ready-made (3, 6, 10, 11, 13).*
