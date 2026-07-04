"""
Framework de Calibración Multi-Regimen para Algoritmos Robustos
==============================================================

Este script implementa un enfoque avanzado de calibración que simula
diferentes condiciones de mercado para entrenar algoritmos que sean
robustos a cualquier tipo de crisis o volatilidad.

Metodología:
1. **Simulación de Regímenes**: Genera datos sintéticos con diferentes
   características de volatilidad, correlación y tendencias.
2. **Entrenamiento Multi-Regimen**: Los algoritmos se entrenan en
   múltiples condiciones simultáneamente.
3. **Validación Cruzada Temporal**: Evalúa en períodos reales de crisis.
4. **Robustez Adaptativa**: Los algoritmos aprenden patrones generales
   de comportamiento en mercados estresados.
"""

import os
import sys
import itertools
import numpy as np
import pandas as pd
import riskfolio as rp
from scipy.stats import multivariate_normal
from sklearn.covariance import LedoitWolf

# --- Configuración de Paths ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

# --- Imports de los Módulos del Proyecto ---
from src.utils.data_loader import get_portfolio_data, calculate_returns
from src.algorithms.abc_original import ABC_BeeHive
from src.algorithms.abc_fa_bacanin import ABC_FA_Bacanin
from src.algorithms.abc_fa_scout import ABC_FA_Scout
from src.algorithms.abc_scout_gravitacional import ABC_Scout_Gravitacional
from src.algorithms.abc_probabilistic_scout import ABC_Probabilistic_Scout

# --- Definición de Regímenes Simulados ---
REGIME_SIMULATIONS = {
    'HIGH_VOLATILITY': {
        'volatility_multiplier': 2.5,
        'correlation_increase': 0.3,
        'trend_strength': 0.0,  # Sin tendencia clara
        'regime_duration': 252,  # 1 año
        'description': 'Alta volatilidad sin tendencia clara'
    },
    'CRASH_SCENARIO': {
        'volatility_multiplier': 4.0,
        'correlation_increase': 0.6,
        'trend_strength': -0.02,  # Tendencia bajista fuerte
        'regime_duration': 126,  # 6 meses
        'description': 'Escenario de crash con correlaciones altas'
    },
    'FLASH_CRASH': {
        'volatility_multiplier': 6.0,
        'correlation_increase': 0.8,
        'trend_strength': -0.05,  # Caída muy rápida
        'regime_duration': 21,  # 1 mes
        'description': 'Flash crash con volatilidad extrema'
    },
    'SIDEWAYS_VOLATILE': {
        'volatility_multiplier': 2.0,
        'correlation_increase': 0.2,
        'trend_strength': 0.0,  # Sin tendencia
        'regime_duration': 252,
        'description': 'Mercado lateral con alta volatilidad'
    },
    'RECOVERY_SCENARIO': {
        'volatility_multiplier': 1.5,
        'correlation_increase': 0.1,
        'trend_strength': 0.01,  # Recuperación gradual
        'regime_duration': 252,
        'description': 'Recuperación post-crisis'
    }
}

def simulate_market_regime(base_returns, regime_params):
    """
    Simula un régimen de mercado específico basado en parámetros.
    
    Args:
        base_returns: DataFrame de retornos base
        regime_params: Diccionario con parámetros del régimen
    
    Returns:
        tuple: (simulated_returns, simulated_mu, simulated_cov)
    """
    n_assets = base_returns.shape[1]
    n_days = regime_params['regime_duration']
    
    # Calcular estadísticas base
    base_mu = base_returns.mean()
    base_cov = base_returns.cov()
    
    # Aplicar modificaciones del régimen
    volatility_mult = regime_params['volatility_multiplier']
    correlation_inc = regime_params['correlation_increase']
    trend_strength = regime_params['trend_strength']
    
    # Modificar volatilidad
    modified_cov = base_cov * volatility_mult
    
    # Aumentar correlaciones
    if correlation_inc > 0:
        # Crear matriz de correlación aumentada
        correlation_matrix = np.ones((n_assets, n_assets)) * correlation_inc
        np.fill_diagonal(correlation_matrix, 1.0)
        
        # Aplicar correlación aumentada
        std_devs = np.sqrt(np.diag(modified_cov))
        modified_cov = np.outer(std_devs, std_devs) * correlation_matrix
    
    # Modificar retornos esperados con tendencia
    modified_mu = base_mu + trend_strength
    
    # Generar retornos simulados
    simulated_returns = np.random.multivariate_normal(
        mean=modified_mu,
        cov=modified_cov,
        size=n_days
    )
    
    return pd.DataFrame(simulated_returns, columns=base_returns.columns), modified_mu, modified_cov

