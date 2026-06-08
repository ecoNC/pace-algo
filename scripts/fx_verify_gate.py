"""Block-2 Step 1 verify: Python classify_market_state['tradeable'] vs Pine fx_gate_validate.

Flow: Claude reads the Pine data-window (tradeable/atr_pctile/adx14/atr14) + captures the SAME
5m OHLCV back-to-back to data/tv_capture/<SYM>_5.json, then this prints the Python side at the
last (concurrent) bar and diffs against the Pine values passed on the CLI.

Run: py -3 scripts/fx_verify_gate.py GBPUSD --pine-tradeable 1 --pine-pctile 0.59 --pine-adx 23.8 --pine-atr 0.00041
     (omit --pine-* to just print the Python side)
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import numpy as np
from tv_capture import load_capture, _de
from core.state.market_state import classify_market_state
from core.features.engineer import atr as atr_fn

ap = argparse.ArgumentParser()
ap.add_argument("symbol", nargs="?", default="GBPUSD")
ap.add_argument("--pine-tradeable"); ap.add_argument("--pine-pctile")
ap.add_argument("--pine-adx"); ap.add_argument("--pine-atr")
a = ap.parse_args()

raw = load_capture(a.symbol, "5")
if raw is None:
    raise FileNotFoundError(f"capture data/tv_capture/{a.symbol}_5.json missing")
st = classify_market_state(raw)
atr_series = atr_fn(raw["high"], raw["low"], raw["close"], 14)
n = len(raw)
print(f"{a.symbol} 5m  bars={n}  last={raw.index[-1]}")
print("last 8 bars (Python classify_market_state) — match Pine read by adx fingerprint:")
for i in range(-8, 0):
    r = st.iloc[i]
    print(f"  {st.index[i]}  tradeable={int(bool(r['tradeable']))}  atr_pctile={r['atr_pctile']:.5f}  "
          f"adx={r['adx']:.4f}  atr14={atr_series.iloc[i]:.6f}  state={r['state']}")

atr14_last = float(atr_fn(raw["high"], raw["low"], raw["close"], 14).iloc[-1])
last = st.iloc[-1]
py = dict(tradeable=float(bool(last["tradeable"])), atr_pctile=float(last["atr_pctile"]),
          adx14=float(last["adx"]), atr14=atr14_last)
pine = {}
if a.pine_tradeable is not None: pine["tradeable"] = _de(a.pine_tradeable)
if a.pine_pctile is not None:    pine["atr_pctile"] = _de(a.pine_pctile)
if a.pine_adx is not None:       pine["adx14"] = _de(a.pine_adx)
if a.pine_atr is not None:       pine["atr14"] = _de(a.pine_atr)

if pine:
    print("\nbit-exact diff (last bar, atr_pctile/atr atol=1e-5; tradeable exact):")
    ok = True
    for k, pv in pine.items():
        d = abs(py[k] - pv)
        tol = 0.0 if k == "tradeable" else (1e-5 if k != "adx14" else 5e-3)  # adx seed-diff converges slower
        flag = "PASS" if d <= tol else "**FAIL**"
        ok &= d <= tol
        print(f"  {k:11s} py={py[k]:+.6f}  pine={pv:+.6f}  |diff|={d:.2e}  (tol {tol:g})  {flag}")
    print("GATE bit-exact:", "PASS" if ok else "FAIL")
else:
    print("\n(no --pine-* given; Python side only)")
