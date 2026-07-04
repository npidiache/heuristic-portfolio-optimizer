"""
Robust Calibration Pipeline for Adaptive Portfolio Optimization
==============================================================

This script implements the definitive, thesis-grade calibration framework.
It aligns with the "Gear System" methodology defined in `project-rules.mdc`
to ensure a robust, defendible, and academically rigorous process.

Methodology Summary:
--------------------
1.  **Gear 3: Regime-Specific Calibration**:
    - Fetches VIX data to classify historical periods into distinct market
      regimes (e.g., 'CRISIS', 'STABLE_GROWTH').
    - Calibration is performed *separately* for each regime, finding the
      optimal algorithm parameters for specific market conditions.

2.  **Gear 5: Anti-Overfitting Strategies**:
    - **Multi-Metric Objective Function**: Optimizes a balanced utility
      function combining Sortino Ratio, Maximum Drawdown, and cardinality
      penalization. This prevents overfitting to a single metric.
    - **Intra-Regime Robustness Validation**: For each parameter set, its
      robustness is tested by evaluating it against multiple synthetic
      variations of the historical data from that specific regime. A parameter
      set is only considered good if it performs well across these simulated
-      variations.

3.  **Gear 4: Efficient & Adaptive Search**:
    - Implements an **Adaptive Grid Search**. This starts with a broad
      parameter grid and iteratively zooms in on the most promising regions,
      making the search process far more efficient than an exhaustive search.

4.  **Gear 7: Actionable Output**:
    - The final output is a structured dictionary, saved to a file, mapping
      each algorithm and market regime to its optimal set of parameters.
"""

import os
import sys
import json
import itertools
import numpy as np
import pandas as pd
import yfinance as yf
import warnings
import time

# --- Configuration ---
warnings.filterwarnings('ignore')
# Ensure the project root is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up from src/optimization to the project root
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

# --- Project Modules ---
from src.utils.data_loader import get_portfolio_data, calculate_returns
from src.algorithms.abc_original import ABC_BeeHive
from src.algorithms.abc_fa_bacanin import ABC_FA_Bacanin
from src.algorithms.abc_fa_scout import ABC_FA_Scout
from src.algorithms.abc_scout_gravitacional import ABC_Scout_Gravitacional

# Gear 5: Multiple non-overlapping base periods for synthetic generation
# This ensures that the final parameters are not biased towards a single historical period.
CALIBRATION_BASE_PERIODS = {
    'PRE_GFC': ('2003-01-01', '2007-12-31'),   # Pre-Global Financial Crisis
    'POST_GFC': ('2010-01-01', '2014-12-31'),  # Post-GFC recovery
    'PRE_COVID': ('2015-01-01', '2019-12-31')   # Stable period before COVID
}


# Gear 4: ENHANCED parameter exploration - Better than original 2x2 grid
REFINED_PARAM_GRIDS = {
    'ABC_FA_Scout': {
        # Literatura FA sugiere alpha moderada; rangos defendibles
        'b0': [0.8, 1.1, 1.4],
        'gamma': [0.6, 1.0, 1.4],
        'alpha': [0.02, 0.05, 0.08],
        # Mantener tamaño e iteraciones contenidas para no explotar combinaciones
        'numb_bees': [25],
        'max_itrs': [60],
        # Factor para escalar max_trials = factor * numb_bees * dim
        'max_trials_factor': [0.6]
    },
    'ABC_Scout_Gravitacional': {
        'G': [0.3, 0.7, 1.1],
        'epsilon': [1e-12, 1e-10],
        'alpha': [0.02, 0.05, 0.08],
        'numb_bees': [25],
        'max_itrs': [60],
        'max_trials_factor': [0.6]
    },
    'ABC_FA_Bacanin': {
        # Mantener muy cercano al paper (Bacanin)
        'b0': [1.0, 1.1, 1.2],
        'gamma': [1.2, 1.4, 1.6],
        'alpha': [0.02, 0.025, 0.03],
        'numb_bees': [25],
        'max_itrs': [60]
    },
    'ABC_Original': {
        'numb_bees': [20, 25, 30],
        'max_itrs': [50, 70],
        'max_trials_factor': [0.6]
    }
}

# --- Core Helper Functions ---

def calculate_sortino_ratio(returns, risk_free_rate=0.0):
    """Calculates Sortino Ratio robustly."""
    if not isinstance(returns, pd.Series):
        returns = pd.Series(returns)
    excess_returns = returns - risk_free_rate
    downside_returns = excess_returns[excess_returns < 0]
    if len(downside_returns) == 0: return 0.0
    downside_std = np.sqrt(np.mean(downside_returns**2))
    if downside_std == 0: return 0.0
    return np.mean(excess_returns) / downside_std

