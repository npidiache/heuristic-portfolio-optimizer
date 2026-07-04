# The objective function: Eq. 13 vs. Eq. 18 (committee tasks 4 and 5)

This note resolves two committee comments on the thesis document:

- **Task 4** — *"Is the multi-objective utility function (Eq. 13) the same
  as the fitness function (Eq. 18)? Should they be equal?"*
- **Task 5** — *"Eq. 13 integrates Sortino, Omega, CVaR and HHI, but the
  penalty weights λ and η are never defined."*

## 1. The two equations are related but not identical (task 4)

**Eq. 13 (documented utility)** describes the *conceptual* multi-objective
preference the thesis optimizes for: reward per unit of downside risk
(Sortino), gain/loss asymmetry (Omega), tail-risk control (CVaR), and a
concentration penalty (HHI).

**Eq. 18 (executed fitness)** is the *computable scalarization* of that
preference that the optimizers actually minimize. As executed in the frozen
backtest harness (`legacy/test_calibrated_crisis_performance_v2.py`,
function `utility_objective_with_cardinality`, wired in
`run_backtest_for_period`):

```
U(w) = wᵀμ − λ·CVaR_α(R·w) − η·‖w‖₁ − λ_card·card(w)
fitness(w) = −U(w)          (minimization), with
fitness(w) = 10¹⁰           when Σwᵢ ≤ 10⁻⁹ (empty-portfolio sentinel)
```

where `w` is normalized inside the function, `μ` are mean daily log returns,
`R` the daily log-return matrix, and `card(w)` the quadratic excess-holdings
penalty.

The mapping between the two:

| Eq. 13 term | Eq. 18 realization | Why |
| --- | --- | --- |
| Sortino / Omega reward | `wᵀμ` (expected return) with downside handled by the CVaR term | Sortino and Omega are ratio statistics of the realized path — expensive and noisy inside a 3,000-evaluation search loop; the executed form uses the classical return-minus-risk scalarization |
| CVaR penalty (weight λ) | `λ · CVaR_α(R·w)`, λ = 0.7, α = 0.99, historical estimator | Direct |
| HHI concentration penalty | `λ_card · card(w)` quadratic penalty above a target holding count | The executed harness controls concentration through cardinality, not HHI; HHI is reported as a *metric* in the results tables |
| Diversification (weight η) | `η · ‖w‖₁`, η = 5·10⁻⁴ | For a normalized long-only portfolio `‖w‖₁ = 1`, so this term is a constant offset in the frozen runs; it becomes active only if short positions are ever allowed |

**Answer to the committee:** they are not, and need not be, the same
function. Eq. 13 states the investor preference; Eq. 18 is its executable
scalarization inside the metaheuristic, and Sortino/Omega/HHI re-enter as
*evaluation metrics* on the optimized portfolios (the tables of §Resultados).
The thesis text should state this explicitly and cross-reference the two
equations. What must hold — and does — is that both express the same
preference direction: more return, less tail risk, less concentration.

## 2. The executed parameter values (task 5)

Frozen in code as `hive_abc.objectives.UtilityParams` (defaults) and
verified by unit tests:

| Symbol | Meaning | Executed value |
| --- | --- | --- |
| λ (`lambda_cvar`) | CVaR aversion | **0.7** |
| α (`cvar_alpha`) | CVaR tail parameter (riskfolio `CVaR_Hist` convention) | **0.99** |
| η (`eta_l1`) | L1 regularization weight | **5·10⁻⁴** |
| λ_card (`lambda_cardinality`) | Cardinality penalty weight | **0.008 · (n/20)** (scales with universe size; 0.008 at the thesis's n = 20) |
| — (`target_cardinality`) | Holdings tolerated without penalty | **10** |
| — (`cardinality_threshold`) | Weight that counts as a holding | **1%** |

Notes for the thesis text:

- The value α = 0.99 follows the **riskfolio-lib parameterization** of
  `CVaR_Hist`, where `alpha` is the coverage of the sorted-return average —
  not the usual "5% tail" significance convention. The native
  reimplementation (`hive_abc.objectives.cvar_historical`) replicates that
  estimator exactly to keep results unchanged.
- Because `‖w‖₁ = 1` after normalization in a long-only portfolio, η acts as
  a constant in every frozen run; it is documented for completeness and for
  future long/short extensions.

## 3. Where this lives in code

- `src/hive_abc/objectives/utility.py` — `UtilityParams` (the table above)
  and `PortfolioUtilityObjective` (Eq. 18 exactly as executed).
- `src/hive_abc/objectives/risk.py` — the riskfolio-parity CVaR estimator.
- `src/hive_abc/objectives/penalties.py` — the single cardinality-penalty
  definition used by the final runs (the legacy harness contained an unused
  second variant, which has been dropped).
- `tests/objectives/` — hand-computed unit tests locking each term.
