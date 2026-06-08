"""Block-2 Step 4 verify (fallback): per Pine-signal bar, recompute the chain in Python from TV
captures and confirm pooled/size + Class-C bars_since_sweep_down match Pine — verifying feed-level
features + Class-C + chain on real bars. ema_200_dist_atr is INJECTED from Pine's label (full-history,
formula-trusted Class-B) because the 500-bar capture cannot warm ema200.

MENGEN vor Wert: first report whether every Pine signal in the capture window is reproduced
(SET), then the values (pooled/size) and the Class-C bss diff column.

Run: py -3 scripts/fx_verify_whole_chain.py GBPUSD
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import numpy as np
import pandas as pd
import lightgbm as lgb
from tv_capture import features_from_captures, load_capture
from phase3_density import FEATURES_9
from core.state.market_state import classify_market_state, DEFAULT_PARAMS as MS

MODELS = REPO / "artifacts" / "models"
snap = json.loads((MODELS / "fx_ship_snapshot.json").read_text())
GL, GS, THR, Q1, Q2 = (snap["gen_long"], snap["gen_short"], snap["pooled_thr"], snap["size_q1"], snap["size_q2"])
feats_full = json.loads((MODELS / "fx_feats_full.json").read_text())
NEG = -1e9
EMA_COL = "ema_200_dist_atr"

def load(t):
    return lgb.Booster(model_str=(MODELS / snap["models"][t]).read_text(encoding="utf-8").replace("\r\n", "\n"))

def py_bss(raw5):  # Python bars_since_sweep_down on the 5m capture (Class-C reference)
    from core.features.market_structure import compute_smc_features
    from core.features.engineer import atr as atr_fn
    a = atr_fn(raw5["high"], raw5["low"], raw5["close"], 14).values
    smc = compute_smc_features(raw5, a, np.zeros(len(raw5)))
    return smc["bars_since_sweep_down"]

def main():
    sym = sys.argv[1] if len(sys.argv) > 1 else "GBPUSD"
    lbls = json.loads((REPO / "results" / "fx_whole_chain" / f"pine_labels_{sym}_2026-06-08.json").read_text())["labels"]
    pine = []
    for s in lbls:
        t, d, sz, pl, bss, em = s.split("|")
        pine.append(dict(t=int(t) // 1000, dir=int(d), size=float(sz), pooled=float(pl),
                         bss=float(bss), ema=float(em)))
    feats = features_from_captures(sym, "5", full=True)
    st = classify_market_state(load_capture(sym, "5"))
    feats = feats.join(st[["in_ny", "tradeable"]], rsuffix="_ms")
    bss_series = py_bss(load_capture(sym, "5"))
    idx_s = np.asarray(feats.index.asi8)  # dtype datetime64[s] -> asi8 is already unix seconds
    sec_to_pos = {int(s): i for i, s in enumerate(idx_s)}
    lo, hi = int(idx_s.min()), int(idx_s.max())
    mL, mS, meL, meS = load("mL"), load("mS"), load("meL"), load("meS")
    ema_pos = feats_full.index(EMA_COL)

    in_win = [p for p in pine if lo <= p["t"] <= hi]
    print(f"{sym}: capture 5m bars={len(feats)}  window=[{lo},{hi}]  Pine signals in window={len(in_win)}")
    print("per Pine-signal verification (ema_200_dist_atr injected from Pine; bss = Class-C):")
    print(f"{'utc':>20} {'pyPooled':>9} {'pinePool':>9} {'dPool':>8} {'fires':>5} {'sz_py':>5} {'sz_pine':>6} {'bss_py':>6} {'bss_pine':>8} {'bss_ok':>6}")
    set_ok = True; bss_mismatch = 0
    for p in in_win:
        ts = pd.Timestamp(p["t"], unit="s", tz="UTC")
        if p["t"] not in sec_to_pos:
            print(f"  {ts}  <- Pine signal bar NOT in capture index (gap?) -> SET MISS"); set_ok = False; continue
        pos = sec_to_pos[p["t"]]
        row = feats.iloc[pos].copy()
        row[EMA_COL] = p["ema"]                       # inject Pine full-history ema200
        x9 = row[FEATURES_9].values.astype(np.float32).reshape(1, -1)
        x73 = row.reindex(feats_full).fillna(0.0).values.astype(np.float32).reshape(1, -1)
        x73[0, ema_pos] = p["ema"]
        pmL = float(meL.predict(x73)[0])
        gate = (row["in_ny"] > 0.5) and bool(row["tradeable"])
        scoreL = pmL if (gate and float(mL.predict(x9)[0]) >= GL) else NEG
        pooled = scoreL            # GBPUSD long-only (short USDCHF-only)
        fires = pooled >= THR
        size = 0.5 if pooled < Q1 else (1.0 if pooled < Q2 else 1.5)
        bss = float(bss_series.iloc[pos])
        bss_ok = (bss == p["bss"])
        bss_mismatch += (0 if bss_ok else 1)
        set_ok &= bool(fires)
        print(f"  {ts}  {pooled:9.5f} {p['pooled']:9.5f} {pooled-p['pooled']:+8.5f} {str(bool(fires)):>5} "
              f"{size:5.1f} {p['size']:6.1f} {bss:6.0f} {p['bss']:8.0f} {str(bss_ok):>6}")
    print()
    print(f"SET: every Pine signal reproduced by Python? {set_ok}")
    print(f"Class-C bars_since_sweep_down mismatches: {bss_mismatch} / {len(in_win)}")

if __name__ == "__main__":
    main()