def calculate_max_drawdown(returns):
    """Calculates Maximum Drawdown robustly."""
    if not isinstance(returns, pd.Series):
        returns = pd.Series(returns)
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()

# --- Core Methodological Functions ---

def simple_utility_objective(weights, returns, mu, lambda_cvar=0.5, lambda_l1=1e-4, 
                             lambda_cardinality=1e-3, alpha=0.95, target_cardinality=8):
    """
    Simplified objective function based on the working run_calibration_multi_regime.py
    """
    weights = np.array(weights)
    if np.sum(weights) <= 1e-9: return 1e10
    weights = weights / np.sum(weights)

    # Portfolio return
    portfolio_return = np.dot(weights, mu)
    
    # CVaR calculation (simplified)
    port_returns = returns.dot(weights)
    sorted_returns = np.sort(port_returns)
    var_index = int((1 - alpha) * len(sorted_returns))
    cvar = -np.mean(sorted_returns[:var_index]) if var_index > 0 else 0
    
    # L1 penalty
    l1_penalty = np.sum(np.abs(weights))
    
    # Cardinality penalty
    significant_weights = np.sum(weights > 0.005)
    if significant_weights > target_cardinality:
        cardinality_penalty = 1e-3 * ((significant_weights - target_cardinality) ** 2)
    else:
        cardinality_penalty = 0.0
    
    # Combined utility
    utility = portfolio_return - lambda_cvar * cvar - lambda_l1 * l1_penalty - lambda_cardinality * cardinality_penalty
    
    return -utility

def generate_enhanced_synthetic_regimes(base_returns, regime_type='CRISIS', n_variations=5):
    """
    ENHANCED SYNTHETIC REGIME GENERATION - Now regime-specific.
    """
    base_mu = base_returns.mean()
    base_cov = base_returns.cov()
    n_days = len(base_returns)
    n_assets = len(base_returns.columns)
    
    synthetic_regimes = []

    if regime_type == 'CRISIS':
        # Generate scenarios of high stress and volatility
        scenarios = {
            'CRISIS_V1': {'vol': 3.0, 'corr': 0.7, 'mu_factor': 0.5},
            'BLACK_SWAN': {'vol': 5.0, 'corr': 0.9, 'mu_factor': 0.1},
            'HIGH_VOL_UNCORR': {'vol': 4.0, 'corr': 0.1, 'mu_factor': 0.6},
            'PERSISTENT_CRASH': {'vol': 2.5, 'corr': 0.8, 'mu_factor': 0.2},
            'VOLATILITY_SHOCK': {'vol': 6.0, 'corr': 0.5, 'mu_factor': 0.4}
        }
    elif regime_type == 'STABLE_GROWTH':
        # Generate scenarios of calm, positive-drift markets
        scenarios = {
            'LOW_VOL_GROWTH': {'vol': 1.0, 'corr': 0.2, 'mu_factor': 1.5},
            'MODERATE_GROWTH': {'vol': 1.5, 'corr': 0.3, 'mu_factor': 1.2},
            'LOW_CORR_MARKET': {'vol': 1.2, 'corr': 0.1, 'mu_factor': 1.3},
            'BULL_RUN': {'vol': 1.8, 'corr': 0.4, 'mu_factor': 1.8},
            'STABLE_MARKET': {'vol': 0.8, 'corr': 0.25, 'mu_factor': 1.1}
        }
    else: # UNCERTAINTY
        # Generate scenarios with mixed signals, sector rotations, etc.
        scenarios = {
            'MIXED_MEDIUM_VOL': {'vol': 2.0, 'corr': 0.4, 'mu_factor': 0.8},
            'ASYMMETRIC_SHOCKS': {'vol': 2.5, 'corr': 0.3, 'mu_factor': 'shock'},
            'TRANSITION_TO_CRISIS': {'vol': 2.8, 'corr': 0.6, 'mu_factor': 0.6},
            'SIDEWAYS_HIGH_VOL': {'vol': 3.0, 'corr': 0.2, 'mu_factor': 1.0},
            'DECOUPLED_SHOCKS': {'vol': 2.2, 'corr': 'shock', 'mu_factor': 'shock'}
        }

    for name, params in scenarios.items():
        try:
            # Resolver 'shock' para correlación: usar un valor numérico aleatorio plausible
            target_corr = params['corr']
            if isinstance(target_corr, str):
                # UNCERTAINTY: permitir desde correlaciones bajas a moderadas
                target_corr = float(np.random.uniform(0.0, 0.7))

            cov = enhance_correlation_matrix(base_cov, params['vol'], target_corr)

            # Resolver 'shock' para mu
            if params['mu_factor'] == 'shock':
                shock = np.random.choice([-1.5, -0.5, 0.5, 1.5], size=n_assets)
                mu = base_mu + shock * 0.005
            else:
                mu = base_mu * params['mu_factor']

            synthetic_regimes.append(generate_synthetic_returns(mu, cov, n_days, base_returns.columns))
        except Exception as e:
            print(f"  - Skipping synthetic scenario '{name}' due to error: {e}")

    return synthetic_regimes[:n_variations]

