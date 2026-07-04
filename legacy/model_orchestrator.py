"""
Model Orchestrator: ejecuta backtests multi-período usando run_backtest_for_period.
"""
import sys
import os
import argparse
import time

# Asegurar que el proyecto esté en sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from tests.test_calibrated_crisis_performance_v2 import run_backtest_for_period

# Periodos por defecto (crisis)
DEFAULT_PERIODS = {
    # COVID-19
    "covid_2020": ("2020-02-01", "2020-07-30"),
    # Crisis Financiera Global (GFC)
    "gfc_2007_2009": ("2007-10-01", "2009-03-30"),
    # Estabilidad 2023
    "2023_stability": ("2023-01-01", "2024-12-31"),
    # Guerra Rusia-Ucrania (choque 2022)
    "war_2022": ("2022-02-01", "2022-08-01")
}

# Regimen por defecto para cada periodo (puede personalizarse)
DEFAULT_REGIMES = {
    "covid_2020": "CRISIS",
    "gfc_2007_2009": "CRISIS",
    "2023_stability": "STABLE_GROWTH",
    "war_2022": "UNCERTAINTY",
}

def parse_args():
    parser = argparse.ArgumentParser(description="Orquestador de backtests multi-período")
    parser.add_argument(
        "--periods",
        nargs="*",
        default=list(DEFAULT_PERIODS.keys()),
        help=f"Slugs de periodos a ejecutar (default: {list(DEFAULT_PERIODS.keys())})",
    )
    parser.add_argument("--n", type=int, default=20, help="Número de ejecuciones (seeds) por periodo")
    parser.add_argument("--regime", type=str, default=None, help="Regimen a aplicar (CRISIS, STABLE_GROWTH, UNCERTAINTY). Si no se especifica, usa DEFAULT_REGIMES por periodo.")
    parser.add_argument(
        "--stock-picking",
        type=str,
        choices=["dynamic", "zscore_file"],
        default="zscore_file",
        help="Método de selección de universo: 'dynamic' (ventana previa por precios) o 'zscore_file' (top-20 en data/z_score.csv)",
    )
    return parser.parse_args()


def fmt_duration(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m {s}s"


def main():
    args = parse_args()
    to_run = []
    for slug in args.periods:
        if slug not in DEFAULT_PERIODS:
            print(f"⚠️ Periodo desconocido: {slug}. Skipping.")
            continue
        start_date, end_date = DEFAULT_PERIODS[slug]
        regime = args.regime if args.regime else DEFAULT_REGIMES.get(slug, "CRISIS")
        to_run.append((slug, start_date, end_date, regime))

    if not to_run:
        print("❌ No hay periodos válidos para ejecutar.")
        sys.exit(1)

    print(f"🚀 Ejecutando {len(to_run)} periodos: {[slug for slug, _, _, _ in to_run]}")

    total_t0 = time.time()
    per_period_times = []

    for slug, start, end, regime in to_run:
        print(f"\n⏱️  Iniciando periodo {slug} [{start} → {end}] (regimen={regime})...")
        t0 = time.time()
        try:
            run_backtest_for_period(start_date=start, end_date=end, period_slug=slug, regime=regime, n_executions=args.n, stock_picking=args.stock_picking)
        except Exception as e:
            print(f"❌ Error ejecutando periodo {slug}: {e}")
        t1 = time.time()
        elapsed = t1 - t0
        per_period_times.append((slug, elapsed))
        print(f"✅ Periodo {slug} finalizado en {fmt_duration(elapsed)} ({elapsed:.2f}s)")

    total_elapsed = time.time() - total_t0

    print("\n📊 Resumen de tiempos:")
    for slug, secs in per_period_times:
        print(f"  - {slug}: {fmt_duration(secs)} ({secs:.2f}s)")
    print(f"🧮 Tiempo total: {fmt_duration(total_elapsed)} ({total_elapsed:.2f}s)")


if __name__ == "__main__":
    main()
