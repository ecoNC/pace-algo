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
# Expanded 2026-05-27 (Phase B prep, ANN-006 Mantra): wider coverage to test
# universal generalization across asset classes.
#
# Expanded 2026-05-28 per ANN-015 (V1 Training-Pool Expansion + Robustness
# Re-Validation): NZDUSD added to training pool, USDCAD added as new unseen
# hold-out symbol. Goal: NB14f-v2 re-run with broader regime coverage to test
# whether behavioral stability failures (signal_frequency_cv 0.45-0.77 across
# profiles) were a pool-width artifact vs. a deeper architectural issue.

# FX — sauber getrennt in Train vs Hold-Out
FX_TRAIN_SYMBOLS    = ["EURUSD", "USDJPY", "NZDUSD"]                       # validation training pool (ANN-015: +NZDUSD)
FX_HOLDOUT_SYMBOLS  = ["GBPUSD", "AUDUSD", "USDCHF", "USDCAD"]             # validation hold-out (ANN-015: +USDCAD)
FX_SYMBOLS          = FX_TRAIN_SYMBOLS + FX_HOLDOUT_SYMBOLS

# ── Supported-Pairs Lock (ANN-020, 2026-06-01) ─────────────────────────────────
# Scientifically locked via scripts/supported_pairs.py (in-pool time-OOS + LOPO).
# Drives PRODUCT scope + production training recipe, NOT the validation split above.
FX_SUPPORTED_PAIRS        = ["USDJPY", "NZDUSD", "GBPUSD", "USDCHF", "USDCAD"]  # monoton, PF@q97>=1.3 & q99>=1.5, OOS-stabil
FX_CONDITIONAL_PAIRS      = ["AUDUSD"]                                          # nur Conservative/q99 (experimental, concept-shift)
FX_UNSUPPORTED_PAIRS      = ["EURUSD"]                                          # kein verlässlicher Edge (high-liquidity low-edge)
FX_PRODUCTION_TRAIN_PAIRS = FX_SUPPORTED_PAIRS + FX_CONDITIONAL_PAIRS           # production model trains in-pool on these

# Crypto — 24/7 markets, different volatility regimes
CRYPTO_SYMBOLS      = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"]

# Commodities — Gold + Silver + Oil (Silver/Oil via Polygon, see INDEX_SYMBOLS_FUTURE)
METAL_SYMBOLS       = ["XAUUSD"]                                 # Dukascopy

# Indices / ETFs — institutional flow, macro-driven (REQUIRES Polygon.io API, Phase B+)
INDEX_SYMBOLS_FUTURE = ["SPY", "QQQ", "DIA", "IWM", "USO", "XAGUSD"]

# Legacy hold-out aliases (used by NB12 + earlier pipelines)
DEV_HOLDOUT_SYMBOLS   = ["SOLUSDT", "GBPUSD"]      # can be peeked at during development
FINAL_HOLDOUT_SYMBOLS = ["QQQ"]                    # blind until final evaluation

# Phase 1 training pool (legacy — used by NB05–NB12)
PHASE1_TRAINING_SYMBOLS = (
    [s for s in CRYPTO_SYMBOLS if s not in DEV_HOLDOUT_SYMBOLS] +
    [s for s in FX_SYMBOLS if s not in DEV_HOLDOUT_SYMBOLS] +
    METAL_SYMBOLS
)

# Asset-Group dict — used by NB13+ for per-class evaluation + SHAP stability
ASSET_GROUPS = {
    "fx":          FX_SYMBOLS,
    "crypto":      CRYPTO_SYMBOLS,
    "commodities": METAL_SYMBOLS,
    "indices":     INDEX_SYMBOLS_FUTURE,   # gated by Polygon availability
}

# ---------------------------------------------------------------------------
# TIMEFRAMES
# ---------------------------------------------------------------------------
# Expanded 2026-05-27: PRIMARY_TIMEFRAMES now covers 5M/15M/30M/1H per Phase B plan.
# NB14 will systematically compare these. NB13 trains separate models per (asset_group, TF).
PRIMARY_TIMEFRAMES      = ["5m", "15m", "30m", "1h"]
PRIMARY_TIMEFRAMES_FAST = ["15m"]                  # for quick smoke-tests
HTF_CONTEXT_TIMEFRAMES  = ["1h", "4h"]             # used as shift(1) features in any LTF model

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

# ---------------------------------------------------------------------------
# PHASE B HYPOTHESIS THRESHOLDS (NB13 decision logic)
# ---------------------------------------------------------------------------
# Reference: /research/asset_generalization.md hypotheses H1–H6.
# These thresholds turn Phase B from "look at the numbers" into deterministic Decisions.
PHASE_B_THRESHOLDS = {
    # H1 — Universal-PF cost: how much PF does generalization actually cost?
    "h1_mean_pf_min":              1.4,   # mean across asset classes — TRUE if >= 1.4
    "h1_min_pf_per_class":         1.3,   # min single-asset-class PF for "no class breaks"

    # H5 — Consensus generalization across asset classes
    "h5_consensus_lift_threshold": 0.15,  # PF lift over LGBM-Alone, per asset class
    "h5_min_asset_classes":        3,     # of >=5 — needed for "generalizes" verdict

    # H6 — XGBoost-Lift generalization
    "h6_xgb_lift_threshold":       0.05,  # PF lift over LGBM, per asset class
    "h6_min_asset_classes":        4,     # of >=5 — needed for "switch to XGB" verdict

    # Statistical guardrails (avoid claims on too-few trades)
    "min_trades_per_tier_asset":   200,   # below this: "data insufficient", not "no edge"

    # Stability guardrails
    "max_stability_cv":            0.25,
}

