# Methodology map: thesis → repository

How each stage of the thesis methodology (§Metodología) maps to this
repository. The thesis document itself is frozen under [`thesis/`](../../thesis);
this note is the engineer's index into it.

## Pipeline

```
frozen NASDAQ prices (2000–2025)
        │
        ▼
universe selection ──────────────► hive_abc.data.universe
  ├─ dynamic market z-score          (momentum 12-1, −vol, −MDD; ρ<0.8 greedy)
  └─ fixed fundamentals top-20       (data/frozen/z_score.csv)
        │
        ▼
moments (μ, Σ) on daily log returns ► hive_abc.data.loading
        │
        ▼
objective: Eq. 18 scalarization ────► hive_abc.objectives
  (return − λ·CVaR − η·L1 − λc·card;  see docs/thesis/objective_function.md)
        │
        ▼
optimizers (20 seeds each) ─────────► hive_abc.algorithms + benchmarks
  ABC / ABC-FA / ABC-FAEM / ABC-GSA / PMVG / 1/N
  calibrated per regime ─────────────► backtest/regime_parameters.json
    (multi-regime robust calibration: synthetic scenarios, worst-case
     Sortino, 3-seed-period consensus — see docs/thesis/calibration.md;
     pipeline scripts preserved in legacy/)
        │
        ▼
4 volatility regimes ───────────────► hive_abc.backtest.periods
  covid_2020 · gfc_2007_2009 · war_2022 · 2023_stability
        │
        ▼
metrics (Sortino, MDD, Jensen α vs ^IXIC, Omega, cardinality, HHI)
  + Wilcoxon on per-seed Sortino ───► hive_abc.metrics
        │
        ▼
canonical tables (frozen) ──────────► data/canonical/thesis_results_v1.json
```

## Reference literature

The thesis's reference corpus (30+ papers) is not committed here — the PDFs
remain in the original research workspace (`Hive ABC/docs/Artículos`). Key
citations used by the code are quoted in the algorithm docstrings:

- Karaboga, D. (2005). *An idea based on honey bee swarm for numerical
  optimization*. Technical Report TR-06, Erciyes University.
- Karaboga, D., & Akay, B. (2009). *A comparative study of the artificial
  bee colony algorithm*. Applied Mathematics and Computation, 214(1).
- Yang, X.-S. (2009). *Firefly algorithms for multimodal optimization*.
  SAGA 2009.
- Tuba, M., & Bacanin, N. (2014). *Artificial bee colony algorithm
  hybridized with firefly algorithm for cardinality constrained
  mean-variance portfolio selection*. Applied Mathematics & Information
  Sciences, 8(6). — the original ABC-FA implementation credited by
  `ABCFABacanin`.
- Rashedi, E., Nezamabadi-pour, H., & Saryazdi, S. (2009). *GSA: A
  gravitational search algorithm*. Information Sciences, 179(13).
- Ertenlice, O., & Kalayci, C. B. (2018). *A survey of swarm intelligence
  for portfolio optimization*. Swarm and Evolutionary Computation, 39.
- Markowitz, H. (1952). *Portfolio selection*. The Journal of Finance, 7(1).

## Known deviations from the legacy pipeline

Documented, intentional, and guarded by the reproduction tiers:

1. **Seeding** — pinned seeds + stable per-model offsets replace the
   unseeded `random.randint` draw and the platform-dependent per-class hash
   derivation. Statistical (band) reproduction is the contract.
2. **Benchmark data** — Jensen alpha reads the frozen
   `data/frozen/benchmark_ixic_2007_2024.csv` instead of downloading ^IXIC
   at runtime (values shift ≤ 0.06 from Yahoo revisions).
3. **Convex solver** — Clarabel (with SCS fallback) replaces the deprecated
   ECOS; min-variance solutions agree to ~1e-6.
4. **Metrics** — native quantstats-parity implementations replace the
   quantstats/riskfolio runtime dependencies (locked by `-m parity` tests).
