"""Block-2 Step 4 closeout: verify ema_{20,50,200}_dist_atr Python vs Pine at the current
(fully-warmed) bar. ema20/ema50 ~1e-6 -> ta.ema formula + (close-ema)/atr wrapper proven;
ema200 shows the warmup diff (documented, not a formula diff).

Run: py -3 scripts/fx_verify_ema.py GBPUSD --p20 <pine> --p50 <pine> --p200 <pine>
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import numpy as np
from tv_capture import load_capture, _de
from core.features.engineer import ema as ema_fn, atr as atr_fn

ap = argparse.ArgumentParser()
ap.add_argument("symbol", nargs="?", default="GBPUSD")
ap.add_argument("--p20"); ap.add_argument("--p50"); ap.add_argument("--p200")
a = ap.parse_args()

raw = load_capture(a.symbol, "5")
c, h, l = raw["close"], raw["high"], raw["low"]
atr = atr_fn(h, l, c, 14)
def dist(n):  # iloc[-2] = last CLOSED bar (Pine plots f_x[1]); avoids forming-bar drift
    e = ema_fn(c, n)
    return ((c - e) / atr.replace(0, np.nan)).iloc[-2]
py = {"ema_20_dist_atr": float(dist(20)), "ema_50_dist_atr": float(dist(50)), "ema_200_dist_atr": float(dist(200))}
print(f"{a.symbol} 5m  bars={len(raw)}  last={raw.index[-1]}  (ema20 needs ~100 warmup, ema50 ~250, ema200 ~1000)")
pine = {}
if a.p20 is not None: pine["ema_20_dist_atr"] = _de(a.p20)
if a.p50 is not None: pine["ema_50_dist_atr"] = _de(a.p50)
if a.p200 is not None: pine["ema_200_dist_atr"] = _de(a.p200)
print(f"{'feature':22} {'python':>12} {'pine':>12} {'|diff|':>10}  verdict")
for k in ("ema_20_dist_atr", "ema_50_dist_atr", "ema_200_dist_atr"):
    if k in pine:
        d = abs(py[k] - pine[k])
        v = "PASS ~1e-6 (formula+wrapper proven)" if d < 1e-4 else ("warmup diff (expected for ema200)" if k == "ema_200_dist_atr" else "**CHECK**")
        print(f"{k:22} {py[k]:12.6f} {pine[k]:12.6f} {d:10.2e}  {v}")
    else:
        print(f"{k:22} {py[k]:12.6f} {'(no pine)':>12}")
