# Model Validation Report

Generated: 2026-06-01T08-40-18Z

## 1. Structural audit + probability diagnostics (mean over seeds)

| variant | num_trees | eff_trees | uniq_probs | leaf_range | q90 | q97 | q99 | sep90-99 | ECE |
|---|---|---|---|---|---|---|---|---|---|
| lgbm_es10_30 | 2 | 2 | 14 | 0.5172 | 0.4021 | 0.4049 | 0.4072 | 0.0051 | 0.0104 |
| lgbm_noes_100 | 100 | 100 | 2051 | 0.5377 | 0.5356 | 0.5561 | 0.5821 | 0.0464 | 0.1056 |
| lgbm_noes_30 | 30 | 30 | 1405 | 0.5377 | 0.4970 | 0.5072 | 0.5187 | 0.0216 | 0.0805 |
| lgbm_noes_300 | 300 | 300 | 2712 | 0.5377 | 0.5526 | 0.5836 | 0.6200 | 0.0674 | 0.1065 |
| xgb_100 | 100 | 100 | 2115 | 0.1749 | 0.5370 | 0.5574 | 0.5843 | 0.0473 | 0.1060 |

## 2. Seed drift (std across seeds)

| variant | q90_std | q97_std | q99_std | proba_mean_std | uniq_probs_std |
|---|---|---|---|---|---|
| lgbm_es10_30 | 0.00053 | 0.00235 | 0.00175 | 0.00010 | 2.1 |
| lgbm_noes_100 | 0.00109 | 0.00185 | 0.00442 | 0.00081 | 25.5 |
| lgbm_noes_30 | 0.00066 | 0.00126 | 0.00232 | 0.00054 | 27.8 |
| lgbm_noes_300 | 0.00075 | 0.00227 | 0.00151 | 0.00054 | 21.5 |
| xgb_100 | 0.00018 | 0.00094 | 0.00286 | 0.00032 | 25.4 |

## 3. Holdout robustness — PF @ q97 (mean / std over seeds)

| variant | GBPUSD | AUDUSD | USDCHF | USDCAD | regime_pf_cv |
|---|---|---|---|---|---|
| lgbm_es10_30 | 0.76/0.30 | 1.42/0.04 | 1.09/0.30 | 1.43/0.58 | 0.29 |
| lgbm_noes_100 | 1.57/0.07 | 0.86/0.10 | 1.44/0.15 | 1.85/0.05 | 0.20 |
| lgbm_noes_30 | 1.48/0.15 | 0.88/0.04 | 1.27/0.10 | 1.79/0.27 | 0.18 |
| lgbm_noes_300 | 1.44/0.12 | 0.99/0.05 | 1.01/0.11 | 1.46/0.15 | 0.16 |
| xgb_100 | 1.69/0.19 | 0.93/0.05 | 1.22/0.10 | 1.96/0.15 | 0.16 |

## Interpretation hooks

- Degenerate stump signature: effective_trees≈1, uniq_probs tiny (<30), leaf_range tiny, huge seed drift.
- Healthy ensemble: effective_trees≈num_trees, uniq_probs in thousands, smooth hist, low seed drift, low ECE.
- 'Survives stably' = holdout PF mean>1 across ALL pairs with low std + low regime_pf_cv.