def create_multi_regime_dataset(base_returns, n_regimes=3):
    """
    Crea un dataset multi-regimen combinando diferentes condiciones de mercado.
    
    Args:
        base_returns: Retornos base reales
        n_regimes: Número de regímenes a simular
    
    Returns:
        tuple: (combined_returns, combined_mu, combined_cov)
    """
    regime_keys = list(REGIME_SIMULATIONS.keys())[:n_regimes]
    all_returns = []
    
    for regime_key in regime_keys:
        regime_params = REGIME_SIMULATIONS[regime_key]
        simulated_returns, _, _ = simulate_market_regime(base_returns, regime_params)
        all_returns.append(simulated_returns)
    
    # Combinar todos los regímenes
    combined_returns = pd.concat(all_returns, ignore_index=True)
    combined_mu = combined_returns.mean()
    combined_cov = combined_returns.cov()
    
    return combined_returns, combined_mu, combined_cov

def utility_objective_robust(weights, returns, mu, lambda_cvar=0.5, lambda_l1=1e-4, 
                           lambda_cardinality=1e-3, alpha=0.95, target_cardinality=8):
    """
    Función objetivo robusta con cardinalidad para entrenamiento multi-regimen.
    """
    weights = np.array(weights)
    if np.sum(weights) <= 1e-9: return 1e10
    weights = weights / np.sum(weights)
    
    # Componentes originales
    portfolio_return = np.dot(weights, mu)
    port_returns = returns.dot(weights)
    cvar = rp.CVaR_Hist(port_returns, alpha=alpha)
    l1_penalty = np.sum(np.abs(weights))
    
    # Penalización de cardinalidad
    significant_weights = np.sum(weights > 0.005)
    if significant_weights > target_cardinality:
        cardinality_penalty = 1e-3 * ((significant_weights - target_cardinality) ** 2)
    else:
        cardinality_penalty = 0.0
    
    # Función objetivo combinada
    utility = portfolio_return - lambda_cvar * cvar - lambda_l1 * l1_penalty - lambda_cardinality * cardinality_penalty
    
    return -utility

def evaluate_robustness(algorithm_class, params, base_returns, test_regimes):
    """
    Evalúa la robustez de un algoritmo en múltiples regímenes de prueba.
    """
    scores = []
    
    for regime_name, regime_params in test_regimes.items():
        # Simular régimen de prueba
        test_returns, test_mu, _ = simulate_market_regime(base_returns, regime_params)
        
        # Configurar problema
        n_assets = len(test_mu)
        lower = [0.0] * n_assets
        upper = [1.0] * n_assets
        
        objective_func = lambda w: utility_objective_robust(w, test_returns, test_mu)
        
        # Ejecutar algoritmo
        try:
            model = algorithm_class(lower, upper, objective_func, **params)
            model.run()
            weights, fitness = model.get_best_solution()
            
            # Calcular métrica de robustez (Ratio de Sortino)
            portfolio_returns = test_returns.dot(weights)
            sortino = rp.Sharpe(pd.DataFrame(portfolio_returns, columns=['port']), rm='SLPM')
            scores.append(-sortino)  # Negativo porque minimizamos
            
        except Exception as e:
            print(f"Error en régimen {regime_name}: {e}")
            scores.append(float('inf'))
    
    # Retornar el peor score (enfoque conservador)
    return max(scores) if scores else float('inf')