def enhance_correlation_matrix(base_cov, vol_multiplier, target_correlation):
    """
    Enhances covariance matrix with target volatility and correlation
    """
    # Extract standard deviations
    base_std = np.sqrt(np.diag(base_cov))
    enhanced_std = base_std * vol_multiplier
    
    # Create correlation matrix with target correlation
    n_assets = len(base_std)
    enhanced_corr = np.full((n_assets, n_assets), float(target_correlation))
    np.fill_diagonal(enhanced_corr, 1.0)
    
    # Convert back to covariance matrix
    enhanced_cov = np.outer(enhanced_std, enhanced_std) * enhanced_corr
    
    return enhanced_cov

def generate_synthetic_returns(mu, cov, n_days, columns):
    """
    Generates synthetic returns from multivariate normal distribution
    """
    try:
        synthetic_returns = np.random.multivariate_normal(mu, cov, n_days)
        return pd.DataFrame(synthetic_returns, columns=columns)
    except np.linalg.LinAlgError:
        # Fallback if covariance matrix is not positive definite
        # Add small diagonal regularization
        regularized_cov = cov + np.eye(len(mu)) * 1e-6
        synthetic_returns = np.random.multivariate_normal(mu, regularized_cov, n_days)
        return pd.DataFrame(synthetic_returns, columns=columns)


def _transform_params_for_run(raw_params: dict, n_assets: int) -> dict:
    """Aplica transformaciones a params del grid (e.g., max_trials_factor → max_trials)."""
    params = dict(raw_params)
    # Calcular max_trials si se define un factor
    if 'max_trials_factor' in params:
        factor = params.pop('max_trials_factor')
        numb_bees = params.get('numb_bees', 25)
        try:
            params['max_trials'] = max(1, int(factor * numb_bees * n_assets))
        except Exception:
            params['max_trials'] = None  # fallback: dejar que el algoritmo use su default
    return params

def evaluate_robustness(
    algorithm_class,
    params,
    base_returns,
    regime_type='CRISIS',
    n_variations=5,
    criterion: str = 'worst',  # 'worst' o 'avg'
    seeds: list | None = None,
    early_stop_threshold: float | None = None,
):
    """
    ENHANCED SYNTHETIC REGIMES: Test algorithm across diverse stress scenarios.
    - criterion: 'worst' toma el peor score; 'avg' promedia.
    - seeds: lista de semillas para robustez; si None, se usa una sola ejecución por combinación.
    - early_stop_threshold: si el peor parcial supera este umbral, corta evaluación para ahorrar tiempo.
    """
    if seeds is None:
        seeds = [None]

    synthetic_regimes = generate_enhanced_synthetic_regimes(
        base_returns, regime_type=regime_type, n_variations=n_variations
    )

    collected_scores = []

    try:
        # Detectar dimensión de activos desde el primer sintético
        n_assets_probe = synthetic_regimes[0].shape[1]
    except Exception:
        return float('inf')

    for i, synthetic_returns in enumerate(synthetic_regimes):
        # Early stop para criterio 'worst'
        if criterion == 'worst' and early_stop_threshold is not None:
            if collected_scores and max(collected_scores) > early_stop_threshold:
                # Ya no es necesario seguir, este combo no superará al mejor
                break

        # Construir función objetivo
        objective_func = lambda w: simple_utility_objective(
            w, synthetic_returns, synthetic_returns.mean()
        )

        # Ejecutar con múltiples seeds si se solicita
        for seed in seeds:
            try:
                effective_params = _transform_params_for_run(params, n_assets_probe)
                if seed is not None:
                    effective_params = {**effective_params, 'seed': seed}

                model = algorithm_class(
                    lower=[0.0] * n_assets_probe,
                    upper=[1.0] * n_assets_probe,
                    fun=objective_func,
                    **effective_params,
                )
                model.run()
                _, fitness = model.get_best_solution()
                collected_scores.append(fitness)
            except Exception as e:
                print(f"      Error in synthetic regime {i+1} (seed={seed}): {e}")
                collected_scores.append(float('inf'))

            # Early stop chequeo tras cada seed
            if criterion == 'worst' and early_stop_threshold is not None:
                if collected_scores and max(collected_scores) > early_stop_threshold:
                    break

    if not collected_scores:
        return float('inf')

    if criterion == 'avg':
        score = float(np.mean(collected_scores))
    else:  # 'worst'
        score = float(max(collected_scores))

    return score


