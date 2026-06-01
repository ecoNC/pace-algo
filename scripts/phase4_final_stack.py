"""
Phase 4 final: confirm the two winning levers STACK.

  META  : secondary full-73 model re-ranks primary candidates (precision).  +WR +PF
  SIZED : proba/meta-tiered position size 0.5/1.0/1.5x within selected set.  +PF

Variants: V1_baseline, BASELINE_SIZED, META, META_SIZED.
Locked V1 selection (long + USDCHF-short, POOLED top10, ECN 0.5pip, long-9, seed 42).

Output: results/model_validation/phase4_final_<UTC>/final.json
Run:    python scripts/phase4_final_stack.py
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

SPREAD, TOPN, SEED, GEN_MULT, NEG = 0.5, 10, 42, 3.0, -1e9


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase4_final_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    feats_full = feature_cols(pool)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d, f=FEATURES_9: d[f].values.astype(np.float32)
    print(f"pool={len(pool):,}  full_features={len(feats_full)}")

    variants = ["V1_baseline", "BASELINE_SIZED", "META", "META_SIZED"]
    acc = {v: {"R": [], "S": [], "pf": [], "yr": {}} for v in variants}

    def record(name, sel, sized):
        r = netR(sel["gR"].values, sel["cost"].values, SPREAD)
        sz = tier_size(sel["proba"].values) if sized else np.ones(len(sel))
        acc[name]["R"].append(r); acc[name]["S"].append(sz)
        st = pf_wr_sized(r, sz); acc[name]["pf"].append(st["pf"] if st else None)
        yrs = sel["ts"].dt.year.values
        for y in (2024, 2025, 2026):
            mk = yrs == y
            acc[name]["yr"].setdefault(y, {"R": [], "S": []})
            acc[name]["yr"][y]["R"].append(netR(sel["gR"].values[mk], sel["cost"].values[mk], SPREAD))
            acc[name]["yr"][y]["S"].append(sz[mk])

    def sel_from(va_c, te_c):
        thr = calib_thr(va_c["proba"].values, max(1, va_c["day"].nunique()), TOPN)
        return te_c[te_c["proba"].values >= thr]

    for ts0 in FOLD_STARTS:
        te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
        te = pool[(pool.index >= te_s) & (pool.index < te_e)]
        if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
        gv = va["_in_ny"].values & va["_tradeable"].values
        gt = te["_in_ny"].values & te["_tradeable"].values
        if gv.sum() < 100 or gt.sum() < 100: continue
        mL = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, 100, None, SEED)
        mS = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, 100, None, SEED)
        pvL, ptL = predict(mL, "lgbm", X(va)), predict(mL, "lgbm", X(te))
        pvS, ptS = predict(mS, "lgbm", X(va)), predict(mS, "lgbm", X(te))

        base_sel = sel_from(build_cands(va, pvL, pvS, gv, "long_short_usdchf"),
                            build_cands(te, ptL, ptS, gt, "long_short_usdchf"))
        record("V1_baseline", base_sel, False)
        record("BASELINE_SIZED", base_sel, True)

        # META
        ndays = max(1, va.index[gv].normalize().nunique())
        genL = calib_thr(pvL[gv], ndays, TOPN * GEN_MULT); genS = calib_thr(pvS[gv], ndays, TOPN * GEN_MULT)
        trva = pool[pool.index < te_s]; gtrva = trva["_in_ny"].values & trva["_tradeable"].values
        candL = gtrva & (mL.predict(X(trva)) >= genL); candS = gtrva & (mS.predict(X(trva)) >= genS)
        if candL.sum() > 200 and candS.sum() > 200:
            metaL = train_lgbm(X(trva[candL], feats_full), trva["_lab_long"].values[candL],
                               X(trva[candL], feats_full), trva["_lab_long"].values[candL], 100, None, SEED)
            metaS = train_lgbm(X(trva[candS], feats_full), trva["_lab_short"].values[candS],
                               X(trva[candS], feats_full), trva["_lab_short"].values[candS], 100, None, SEED)

            def marr(df, primP, gen, meta):
                cand = (df["_in_ny"].values & df["_tradeable"].values) & (primP >= gen)
                out = np.full(len(df), NEG)
                if cand.sum():
                    out[cand] = meta.predict(X(df[cand], feats_full))
                return out
            meta_sel = sel_from(
                build_cands(va, marr(va, pvL, genL, metaL), marr(va, pvS, genS, metaS), gv, "long_short_usdchf"),
                build_cands(te, marr(te, ptL, genL, metaL), marr(te, ptS, genS, metaS), gt, "long_short_usdchf"))
            record("META", meta_sel, False)
            record("META_SIZED", meta_sel, True)

    def block(d):
        allR = np.concatenate(d["R"]) if d["R"] else np.array([])
        allS = np.concatenate(d["S"]) if d["S"] else np.array([])
        st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
        pfl = [p for p in d["pf"] if p is not None]
        yr = {str(y): (pf_wr_sized(np.concatenate(v["R"]), np.concatenate(v["S"])) or {"pf": None})["pf"]
              for y, v in d["yr"].items()}
        return dict(trades_per_day=round(st["n"] / days, 2),
                    net_pf=round(float(np.mean(pfl)), 3) if pfl else None,
                    pf_std=round(float(np.std(pfl)), 3) if pfl else None, wr=st["wr"], pf_by_year=yr)

    res = {v: block(acc[v]) for v in variants}
    (OUT / "final.json").write_text(json.dumps(dict(spread=SPREAD, topN=TOPN, results=res), indent=2, default=str), encoding="utf-8")
    print(f"\n{'variant':16s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'tr/day':>7s}  {'PF 24/25/26'}")
    for v in variants:
        d = res[v]; pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else " n/a"
        yr = "/".join(str(d["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
        print(f"{v:16s} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>7.2f}  {yr}")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
