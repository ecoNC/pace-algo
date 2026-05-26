"""Validation helpers: Pine-equivalent computation + bit-exact checks."""

from .pine_simulator import (
    pine_ema, pine_rma, pine_sma, pine_atr, pine_rsi, pine_adx,
    pine_rolling_max, pine_rolling_min, pine_bb_width_pct,
    pine_atr_percentile, pine_realized_vol, pine_stoch_rsi_k,
    pine_roc, pine_macd_hist, pine_true_range,
    compute_features_pine,
    evaluate_tree, predict_forest_manual,
)

__all__ = [
    "pine_ema", "pine_rma", "pine_sma", "pine_atr", "pine_rsi", "pine_adx",
    "pine_rolling_max", "pine_rolling_min", "pine_bb_width_pct",
    "pine_atr_percentile", "pine_realized_vol", "pine_stoch_rsi_k",
    "pine_roc", "pine_macd_hist", "pine_true_range",
    "compute_features_pine",
    "evaluate_tree", "predict_forest_manual",
]
