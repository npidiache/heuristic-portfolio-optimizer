"""
Backtesting de Algoritmos Calibrados (Versión v2, parámetros actualizados)
=========================================================================

Esta versión replica la lógica y métricas del test original para COVID-19,
pero usa los parámetros calibrados finales (regimen CRISIS) guardados en
`final_adaptive_parameters.json`.
"""

import sys
import os
import numpy as np
import pandas as pd
import time
from scipy.stats import wilcoxon
import riskfolio as rp
import random
import quantstats as qs
from datetime import datetime, timedelta
import json

# --- Configuración de Paths ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# --- Imports de los Módulos del Proyecto ---
from src.utils.data_loader import get_portfolio_data, calculate_returns, load_nasdaq_data
from src.algorithms.abc_original import ABC_BeeHive
from src.algorithms.abc_fa_bacanin import ABC_FA_Bacanin
from src.algorithms.abc_fa_scout import ABC_FA_Scout
# from src.algorithms.abc_probabilistic_scout import ABC_Probabilistic_Scout
from src.algorithms.abc_scout_gravitacional import ABC_Scout_Gravitacional
from src.algorithms.pmvg_cvx import PMVG_CVX

# --- Definición de la Función Objetivo de Utilidad ---
def utility_objective(weights, returns, mu, lambda_cvar=0.7, lambda_l1=1e-4, alpha=0.99):
    weights = np.array(weights)
    if np.sum(weights) <= 1e-9: return 1e10
    weights = weights / np.sum(weights)
    portfolio_return = np.dot(weights, mu)
    port_returns = returns.dot(weights)
    cvar = rp.CVaR_Hist(port_returns, alpha=alpha)
    l1_penalty = np.sum(np.abs(weights))
    utility = portfolio_return - lambda_cvar * cvar - lambda_l1 * l1_penalty
    return -utility


def cardinality_penalty(weights, target_cardinality=8, threshold=0.01):
    """
    Penaliza portafolios con demasiados activos significativos.
    threshold: peso mínimo para considerar un activo como significativo (p.ej.1%)
    """
    significant_weights = np.sum(weights > threshold)
    if significant_weights <= target_cardinality:
        return 0.0
    else:
        excess = significant_weights - target_cardinality
        return (excess ** 2)


def utility_objective_with_cardinality(weights, returns, mu, lambda_cvar=0.7, lambda_l1=1e-4, 
                                      lambda_cardinality=1e-3, alpha=0.95, target_cardinality=8,
                                      cardinality_threshold=0.001):
    """
    Función objetivo con restricción de cardinalidad escalable por dimensión.
    """
    weights = np.array(weights)
    if np.sum(weights) <= 1e-9: return 1e10
    weights = weights / np.sum(weights)
    portfolio_return = np.dot(weights, mu)
    port_returns = returns.dot(weights)
    cvar = rp.CVaR_Hist(port_returns, alpha=alpha)
    l1_penalty = np.sum(np.abs(weights))
    card_pen = cardinality_penalty(weights, target_cardinality, threshold=cardinality_threshold)
    utility = portfolio_return - lambda_cvar * cvar - lambda_l1 * l1_penalty - lambda_cardinality * card_pen
    return -utility


def enforce_top_k(weights, k):
    """Devuelve un vector de pesos recortado a los top-k por magnitud y renormalizado."""
    w = np.array(weights, dtype=float)
    if np.sum(w) <= 1e-12:
        return w
    w = w / np.sum(w)
    if k >= len(w):
        return w
    idx_sorted = np.argsort(-w)
    keep = idx_sorted[:k]
    w_new = np.zeros_like(w)
    w_new[keep] = w[keep]
    s = w_new.sum()
    if s > 0:
        w_new /= s
    return w_new


# --- Stock Picking Ex-Ante (z-scores) ---
def _safe_z(series: pd.Series) -> pd.Series:
    m, s = series.mean(), series.std(ddof=0)
    if s == 0 or np.isnan(s):
        return pd.Series(0.0, index=series.index)
    return (series - m) / s


