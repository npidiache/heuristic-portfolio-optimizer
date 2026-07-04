"""
Grid Search Refinado con Estrategias Anti-Overfitting
=====================================================

Este script implementa un grid search refinado que maximiza el potencial
de mejora mientras minimiza el riesgo de overfitting.
"""

import numpy as np
import pandas as pd
import itertools
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')

# --- Grid Search Refinado Anti-Overfitting ---
REFINED_PARAM_GRIDS = {
    'ABC_FA_Scout': {
        'max_trials': [8, 12, 15, 18, 22, 25],
        'gamma': [0.6, 0.8, 1.0, 1.2, 1.4, 1.6],
        'alpha': [0.03, 0.05, 0.07, 0.09, 0.11, 0.13],
        'b0': [0.8, 1.0, 1.2, 1.4, 1.6],
        'numb_bees': [15, 20, 25, 30, 35],
        'max_itrs': [40, 60, 80, 100, 120]
    },
    'ABC_FA_Bacanin': {
        'max_trials': [8, 12, 15, 18, 22, 25],
        'b0': [0.8, 1.0, 1.2, 1.4, 1.6, 1.8],
        'gamma': [0.6, 0.8, 1.0, 1.2, 1.4, 1.6],
        'alpha': [0.03, 0.05, 0.07, 0.09, 0.11, 0.13],
        'numb_bees': [15, 20, 25, 30, 35],
        'max_itrs': [40, 60, 80, 100, 120]
    },
    'ABC_Scout_Gravitacional': {
        'max_trials': [8, 12, 15, 18, 22, 25],
        'G': [0.3, 0.5, 0.7, 0.9, 1.1, 1.3],
        'epsilon': [1e-12, 1e-10, 1e-08, 1e-06],
        'alpha': [0.02, 0.03, 0.04, 0.05, 0.06, 0.07],
        'numb_bees': [15, 20, 25, 30, 35],
        'max_itrs': [40, 60, 80, 100, 120]
    },
    'ABC_Probabilistic_Scout': {
        'max_trials': [8, 12, 15, 18, 22, 25],
        'epsilon': [0.03, 0.05, 0.07, 0.09, 0.11, 0.13],
        'numb_bees': [15, 20, 25, 30, 35],
        'max_itrs': [40, 60, 80, 100, 120]
    }
}

def calculate_grid_size(param_grid):
    """Calcula el tamaño total del grid de parámetros."""
    total_combinations = 1
    for param_values in param_grid.values():
        total_combinations *= len(param_values)
    return total_combinations

def estimate_computation_time(grid_size, n_regimes=20, avg_time_per_run=2.0):
    """Estima el tiempo de computación total."""
    total_runs = grid_size * n_regimes
    total_time_seconds = total_runs * avg_time_per_run
    total_time_hours = total_time_seconds / 3600
    return total_time_hours

def adaptive_grid_search_robust(algorithm_class, param_grid, base_returns, 
                               max_iterations=50, convergence_threshold=0.001):
    """
    Búsqueda adaptativa que refina el grid basado en resultados.
    """
    print(f"🔍 Iniciando búsqueda adaptativa para {algorithm_class.__name__}")
    print(f"   Grid inicial: {calculate_grid_size(param_grid)} combinaciones")
    
    current_grid = param_grid.copy()
    best_params = None
    best_score = float('inf')
    improvement_history = []
    
    for iteration in range(max_iterations):
        print(f"  Iteración {iteration + 1}/{max_iterations}")
        
        # Evaluar combinaciones actuales
        scores = []
        combinations = list(itertools.product(*current_grid.values()))
        
        for i, combination in enumerate(combinations):
            params = dict(zip(current_grid.keys(), combination))
            
            # Evaluar robustez
            score = evaluate_robustness_robust(algorithm_class, params, base_returns)
            scores.append((params, score))
            
            if i % 100 == 0:
                print(f"    Progreso: {i}/{len(combinations)} combinaciones evaluadas")
        
        # Encontrar mejor combinación
        best_combination, best_current_score = min(scores, key=lambda x: x[1])
        
        # Calcular mejora
        improvement = best_score - best_current_score
        improvement_history.append(improvement)
        
        if best_current_score < best_score:
            best_score = best_current_score
            best_params = best_combination
            print(f"    ✨ Nuevo mejor score: {best_score:.6f}")
            print(f"    📊 Parámetros: {best_params}")
        
        # Condición de parada
        if iteration > 5 and abs(improvement) < convergence_threshold:
            print(f"    🛑 Convergencia alcanzada en iteración {iteration + 1}")
            break
        
        # Refinar grid alrededor del mejor punto
        current_grid = refine_grid_around_best(current_grid, best_combination)
        
        print(f"    📈 Grid refinado: {calculate_grid_size(current_grid)} combinaciones")
    
    return best_params, best_score, improvement_history

