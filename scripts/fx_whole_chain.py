"""Block-2 Step 4: Python whole-chain REFERENCE on captured TV bars.

Runs the exact production chain on TV-captured OHLCV (feed-consistent with Pine):
  tv_capture (5m+1h+4h) -> features_from_captures(full=73) -> 4 cascades (booster.predict)
  -> selection chain (gen->meta->POOLED->signal>=pooled_thr->sizing, FIXED snapshot thresholds)
Outputs the SIGNAL-BAR SET (timestamps), count, and per-bar signal/dir/size, so Step-4 can do
MENGEN-identity (same entry bars Pine<->Python) BEFORE value-identity.

feats_full (73-name training order) is cached to artifacts/models/fx_feats_full.json (build_pool
is heavy; cache once). Unreferenced cols (e.g. macro) are filled 0 — boosters ignore them.

Usage:
  python scripts/fx_whole_chain.py GBPUSD            # print signal set + counts on the capture
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import numpy as np
import lightgbm as lgb
from tv_capture import features_from_captures
from phase3_density import FEATURES_9
from core.state.market_state import classify_market_state, DEFAULT_PARAMS as MS

MODELS = REPO / "artifacts" / "models"
snap = json.loads((MODELS / "fx_ship_snapshot.json").read_text())
GL, GS, THR, Q1, Q2 = (snap["gen_long"], snap["gen_short"], snap["pooled_thr"],
                       snap["size_q1"], snap["size_q2"])
VQ, VS = MS["vol_quiet"], MS["vol_shock"]
NEG = -1e9
FEATS_CACHE = MODELS / "fx_feats_full.json"

def load(t):
    return lgb.Booster(model_str=(MODELS / snap["models"][t]).read_text(encoding="utf-8").replace("\r\n", "\n"))

def feats_full():
    if FEATS_CACHE.exists():
        return json.loads(FEATS_CACHE.read_text())
    from phase3_density import build_pool
    from phase3_short_features import feature_cols
    ff = feature_cols(build_pool())
    FEATS_CACHE.write_text(json.dumps(ff))
    return ff

def whole_chain(symbol: str):
    ff = feats_full()
    feats = features_from_captures(symbol, "5", full=True)
    # tradeable gate from classify_market_state on the same 5m bars (Step-1 gate)
    from tv_capture import load_capture
    st = classify_market_state(load_capture(symbol, "5"))
    feats = feats.join(st[["in_ny", "tradeable"]], rsuffix="_ms")
    X9 = feats[FEATURES_9].values.astype(np.float32)
    X73 = feats.reindex(columns=ff, fill_value=0.0).values.astype(np.float32)
    mL, mS, meL, meS = load("mL"), load("mS"), load("meL"), load("meS")
    pL, pS = mL.predict(X9), mS.predict(X9)
    pmL, pmS = meL.predict(X73), meS.predict(X73)
    gate = (feats["in_ny"].values > 0.5) & feats["tradeable"].values
    usdchf = "USDCHF" in symbol
    scoreL = np.where(gate & (pL >= GL), pmL, NEG)
    scoreS = np.where((usdchf) & gate & (pS >= GS), pmS, NEG)
    pooled = np.maximum(scoreL, scoreS)
    signal = pooled >= THR
    size = np.where(pooled < Q1, 0.5, np.where(pooled < Q2, 1.0, 1.5))
    direction = np.where(scoreL >= scoreS, 1, -1)
    return feats.index, signal, direction, size, pooled, dict(pL=pL, pS=pS, pmL=pmL, pmS=pmS)

def main():
    sym = sys.argv[1] if len(sys.argv) > 1 else "GBPUSD"
    idx, signal, direction, size, pooled, probs = whole_chain(sym)
    sig_idx = np.where(signal)[0]
    print(f"{sym}: bars={len(idx)}  window={idx[0]} .. {idx[-1]}  signals={len(sig_idx)}")
    print("signal-bar SET (timestamp / dir / size / pooled):")
    for i in sig_idx:
        d = "LONG" if direction[i] > 0 else "SHORT"
        print(f"  {idx[i]}  {d}  size={size[i]}  pooled={pooled[i]:.5f}")
    if len(sig_idx) == 0:
        print("  (none in window — window may be outside NY session)")

if __name__ == "__main__":
    main()
