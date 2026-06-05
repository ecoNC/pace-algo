# FX Ship-Modell — Production-Train + Export-De-Risk (Heim-PC, 2026-06-03)

**ANN-026 Schritte 2' (4 Cascades + Thresholds) + 4' (OOS-Revalidierung) + 3'-Vorab (bit-exact alle Cascades).**
Lokal gefahren — Daten `data/processed_v2/`, Pipeline `phase3_density.build_pool` (POOL 1,62 M, 5 FX).

## Production-Split
- train < 2025-01-01 (1,097 M) · val [2025-01, 2025-07) Threshold-Calib (185 k) · **Holdout ≥ 2025-07 (341 k, OOS)**.
- 4 Cascades, 50t, seed 42, FEATURES_9-Primary + full-73-Meta, NY-Gate, POOLED top10/Tag, R=1.5.

## OOS-Holdout (≥2025-07, ungesehen) — Ship-Modell-Gate (Schritt 4')

| Spread | net PF | WR | n |
|---|---|---|---|
| 0.3 pip | 2.04 | 54.4% | 3179 (~9.6/Tag) |
| **0.5 pip (ECN)** | **1.85** | 54.4% | |
| 1.0 pip | 1.46 | | |

→ **PASS** (>1.3-Bar; ~9.6 Trades/Tag = lock-konform; konsistent mit Walk-Forward 1.51@0.5pip).
Caveat: ein Holdout-Fenster (2025–26 waren starke Jahre) — der robustere Multi-Fold-Wert bleibt 1.51.
Ship = 50t-Config (ANN-026); 1.73/100t nicht vererbt/nötig.

## Bit-exact (Schritt 3'-Vorab) — alle 4 Cascades

| Cascade | Feats | Trees | Pine-Größe | bit-exact (5000 Holdout) |
|---|---|---|---|---|
| mL primary-long | 9 | 50 | 21.392 chars | ✅ max_abs_diff 0.0 |
| mS primary-short | 9 | 50 | 21.500 | ✅ 0.0 |
| meL meta-long | 73 | 50 | 22.914 | ✅ 0.0 |
| meS meta-short | 73 | 50 | 21.555 | ✅ 0.0 |

→ Pine-Cascade == LightGBM-Booster für ALLE vier. Cascade-Größe ~22 KB je (Tree-Tiefe-getrieben,
nicht Feature-Zahl) → 4 Cascades ≈ 88 KB Pine; passt (Lock: 88% Ops-Budget).

## Snapshot (was Pine braucht) — `artifacts/models/fx_ship_snapshot.json`
gen_long 0.4994 · gen_short 0.4964 · pooled_thr 0.4929 · size_q1 0.5075 · size_q2 0.6180 · TOPN 10.
4 Booster: `fx_ship_{mL,mS,meL,meS}_50t_2026-06-03.txt`.

## Verbleibend (Schritt 3' Vollintegration — der große Pine-Build)
- **Feature-Engine in Pine bit-exact:** die 9 Primary-Feats (inkl. `in_ny`, `is_fx_market_open`,
  `vol_tradeable`-State, `htf_4h_*`) + die full-73 für die Meta (ema/adx/rsi/macd/bb/SMC/FVG/sweeps/
  htf-context) — via `core/export/pine_features.py`. **Der eigentliche harte Rest.**
- Skelett `pace_algo_v1_ml_export_PARKED.pine` patchen: 4 Cascades + gen→meta→POOLED(thr)→Sizing(q1/q2).
- **Whole-chain bit-exact** (Python-End-to-End == Pine) auf Holdout.
- TV-Compile (Heim-PC) + Ship-Form → COVERAGE_MATRIX FX-Majors → Edge-Validated.

Scripts: `scripts/fx_production_train.py`, `scripts/fx_bitexact_all.py`, `scripts/fx_primary_export_smoke.py`.
