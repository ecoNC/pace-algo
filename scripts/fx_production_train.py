"""FX production train — ship model (50t lock config), Heim-PC 2026-06-03 (ANN-026 step 2'+4').

Trains the 4 cascades of the locked FX config on a single production split and snapshots
everything Pine needs, then measures the SHIPPED model's OOS PF on a clean holdout.

Split:   train < (CUTOFF-26w)  |  val [CUTOFF-26w, CUTOFF) (threshold calib)  |  holdout >= CUTOFF (OOS)
Cascades: primary L/S (FEATURES_9, 50t) + meta L/S (full-73, 50t), POOLED top10/day, NY gate, R=1.5.
Outputs: artifacts/models/fx_ship_{mL,mS,meL,meS}_50t_2026-06-03.txt + fx_ship_snapshot.json

Run: py -3 scripts/fx_production_train.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
from datetime import datetime, timezone
warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))

import numpy as np
import pandas as pd
from phase3_density import build_pool, FEATURES_9, netR
from phase3_selection_compare import calib_thr
from phase3_v1_config import build_cands
from phase3_short_features import feature_cols
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from model_validation_suite import train_lgbm, predict

TREES, TOPN, SEED, GEN_MULT, NEG = 50, 10, 42, 3.0, -1e9
CUTOFF = pd.Timestamp("2025-07-01", tz="UTC")
VALW = pd.Timedelta(weeks=26)
MODELS = REPO / "artifacts" / "models"

def main():
    pool = build_pool()
    feats_full = feature_cols(pool)
    X9  = lambda d: d[FEATURES_9].values.astype(np.float32)
    X73 = lambda d: d[feats_full].values.astype(np.float32)

    vs = CUTOFF - VALW
    tr = pool[pool.index < vs]
    va = pool[(pool.index >= vs) & (pool.index < CUTOFF)]
    te = pool[pool.index >= CUTOFF]
    print(f"pool={len(pool):,}  train={len(tr):,}  val={len(va):,}  holdout(OOS)={len(te):,}")

    # 1) primary L/S (9-feat)
    mL = train_lgbm(X9(tr), tr["_lab_long"].values,  X9(va), va["_lab_long"].values,  TREES, None, SEED)
    mS = train_lgbm(X9(tr), tr["_lab_short"].values, X9(va), va["_lab_short"].values, TREES, None, SEED)

    # 2) generous thresholds on gated val
    gv = va["_in_ny"].values & va["_tradeable"].values
    pvL, pvS = predict(mL,"lgbm",X9(va)), predict(mS,"lgbm",X9(va))
    nd = max(1, va.index[gv].normalize().nunique())
    genL = calib_thr(pvL[gv], nd, TOPN*GEN_MULT); genS = calib_thr(pvS[gv], nd, TOPN*GEN_MULT)

    # 3) meta L/S (full-73) on generous candidates from train+val
    trva = pool[pool.index < CUTOFF]; gtv = trva["_in_ny"].values & trva["_tradeable"].values
    cL = gtv & (mL.predict(X9(trva)) >= genL); cS = gtv & (mS.predict(X9(trva)) >= genS)
    print(f"meta candidates: long={cL.sum():,}  short={cS.sum():,}")
    meL = train_lgbm(X73(trva[cL]), trva["_lab_long"].values[cL],  X73(trva[cL]), trva["_lab_long"].values[cL],  TREES, None, SEED)
    meS = train_lgbm(X73(trva[cS]), trva["_lab_short"].values[cS], X73(trva[cS]), trva["_lab_short"].values[cS], TREES, None, SEED)

    def marr(d, pp, gen, me):
        c = (d["_in_ny"].values & d["_tradeable"].values) & (pp >= gen)
        out = np.full(len(d), NEG)
        if c.sum(): out[c] = me.predict(X73(d[c]))
        return out

    # 4) POOLED threshold on val candidates
    cv = build_cands(va, marr(va,pvL,genL,meL), marr(va,pvS,genS,meS), gv, "long_short_usdchf")
    thr = calib_thr(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)

    # 5) OOS holdout: select + size + PF
    gt = te["_in_ny"].values & te["_tradeable"].values
    ptL, ptS = predict(mL,"lgbm",X9(te)), predict(mS,"lgbm",X9(te))
    ct = build_cands(te, marr(te,ptL,genL,meL), marr(te,ptS,genS,meS), gt, "long_short_usdchf")
    sel = ct[ct["proba"].values >= thr]
    sz = tier_size(sel["proba"].values)
    q1, q2 = (np.quantile(sel["proba"].values,[1/3,2/3]) if len(sel)>=3 else (thr,thr))
    days = max(1,(te.index[-1]-te.index[0]).days)
    print(f"\nOOS holdout (>= {CUTOFF.date()}):  selected={len(sel)}  ~{len(sel)/days*7:.1f}/week")
    for s in (0.3,0.5,1.0):
        r = netR(sel["gR"].values, sel["cost"].values, s); st = pf_wr_sized(r, sz)
        if st: print(f"  spread {s}pip:  net_PF={st['pf']:.3f}  WR={st['wr']:.3f}  n={len(r)}")

    # 6) snapshot
    MODELS.mkdir(parents=True, exist_ok=True)
    names = {}
    for tag,m in [("mL",mL),("mS",mS),("meL",meL),("meS",meS)]:
        p = MODELS / f"fx_ship_{tag}_50t_2026-06-03.txt"; m.save_model(str(p)); names[tag]=p.name
    snap = {"created": datetime.now(timezone.utc).isoformat(), "trees": TREES, "seed": SEED,
            "cutoff": str(CUTOFF), "features_9": FEATURES_9, "features_full_n": len(feats_full),
            "gen_long": float(genL), "gen_short": float(genS), "pooled_thr": float(thr),
            "size_q1": float(q1), "size_q2": float(q2), "topn": TOPN, "gen_mult": GEN_MULT,
            "models": names}
    (MODELS / "fx_ship_snapshot.json").write_text(json.dumps(snap, indent=2))
    print("\nsnapshot -> artifacts/models/fx_ship_snapshot.json")
    print({k:snap[k] for k in ("gen_long","gen_short","pooled_thr","size_q1","size_q2")})

if __name__ == "__main__":
    main()
