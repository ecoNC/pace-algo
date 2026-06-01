# PaceAlgo — FX Module LOCK (2026-06-01)

**STATUS: LOCKED.** First validated AI module. Robustness verified (`phase7_fx_lock.py`,
spec: `results/model_validation/phase7_fx_lock_*/fx_lock.json`). Pine export pending
(after crypto module per Nico). Commit family: phase3 `9c3a386` → phase4 `615464d` → this.

---

## Spec (frozen)

| Component | Value |
|---|---|
| Long universe | GBPUSD, USDJPY, USDCAD, NZDUSD, USDCHF |
| Short universe | **USDCHF only** (other shorts thin/decaying — see phase3_short_robustness) |
| Primary ranker | LGBM, **50 trees**, depth 3, 9 features (long-9), long & short |
| Features (9) | hour_cos, hour_sin, rvol_20, ema_20_dist_atr, atr_pct, htf_4h_rsi_14, is_fx_market_open, in_ny, htf_4h_atr_percentile_100 |
| Meta re-rank | secondary LGBM (50t, full-73 features) on the primary's generous candidates |
| Gate | `in_ny` (13–22 UTC) **and** vol_tradeable (state ∉ {QUIET, SHOCK}) |
| Selection | POOLED proba threshold across pairs+dirs, calibrated on validation for **top-10/day** |
| Sizing | proba-tercile 0.5 / 1.0 / 1.5× (optional "Aggressive" mode) |
| Execution | R = 1.5 (TP 1.5·ATR / SL 1.0·ATR, 24-bar time barrier), entry next-bar-open, one position |
| Timeframe | 5m |

---

## Robustness (walk-forward, 20 folds 2024–2026, net, multi-seed)

| Spread | net PF | WR | trades/day | % folds >1 | worst fold | median fold | PF 2024/2025/2026 |
|---|---|---|---|---|---|---|---|
| **0.3 pip (ECN)** | 1.66 | 0.51 | 9.3 | 90% | 0.96 | 1.60 | 1.31 / 2.10 / 1.83 |
| **0.5 pip (ECN)** | 1.51 | 0.51 | 9.3 | 80% | 0.88 | 1.45 | 1.18 / 1.92 / 1.66 |
| 1.0 pip (retail) | 1.18 | 0.51 | 9.3 | 60% | 0.69 | 1.15 | 0.91 / 1.53 / 1.31 |

**Verdict: real & robust at ECN spreads (0.3–0.5 pip)** — all years positive, ≥80% folds
positive, worst fold only −12%, 2026 strong. **Conditional**: at retail 1.0 pip it is
marginal (60% folds, 2024 negative) — do not promise retail-spread performance.

Non-edge sizing core (no sizing) = PF ~1.30 @0.5pip; sizing lifts to ~1.51 at higher
variance. Sizing is an optional capital mode, not the robustness base.

---

## Why we trust it (methodology)

- Walk-forward rolling quarters (each test quarter unseen), multi-seed.
- Net of spread + next-bar-open (gross numbers banned).
- Per-year positive, per-pair long edge broad (all 5 pairs >1.34); short curated to the
  one robust pair (USDCHF).
- No lookahead: POOLED threshold + meta candidate cut calibrated on validation only.
- Edge mechanism understood: ML selection within the NY-gated population; meta removes
  conditional false positives. Not a black-box backtest fit.

## Honest limitations

- Thin edge (PF 1.3 core), **ECN-dependent**. Not a money-printer.
- FX-majors + NY-session specific (does not generalize — see phase5/6).
- Pine cost: primary+meta = 4 cascades @50t ≈ 88% of ops budget (fits).
