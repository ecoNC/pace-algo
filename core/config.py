"""
Central configuration for PaceAlgo ML pipeline.

All hard-coded magic numbers, symbol lists, and budget constraints live here so they
can be reasoned about in one place.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data_cache" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data_cache" / "processed"
ARTIFACTS_MODELS = PROJECT_ROOT / "artifacts" / "models"
ARTIFACTS_REPORTS = PROJECT_ROOT / "artifacts" / "reports"
ARTIFACTS_PINE = PROJECT_ROOT / "artifacts" / "pine_exports"

# ---------------------------------------------------------------------------
# SYMBOL UNIVERSE
# ---------------------------------------------------------------------------
CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
FX_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY"]
METAL_SYMBOLS = ["XAUUSD"]
INDEX_SYMBOLS_FUTURE = ["SPY", "QQQ", "USO"]  # ETF proxies via Polygon (Phase 2)

# Hold-out sets (NEVER used for training)
DEV_HOLDOUT_SYMBOLS = ["SOLUSDT", "GBPUSD"]    # can be peeked at during development
FINAL_HOLDOUT_SYMBOLS = ["QQQ"]                 # blind until final evaluation

# Training universe (Phase 1, free data only)
PHASE1_TRAINING_SYMBOLS = (
    [s for s in CRYPTO_SYMBOLS if s not in DEV_HOLDOUT_SYMBOLS] +
    [s for s in FX_SYMBOLS if s not in DEV_HOLDOUT_SYMBOLS] +
    METAL_SYMBOLS
)

# ---------------------------------------------------------------------------
# TIMEFRAMES
# ---------------------------------------------------------------------------
PRIMARY_TIMEFRAMES = ["5m", "15m"]
HTF_CONTEXT_TIMEFRAMES = ["1h", "4h"]

# ---------------------------------------------------------------------------
# DATE RANGES
# ---------------------------------------------------------------------------
TRAIN_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
TRAIN_END = datetime(2024, 1, 1, tzinfo=timezone.utc)
VAL_END = datetime(2024, 7, 1, tzinfo=timezone.utc)
TEST_END = datetime(2026, 5, 1, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# TRIPLE BARRIER LABELING
# ---------------------------------------------------------------------------
TRIPLE_BARRIER_R_MULTIPLES = [1.5, 2.0, 2.5]  # to be optimized per asset cluster
TRIPLE_BARRIER_SL_ATR_MULT = 1.0
TRIPLE_BARRIER_TIME_LIMIT_BARS = 24  # 24 * 5min = 2 hours for 5M

# ---------------------------------------------------------------------------
# PINE BUDGET (hard limits — model rejected if exceeded)
# ---------------------------------------------------------------------------
PINE_BUDGET = {
    "max_trees":            30,
    "max_tree_depth":       3,
    "max_features_used":    15,    # post-SHAP reduction
    "max_operations_bar":   5000,  # Pine hard limit 9000 — keeps a safety buffer
    "max_request_security": 12,    # Pine hard limit 40
    "max_label_count":      500,
    "max_box_count":        500,
    "max_line_count":       500,
}

# ---------------------------------------------------------------------------
# ML HYPERPARAMETERS (starting defaults — will be Optuna-tuned)
# ---------------------------------------------------------------------------
LGBM_DEFAULTS = {
    "num_leaves":         7,        # max_depth 3 → max 8 leaves
    "max_depth":          3,
    "min_data_in_leaf":   200,
    "learning_rate":      0.05,
    "n_estimators":       30,
    "lambda_l2":          1.0,
    "feature_fraction":   0.8,
    "bagging_fraction":   0.8,
    "bagging_freq":       5,
}

XGB_DEFAULTS = {
    "max_depth":          3,
    "learning_rate":      0.05,
    "n_estimators":       30,
    "reg_lambda":         1.0,
    "subsample":          0.8,
    "colsample_bytree":   0.8,
}

LOGREG_DEFAULTS = {
    "penalty":            "l2",
    "C":                  0.1,
    "class_weight":       "balanced",
    "max_iter":           1000,
}

# ---------------------------------------------------------------------------
# CONFIDENCE TIER THRESHOLDS (will be optimized via Optuna)
# ---------------------------------------------------------------------------
TIER_THRESHOLDS = {
    "standard": 0.45,
    "high":     0.65,
    "premium":  0.80,
}

# ---------------------------------------------------------------------------
# ACCEPTANCE CRITERIA FOR V1.0 RELEASE
# ---------------------------------------------------------------------------
ACCEPTANCE_CRITERIA = {
    "min_pf_overall":       1.6,
    "min_sharpe_overall":   1.2,
    "max_dd_overall":       0.18,
    "min_pf_per_year":      1.4,
    "min_pf_per_asset":     1.4,
    "min_pf_long":          1.3,
    "min_pf_short":         1.3,
    "min_pf_holdout":       1.3,
}
