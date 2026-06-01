"""
Phase 7: FX module robustness profile + LOCK spec.

Verifies the FX module is real & robust before locking, and emits the canonical spec.
Config (the locked FX module):
  long (5 FX) + USDCHF-short + META re-rank + proba sizing, 50 trees, NY gate (in_ny &
  tradeable), POOLED top10/day, R=1.5. Walk-forward (20 folds), net, spread sweep.

Robustness reported: per-fold sized-PF distribution (% folds >1, min, median), per-year
PF, WR, trades/day — at 0.3 / 0.5 / 1.0 pip.

Output: results/model_validation/phase7_fx_lock_<UTC>/fx_lock.json  (= the locked spec)
Run:    python scripts/phase7_fx_lock.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import numpy as np
import pandas as pd

from phase3_density import build_pool, FEATURES_9, netR, VAL_WEEKS, FOLD_STARTS
from phase3_selection_compare import calib_thr
from phase3_v1_config import build_cands
from phase3_short_features import feature_cols
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from model_validation_suite import train_lgbm, predict

TREES, TOPN, SEED, GEN_MULT, NEG = 50, 10, 42, 3.0, -1e9
SPREADS = [0.3, 0.5, 1.0]


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase7_fx_lock_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    feats_full = feature_cols(pool)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d, f=FEATURES_9: d[f].values.astype(np.float32)
    print(f"pool={len(pool):,}  trees={TREES}")

    # per spread: realized R + sizing, per-fold pf, per-year
    acc = {s: {"R": [], "S": [], "foldpf": [], "yr": {2024: {"r": [], "s": []}, 2025: {"r": [], "s": []}, 2026: {"r": [], "s": []}}} for s in SPREADS}

    for ts0 in FOLD_STARTS:
        te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
        te = pool[(pool.index >= te_s) & (pool.index < te_e)]
        if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
        gv = va["_in_ny"].values & va["_tradeable"].values
        gt = te["_in_ny"].values & te["_tradeable"].values
        if gv.sum() < 100 or gt.sum() < 100: continue
        mL = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, TREES, None, SEED)
        mS = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, TREES, None, SEED)
        pvL, ptL = predict(mL, "lgbm", X(va)), predict(mL, "lgbm", X(te))
        pvS, ptS = predict(mS, "lgbm", X(va)), predict(mS, "lgbm", X(te))
        nd = max(1, va.index[gv].normalize().nunique())
        genL = calib_thr(pvL[gv], nd, TOPN * GEN_MULT); genS = calib_thr(pvS[gv], nd, TOPN * GEN_MULT)
        trva = pool[pool.index < te_s]; gtrva = trva["_in_ny"].values & trva["_tradeable"].values
        cL = gtrva & (mL.predict(X(trva)) >= genL); cS = gtrva & (mS.predict(X(trva)) >= genS)
        if cL.sum() <= 200 or cS.sum() <= 200: continue
        meL = train_lgbm(X(trva[cL], feats_full), trva["_lab_long"].values[cL], X(trva[cL], feats_full), trva["_lab_long"].values[cL], TREES, None, SEED)
        meS = train_lgbm(X(trva[cS], feats_full), trva["_lab_short"].values[cS], X(trva[cS], feats_full), trva["_lab_short"].values[cS], TREES, None, SEED)

        def marr(d, pp, gen, me):
            c = (d["_in_ny"].values & d["_tradeable"].values) & (pp >= gen)
            out = np.full(len(d), NEG)
            if c.sum(): out[c] = me.predict(X(d[c], feats_full))
            return out
        cv = build_cands(va, marr(va, pvL, genL, meL), marr(va, pvS, genS, meS), gv, "long_short_usdchf")
        ct = build_cands(te, marr(te, ptL, genL, meL), marr(te, ptS, genS, meS), gt, "long_short_usdchf")
        thr = calib_thr(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
        sel = ct[ct["proba"].values >= thr]
        sz = tier_size(sel["proba"].values); yrs = sel["ts"].dt.year.values
        for s in SPREADS:
            r = netR(sel["gR"].values, sel["cost"].values, s)
            acc[s]["R"].append(r); acc[s]["S"].append(sz)
            st = pf_wr_sized(r, sz)
            if st: acc[s]["foldpf"].append(st["pf"])
            for y in (2024, 2025, 2026):
                mk = yrs == y
                acc[s]["yr"][y]["r"].append(netR(sel["gR"].values[mk], sel["cost"].values[mk], s))
                acc[s]["yr"][y]["s"].append(sz[mk])

    spec = {"module": "FX", "config": {
        "symbols_long": ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF"],
        "symbols_short": ["USDCHF"], "features": FEATURES_9, "meta_features": "full-73",
        "trees": TREES, "gate": "in_ny(13-22 UTC) & vol_tradeable(not QUIET/SHOCK)",
        "selection": f"POOLED proba threshold, top{TOPN}/day", "meta": "secondary full-feature re-rank",
        "sizing": "proba tercile 0.5/1.0/1.5x", "execution": "R=1.5 (TP1.5/SL1.0 ATR, 24-bar), next-bar-open",
    }, "robustness": {}}

    print(f"\n{'spread':7s} {'net_PF':>7s} {'WR':>6s} {'tr/day':>7s} {'folds>1':>8s} {'minfold':>8s} {'medfold':>8s}  {'PF 24/25/26'}")
    for s in SPREADS:
        allR = np.concatenate(acc[s]["R"]); allS = np.concatenate(acc[s]["S"])
        st = pf_wr_sized(allR, allS)
        fpf = np.array(acc[s]["foldpf"])
        yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"] for y, v in acc[s]["yr"].items()}
        prof = dict(net_pf=st["pf"], wr=st["wr"], trades_per_day=round(st["n"] / days, 2),
                    n_folds=len(fpf), pct_folds_pos=round(float((fpf > 1).mean()), 2),
                    min_fold_pf=round(float(fpf.min()), 2), median_fold_pf=round(float(np.median(fpf)), 2),
                    pf_by_year=yr)
        spec["robustness"][f"{s}pip"] = prof
        print(f"{s:<7} {st['pf']:>7} {st['wr']:>6} {prof['trades_per_day']:>7.2f} {prof['pct_folds_pos']:>8} {prof['min_fold_pf']:>8} {prof['median_fold_pf']:>8}  {'/'.join(str(yr[k]) for k in ('2024','2025','2026'))}")

    (OUT / "fx_lock.json").write_text(json.dumps(spec, indent=2, default=str), encoding="utf-8")
    print(f"\nLocked spec -> {OUT/'fx_lock.json'}")


if __name__ == "__main__":
    main()
