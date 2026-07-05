# ABC-FAEM active-scout calibration diagnostic

Generated 2026-07-04 by `scripts/run_faem_activation_calibration.py` (20 pinned seeds per configuration).

This diagnostic keeps the thesis results frozen and changes only ABC-FAEM's scout activation threshold. Instead of the calibrated `max_trials = 0.6 × bees × assets = 300`, it tests thresholds tied to the 60-iteration horizon: 15%, 25%, and 40%, i.e. `max_trials ∈ {9, 15, 24}`. The FAEM trigger remains `p_fa = 1.0`.

> [!IMPORTANT]
> These runs are exploratory diagnostics, not replacement thesis results. They test whether the FAEM mechanism can become active under a minimal, interpretable recalibration.

## Aggregate results

| model                  |   sortino |   max_drawdown |   jensen_alpha |   omega |
|:-----------------------|----------:|---------------:|---------------:|--------:|
| FAEM active mt=9       |     2.420 |         -0.236 |          0.537 |   1.314 |
| ABC original           |     2.405 |         -0.254 |          0.540 |   1.314 |
| FAEM active mt=24      |     2.383 |         -0.247 |          0.546 |   1.311 |
| FAEM active mt=15      |     2.352 |         -0.250 |          0.548 |   1.304 |
| ABC-FAEM frozen mt=300 |     2.324 |         -0.253 |          0.520 |   1.301 |
| PMVG                   |     1.168 |         -0.218 |          0.227 |   1.160 |
| 1/N                    |     0.920 |         -0.289 |          0.201 |   1.127 |

## Mean Sortino by universe

| model                  |   fixed |   dynamic |
|:-----------------------|--------:|----------:|
| ABC original           |   2.662 |     2.149 |
| FAEM active mt=9       |   2.625 |     2.215 |
| FAEM active mt=24      |   2.593 |     2.173 |
| FAEM active mt=15      |   2.586 |     2.118 |
| ABC-FAEM frozen mt=300 |   2.583 |     2.065 |
| PMVG                   |   1.320 |     1.017 |
| 1/N                    |   1.101 |     0.739 |

## Active FAEM Sortino deltas

| universe   | period         | model             |   sortino |   delta_vs_frozen_faem |   delta_vs_abc_original |
|:-----------|:---------------|:------------------|----------:|-----------------------:|------------------------:|
| fixed      | covid_2020     | FAEM active mt=9  |     4.328 |                  0.038 |                  -0.320 |
| fixed      | covid_2020     | FAEM active mt=15 |     4.644 |                  0.354 |                  -0.004 |
| fixed      | covid_2020     | FAEM active mt=24 |     4.651 |                  0.361 |                   0.003 |
| fixed      | gfc_2007_2009  | FAEM active mt=9  |     0.364 |                  0.022 |                   0.003 |
| fixed      | gfc_2007_2009  | FAEM active mt=15 |     0.322 |                 -0.020 |                  -0.039 |
| fixed      | gfc_2007_2009  | FAEM active mt=24 |     0.399 |                  0.057 |                   0.038 |
| fixed      | war_2022       | FAEM active mt=9  |     0.799 |                 -0.012 |                   0.055 |
| fixed      | war_2022       | FAEM active mt=15 |     0.645 |                 -0.166 |                  -0.099 |
| fixed      | war_2022       | FAEM active mt=24 |     0.622 |                 -0.189 |                  -0.122 |
| fixed      | 2023_stability | FAEM active mt=9  |     5.011 |                  0.123 |                   0.115 |
| fixed      | 2023_stability | FAEM active mt=15 |     4.731 |                 -0.157 |                  -0.165 |
| fixed      | 2023_stability | FAEM active mt=24 |     4.700 |                 -0.188 |                  -0.196 |
| dynamic    | covid_2020     | FAEM active mt=9  |     4.109 |                  0.322 |                   0.172 |
| dynamic    | covid_2020     | FAEM active mt=15 |     3.808 |                  0.021 |                  -0.129 |
| dynamic    | covid_2020     | FAEM active mt=24 |     4.059 |                  0.272 |                   0.122 |
| dynamic    | gfc_2007_2009  | FAEM active mt=9  |    -0.210 |                  0.005 |                  -0.106 |
| dynamic    | gfc_2007_2009  | FAEM active mt=15 |    -0.061 |                  0.154 |                   0.043 |
| dynamic    | gfc_2007_2009  | FAEM active mt=24 |    -0.107 |                  0.108 |                  -0.003 |
| dynamic    | war_2022       | FAEM active mt=9  |     0.685 |                  0.141 |                  -0.073 |
| dynamic    | war_2022       | FAEM active mt=15 |     0.671 |                  0.127 |                  -0.087 |
| dynamic    | war_2022       | FAEM active mt=24 |     0.781 |                  0.237 |                   0.023 |
| dynamic    | 2023_stability | FAEM active mt=9  |     4.277 |                  0.134 |                   0.274 |
| dynamic    | 2023_stability | FAEM active mt=15 |     4.055 |                 -0.088 |                   0.052 |
| dynamic    | 2023_stability | FAEM active mt=24 |     3.961 |                 -0.182 |                  -0.042 |

## Interpretation

The best active-scout threshold is `FAEM active mt=9` with mean Sortino 2.420, a +0.096 delta versus frozen ABC-FAEM and a +0.015 delta versus ABC original. This confirms the FAEM scout can be made operational with a proportional `max_trials` rule, but it does not provide a strong enough aggregate improvement over ABC original to replace the frozen thesis setting.

The most defensible reading is that proportional `max_trials` makes the FAEM phase reachable and therefore makes the recovery mechanism visible. However, the active variants are still conditional: they can improve some regimes and weaken others because they replace ABC's random restart with elite-guided recovery. The evidence supports a future calibration line, not an ex-post replacement of the frozen thesis configuration.
