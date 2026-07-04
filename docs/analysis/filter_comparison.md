# Best model with vs. without the z-score filter (committee task 12)

Generated 2026-07-04 by `scripts/run_filter_comparison.py` (20 pinned seeds per configuration).

Per period, the best fixed-universe model from the canonical tables is re-run on (a) the thesis's fundamentals z-score top-20 and (b) an unfiltered top-20 by data coverage under the same liquidity/history screen — isolating the contribution of the selection stage.

## Summary (for the results-section mention)

| period — model                 |   with z-score filter |   without filter |   filter advantage |
|:-------------------------------|----------------------:|-----------------:|-------------------:|
| 2023_stability — ABC-GSA       |                 4.379 |            5.751 |             -1.372 |
| covid_2020 — ABC (original)    |                 4.822 |            2.475 |              2.347 |
| gfc_2007_2009 — ABC (original) |                 0.439 |           -0.131 |              0.570 |
| war_2022 — ABC-FAEM            |                 0.661 |            1.110 |             -0.449 |

## Full annex detail

| period         | model          | universe            |   sortino |   max_drawdown |   jensen_alpha |   omega |   cardinality |
|:---------------|:---------------|:--------------------|----------:|---------------:|---------------:|--------:|--------------:|
| covid_2020     | ABC (original) | with z-score filter |     4.822 |         -0.190 |          1.134 |   1.640 |             7 |
| covid_2020     | ABC (original) | without filter      |     2.475 |         -0.278 |          0.563 |   1.351 |             8 |
| gfc_2007_2009  | ABC (original) | with z-score filter |     0.439 |         -0.316 |          0.426 |   1.054 |             6 |
| gfc_2007_2009  | ABC (original) | without filter      |    -0.131 |         -0.385 |          0.317 |   0.984 |            10 |
| war_2022       | ABC-FAEM       | with z-score filter |     0.661 |         -0.145 |          0.317 |   1.081 |             9 |
| war_2022       | ABC-FAEM       | without filter      |     1.110 |         -0.139 |          0.340 |   1.128 |             8 |
| 2023_stability | ABC-GSA        | with z-score filter |     4.379 |         -0.166 |          0.262 |   1.565 |            10 |
| 2023_stability | ABC-GSA        | without filter      |     5.751 |         -0.172 |          0.688 |   1.736 |            11 |
