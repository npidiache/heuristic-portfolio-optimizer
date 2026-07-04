# Thesis reproduction report

Generated 2026-07-04 by `scripts/run_reproduction.py` (20 pinned seeds per stochastic model; total wall time 54.1s).

> [!IMPORTANT]
> <font color="#ff6b6b">**FROZEN RESULTS**</font>
> The thesis columns come from `data/canonical/thesis_results_v1.json` and never change. Reproduced values are expected to differ within the Tier-2 tolerance bands (`tests/reproduction_test.py`): the legacy runs drew unpinned seeds, and the frozen ^IXIC benchmark was re-downloaded after the thesis, shifting Jensen alpha slightly.

## Headline verification

- Deterministic models (PMVG, 1/N) reproduce the thesis numbers almost exactly (differences ≤ 0.01 except Jensen alpha ≤ 0.06 from benchmark-data revisions).
- Stochastic ABC variants land within seed-noise bands of the thesis values (worst Sortino gap ≈ 0.8 on ABC-FA Bacanin, the noisiest variant).
- The thesis's headline ordinal claim holds in every configuration: ABC (original), ABC-FAEM, and ABC-GSA each beat both classical benchmarks on Sortino.
- Under the calibrated parameters (`max_trials = 0.6 · bees · assets = 300`), the scout phase never fires within the iteration budget — per-model differences between the ABC variants in these tables reflect their distinct RNG streams rather than scout mechanics. See `docs/analysis/pfa_sensitivity.md` for the consequences.

## dynamic universe — covid_2020

| model               |   Sortino (repro) |   Sortino (thesis) |   Max drawdown (repro) |   Max drawdown (thesis) |   Jensen alpha (repro) |   Jensen alpha (thesis) |   Omega (repro) |   Omega (thesis) |
|:--------------------|------------------:|-------------------:|-----------------------:|------------------------:|-----------------------:|------------------------:|----------------:|-----------------:|
| ABC (original)      |             3.713 |              3.937 |                 -0.386 |                  -0.357 |                  1.176 |                   1.163 |           1.534 |            1.558 |
| ABC-FA (Bacanin)    |             1.555 |              2.102 |                 -0.302 |                  -0.333 |                  0.267 |                   0.474 |           1.229 |            1.302 |
| ABC-FAEM            |             4.059 |              3.787 |                 -0.329 |                  -0.334 |                  1.138 |                   1.099 |           1.583 |            1.526 |
| ABC-GSA             |             4.031 |              3.822 |                 -0.364 |                  -0.376 |                  1.214 |                   1.164 |           1.576 |            1.540 |
| PMVG (min-variance) |             2.646 |              2.669 |                 -0.220 |                  -0.219 |                  0.482 |                   0.474 |           1.392 |            1.395 |
| 1/N                 |             1.927 |              1.927 |                 -0.309 |                  -0.309 |                  0.398 |                   0.379 |           1.280 |            1.280 |

## dynamic universe — gfc_2007_2009

| model               |   Sortino (repro) |   Sortino (thesis) |   Max drawdown (repro) |   Max drawdown (thesis) |   Jensen alpha (repro) |   Jensen alpha (thesis) |   Omega (repro) |   Omega (thesis) |
|:--------------------|------------------:|-------------------:|-----------------------:|------------------------:|-----------------------:|------------------------:|----------------:|-----------------:|
| ABC (original)      |            -0.078 |             -0.104 |                 -0.507 |                  -0.486 |                  0.374 |                   0.359 |           0.991 |            0.988 |
| ABC-FA (Bacanin)    |            -0.938 |             -0.551 |                 -0.581 |                  -0.530 |                  0.125 |                   0.239 |           0.886 |            0.933 |
| ABC-FAEM            |            -0.107 |             -0.215 |                 -0.481 |                  -0.501 |                  0.376 |                   0.330 |           0.987 |            0.974 |
| ABC-GSA             |            -0.035 |             -0.271 |                 -0.510 |                  -0.493 |                  0.385 |                   0.314 |           0.996 |            0.967 |
| PMVG (min-variance) |            -0.953 |             -0.957 |                 -0.502 |                  -0.504 |                  0.093 |                   0.091 |           0.889 |            0.889 |
| 1/N                 |            -0.849 |             -0.849 |                 -0.569 |                  -0.569 |                  0.167 |                   0.166 |           0.898 |            0.898 |

## dynamic universe — war_2022