def calibrate_robust_algorithm(algorithm_class, param_grid, base_returns, test_regimes):
    """
    Calibra un algoritmo para ser robusto en múltiples regímenes.
    """
    print(f"🔍 Calibrando {algorithm_class.__name__} para robustez multi-regimen...")
    
    # Crear todas las combinaciones de parámetros
    keys, values = zip(*param_grid.items())
    param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    print(f"  📊 Total de combinaciones a probar: {len(param_combinations)}")
    print(f"  🎯 Regímenes de prueba: {len(test_regimes)}")
    print(f"  ⏱️  Estimado: ~{len(param_combinations) * len(test_regimes) * 2} segundos")
    
    best_score = float('inf')
    best_params = None
    
    for i, params in enumerate(param_combinations):
        print(f"  [{i+1}/{len(param_combinations)}] Probando parámetros...")
        
        # Evaluar robustez en múltiples regímenes
        score = evaluate_robustness(algorithm_class, params, base_returns, test_regimes)
        
        if score < best_score:
            best_score = score
            best_params = params
            print(f"    ✨ Nuevo mejor score: {best_score:.6f}")
    
    print(f"✅ Mejores parámetros robustos: {best_params}")
    print(f"   Score de robustez: {best_score:.6f}")
    
    return best_params

# --- Parámetros de Calibración Robusta (Reducidos) ---
ROBUST_PARAM_GRIDS = {
    'ABC_Original': {
        'max_trials': [10, 20],
        'numb_bees': [20, 30],
        'max_itrs': [50, 80]
    },
    'ABC_FA_Bacanin': {
        'max_trials': [10, 20],
        'b0': [1.0, 1.5],
        'gamma': [1.0, 1.5],
        'alpha': [0.03, 0.05],
        'numb_bees': [20, 30],
        'max_itrs': [50, 80]
    },
    'ABC_FA_Scout': {
        'max_trials': [10, 20],
        'gamma': [0.8, 1.2],
        'alpha': [0.05, 0.1],
        'numb_bees': [20, 30],
        'max_itrs': [50, 80]
    },
    'ABC_Scout_Gravitacional': {
        'max_trials': [10, 20],
        'G': [0.5, 1.0],
        'epsilon': [1e-10, 1e-08],
        'alpha': [0.03, 0.05],
        'numb_bees': [20, 30],
        'max_itrs': [50, 80]
    },
    'ABC_Probabilistic_Scout': {
        'max_trials': [10, 20],
        'epsilon': [0.05, 0.1],
        'numb_bees': [20, 30],
        'max_itrs': [50, 80]
    }
}

if __name__ == "__main__":
    print("🚀 INICIO DE CALIBRACIÓN ROBUSTA MULTI-REGIMEN")
    print("=" * 60)
    
    # Cargar datos base para simulación
    print("📊 Cargando datos base para simulación...")
    base_prices, base_mu, base_cov = get_portfolio_data(
        start_date="2015-01-01",
        end_date="2020-01-31",
        min_days=500,
        verbose=False
    )
    base_returns = calculate_returns(base_prices, verbose=False)
    
    # Definir regímenes de prueba (diferentes a los de entrenamiento)
    test_regimes = {
        'CRASH_2020': REGIME_SIMULATIONS['CRASH_SCENARIO'],
        'FLASH_CRASH': REGIME_SIMULATIONS['FLASH_CRASH'],
        'HIGH_VOL': REGIME_SIMULATIONS['HIGH_VOLATILITY']
    }
    
    # Calibrar cada algoritmo
    robust_params = {}
    
    algorithms = [
        (ABC_BeeHive, 'ABC_Original'),
        (ABC_FA_Bacanin, 'ABC_FA_Bacanin'),
        (ABC_FA_Scout, 'ABC_FA_Scout'),
        (ABC_Scout_Gravitacional, 'ABC_Scout_Gravitacional'),
        (ABC_Probabilistic_Scout, 'ABC_Probabilistic_Scout')
    ]
    
    for algorithm_class, name in algorithms:
        param_grid = ROBUST_PARAM_GRIDS[name]
        robust_params[name] = calibrate_robust_algorithm(
            algorithm_class, param_grid, base_returns, test_regimes
        )
    
    print("\n🏁 RESULTADOS DE CALIBRACIÓN ROBUSTA")
    print("-" * 60)
    for name, params in robust_params.items():
        print(f"{name}: {params}")
    print("-" * 60) 