def _compute_max_drawdown_from_returns(returns: pd.Series) -> float:
    # Usar quantstats si está disponible; fallback a cálculo manual
    try:
        return float(qs.stats.max_drawdown(returns))
    except Exception:
        cum = (1 + returns.fillna(0)).cumprod()
        running_max = cum.cummax()
        dd = (cum / running_max) - 1.0
        return float(dd.min())


def select_universe_by_zscores(prices_file: str,
                               start_date: str,
                               lookback_days: int = 252,
                               gap_days: int = 21,
                               min_days_pre: int = 180,
                               target_n: int = 20,
                               corr_threshold: float = 0.8,
                               outputs_dir: str = None) -> list:
    # Fechas de la ventana previa
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_pre_dt = start_dt - timedelta(days=1)
    start_pre_dt = end_pre_dt - timedelta(days=lookback_days)
    start_pre, end_pre = start_pre_dt.strftime("%Y-%m-%d"), end_pre_dt.strftime("%Y-%m-%d")

    print(f"🔎 Selección ex-ante (z-scores) en ventana previa: {start_pre} a {end_pre}")
    prices_pre = load_nasdaq_data(prices_file, start_pre, end_pre, tickers=None, min_days=min_days_pre, verbose=True)
    returns_pre = calculate_returns(prices_pre, verbose=False)

    # Si no hay suficientes datos, relajar min_days y reintentar una vez
    if returns_pre.shape[1] == 0:
        print("⚠️ Ventana previa sin activos suficientes; relajando min_days_pre a 120 y reintentando...")
        prices_pre = load_nasdaq_data(prices_file, start_pre, end_pre, tickers=None, min_days=120, verbose=True)
        returns_pre = calculate_returns(prices_pre, verbose=False)

    # Momentum 12-1 aproximado: acumulado excluyendo últimos gap_days
    if returns_pre.shape[0] <= gap_days:
        gap_days = max(1, min(gap_days, max(1, returns_pre.shape[0] // 10)))
    mom_series = (returns_pre.iloc[:-gap_days].sum()) if returns_pre.shape[0] > gap_days else returns_pre.sum()

    # Volatilidad y Max Drawdown por activo (en returns)
    vol_series = returns_pre.std()
    mdd_series = returns_pre.apply(_compute_max_drawdown_from_returns, axis=0)

    # Z-scores (mayor es mejor). Para riesgo, usar signo inverso
    z_mom = _safe_z(mom_series)
    z_neg_vol = _safe_z(-vol_series)
    z_neg_mdd = _safe_z(-mdd_series)

    score = 0.5 * z_mom + 0.3 * z_neg_vol + 0.2 * z_neg_mdd
    rank = score.dropna().sort_values(ascending=False)

    # Fallback si rank está vacío: usar momentum simple
    if rank.empty:
        print("⚠️ Rank vacío; aplicando fallback de momentum simple para selección top-N.")
        rank = mom_series.dropna().sort_values(ascending=False)

    # Diversificación por correlación (greedy)
    corr = returns_pre.corr().fillna(0)
    selected = []
    for ticker in rank.index:
        if len(selected) >= target_n:
            break
        if not selected:
            selected.append(ticker)
            continue
        # si falta en corr (columnas), aceptar por defecto
        if (ticker not in corr.index) or any((s not in corr.columns) for s in selected):
            selected.append(ticker)
            continue
        max_corr = max(abs(float(corr.loc[ticker, s])) for s in selected if (ticker in corr.index and s in corr.columns))
        if max_corr < corr_threshold:
            selected.append(ticker)
    # Si faltan, completar ignorando correlación
    if len(selected) < target_n:
        for ticker in rank.index:
            if ticker not in selected:
                selected.append(ticker)
            if len(selected) >= target_n:
                break

    # Truncar a exactamente target_n y asegurar unicidad
    selected = list(dict.fromkeys(selected))[:target_n]

    # Guardar selección
    if outputs_dir:
        df_out = pd.DataFrame({
            'ticker': list(rank.index),
            'score': score.reindex(rank.index).values,
            'z_mom': z_mom.reindex(rank.index).values,
            'z_neg_vol': z_neg_vol.reindex(rank.index).values,
            'z_neg_mdd': z_neg_mdd.reindex(rank.index).values,
            'selected': [t in selected for t in rank.index]
        })
        df_out.to_csv(os.path.join(outputs_dir, 'universe_selection.csv'), index=False)
        print(f"✅ Universo seleccionado guardado en {os.path.join(outputs_dir, 'universe_selection.csv')} ({len(selected)} activos)")

    return selected


def select_universe_from_zscore_file(zscore_file: str,
                                     top_n: int = 20,
                                     outputs_dir: str = None) -> list:
    """Selecciona top-N tickers por Z_Score desde un CSV estático (data/z_score.csv)."""
    print(f"🔎 Selección por archivo Z-Score: {zscore_file} (top {top_n})")
    try:
        df = pd.read_csv(zscore_file, sep=';', decimal=',')
    except Exception as e:
        raise RuntimeError(f"No se pudo leer el archivo Z-Score: {e}")

    if 'Ticker' not in df.columns or 'Z_Score' not in df.columns:
        raise ValueError("El archivo Z-Score debe contener columnas 'Ticker' y 'Z_Score'")

    df = df[df['Ticker'] != 'NASDAQ_100']
    df = df.dropna(subset=['Z_Score'])
    df = df.sort_values(by='Z_Score', ascending=False)
    top = df.head(top_n).copy()
    selected = top['Ticker'].astype(str).tolist()

    if outputs_dir:
        out_path = os.path.join(outputs_dir, 'universe_selection.csv')
        df_out = top[['Ticker', 'Z_Score']].copy()
        df_out.columns = ['ticker', 'score']
        df_out['selected'] = True
        df_out.to_csv(out_path, index=False)
        print(f"✅ Universo Z-Score guardado en {out_path} ({len(selected)} activos)")

    return selected


# --- Funciones Auxiliares de Análisis ---
def _print_wilcoxon_result(results_df, col1, col2, alpha=0.05):
    print(f"\n--- Comparación: {col1} vs {col2} ---")
    try:
        stat, p_value = wilcoxon(results_df[col1], results_df[col2])
        print(f"P-valor: {p_value:.6f}")
        if p_value < alpha:
            print(f"Conclusión: La diferencia es ESTADÍSTICAMENTE SIGNIFICATIVA.")
            winner = col2 if results_df[col2].mean() < results_df[col1].mean() else col1
            print(f"🏆 El algoritmo '{winner}' es superior.")
        else:
            print(f"Conclusión: La diferencia NO es estadísticamente significativa.")
            print("⚖️  Ambos algoritmos muestran un rendimiento similar.")
    except ValueError as e:
        print(f"Advertencia: No se pudo realizar el test de Wilcoxon ({e}).")


def _print_portfolio(name, weights, tickers, threshold=0.01):
    print(f"\n--- Portafolio Óptimo: {name} ---")
    weights = np.array(weights)
    if np.sum(weights) <= 1e-9:
        print("  El portafolio está vacío o los pesos son insignificantes.")
        print("-" * (28 + len(name)))
        return
    normalized_weights = weights / np.sum(weights)
    portfolio = pd.Series(normalized_weights, index=tickers).sort_values(ascending=False)
    portfolio_filtered = portfolio[portfolio >= threshold]
    if portfolio_filtered.empty:
        print(f"  Sin asignaciones significativas (todos los pesos < {threshold:.0%}).")
    else:
        print(f"  Mostrando activos con peso >= {threshold:.0%}:")
        for ticker, weight in portfolio_filtered.items():
            print(f"  {ticker:<6}: {weight:.2%}")
    print("-" * 20)
    print(f"  Suma de pesos mostrados: {portfolio_filtered.sum():.2%}")
    print(f"  Suma total del portafolio: {portfolio.sum():.2%}")
    print(f"  Activos mostrados: {len(portfolio_filtered)}/{len(tickers)}")
    significant_weights = np.sum(normalized_weights > 0.005)
    print(f"  Cardinalidad (>0.5%): {significant_weights} activos")
    print("-" * (28 + len(name)))


def analyze_cardinality_performance(best_portfolios, prices, benchmark_returns):
    print("\n\n🎯 ANÁLISIS DE CARDINALIDAD Y EFICIENCIA")
    print("-" * 50)
    cardinality_results = {}
    for name, weights in best_portfolios.items():
        normalized_weights = np.array(weights) / np.sum(weights)
        daily_asset_returns = prices.pct_change().dropna()
        portfolio_returns = pd.Series(daily_asset_returns.dot(normalized_weights), name=name)
        sortino = qs.stats.sortino(portfolio_returns)
        max_dd = qs.stats.max_drawdown(portfolio_returns)
        hhi = np.sum(normalized_weights ** 2)
        significant_weights = np.sum(normalized_weights > 0.005)
        min_significant_weight = np.min(normalized_weights[normalized_weights > 0.005]) if significant_weights > 0 else 0.0
        cardinality_results[name] = {
            'cardinality': significant_weights,
            'max_weight': np.max(normalized_weights),
            'min_significant_weight': min_significant_weight,
            'hhi': hhi,
            'sortino': sortino,
            'max_drawdown': max_dd
        }
    results_df = pd.DataFrame(cardinality_results).T
    results_df.index.name = 'Algoritmo'
    print("📊 MÉTRICAS DE CARDINALIDAD:")
    print(results_df.round(4).to_markdown())
    print("\n🔍 ANÁLISIS DE EFICIENCIA:")
    print("Algoritmo con menor cardinalidad:", results_df['cardinality'].idxmin())
    print("Algoritmo con mayor concentración (HHI):", results_df['hhi'].idxmax())
    print("Algoritmo con mejor Sortino/Cardinalidad:", 
          (results_df['sortino'] / results_df['cardinality']).idxmax())
    return results_df


def analyze_performance_metrics(best_portfolios, prices, benchmark_returns):
    print("\n\n📊 ANÁLISIS DE MÉTRICAS DE DESEMPEÑO")
    print("-" * 50)
    portfolio_returns = {}
    for name, weights in best_portfolios.items():
        normalized_weights = np.array(weights) / np.sum(weights)
        daily_asset_returns = prices.pct_change().dropna()
        portfolio_returns[name] = pd.Series(daily_asset_returns.dot(normalized_weights), name=name)
    reference_key = next(iter(portfolio_returns))
    aligned_benchmark = benchmark_returns.reindex(portfolio_returns[reference_key].index).ffill().bfill()
    metrics = ['Sortino Ratio', 'Max Drawdown', 'Jensen Alpha (anual)', 'Omega Ratio']
    results_df = pd.DataFrame(index=metrics, columns=best_portfolios.keys())
    results_df.index.name = 'Métrica'
    for name, p_returns in portfolio_returns.items():
        p_returns = p_returns.fillna(0).astype(float)
        results_df.loc['Sortino Ratio', name] = qs.stats.sortino(p_returns)
        results_df.loc['Max Drawdown', name] = qs.stats.max_drawdown(p_returns)
        greeks = qs.stats.greeks(p_returns, benchmark=aligned_benchmark)
        results_df.loc['Jensen Alpha (anual)', name] = greeks['alpha']
        results_df.loc['Omega Ratio', name] = qs.stats.omega(p_returns)
    results_transposed = results_df.T
    results_transposed.index.name = 'Algoritmo'
    print(results_transposed.round(4).to_markdown())
    print("\n* Jensen Alpha se calcula contra el índice NASDAQ Composite (^IXIC).")
    print("* Un Alpha > 0 indica un rendimiento superior al esperado para el nivel de riesgo.")
    return results_transposed


# --- Ejecución del Backtest (COVID) ---
def _load_regime_params(regime: str, n_assets: int) -> dict:
    """Carga parámetros por algoritmo desde final_adaptive_parameters.json y computa max_trials si aplica."""
    module_root = project_root
    params_path = os.path.join(module_root, 'src', 'optimization', 'final_adaptive_parameters.json')
    with open(params_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if regime not in data:
        raise ValueError(f"Regimen '{regime}' no encontrado en final_adaptive_parameters.json")
    reg = data[regime]

    def with_trials(p: dict) -> dict:
        p = dict(p)
        factor = p.pop('max_trials_factor', None)
        if factor is not None:
            nb = p.get('numb_bees', 20)
            p['max_trials'] = int(max(1, factor * nb * n_assets))
        return p

    return {
        'ABC_Original': with_trials(reg.get('ABC_Original', {})),
        'ABC_FA_Bacanin': with_trials(reg.get('ABC_FA_Bacanin', {})),
        'ABC_FA_Scout': with_trials(reg.get('ABC_FA_Scout', {})),
        'ABC_Scout_Gravitacional': with_trials(reg.get('ABC_Scout_Gravitacional', {})),
    }


def run_backtest_for_period(start_date: str, end_date: str, period_slug: str, regime: str = 'CRISIS', n_executions: int = 20, stock_picking: str = 'dynamic'):
    print(f"\n📊 Cargando datos del período: {start_date} a {end_date} ({period_slug})...")

    # --- Outputs (estructurados por carpetas) ---
    base_dir = os.path.join(project_root, 'outputs', 'backtests', period_slug)
    summaries_dir = os.path.join(base_dir, 'summaries')
    weights_dir = os.path.join(base_dir, 'weights')
    metrics_dir = os.path.join(base_dir, 'metrics')
    cardinality_dir = os.path.join(base_dir, 'cardinality')
    stats_dir = os.path.join(base_dir, 'stats')
    selection_dir = os.path.join(base_dir, 'selection')
    for d in [summaries_dir, weights_dir, metrics_dir, cardinality_dir, stats_dir, selection_dir]:
        os.makedirs(d, exist_ok=True)

    # Selección del universo (N=20) según modo indicado
    prices_file = os.path.join(project_root, "data", "raw", "nasdaq_prices_2000_2025.csv")
    zscore_file = os.path.join(project_root, "data", "z_score.csv")
    if stock_picking == 'dynamic':
        selected_tickers = select_universe_by_zscores(
            prices_file=prices_file,
            start_date=start_date,
            lookback_days=252,
            gap_days=21,
            min_days_pre=180,
            target_n=20,
            corr_threshold=0.8,
            outputs_dir=selection_dir
        )
    elif stock_picking == 'zscore_file':
        selected_tickers = select_universe_from_zscore_file(
            zscore_file=zscore_file,
            top_n=20,
            outputs_dir=selection_dir
        )
    else:
        raise ValueError("stock_picking debe ser 'dynamic' o 'zscore_file'")
    if not selected_tickers or len(selected_tickers) < 5:
        raise RuntimeError("Selección de universo fallida o insuficiente; revise datos/ventana previa.")
    print(f"🧩 Universo final seleccionado: {len(selected_tickers)} tickers -> {selected_tickers}")

    try:
        # Cargar universo seleccionado en la ventana de test
        prices, mu, cov, benchmark_returns = get_portfolio_data(
            start_date=start_date,
            end_date=end_date,
            tickers=selected_tickers,
            min_days=50,
            fetch_benchmark=True
        )
        returns = calculate_returns(prices)
        print(f"✅ Datos cargados: {len(mu)} activos. Universo seleccionado por z-scores.")
    except Exception as e:
        print(f"❌ Error al cargar datos: {e}")
        return

    tickers = mu.index.tolist()
    n_assets = len(mu)

    # Parámetros de regularización para universos medianos (n≈20)
    lambda_l1 = 5e-4
    lambda_cardinality_eff = 0.008 * (n_assets / 20.0)
    card_threshold = 0.01  # 1% coherente con definición de significancia

    objective_func = lambda w: utility_objective_with_cardinality(
        w, returns, mu, 
        lambda_cvar=0.7, 
        lambda_l1=lambda_l1,
        lambda_cardinality=lambda_cardinality_eff,
        alpha=0.99, 
        target_cardinality=10,  # Alinear con k_top
        cardinality_threshold=card_threshold
    )

    equally_weighted_portfolio = np.ones(n_assets) / n_assets
    ew_fitness = objective_func(equally_weighted_portfolio)
    print(f"📊 Benchmark Equally Weighted fitness: {ew_fitness:.6f}")

    lower = [0.0] * n_assets
    upper = [1.0] * n_assets

    # --- PARÁMETROS ÓPTIMOS POR REGIMEN ---
    fixed_params = {'verbose': False}
    regime_params = _load_regime_params(regime=regime, n_assets=n_assets)

    original_params = {**fixed_params, **regime_params['ABC_Original']}
    bacanin_params = {**fixed_params, **regime_params['ABC_FA_Bacanin']}
    scout_params = {**fixed_params, **regime_params['ABC_FA_Scout']}
    gravitacional_params = {**fixed_params, **regime_params['ABC_Scout_Gravitacional']}

    results = {
        'ABC_Original': [], 
        'ABC_FA_Bacanin': [], 
        'ABC_FA_Scout': [],
        'ABC_Scout_Gravitacional': [],
        'PMVG_CVX': [],
        'Equally_Weighted': []
    }
    seeds = [random.randint(0, 10000) for _ in range(n_executions)]

    start_time = time.time()
    print(f"\n🚀 Ejecutando backtest {n_executions} veces cada algoritmo...")

    for i in range(n_executions):
        seed = seeds[i]

        abc_original = ABC_BeeHive(lower, upper, objective_func, seed=seed, **original_params)
        abc_original.run()
        weights, fitness = abc_original.get_best_solution()
        results['ABC_Original'].append((fitness, weights))

        abc_fa = ABC_FA_Bacanin(lower, upper, objective_func, seed=seed, **bacanin_params)
        abc_fa.run()
        weights, fitness = abc_fa.get_best_solution()
        results['ABC_FA_Bacanin'].append((fitness, weights))

        abc_fa_scout = ABC_FA_Scout(lower, upper, objective_func, seed=seed, **scout_params)
        print(f"   ABC_FA_Scout - Parámetros: b0={scout_params.get('b0')}, gamma={scout_params.get('gamma')}, alpha={scout_params.get('alpha')}")
        abc_fa_scout.run()
        weights, fitness = abc_fa_scout.get_best_solution()
        results['ABC_FA_Scout'].append((fitness, weights))

        abc_gravitacional = ABC_Scout_Gravitacional(lower, upper, objective_func, seed=seed, **gravitacional_params)
        print(f"   ABC_Scout_Gravitacional - Parámetros: G={gravitacional_params.get('G')}, alpha={gravitacional_params.get('alpha')}")
        abc_gravitacional.run()
        weights, fitness = abc_gravitacional.get_best_solution()
        results['ABC_Scout_Gravitacional'].append((fitness, weights))

        # PMVG (determinístico). Para comparabilidad, usa el mismo objetivo
        pmvg = PMVG_CVX(lower, upper, objective_func, mu=mu.values, cov=cov.values)
        pmvg.run()
        weights, fitness = pmvg.get_best_solution()
        results['PMVG_CVX'].append((fitness, weights))

        results['Equally_Weighted'].append((ew_fitness, equally_weighted_portfolio))

        print(f"   Run {i+1}/{n_executions} completado...")
        print(f"   - ABC_FA_Scout fitness: {results['ABC_FA_Scout'][-1][0]:.6f}")
        print(f"   - ABC_Scout_Gravitacional fitness: {results['ABC_Scout_Gravitacional'][-1][0]:.6f}")
        print(f"   - Equally_Weighted fitness: {ew_fitness:.6f} (benchmark)")
        print(f"   - PMVG_CVX fitness: {results['PMVG_CVX'][-1][0]:.6f}")

    end_time = time.time()
    print(f"✅ Backtest completado en {end_time - start_time:.2f} segundos.")

    objective_values = {alg: [res[0] for res in results[alg]] for alg in results}
    results_df = pd.DataFrame(objective_values)
    best_portfolios_raw = {alg: min(results[alg], key=lambda item: item[0])[1] for alg in results}

    # Usar únicamente portafolios RAW (sin poda Top-k)
    best_portfolios = {k: np.array(v) / np.sum(v) for k, v in best_portfolios_raw.items()}

    # Guardar resultados de objetivos
    results_df.to_csv(os.path.join(stats_dir, 'objective_values.csv'), index=False)
    results_df.describe().to_csv(os.path.join(stats_dir, 'objective_describe.csv'))

    print("\n\n📈 ANÁLISIS ESTADÍSTICO DEL BACKTEST (CRISIS)")
    print("-" * 50)
    print("Estadísticas Descriptivas (Mejor valor objetivo):")
    print(results_df.describe().loc[['mean', 'std', 'min', 'max']].round(6))

    # Wilcoxon sobre Sortino por seed (no sobre fitness)
    print("\n--- Pruebas de Significancia Estadística (Wilcoxon sobre Sortino por seed) ---")
    # Construir sortinos por seed para cada algoritmo
    daily_asset_returns = prices.pct_change().dropna()
    sortino_per_seed = {}
    for alg, run_list in results.items():
        seed_sortinos = []
        for fitness, w in run_list:
            w_norm = np.array(w) / (np.sum(w) if np.sum(w) > 1e-12 else 1.0)
            p_returns = pd.Series(daily_asset_returns.dot(w_norm), name=alg).fillna(0).astype(float)
            seed_sortinos.append(qs.stats.sortino(p_returns))
        sortino_per_seed[alg] = seed_sortinos
    sortino_df = pd.DataFrame(sortino_per_seed)
    sortino_df.to_csv(os.path.join(stats_dir, 'sortino_per_seed.csv'), index=False)

    comparisons = [
        ('ABC_Original', 'ABC_FA_Bacanin'),
        ('ABC_Original', 'ABC_FA_Scout'),
        ('ABC_Original', 'ABC_Scout_Gravitacional'),
        ('ABC_Original', 'PMVG_CVX'),
        ('ABC_FA_Bacanin', 'ABC_FA_Scout'),
        ('ABC_FA_Bacanin', 'ABC_Scout_Gravitacional'),
        ('ABC_FA_Bacanin', 'PMVG_CVX'),
        ('ABC_FA_Scout', 'ABC_Scout_Gravitacional'),
        ('ABC_FA_Scout', 'PMVG_CVX'),
        ('PMVG_CVX', 'ABC_Scout_Gravitacional'),
        ('Equally_Weighted', 'ABC_Original'),
        ('Equally_Weighted', 'ABC_FA_Bacanin'),
        ('Equally_Weighted', 'ABC_FA_Scout'),
        ('Equally_Weighted', 'ABC_Scout_Gravitacional'),
        ('Equally_Weighted', 'PMVG_CVX'),
    ]
    wilcoxon_rows = []
    for a, b in comparisons:
        try:
            stat, p_value = wilcoxon(sortino_df[a], sortino_df[b])
            signif = p_value < 0.05
            winner = b if np.mean(sortino_df[b]) > np.mean(sortino_df[a]) else a
            wilcoxon_rows.append({'A': a, 'B': b, 'p_value': p_value, 'significant': signif, 'winner': winner, 'metric': 'Sortino'})
            print(f"\n--- Comparación: {a} vs {b} ---")
            print(f"P-valor: {p_value:.6f}")
            if signif:
                print("Conclusión: La diferencia es ESTADÍSTICAMENTE SIGNIFICATIVA.")
                print(f"🏆 El algoritmo '{winner}' es superior (Sortino).")
            else:
                print("Conclusión: La diferencia NO es estadísticamente significativa.")
                print("⚖️  Ambos algoritmos muestran un rendimiento similar (Sortino).")
        except ValueError as e:
            wilcoxon_rows.append({'A': a, 'B': b, 'p_value': np.nan, 'significant': False, 'winner': None, 'metric': 'Sortino'})
            print(f"Advertencia: No se pudo realizar el test de Wilcoxon ({e}).")
    wilcoxon_df = pd.DataFrame(wilcoxon_rows)
    wilcoxon_df.to_csv(os.path.join(stats_dir, 'wilcoxon_results.csv'), index=False)

    print("\n\n🔍 ANÁLISIS DE LOS PORTAFOLIOS ÓPTIMOS (CALIBRADOS)")
    print("-" * 50)
    for alg_name, weights in best_portfolios.items():
        if alg_name == 'Equally_Weighted':
            print(f"\n--- Portafolio Benchmark: {alg_name} ---")
            print("  📊 Portafolio igualmente ponderado (1/N strategy)")
            print(f"  Peso por activo: {100/len(tickers):.2f}% ({len(tickers)} activos)")
            print(f"  Cardinalidad: {len(tickers)} activos")
            print(f"  HHI: {1/len(tickers):.4f}")
            print("-" * (29 + len(alg_name)))
        else:
            _print_portfolio(alg_name, weights, tickers)

    # Métricas RAW
    perf_df_raw = analyze_performance_metrics(best_portfolios, prices, benchmark_returns)
    card_df_raw = analyze_cardinality_performance(best_portfolios, prices, benchmark_returns)

    # Guardar pesos de los mejores portafolios (RAW)
    for alg_name, weights in best_portfolios_raw.items():
        ws = pd.Series(np.array(weights) / np.sum(weights), index=tickers, name='weight')
        ws.to_frame().to_csv(os.path.join(weights_dir, f'best_weights_{alg_name}_raw.csv'))

    # Generar markdown consolidado
    md_lines = []
    md_lines.append(f"# Backtest — Resultados (Universo Seleccionado por Z-Score) — {period_slug}")
    md_lines.append("")
    if stock_picking == 'dynamic':
        md_lines.append("- Universo: selección ex-ante dinámica por precios (Momentum 12-1, -Vol, -MaxDD), N=20, diversificación por correlación (ρ<0.8)")
    else:
        md_lines.append("- Universo: top-20 por Z_Score desde data/z_score.csv (estático)")
    md_lines.append(f"- Ventana: {start_date} a {end_date}")
    md_lines.append(f"- Regimen aplicado: {regime}")
    md_lines.append(f"- Modo de stock picking: {stock_picking}")
    # Objetivo dinámico
    md_lines.append(
        f"- Función objetivo: retorno − {0.7:.2f}·CVaR (α={0.99:.2f}) − {lambda_l1:.1e}·L1 − λ_card·Card (λ_card={lambda_cardinality_eff:.4f}; threshold={card_threshold*100:.1f}%; target=10)"
    )
    md_lines.append(f"- Ejecuciones: {n_executions} seeds por algoritmo")
    md_lines.append("- Benchmark: Equally Weighted (1/N) y ^IXIC para Jensen Alpha")
    md_lines.append("")
    md_lines.append("## 1) Métricas de desempeño")
    md_lines.append(perf_df_raw.round(4).to_markdown())
    md_lines.append("")
    md_lines.append("## 2) Pruebas de significancia (Wilcoxon sobre Sortino)")
    md_lines.append(wilcoxon_df.round(6).to_markdown(index=False))
    md_lines.append("")
    md_lines.append("## 3) Cardinalidad y eficiencia")
    md_lines.append(card_df_raw.round(4).to_markdown())
    md_lines.append("")
    md_lines.append("## 4) Parámetros utilizados (por algoritmo)")
    # Mostrar params reales (sin 'verbose')
    def _clean(d):
        dd = dict(d)
        dd.pop('verbose', None)
        return dd
    md_lines.append(f"- ABC_Original: {json.dumps(_clean(original_params), ensure_ascii=False)}")
    md_lines.append(f"- ABC_FA_Bacanin: {json.dumps(_clean(bacanin_params), ensure_ascii=False)}")
    md_lines.append(f"- ABC_FA_Scout: {json.dumps(_clean(scout_params), ensure_ascii=False)}")
    md_lines.append(f"- ABC_Scout_Gravitacional: {json.dumps(_clean(gravitacional_params), ensure_ascii=False)}")
    md_lines.append(f"- PMVG_CVX: {{'type': 'convex_min_variance', 'constraints': 'long-only, sum=1'}}")
    md_lines.append("")
    md_lines.append("Reproducibilidad:")
    md_lines.append("- Script: `tests/test_calibrated_crisis_performance_v2.py`")
    md_lines.append("- Datos: `data/raw/nasdaq_prices_2000_2025.csv` + benchmark `^IXIC`")
    with open(os.path.join(summaries_dir, f'{period_slug}_summary.md'), 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))

    # Guardar métricas
    perf_df_raw.to_csv(os.path.join(metrics_dir, 'performance_metrics_raw.csv'))
    card_df_raw.to_csv(os.path.join(cardinality_dir, 'cardinality_metrics_raw.csv'))

    print("\n🎉 Backtest completado. Resultados guardados en:", base_dir)


if __name__ == "__main__":
    # Default: COVID-19 (CRISIS)
    run_backtest_for_period(start_date="2020-02-01", end_date="2020-07-30", period_slug="covid_2020", regime='CRISIS', n_executions=20)


