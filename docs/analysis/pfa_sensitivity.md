# PFA sensitivity analysis — ABC-FAEM (committee task 9)

Generated 2026-07-04 by `scripts/run_pfa_sensitivity.py` (20 pinned seeds; fixed fundamentals universe; ABC-FAEM only, as the committee note requests).

`p_fa` is the probabilistic trigger of ABC-FAEM's scout phase (thesis p. 21): with probability `p_fa` a stalled bee performs the firefly move toward a softmax-selected elite; otherwise it restarts at random. The frozen thesis runs used the mechanism unconditionally (`p_fa = 1.0`).

## 1. Calibrated configuration (thesis parameters)

Under the calibrated stagnation threshold (`max_trials = 0.6 x 25 bees x 20 assets = 300`) a bee accumulates at most ~30 unsuccessful trials within the 60-iteration budget, so the scout phase — and therefore `p_fa` — is **never exercised**. The sweep confirms this: all metrics are bit-identical across `p_fa` values (verified: True).

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

## 2. Stressed configuration (annex diagnostic, max_trials = 15)

To characterize the mechanism itself, the annex repeats the sweep with an artificially low stagnation threshold so scouts fire regularly. **These numbers are NOT comparable with the thesis tables** — they only show the direction and size of the PFA effect when the trigger is active.

### Sortino

| period         |   0.3 |   0.4 |   0.5 |   1.0 |
|:---------------|------:|------:|------:|------:|
| 2023_stability | 4.909 | 4.909 | 4.909 | 4.731 |
| covid_2020     | 4.924 | 4.550 | 4.550 | 4.644 |
| gfc_2007_2009  | 0.358 | 0.358 | 0.358 | 0.322 |
| war_2022       | 0.645 | 0.645 | 0.645 | 0.645 |

### Mean best fitness (lower is better)

| period         |       0.3 |       0.4 |       0.5 |       1.0 |
|:---------------|----------:|----------:|----------:|----------:|
| 2023_stability | -0.002379 | -0.002389 | -0.002392 | -0.002418 |
| covid_2020     | -0.005402 | -0.005383 | -0.005405 | -0.005421 |
| gfc_2007_2009  |  0.001542 |  0.001542 |  0.001542 |  0.001543 |
| war_2022       |  0.000984 |  0.000945 |  0.000898 |  0.000910 |

### Fitness dispersion across seeds

| period         |      0.3 |      0.4 |      0.5 |      1.0 |
|:---------------|---------:|---------:|---------:|---------:|
| 2023_stability | 0.001900 | 0.001901 | 0.001908 | 0.001904 |
| covid_2020     | 0.000497 | 0.000519 | 0.000421 | 0.000482 |
| gfc_2007_2009  | 0.000169 | 0.000169 | 0.000169 | 0.000162 |
| war_2022       | 0.000289 | 0.000238 | 0.000233 | 0.000260 |