# ---------------------------------------------------------------------------
# PHASE C THRESHOLDS — NB14 Multi-TF Deep Dive (FX-Modell, V1)
# ---------------------------------------------------------------------------
# Reference: /research/timeframe_comparisons.md hypotheses H1–H5.
# Produktorientierte Schwellen — Stability/Konsistenz/UX > Peak-PF.
# Per Nico-Direktive 2026-05-27.
PHASE_C_THRESHOLDS = {
    # H1 — 5m als V1-Default-TF
    "h1_min_premium_pf_holdout":   2.0,
    "h1_max_stability_cv":         0.20,
    "h1_max_drawdown":             0.18,
    "h1_min_trades_per_day":       3.0,   # premium tier, pro Symbol

    # H2 — 15m als "Conservative"-Profil
    "h2_min_premium_pf":           1.5,
    "h2_max_stability_cv":         0.15,
    "h2_min_trades_per_day":       1.0,

    # H3 — 30m/1h von V1 ausschließen
    "h3_exclude_threshold_pf":     1.5,   # OOS unter diesem PF → out

    # H4 — Pooled-Modell besser als Single-TF-Modell
    "h4_min_pooled_lift":          0.0,   # nicht schlechter
    "h4_required_tf_count":        3,     # in mind. 3 von 4 TFs gewinnen

    # H5 — Top-3%-Cutoff auf 1h reanimiert die Edge
    "h5_relaxed_cutoff_premium":   0.97,  # top 3% statt top 1%
    "h5_min_trades_per_year":      30,
}

# ---------------------------------------------------------------------------
# PRODUCT METRIC THRESHOLDS — NB14 (und alle folgenden Produkt-Notebooks)
# ---------------------------------------------------------------------------
# Nicht-Quant-Schwellen die Produktqualität (UX, Alert-Verhalten, Chart-Sauberkeit)
# bewerten. Hier gilt: lieber wenige aussagekräftige Signale als ein Alert-Sturm.
PRODUCT_METRIC_THRESHOLDS = {
    # Signal-Frequenz pro Tier — Erwartung "frequent enough to feel active,
    # selective enough to feel premium"
    "signals_per_day_premium_min":      1.0,    # min/symbol/Tag für Premium
    "signals_per_day_premium_max":      8.0,    # max — sonst Alert-Müdigkeit
    "signals_per_day_high_min":         3.0,
    "signals_per_day_high_max":         20.0,
    "signals_per_day_standard_max":     80.0,   # absolute Obergrenze gesamt

    # Trade Duration — wie lange läuft ein offener Trade?
    "trade_duration_min_bars":          3,      # < 3 = "scalp-spam", Pine-Boxes überladen
    "trade_duration_max_bars":          24,     # > 24 = Trade läuft zu lang, User verliert Fokus

    # Premium Signal Density — Anteil aller Bars die Premium-Signal sind
    "premium_density_max":              0.015,  # 1.5% — sonst nicht mehr "Premium"

    # Chart Cleanliness — wie viele aktive Boxes im sichtbaren 200-Bar-Fenster
    "max_boxes_visible_window":         8,      # Pine box-budget realistisch nutzen
    "max_overlapping_signals":          2,      # nicht mehr als 2 Signale gleichzeitig offen

    # Session Dependency — Edge sollte nicht in 1 Session konzentriert sein
    "max_signal_share_single_session":  0.65,   # max 65% aller Signale in einer Session

    # Pine UX Practicality — Pine-Budget für diesen TF
    "max_pine_ops_per_bar":             5000,   # hard Pine-Limit-Sicherheitspuffer
    "max_request_security_calls":       12,
}

# ---------------------------------------------------------------------------
# QUALITY ANCHOR (ANN-010) — Multi-Model-Gating
# ---------------------------------------------------------------------------
# Reference: docs/decisions/ANN-010-quality-anchor.md
# Jedes neue Modell (FX-V1, Crypto-V2, Indices-V2, Commodity-V2) MUSS diesen Check passieren.
QUALITY_ANCHOR = {
    "strict": {
        "min_premium_pf_oos":          1.5,
        "min_premium_pf_holdout":      1.4,
        "min_pf_per_symbol":           1.3,
        "max_stability_cv":            0.25,
        "min_pf_per_year":             1.2,
        "min_trades_per_year_tier":    30,
    },
    "soft_reference": {
        "fx_premium_pf_anchor":        2.0,
        "premium_wr_target":           0.60,
    },
    "deployment_action": {
        "all_strict_passed":  "auto-deploy candidate",
        "missing_1_strict":   "requires Nico explicit override",
        "missing_2plus":      "deployment blocked — re-research required",
    },
}