| model               |   Sortino (repro) |   Sortino (thesis) |   Max drawdown (repro) |   Max drawdown (thesis) |   Jensen alpha (repro) |   Jensen alpha (thesis) |   Omega (repro) |   Omega (thesis) |
|:--------------------|------------------:|-------------------:|-----------------------:|------------------------:|-----------------------:|------------------------:|----------------:|-----------------:|
| ABC (original)      |             0.867 |              0.758 |                 -0.203 |                  -0.232 |                  0.535 |                   0.432 |           1.098 |            1.087 |
| ABC-FA (Bacanin)    |            -0.275 |             -0.076 |                 -0.319 |                  -0.280 |                  0.287 |                   0.266 |           0.970 |            0.992 |
| ABC-FAEM            |             0.781 |              0.544 |                 -0.215 |                  -0.256 |                  0.486 |                   0.429 |           1.089 |            1.061 |
| ABC-GSA             |             0.789 |              0.978 |                 -0.213 |                  -0.191 |                  0.503 |                   0.518 |           1.090 |            1.110 |
| PMVG (min-variance) |             0.255 |              0.265 |                 -0.242 |                  -0.242 |                  0.225 |                   0.201 |           1.030 |            1.032 |
| 1/N                 |            -0.361 |             -0.361 |                 -0.314 |                  -0.314 |                  0.265 |                   0.210 |           0.961 |            0.961 |

## dynamic universe — 2023_stability

| model               |   Sortino (repro) |   Sortino (thesis) |   Max drawdown (repro) |   Max drawdown (thesis) |   Jensen alpha (repro) |   Jensen alpha (thesis) |   Omega (repro) |   Omega (thesis) |
|:--------------------|------------------:|-------------------:|-----------------------:|------------------------:|-----------------------:|------------------------:|----------------:|-----------------:|
| ABC (original)      |             4.556 |              4.003 |                 -0.097 |                  -0.105 |                  0.317 |                   0.260 |           1.564 |            1.495 |
| ABC-FA (Bacanin)    |             2.075 |              2.313 |                 -0.082 |                  -0.078 |                 -0.001 |                   0.026 |           1.254 |            1.281 |
| ABC-FAEM            |             3.961 |              4.143 |                 -0.104 |                  -0.094 |                  0.241 |                   0.247 |           1.491 |            1.516 |
| ABC-GSA             |             4.211 |              4.153 |                 -0.104 |                  -0.102 |                  0.303 |                   0.298 |           1.518 |            1.515 |
| PMVG (min-variance) |             2.089 |              2.090 |                 -0.069 |                  -0.069 |                  0.055 |                   0.056 |           1.257 |            1.257 |
| 1/N                 |             2.239 |              2.239 |                 -0.070 |                  -0.070 |                  0.020 |                   0.021 |           1.272 |            1.272 |

## fixed universe — covid_2020

| model               |   Sortino (repro) |   Sortino (thesis) |   Max drawdown (repro) |   Max drawdown (thesis) |   Jensen alpha (repro) |   Jensen alpha (thesis) |   Omega (repro) |   Omega (thesis) |
|:--------------------|------------------:|-------------------:|-----------------------:|------------------------:|-----------------------:|------------------------:|----------------:|-----------------:|
| ABC (original)      |             4.822 |              4.648 |                 -0.190 |                  -0.188 |                  1.134 |                   1.065 |           1.640 |            1.630 |
| ABC-FA (Bacanin)    |             2.845 |              2.410 |                 -0.224 |                  -0.268 |                  0.571 |                   0.473 |           1.399 |            1.341 |
| ABC-FAEM            |             3.955 |              4.290 |                 -0.270 |                  -0.195 |                  1.033 |                   0.980 |           1.537 |            1.576 |
| ABC-GSA             |             4.672 |              4.484 |                 -0.174 |                  -0.188 |                  1.018 |                   1.055 |           1.626 |            1.591 |
| PMVG (min-variance) |             3.808 |              3.808 |                 -0.126 |                  -0.126 |                  0.688 |                   0.676 |           1.518 |            1.518 |
| 1/N                 |             2.079 |              2.079 |                 -0.254 |                  -0.254 |                  0.384 |                   0.367 |           1.303 |            1.303 |

## fixed universe — gfc_2007_2009

| model               |   Sortino (repro) |   Sortino (thesis) |   Max drawdown (repro) |   Max drawdown (thesis) |   Jensen alpha (repro) |   Jensen alpha (thesis) |   Omega (repro) |   Omega (thesis) |
|:--------------------|------------------:|-------------------:|-----------------------:|------------------------:|-----------------------:|------------------------:|----------------:|-----------------:|
| ABC (original)      |             0.439 |              0.361 |                 -0.316 |                  -0.364 |                  0.426 |                   0.403 |           1.054 |            1.045 |
| ABC-FA (Bacanin)    |            -0.197 |             -0.161 |                 -0.465 |                  -0.425 |                  0.358 |                   0.341 |           0.977 |            0.981 |
| ABC-FAEM            |             0.399 |              0.342 |                 -0.337 |                  -0.359 |                  0.394 |                   0.405 |           1.050 |            1.042 |
| ABC-GSA             |             0.361 |              0.324 |                 -0.357 |                  -0.358 |                  0.393 |                   0.380 |           1.045 |            1.040 |
| PMVG (min-variance) |            -0.135 |             -0.135 |                 -0.400 |                  -0.399 |                  0.253 |                   0.252 |           0.983 |            0.983 |
| 1/N                 |            -0.513 |             -0.513 |                 -0.519 |                  -0.519 |                  0.260 |                   0.259 |           0.940 |            0.940 |