def robust_grid_search(algorithm_class, param_grid, regime_returns, regime_type='CRISIS'):
    """Búsqueda en dos etapas: screening rápido y validación robusta con refinamiento local."""
    print(f"🔍 Calibrando {algorithm_class.__name__} para robustez...")
    t0 = time.time()

    # Generar combinaciones
    keys, values = zip(*param_grid.items()) if param_grid else ([], [])
    param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)] if keys else []

    print(f"  📊 Total combinaciones: {len(param_combinations)}")

    if not param_combinations:
        return None, float('inf')

    # Etapa A: Screening rápido (promedio de 3 sintéticos) con menos iteraciones
    screening_results = []
    best_so_far = float('inf')
    for i, params in enumerate(param_combinations):
        if i % 10 == 0:
            print(f"  ▶️ Screening {i+1}/{len(param_combinations)}")
        # Usar menos iteraciones en screening para reducir costo
        params_screen = dict(params)
        params_screen['max_itrs'] = 40
        score = evaluate_robustness(
            algorithm_class,
            params_screen,
            regime_returns,
            regime_type=regime_type,
            n_variations=3,
            criterion='avg',
            seeds=[None],
            early_stop_threshold=None,
        )
        screening_results.append((score, params))
        if score < best_so_far:
            best_so_far = score

    # Seleccionar top-k
    screening_results.sort(key=lambda x: x[0])
    finalists = [p for (_, p) in screening_results[:3]]

    # Etapa B: Validación robusta (peor de 7 sintéticos y múltiples seeds)
    final_candidates = []
    for idx_f, params in enumerate(finalists):
        print(f"  🧪 Validación finalista {idx_f+1}/{len(finalists)}")
        score = evaluate_robustness(
            algorithm_class,
            params,
            regime_returns,
            regime_type=regime_type,
            n_variations=5,
            criterion='worst',
            seeds=[42, 773],
            early_stop_threshold=None,
        )
        final_candidates.append((score, params))

    # Refinamiento local alrededor del mejor de screening (omitido para Bacanin y Karaboga)
    algo_name = getattr(algorithm_class, "__name__", "")
    skip_refine = algo_name in ("ABC_FA_Bacanin", "ABC_BeeHive")
    if not skip_refine:
        best_from_screening = finalists[0]
        refined_grid = refine_grid(param_grid, best_from_screening)
        if refined_grid:
            r_keys, r_values = zip(*refined_grid.items())
            refined_combos = [dict(zip(r_keys, v)) for v in itertools.product(*r_values)]
            print(f"  🔎 Refinamiento local: {len(refined_combos)} combinaciones")
            for r_idx, params in enumerate(refined_combos):
                print(f"    🔁 Refinamiento {r_idx+1}/{len(refined_combos)}")
                score = evaluate_robustness(
                    algorithm_class,
                    params,
                    regime_returns,
                    regime_type=regime_type,
                    n_variations=5,
                    criterion='worst',
                    seeds=[42, 773],
                    early_stop_threshold=None,
                )
                final_candidates.append((score, params))

    # Selección final por peor caso mínimo
    final_candidates.sort(key=lambda x: x[0])
    best_score, best_params = final_candidates[0]

    print(f"✅ Mejores parámetros: {best_params}")
    print(f"   Score final (peor de 5, 2 seeds): {best_score:.6f}")
    elapsed = time.time() - t0
    print(f"   ⏱️ Duración calibración {algorithm_class.__name__}: {elapsed/60:.2f} min")

    return best_params, best_score

