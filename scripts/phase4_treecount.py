"""
Phase 4: does the META edge survive fewer trees (so it fits the Pine ops budget)?

META adds a 2nd model -> 4 cascades total. Measured Pine: feature-engine F~2060 ops,
cascade C(100 trees)~1179 ops, budget 5000. V1+META@100t = 2060+4*1179 = 6776 (136%).
Cascade ops ~ linear in tree count, so this script sweeps trees in {50,60,75,100} for
BOTH primary and meta, reports WR/PF/year, and projects the Pine budget per tree count.
Fit target: V1+META <= ~88% (4420 ops) -> C <= ~590 -> ~50 trees, or relax to <=100%.

Config = locked V1 (long + USDCHF-short, POOLED top10, ECN 0.5pip).
Output: results/model_validation/phase4_treecount_<UTC>/treecount.json
Run:    python scripts/phase4_treecount.py
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
TREES = [50, 60, 75, 100]
F_OPS, C_OPS_100, BUDGET = 2060, 1179, 5000   # measured Pine constants


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase4_treecount_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    feats_full = feature_cols(pool)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d, f=FEATURES_9: d[f].values.astype(np.float32)
    print(f"pool={len(pool):,}  trees={TREES}")

    def sel_from(va_c, te_c):
        thr = calib_thr(va_c["proba"].values, max(1, va_c["day"].nunique()), TOPN)
        return te_c[te_c["proba"].values >= thr]

    results = {}
    for nt in TREES:
        acc = {"META": {"R": [], "S": [], "pf": [], "yr": {}}, "META_SIZED": {"R": [], "S": [], "pf": [], "yr": {}}}
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            gv = va["_in_ny"].values & va["_tradeable"].values
            gt = te["_in_ny"].values & te["_tradeable"].values
            if gv.sum() < 100 or gt.sum() < 100: continue
            mL = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, nt, None, SEED)
            mS = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, nt, None, SEED)
            pvL, ptL = predict(mL, "lgbm", X(va)), predict(mL, "lgbm", X(te))
            pvS, ptS = predict(mS, "lgbm", X(va)), predict(mS, "lgbm", X(te))
            ndays = max(1, va.index[gv].normalize().nunique())
            genL = calib_thr(pvL[gv], ndays, TOPN * GEN_MULT); genS = calib_thr(pvS[gv], ndays, TOPN * GEN_MULT)
            trva = pool[pool.index < te_s]; gtrva = trva["_in_ny"].values & trva["_tradeable"].values
            candL = gtrva & (mL.predict(X(trva)) >= genL); candS = gtrva & (mS.predict(X(trva)) >= genS)
            if candL.sum() <= 200 or candS.sum() <= 200: continue
            metaL = train_lgbm(X(trva[candL], feats_full), trva["_lab_long"].values[candL],
                               X(trva[candL], feats_full), trva["_lab_long"].values[candL], nt, None, SEED)
            metaS = train_lgbm(X(trva[candS], feats_full), trva["_lab_short"].values[candS],
                               X(trva[candS], feats_full), trva["_lab_short"].values[candS], nt, None, SEED)

            def marr(df, primP, gen, meta):
                cand = (df["_in_ny"].values & df["_tradeable"].values) & (primP >= gen)
                out = np.full(len(df), NEG)
                if cand.sum():
                    out[cand] = meta.predict(X(df[cand], feats_full))
                return out
            sel = sel_from(
                build_cands(va, marr(va, pvL, genL, metaL), marr(va, pvS, genS, metaS), gv, "long_short_usdchf"),
                build_cands(te, marr(te, ptL, genL, metaL), marr(te, ptS, genS, metaS), gt, "long_short_usdchf"))
            for name, sized in [("META", False), ("META_SIZED", True)]:
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

        c_ops = C_OPS_100 * nt / 100.0
        ops_meta = F_OPS + 4 * c_ops
        results[nt] = {"META": block(acc["META"]), "META_SIZED": block(acc["META_SIZED"]),
                       "pine_ops_v1_meta": int(ops_meta), "pine_pct": round(ops_meta / BUDGET, 2)}

    (OUT / "treecount.json").write_text(json.dumps(dict(spread=SPREAD, topN=TOPN, trees=TREES,
        pine={"F": F_OPS, "C100": C_OPS_100, "budget": BUDGET}, results=results), indent=2, default=str), encoding="utf-8")
    print(f"\n{'trees':6s} {'variant':12s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'tr/day':>7s} {'PF 24/25/26':>18s} {'PineBudget':>11s}")
    for nt in TREES:
        for v in ("META", "META_SIZED"):
            d = results[nt][v]; pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else " n/a"
            yr = "/".join(str(d["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
            bud = f"{results[nt]['pine_pct']:.0%}" if v == "META" else ""
            print(f"{nt:<6d} {v:12s} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>7.2f} {yr:>18s} {bud:>11s}")
    print(f"\nTarget: highest tree count whose V1+META Pine budget <= ~100% with edge intact. Done -> {OUT}")


if __name__ == "__main__":
    main()