def refine_grid_around_best(current_grid, best_params):
    """
    Refina el grid alrededor del mejor punto encontrado.
    """
    refined_grid = {}
    
    for param_name, best_value in best_params.items():
        current_values = current_grid[param_name]
        best_index = current_values.index(best_value)
        
        # Crear rango refinado alrededor del mejor valor
        if len(current_values) > 1:
            # Calcular paso refinado
            if best_index == 0:
                # Mejor valor es el mínimo
                refined_values = [
                    best_value,
                    best_value + (current_values[1] - best_value) * 0.5,
                    current_values[1]
                ]
            elif best_index == len(current_values) - 1:
                # Mejor valor es el máximo
                refined_values = [
                    current_values[-2],
                    best_value - (best_value - current_values[-2]) * 0.5,
                    best_value
                ]
            else:
                # Mejor valor está en el medio
                step = (current_values[best_index + 1] - current_values[best_index - 1]) / 4
                refined_values = [
                    current_values[best_index - 1],
                    best_value - step,
                    best_value,
                    best_value + step,
                    current_values[best_index + 1]
                ]
        else:
            # Mantener valor único
            refined_values = [best_value]
        
        refined_grid[param_name] = refined_values
    
    return refined_grid

def evaluate_robustness_robust(algorithm_class, params, base_returns):
    """
    Evaluación de robustez con múltiples regímenes sintéticos.
    """
    # Generar regímenes de prueba diversos
    test_regimes = generate_diverse_test_regimes(n_regimes=15)
    
    regime_scores = []
    
    for regime in test_regimes:
        try:
            # Simular régimen
            simulated_returns = simulate_regime_robust(base_returns, regime)
            
            # Configurar problema
            n_assets = simulated_returns.shape[1]
            lower = [0.0] * n_assets
            upper = [1.0] * n_assets
            
            # Función objetivo multi-métrica
            objective_func = lambda w: multi_metric_objective_robust(
                w, simulated_returns, simulated_returns.mean()
            )
            
            # Ejecutar algoritmo
            model = algorithm_class(lower, upper, objective_func, **params)
            model.run()
            weights, fitness = model.get_best_solution()
            
            # Calcular métrica de robustez
            portfolio_returns = simulated_returns.dot(weights)
            sortino = calculate_sortino_ratio_robust(portfolio_returns)
            regime_scores.append(-sortino)  # Negativo porque minimizamos
            
        except Exception as e:
            # Penalizar errores
            regime_scores.append(float('inf'))
    
    # Retornar el peor score (enfoque conservador)
    return max(regime_scores) if regime_scores else float('inf')

def generate_diverse_test_regimes(n_regimes=15):
    """
    Genera regímenes de prueba con máxima diversidad.
    """
    regimes = []
    
    # Parámetros base
    volatility_range = np.linspace(1.5, 6.0, 8)
    correlation_range = np.linspace(0.1, 0.8, 7)
    trend_range = np.linspace(-0.05, 0.02, 6)
    duration_range = [21, 63, 126, 252]
    
    # Generar combinaciones aleatorias
    np.random.seed(42)  # Para reproducibilidad
    for _ in range(n_regimes):
        regime = {
            'volatility_multiplier': np.random.choice(volatility_range),
            'correlation_increase': np.random.choice(correlation_range),
            'trend_strength': np.random.choice(trend_range),
            'regime_duration': np.random.choice(duration_range)
        }
        regimes.append(regime)
    
    return regimes