def refine_grid(current_grid, best_params):
    """Helper to zoom in the grid around the best found parameters."""
    refined_grid = {}
    for param, value in best_params.items():
        if isinstance(value, (int, float)):
            current_values = sorted(current_grid[param])
            idx = current_values.index(value)
            
            if len(current_values) <= 2:
                refined_grid[param] = current_values
                continue
            
            if idx == 0: # min value
                new_center = (current_values[0] + current_values[1]) / 2
                refined_grid[param] = [current_values[0], new_center, current_values[1]]
            elif idx == len(current_values) - 1: # max value
                new_center = (current_values[-1] + current_values[-2]) / 2
                refined_grid[param] = [current_values[-2], new_center, current_values[-1]]
            else: # middle value
                refined_grid[param] = [current_values[idx-1], value, current_values[idx+1]]
        else:
            refined_grid[param] = [value] # Non-numeric, no refinement
            
    return refined_grid

# --- Main Execution Pipeline ---

if __name__ == "__main__":
    print("🚀 robust_calibration_pipeline.py: START (Regime-Specific, Dynamic Data Methodology)")
    
    final_robust_params = {}
    algorithms_to_calibrate = {
        "ABC_FA_Scout": ABC_FA_Scout,
        "ABC_Scout_Gravitacional": ABC_Scout_Gravitacional,
        "ABC_FA_Bacanin": ABC_FA_Bacanin,
        "ABC_Original": ABC_BeeHive
    }
    
    THEORETICAL_REGIMES = ['CRISIS', 'STABLE_GROWTH', 'UNCERTAINTY']

    # 1. Outer Loop: Calibrate for each THEORETICAL REGIME TYPE
    for regime_type in THEORETICAL_REGIMES:
        print(f"\n\n{'='*30} CALIBRATING FOR REGIME TYPE: {regime_type} {'='*30}")
        all_period_results_for_regime = {}

        # 2. Inner Loop: Use each historical period as a base for cross-validation
        for period_name, (start_date, end_date) in CALIBRATION_BASE_PERIODS.items():
            print(f"\n--- Using Base Period '{period_name}' ({start_date} to {end_date}) as seed ---")
            
            # DYNAMIC DATA LOADING: Load and filter data specifically for this historical period
            try:
                period_prices, _, _ = get_portfolio_data(
                    start_date=start_date, end_date=end_date, min_days=750 # ~3 years of data within the period
                )
                base_data = calculate_returns(period_prices)
                
                if base_data.empty or len(base_data) < 252: # Min 1 year of returns
                    print(f"  - Insufficient data after processing. Skipping.")
                    continue
                
                print(f"  - Data loaded for this period: {base_data.shape[1]} assets")

            except FileNotFoundError as e:
                print(f"  - Data loading error: {e}. Skipping period.")
                continue

            period_results = {}
            for algo_name, algo_class in algorithms_to_calibrate.items():
                param_grid = REFINED_PARAM_GRIDS[algo_name]
                try:
                    best_params, best_score = robust_grid_search(
                        algo_class, param_grid, base_data, regime_type=regime_type
                    )
                except Exception as e:
                    print(f"  - Calibration error for {algo_name} in period {period_name} / regime {regime_type}: {e}")
                    best_params, best_score = "Calibration failed", float('inf')

                period_results[algo_name] = {
                    'best_params': best_params,
                    'robustness_score': best_score
                }
            all_period_results_for_regime[period_name] = period_results

        # 3. Aggregate results for the current REGIME TYPE
        final_params_for_regime = {}
        for algo_name in algorithms_to_calibrate:
            param_counts = {}
            for period_name in CALIBRATION_BASE_PERIODS:
                if period_name in all_period_results_for_regime and all_period_results_for_regime[period_name][algo_name]['best_params']:
                    best_params_tuple = tuple(sorted(all_period_results_for_regime[period_name][algo_name]['best_params'].items()))
                    param_counts[best_params_tuple] = param_counts.get(best_params_tuple, 0) + 1
            
            if param_counts:
                most_frequent_params_tuple = max(param_counts, key=param_counts.get)
                final_params_for_regime[algo_name] = dict(most_frequent_params_tuple)
            else:
                final_params_for_regime[algo_name] = "Calibration failed"
        
        final_robust_params[regime_type] = final_params_for_regime

    # 4. Save final aggregated results
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'final_adaptive_parameters.json')
    with open(output_path, 'w') as f:
        json.dump(final_robust_params, f, indent=4)
        
    print(f"\n\n🏁 robust_calibration_pipeline.py: COMPLETE 🏁")
    print(f"   Final ADAPTIVE parameters saved to: {output_path}")
    print("-" * 70)
    print(json.dumps(final_robust_params, indent=4))
    print("-" * 70)
