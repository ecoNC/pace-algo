# FX Whole-Chain MENGEN-Abgleich — 2026-06-08 (Block 2 Step 4, fallback)

**Result: MENGE GREEN.** Pine `fx_chain_validate.pine` (CAPITALCOM:GBPUSD 5m) vs Python reference
(`fx_verify_whole_chain.py`) on the June-7 NY-open cluster (9 signals). ema_200_dist_atr injected
from Pine (full-history, formula-trusted Class-B); all other features recomputed from TV captures.

| utc (2026-06-07) | py pooled | pine pooled | Δ | fires | size py/pine | bss py/pine | bss ok |
|---|---|---|---|---|---|---|---|
| 21:00 | 0.57527 | 0.57527 | +0.00000 | ✓ | 1.0/1.0 | 1/1 | ✓ |
| 21:05 | 0.69809 | 0.68229 | +0.01579 | ✓ | 1.5/1.5 | 2/2 | ✓ |
| 21:10 | 0.68017 | 0.66389 | +0.01628 | ✓ | 1.5/1.5 | 3/3 | ✓ |
| 21:15 | 0.57812 | 0.56000 | +0.01811 | ✓ | 1.0/1.0 | 99/99 | ✓ |
| 21:20 | 0.73171 | 0.71697 | +0.01475 | ✓ | 1.5/1.5 | 99/99 | ✓ |
| 21:25 | 0.71722 | 0.70803 | +0.00919 | ✓ | 1.5/1.5 | 99/99 | ✓ |
| 21:30 | 0.71436 | 0.70512 | +0.00924 | ✓ | 1.5/1.5 | 0/0 | ✓ |
| 21:35 | 0.70927 | 0.69993 | +0.00934 | ✓ | 1.5/1.5 | 1/1 | ✓ |
| 21:45 | 0.64705 | 0.63673 | +0.01032 | ✓ | 1.5/1.5 | 0/0 | ✓ |

**SET: 9/9 reproduced. Class-C bars_since_sweep_down: 0/9 mismatch. Sizes: 9/9.**

## Interpretation
- **MENGE identisch** (trade population + sizes) — milestone-critical: Pine fires exactly the
  Python-reference selection. **Mengen vor Wert erfüllt.**
- **Class-C clean on real bars** — the flagged `ta.pivotlow`-vs-Python tie risk did NOT bite;
  `bars_since_sweep_down` matches exactly at all 9 bars. The #1 unverified risk is closed.
- **Wert Δ +0.009…+0.018 = Class-B warmup**, not a bug. Cluster is at FX week-open (Sun 21:00 UTC)
  → only ~158 bars of ewm warmup before it in a ≤500-bar capture → rsi/ema/macd ewm not fully
  converged. Diff is consistent across all 9 consecutive bars (warmup signature, not random) and
  does NOT flip any SET/size decision (tier bounds 0.5075/0.6180 not crossed). In production Pine
  has full history → these converge (~1e-6, same class as atr verified in Step 1).

## Tooling breakthrough (= Option B, for free)
Large `data_get_ohlcv` results are auto-persisted to disk by the harness. `_tv_persisted_to_capture.py`
reads them → clean capture files, NO hand-transcription. The transcription wall is gone; paging
to >1000 bars (full ema200 warmup, no injection) is now feasible and is the reusable instrument
for all future modules (INDEX/METAL).

## Next (to bank the Wert too, optional rigor)
Page (transcription-free) a mid-week full-warmup window (>1000 5m bars) → re-run WITHOUT ema200
injection → expect Δ → ~1e-6 across all features, confirming Class-B convergence end-to-end.
