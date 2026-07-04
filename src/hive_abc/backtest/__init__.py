"""Backtest engine over the frozen thesis periods and calibrated parameters.

Populated in Phase 3: `periods` (registry of the four volatility regimes),
`params` (loader for `regime_parameters.json`, the frozen per-regime
calibration), and `engine` (`BacktestConfig` / `run_backtest`).
"""