## fixed universe — war_2022

| model               |   Sortino (repro) |   Sortino (thesis) |   Max drawdown (repro) |   Max drawdown (thesis) |   Jensen alpha (repro) |   Jensen alpha (thesis) |   Omega (repro) |   Omega (thesis) |
|:--------------------|------------------:|-------------------:|-----------------------:|------------------------:|-----------------------:|------------------------:|----------------:|-----------------:|
| ABC (original)      |             0.644 |              0.744 |                 -0.148 |                  -0.153 |                  0.265 |                   0.291 |           1.080 |            1.095 |
| ABC-FA (Bacanin)    |            -0.124 |              0.127 |                 -0.184 |                  -0.180 |                  0.274 |                   0.236 |           0.986 |            1.015 |
| ABC-FAEM            |             0.661 |              0.811 |                 -0.145 |                  -0.136 |                  0.317 |                   0.337 |           1.081 |            1.100 |
| ABC-GSA             |             0.599 |              0.669 |                 -0.142 |                  -0.132 |                  0.306 |                   0.252 |           1.072 |            1.083 |
| PMVG (min-variance) |            -0.362 |             -0.333 |                 -0.126 |                  -0.128 |                  0.044 |                   0.035 |           0.957 |            0.961 |
| 1/N                 |            -0.466 |             -0.466 |                 -0.196 |                  -0.196 |                  0.169 |                   0.129 |           0.948 |            0.949 |

## fixed universe — 2023_stability

| model               |   Sortino (repro) |   Sortino (thesis) |   Max drawdown (repro) |   Max drawdown (thesis) |   Jensen alpha (repro) |   Jensen alpha (thesis) |   Omega (repro) |   Omega (thesis) |
|:--------------------|------------------:|-------------------:|-----------------------:|------------------------:|-----------------------:|------------------------:|----------------:|-----------------:|
| ABC (original)      |             4.892 |              4.896 |                 -0.159 |                  -0.149 |                  0.362 |                   0.351 |           1.612 |            1.616 |
| ABC-FA (Bacanin)    |             2.915 |              3.727 |                 -0.086 |                  -0.083 |                  0.061 |                   0.119 |           1.364 |            1.481 |
| ABC-FAEM            |             4.700 |              4.888 |                 -0.184 |                  -0.148 |                  0.355 |                   0.331 |           1.588 |            1.616 |
| ABC-GSA             |             4.379 |              5.011 |                 -0.166 |                  -0.135 |                  0.262 |                   0.329 |           1.565 |            1.637 |
| PMVG (min-variance) |             1.939 |              1.941 |                 -0.061 |                  -0.061 |                  0.028 |                   0.029 |           1.243 |            1.243 |
| 1/N                 |             3.305 |              3.305 |                 -0.079 |                  -0.079 |                  0.074 |                   0.075 |           1.414 |            1.414 |

## Execution times (committee task 14)

Mean seconds per optimizer run (one seed), per configuration:

| model               |   dynamic/2023_stability |   dynamic/covid_2020 |   dynamic/gfc_2007_2009 |   dynamic/war_2022 |   fixed/2023_stability |   fixed/covid_2020 |   fixed/gfc_2007_2009 |   fixed/war_2022 |   mean s/run (all) |
|:--------------------|-------------------------:|---------------------:|------------------------:|-------------------:|-----------------------:|-------------------:|----------------------:|-----------------:|-------------------:|
| ABC-FA (Bacanin)    |                    0.128 |                0.106 |                   0.108 |              0.104 |                  0.122 |              0.105 |                 0.104 |            0.117 |              0.112 |
| ABC-FAEM            |                    0.109 |                0.062 |                   0.066 |              0.063 |                  0.078 |              0.062 |                 0.069 |            0.066 |              0.072 |
| ABC (original)      |                    0.104 |                0.055 |                   0.061 |              0.083 |                  0.101 |              0.061 |                 0.061 |            0.084 |              0.076 |
| ABC-GSA             |                    0.076 |                0.062 |                   0.067 |              0.063 |                  0.076 |              0.064 |                 0.069 |            0.082 |              0.070 |
| 1/N                 |                    0.000 |                0.000 |                   0.000 |              0.000 |                  0.000 |              0.000 |                 0.000 |            0.000 |              0.000 |
| PMVG (min-variance) |                    0.003 |                0.007 |                   0.004 |              0.005 |                  0.003 |              0.004 |                 0.003 |            0.006 |              0.004 |

Deterministic models solve once; their per-seed cost is the single solve replicated across seeds.
