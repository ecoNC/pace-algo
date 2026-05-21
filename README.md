# PaceAlgo ML — Quantitative ML Pipeline for TradingView Indicator

Machine Learning pipeline that trains LightGBM / XGBoost / Logistic Regression models on multi-asset OHLCV data, validates them out-of-sample, and exports the trained model as a Pine Script v6 indicator for TradingView.

**Product target:** PaceAlgo — Invite-Only TradingView indicator ($39-49/mo subscription).

---

## Architecture

```
pace-algo/
├── core/                    # Platform-agnostic Python ML code
│   ├── data/                # Multi-source OHLCV fetchers
│   ├── features/            # Feature engineering (30+ features, ATR-normalized)
│   ├── labeling/            # Triple Barrier labeling
│   ├── train/               # Walk-Forward training (LGBM/XGB/LogReg)
│   ├── analysis/            # SHAP, calibration, regime stability
│   ├── models/              # Serialized model artifacts (.pkl)
│   └── export/              # Pine code generation
├── deploy_pine/             # Pine Script v6 output target
├── deploy_server/           # Future backend deployment (V2+)
├── notebooks/               # Colab notebooks — your monthly workflow
├── data_cache/              # Cached OHLCV (Parquet)
├── artifacts/               # Models, reports, generated Pine code
└── tests/                   # Unit tests + Pine compatibility checks
```

---

## Monthly Workflow (for Nico)

The pipeline is designed for monthly retraining in Google Colab. Each notebook is independently runnable.

| Step | Notebook | Time | Output |
|---|---|---|---|
| 1 | `01_fetch_data.ipynb` | ~10 min | Updated OHLCV cache |
| 2 | `02_feature_engineering.ipynb` | ~5 min | Feature matrices |
| 3 | `03_asset_clustering.ipynb` | ~2 min | Asset cluster assignments |
| 4 | `04_triple_barrier_labeling.ipynb` | ~3 min | Multi-R labels |
| 5 | `05_train_lgbm.ipynb` | ~15 min | LightGBM model + SHAP |
| 6 | `06_train_xgb.ipynb` | ~15 min | XGBoost model + SHAP |
| 7 | `07_train_logreg.ipynb` | ~3 min | LogReg baseline |
| 8 | `08_evaluate_ensemble.ipynb` | ~10 min | Multi-dimensional report |
| 9 | `09_export_pine.ipynb` | ~2 min | `pace_algo_v[X.Y].pine` file |

**Total monthly effort:** ~1 hour click-through in Colab.

---

## Architecture Principles

1. **Multi-Asset Training** — 11 symbols across crypto/FX/metals/indices
2. **Triple Barrier Labeling** (Marcos López de Prado)
3. **Walk-Forward Validation** + Hold-Out Asset Validation
4. **Isotonic Probability Calibration**
5. **SHAP-driven Feature Selection** (30 → 15 features)
6. **No-Trade Class** explicit in label space
7. **Multi-Timeframe Features** (current TF + 1H + 4H context)
8. **Two-Stage Regime Gating** (rule-based filter → ML decision)
9. **Asset-Class Detection** via K-Means clustering, NOT ticker strings
10. **Pine Budget Enforcement** — automated compatibility check

---

## Performance Targets (V1.0)

| Metric | Target | Acceptance |
|---|---|---|
| Profit Factor (OOS) | > 1.6 | mandatory |
| Sharpe Ratio | > 1.2 | mandatory |
| Max Drawdown | < 18% | mandatory |
| Min PF per year (2020-2024) | > 1.4 | mandatory |
| Min PF per asset class | > 1.4 | mandatory |
| Hold-Out (NDX) PF | > 1.3 | mandatory |

---

## Data Sources

### Phase 1 (free, current)
- **Binance API** — BTC, ETH, SOL (OHLCV + Funding + OI)
- **Dukascopy** — EURUSD, GBPUSD, USDJPY, XAUUSD
- **Yahoo Finance** — VIX, DXY (macro context)

### Phase 2 (later, $29/month)
- **Polygon.io** — SPY, QQQ, USO (US indices/commodities)

---

## Setup (one-time)

This repo is designed to be opened in Google Colab. No local Python install required.

1. Repo is at `github.com/ecoNC/pace-algo` (private)
2. In Colab: `File → Open Notebook → GitHub → ecoNC/pace-algo → notebooks/01_fetch_data.ipynb`
3. Notebook auto-installs dependencies, fetches data, saves results to Google Drive

---

## Pine Budget (hard limits)

```python
PINE_BUDGET = {
    'max_trees':            30,    # per model
    'max_tree_depth':       3,     # max 7 leaves/tree
    'max_features_used':    15,    # after SHAP reduction
    'max_operations_bar':   5000,  # Pine limit 9000 — safety buffer
    'max_request_security': 12,    # Pine limit 40
}
```

Every trained model is automatically validated against this budget before being approved for Pine export.

---

## License

Proprietary — © 2026 Nico Flotz. All rights reserved.
