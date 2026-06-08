"""Block-2 Step 3 verify (logic, no TV): reproduce the Pine selection-chain formula in Python on
the holdout and confirm it yields the SAME selected trade-set + sizes as fx_production_train.py's
own build_cands/sel/tier_size. This catches the three operator-order traps definitively:
mis-ordering gen/meta, dedupe direction, or sizing-source would change the selected set/sizes.

Run: py -3 scripts/fx_verify_chain_logic.py
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
from phase3_density import build_pool, FEATURES_9
from phase3_short_features import feature_cols
from phase3_v1_config import build_cands
from phase4_ensemble_sizing import tier_size

MODELS = REPO / "artifacts" / "models"
snap = json.loads((MODELS / "fx_ship_snapshot.json").read_text())
GL, GS, THR, Q1, Q2 = (snap["gen_long"], snap["gen_short"], snap["pooled_thr"],
                       snap["size_q1"], snap["size_q2"])
CUTOFF = pd.Timestamp(snap["cutoff"])
NEG = -1e9

def load(t):
    return lgb.Booster(model_str=(MODELS / snap["models"][t]).read_text(encoding="utf-8").replace("\r\n", "\n"))

def main():
    pool = build_pool(); ff = feature_cols(pool)
    X9 = lambda d: d[FEATURES_9].values.astype(np.float32)
    X73 = lambda d: d[ff].values.astype(np.float32)
    mL, mS, meL, meS = load("mL"), load("mS"), load("meL"), load("meS")
    te = pool[pool.index >= CUTOFF]
    gate = te["_in_ny"].values & te["_tradeable"].values
    usdchf = (te["symbol"].values == "USDCHF")
    ptL, ptS = mL.predict(X9(te)), mS.predict(X9(te))
    pmL_all, pmS_all = meL.predict(X73(te)), meS.predict(X73(te))

    # ---- REFERENCE: fx_production_train.py selection (marr + build_cands + fixed thr) ----
    def marr(pp, gen, me_all):
        c = gate & (pp >= gen)
        out = np.full(len(te), NEG); out[c] = me_all[c]; return out
    ref_ct = build_cands(te, marr(ptL, GL, pmL_all), marr(ptS, GS, pmS_all), gate, "long_short_usdchf")
    ref_sel = ref_ct[ref_ct["proba"].values >= THR]
    ref_rows = set(int(r) for r in ref_sel["row"].values)
    ref_size_by_row = dict(zip(ref_sel["row"].values, tier_size(ref_sel["proba"].values)))

    # ---- MINE: the exact Pine per-bar formula (vectorized over te rows) ----
    scoreL = np.where(gate & (ptL >= GL), pmL_all, NEG)
    scoreS = np.where(usdchf & gate & (ptS >= GS), pmS_all, NEG)
    pooled = np.maximum(scoreL, scoreS)
    signal = pooled >= THR
    size = np.where(pooled < Q1, 0.5, np.where(pooled < Q2, 1.0, 1.5))
    mine_rows = set(int(i) for i in np.where(signal)[0])
    mine_size_by_row = {i: float(size[i]) for i in mine_rows}

    # ---- COMPARE: trade-SET first, then sizes (Mengen vor Wert) ----
    only_ref = ref_rows - mine_rows
    only_mine = mine_rows - ref_rows
    print(f"holdout rows={len(te):,}  ref_selected={len(ref_rows)}  mine_selected={len(mine_rows)}")
    print(f"SET identical: {ref_rows == mine_rows}  (only_ref={len(only_ref)}, only_mine={len(only_mine)})")
    if ref_rows == mine_rows:
        size_mismatch = [r for r in ref_rows if abs(ref_size_by_row[r] - mine_size_by_row[r]) > 1e-12]
        print(f"SIZE identical: {len(size_mismatch) == 0}  (mismatches={len(size_mismatch)})")
        # direction check: dedupe keeps higher meta-proba; tie -> long
        ndir_long = int(((scoreL >= scoreS) & signal).sum()); ndir_short = int(((scoreS > scoreL) & signal).sum())
        print(f"directions: long={ndir_long}  short={ndir_short}  (short must be USDCHF-only)")
        bad_short = int((signal & (scoreS > scoreL) & ~usdchf).sum())
        print(f"non-USDCHF shorts (must be 0): {bad_short}")
        ok = (len(size_mismatch) == 0) and bad_short == 0
        print("\nSTEP-3 CHAIN LOGIC:", "PASS" if ok else "FAIL")
        raise SystemExit(0 if ok else 1)
    else:
        print("\nSTEP-3 CHAIN LOGIC: FAIL (trade-set differs -> operator-order bug)")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