def simulate_regime_robust(base_returns, regime_params):
    """
    Simula un régimen de mercado robusto.
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
        correlation_matrix = np.ones((n_assets, n_assets)) * correlation_inc
        np.fill_diagonal(correlation_matrix, 1.0)
        
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
    
    return pd.DataFrame(simulated_returns, columns=base_returns.columns)

def multi_metric_objective_robust(weights, returns, mu, lambda_weights=None):
    """
    Función objetivo multi-métrica para evitar overfitting.
    """
    if lambda_weights is None:
        lambda_weights = {
            'sortino': 0.4,
            'max_dd': 0.3,
            'alpha': 0.2,
            'cardinality': 0.1
        }
    
    weights = np.array(weights)
    if np.sum(weights) <= 1e-9: return 1e10
    weights = weights / np.sum(weights)
    
    # Calcular retornos del portafolio
    portfolio_returns = returns.dot(weights)
    
    # Sortino Ratio
    sortino = calculate_sortino_ratio_robust(portfolio_returns)
    
    # Maximum Drawdown
    max_dd = calculate_max_drawdown_robust(portfolio_returns)
    
    # Jensen Alpha (simplificado)
    alpha = portfolio_returns.mean() - returns.mean().mean()
    
    # Cardinality penalty
    significant_weights = np.sum(weights > 0.005)
    cardinality_penalty = max(0, significant_weights - 8) ** 2 * 1e-3
    
    # Función objetivo balanceada
    objective = (
        lambda_weights['sortino'] * sortino +
        lambda_weights['max_dd'] * max_dd +
        lambda_weights['alpha'] * alpha +
        lambda_weights['cardinality'] * cardinality_penalty
    )
    
    return -objective  # Minimizar

def calculate_sortino_ratio_robust(returns, risk_free_rate=0.0):
    """Calcula Sortino Ratio de forma robusta."""
    excess_returns = returns - risk_free_rate
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0:
        return 0.0
    
    downside_std = np.sqrt(np.mean(downside_returns ** 2))
    if downside_std == 0:
        return 0.0
    
    return np.mean(excess_returns) / downside_std

def calculate_max_drawdown_robust(returns):
    """Calcula Maximum Drawdown de forma robusta."""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()

def temporal_cross_validation_robust(algorithm_class, param_grid, base_returns, n_splits=5):
    """
    Validación cruzada temporal para evitar overfitting temporal.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    
    for train_idx, test_idx in tscv.split(base_returns):
        train_returns = base_returns.iloc[train_idx]
        test_returns = base_returns.iloc[test_idx]
        
        # Calibrar en train
        best_params = calibrate_on_period_robust(algorithm_class, param_grid, train_returns)
        
        # Evaluar en test
        test_score = evaluate_on_period_robust(algorithm_class, best_params, test_returns)
        cv_scores.append(test_score)
    
    return np.mean(cv_scores), np.std(cv_scores)

def calibrate_on_period_robust(algorithm_class, param_grid, returns):
    """Calibración en un período específico."""
    # Implementación simplificada para demostración
    return {'max_trials': 15, 'gamma': 1.0, 'alpha': 0.1}

def evaluate_on_period_robust(algorithm_class, params, returns):
    """Evaluación en un período específico."""
    # Implementación simplificada para demostración
    return -0.5  # Score simulado

# --- Configuración de Ejecución ---
EXECUTION_CONFIG = {
    'max_iterations': 30,
    'convergence_threshold': 0.001,
    'n_regimes': 15,
    'n_cv_splits': 5,
    'timeout_hours': 24
}

def run_refined_calibration():
    """
    Ejecuta la calibración refinada completa.
    """
    print("🚀 INICIO DE CALIBRACIÓN REFINADA CON ANTI-OVERFITTING")
    print("=" * 70)
    
    # Mostrar estadísticas del grid
    for algorithm_name, param_grid in REFINED_PARAM_GRIDS.items():
        grid_size = calculate_grid_size(param_grid)
        estimated_time = estimate_computation_time(grid_size)
        
        print(f"\n📊 {algorithm_name}")
        print(f"   Grid size: {grid_size:,} combinaciones")
        print(f"   Tiempo estimado: {estimated_time:.1f} horas")
        print(f"   Parámetros: {list(param_grid.keys())}")
    
    print(f"\n⚠️  ADVERTENCIA: Tiempo total estimado: ~{sum(estimate_computation_time(calculate_grid_size(grid)) for grid in REFINED_PARAM_GRIDS.values()):.1f} horas")
    print("   Se recomienda ejecutar en paralelo o por lotes")
    
    # Ejemplo de ejecución para un algoritmo
    print(f"\n🎯 Ejemplo de ejecución para ABC_FA_Scout:")
    example_grid = REFINED_PARAM_GRIDS['ABC_FA_Scout']
    example_size = calculate_grid_size(example_grid)
    example_time = estimate_computation_time(example_size)
    
    print(f"   Combinaciones: {example_size:,}")
    print(f"   Tiempo estimado: {example_time:.1f} horas")
    print(f"   Recomendación: Ejecutar en lotes de 1,000 combinaciones")

if __name__ == "__main__":
    run_refined_calibration() 