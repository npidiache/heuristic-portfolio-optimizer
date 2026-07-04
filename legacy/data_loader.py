"""
Data Loader para Datos NASDAQ
============================

Módulo para cargar y procesar datos del NASDAQ descargados previamente.
"""

import pandas as pd
import numpy as np
import os
from typing import Optional, List, Tuple
from datetime import datetime
import yfinance as yf

def get_benchmark_returns(start_date: str, 
                          end_date: str, 
                          ticker: str = "^IXIC", # NASDAQ Composite
                          verbose: bool = True) -> pd.Series:
    """
    Descarga los retornos diarios de un benchmark (e.g., índice) desde Yahoo Finance.

    Args:
        start_date (str): Fecha de inicio (YYYY-MM-DD).
        end_date (str): Fecha de fin (YYYY-MM-DD).
        ticker (str): Ticker del benchmark en Yahoo Finance.
        verbose (bool): Si es True, imprime mensajes de estado.

    Returns:
        pd.Series: Serie de retornos logarítmicos diarios del benchmark.
    """
    if verbose: print(f"📥 Descargando datos del benchmark '{ticker}'...")
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            raise ValueError(f"No se encontraron datos para el ticker '{ticker}' en el período especificado.")
        
        prices = data['Close']
        returns = np.log(prices / prices.shift(1)).dropna()
        if verbose: print(f"✅ Retornos del benchmark '{ticker}' cargados: {len(returns)} días.")
        return returns
    except Exception as e:
        print(f"❌ Error al descargar datos del benchmark: {e}")
        return pd.Series(dtype=float)


def load_nasdaq_data(prices_file: str, 
                    start_date: Optional[str] = None, 
                    end_date: Optional[str] = None, 
                    tickers: Optional[List[str]] = None,
                    min_days: int = 1000,
                    verbose: bool = True) -> pd.DataFrame:
    """
    Carga datos del NASDAQ para uso en otros scripts
    
    Args:
        prices_file (str): Ruta al archivo de precios
        start_date (str): Fecha de inicio (YYYY-MM-DD, opcional)
        end_date (str): Fecha de fin (YYYY-MM-DD, opcional)
        tickers (list): Lista de tickers específicos (opcional)
        min_days (int): Mínimo número de días requeridos por ticker
    
    Returns:
        pd.DataFrame: Datos de precios filtrados
    
    Raises:
        FileNotFoundError: Si el archivo no existe
    """
    if not os.path.exists(prices_file):
        raise FileNotFoundError(f"Archivo no encontrado: {prices_file}")
    
    if verbose: print(f"📂 Cargando datos desde: {prices_file}")
    
    # Cargar datos
    prices = pd.read_csv(prices_file, index_col=0)
    # Convertir índice a datetime de manera segura
    prices.index = pd.to_datetime(prices.index.str[:10])  # Solo tomar YYYY-MM-DD
    
    if verbose: print(f"📊 Datos originales: {prices.shape[0]} días x {prices.shape[1]} tickers")
    
    # Filtrar por fechas
    if start_date:
        start_date = pd.to_datetime(start_date)
        prices = prices[prices.index >= start_date]
        if verbose: print(f"📅 Filtrado desde: {start_date}")
    
    if end_date:
        end_date = pd.to_datetime(end_date)
        prices = prices[prices.index <= end_date]
        if verbose: print(f"📅 Filtrado hasta: {end_date}")
    
    # Filtrar por tickers
    if tickers:
        available_tickers = [t for t in tickers if t in prices.columns]
        missing_tickers = [t for t in tickers if t not in prices.columns]
        if missing_tickers and verbose:
            print(f"⚠️ Tickers no encontrados: {missing_tickers}")
        prices = prices[available_tickers]
        if verbose: print(f"🏢 Filtrado por {len(available_tickers)} tickers específicos")
    
    # Filtrar tickers con pocos datos
    if min_days > 0:
        valid_tickers = []
        for ticker in prices.columns:
            if prices[ticker].notna().sum() >= min_days:
                valid_tickers.append(ticker)
        
        removed_tickers = set(prices.columns) - set(valid_tickers)
        if removed_tickers and verbose:
            print(f"⚠️ Removidos {len(removed_tickers)} tickers con < {min_days} días")
        
        prices = prices[valid_tickers]
    
    if verbose:
        print(f"📊 Datos finales: {prices.shape[0]} días x {prices.shape[1]} tickers")
        print(f"📅 Período: {prices.index.min()} a {prices.index.max()}")
    
    return prices

def calculate_returns(prices: pd.DataFrame, 
                     method: str = 'log', 
                     fill_method: str = 'ffill',
                     verbose: bool = True) -> pd.DataFrame:
    """
    Calcula retornos a partir de precios
    
    Args:
        prices (pd.DataFrame): DataFrame con precios
        method (str): 'log' para retornos logarítmicos, 'simple' para retornos simples
        fill_method (str): Método para llenar valores nulos ('ffill', 'bfill', 'drop')
    
    Returns:
        pd.DataFrame: DataFrame con retornos
    """
    # Llenar valores nulos
    if fill_method == 'ffill':
        prices = prices.ffill()
    elif fill_method == 'bfill':
        prices = prices.fillna(method='bfill')
    elif fill_method == 'drop':
        prices = prices.dropna()
    
    # Calcular retornos
    if method == 'log':
        returns = np.log(prices / prices.shift(1))
    elif method == 'simple':
        returns = (prices - prices.shift(1)) / prices.shift(1)
    else:
        raise ValueError("method debe ser 'log' o 'simple'")
    
    # Remover primera fila (NaN)
    returns = returns.dropna()
    
    if verbose:
        print(f"📈 Retornos calculados: {returns.shape[0]} días x {returns.shape[1]} tickers")
        print(f"📊 Método: {method}")
    
    return returns

def calculate_moments(returns: pd.DataFrame, verbose: bool = True) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Calcula momentos (retorno esperado y matriz de covarianza)
    
    Args:
        returns (pd.DataFrame): DataFrame con retornos
    
    Returns:
        Tuple[pd.Series, pd.DataFrame]: (retornos esperados, matriz de covarianza)
    """
    # Retornos esperados (promedio)
    mu = returns.mean()
    
    # Matriz de covarianza
    cov = returns.cov()
    
    if verbose:
        print(f"📊 Momentos calculados:")
        print(f"   📈 Retorno promedio: {mu.mean():.6f}")
        print(f"   📊 Volatilidad promedio: {np.sqrt(np.diag(cov)).mean():.6f}")
    
    return mu, cov

def get_portfolio_data(start_date: str = "2015-01-01",
                      end_date: str = "2024-01-01",
                      tickers: Optional[List[str]] = None,
                      min_days: int = 1000,
                      fetch_benchmark: bool = False,
                      verbose: bool = True) -> Tuple:
    """
    Función conveniente para obtener datos de portafolio listos para optimización.

    Args:
        start_date (str): Fecha de inicio.
        end_date (str): Fecha de fin.
        tickers (list): Lista de tickers específicos.
        min_days (int): Mínimo días requeridos.
        fetch_benchmark (bool): Si es True, también descarga los retornos del NASDAQ.
        verbose (bool): Si es True, imprime mensajes de estado.

    Returns:
        Tuple:
            - prices (pd.DataFrame): Precios de los activos.
            - mu (pd.Series): Retornos esperados.
            - cov (pd.DataFrame): Matriz de covarianza.
            - benchmark_returns (pd.Series, opcional): Retornos del benchmark.
    """
    # Construir ruta absoluta al archivo de datos para evitar errores de CWD
    module_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(module_dir))
    prices_file = os.path.join(project_root, "data", "raw", "nasdaq_prices_2000_2025.csv")
    
    # Cargar precios
    prices = load_nasdaq_data(prices_file, start_date, end_date, tickers, min_days, verbose=verbose)
    
    # Calcular retornos
    returns = calculate_returns(prices, verbose=verbose)
    
    # Calcular momentos
    mu, cov = calculate_moments(returns, verbose=verbose)
    
    # Llenar valores faltantes (e.g., por días festivos) usando el último valor válido
    prices = prices.ffill()
    
    if fetch_benchmark:
        benchmark_returns = get_benchmark_returns(start_date, end_date, verbose=verbose)
        return prices, mu, cov, benchmark_returns
        
    return prices, mu, cov

def validate_portfolio_data(prices: pd.DataFrame, 
                          mu: pd.Series, 
                          cov: pd.DataFrame) -> bool:
    """
    Valida que los datos de portafolio sean consistentes
    
    Args:
        prices (pd.DataFrame): Precios
        mu (pd.Series): Retornos esperados
        cov (pd.DataFrame): Matriz de covarianza
    
    Returns:
        bool: True si los datos son válidos
    """
    try:
        # Verificar dimensiones
        n_assets = len(prices.columns)
        assert len(mu) == n_assets, f"mu tiene {len(mu)} elementos, se esperaban {n_assets}"
        assert cov.shape == (n_assets, n_assets), f"cov tiene forma {cov.shape}, se esperaba ({n_assets}, {n_assets})"
        
        # Verificar que no hay valores infinitos
        assert not np.any(np.isinf(mu)), "mu contiene valores infinitos"
        assert not np.any(np.isinf(cov)), "cov contiene valores infinitos"
        
        # Verificar que cov es simétrica
        assert np.allclose(cov, cov.T), "Matriz de covarianza no es simétrica"
        
        # Verificar que cov es positiva definida (aproximadamente)
        eigenvals = np.linalg.eigvals(cov)
        min_eigenval = np.min(eigenvals)
        if min_eigenval < -1e-10:  # Tolerancia para errores numéricos
            print(f"⚠️ Matriz de covarianza no es positiva definida (min eigenval: {min_eigenval})")
            return False
        
        print("✅ Datos de portafolio validados correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error validando datos: {e}")
        return False

# Ejemplo de uso
if __name__ == "__main__":
    print("📋 EJEMPLO DE USO:")
    print("=" * 40)
    
    try:
        # Cargar datos
        prices, mu, cov = get_portfolio_data(
            start_date="2020-01-01",
            end_date="2024-01-01",
            tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'],
            min_days=500
        )
        
        # Validar datos
        is_valid = validate_portfolio_data(prices, mu, cov)
        
        if is_valid:
            print("🎉 Datos listos para optimización de portafolios!")
        else:
            print("⚠️ Los datos requieren limpieza adicional")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Asegúrate de ejecutar download_nasdaq_data.py primero") 