"""
Phase 4 batch 2a: variance reduction + expectancy levers (cheap, robust).

  ENSEMBLE : average the ranker proba over multiple seeds -> steadier top-decile
             -> better realized PF + lower std (no extra trades, no lookahead).
  SIZED    : proba-tiered position sizing within the selected set (0.5/1.0/1.5x by
             proba tercile). WR unchanged; lifts R-weighted PF/expectancy. Product lever.

Baseline = locked V1 (long + USDCHF-short, POOLED top10, ECN 0.5pip, long-9).
Reports WR / PF / trades-day / std + per-year.

Output: results/model_validation/phase4_ens_size_<UTC>/ens_size.json
Run:    python scripts/phase4_ensemble_sizing.py
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
from phase3_v1_config import build_cands   # long + USDCHF-short pooled candidates
from model_validation_suite import train_lgbm, predict

SPREAD, TOPN = 0.5, 10
ENS_SEEDS = [42, 7, 13, 21]


def pf_wr_sized(r, size=None):
    r = np.asarray(r, float); ok = np.isfinite(r)
    r = r[ok]; sz = (np.ones_like(r) if size is None else np.asarray(size, float)[ok])
    if len(r) < 10:
        return None
    rr = r * sz
    gw = rr[r > 0].sum(); gl = -rr[r <= 0].sum(); w = int((r > 0).sum())
    return dict(n=int(len(r)), wr=round(w / len(r), 3), pf=round(float(gw / gl), 3) if gl > 0 else 999.0)


def tier_size(proba):
    if len(proba) < 3:
        return np.ones_like(proba)
    q1, q2 = np.quantile(proba, [1 / 3, 2 / 3])
    return np.where(proba < q1, 0.5, np.where(proba < q2, 1.0, 1.5))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase4_ens_size_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d: d[FEATURES_9].values.astype(np.float32)
    print(f"pool={len(pool):,}  ens_seeds={ENS_SEEDS}")

    variants = ["V1_single", "ENSEMBLE", "ENSEMBLE_SIZED"]
    acc = {v: {"R": [], "S": [], "pf": [], "yr": {}} for v in variants}

    for ts0 in FOLD_STARTS:
        te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
        te = pool[(pool.index >= te_s) & (pool.index < te_e)]
        if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
        gv = va["_in_ny"].values & va["_tradeable"].values
        gt = te["_in_ny"].values & te["_tradeable"].values
        if gv.sum() < 100 or gt.sum() < 100: continue
        VL = {}; TL = {}; VS = {}; TS = {}
        for sd in ENS_SEEDS:
            mL = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, 100, None, sd)
            mS = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, 100, None, sd)
            VL[sd], TL[sd] = predict(mL, "lgbm", X(va)), predict(mL, "lgbm", X(te))
            VS[sd], TS[sd] = predict(mS, "lgbm", X(va)), predict(mS, "lgbm", X(te))
        ensVL = np.mean([VL[s] for s in ENS_SEEDS], 0); ensTL = np.mean([TL[s] for s in ENS_SEEDS], 0)
        ensVS = np.mean([VS[s] for s in ENS_SEEDS], 0); ensTS = np.mean([TS[s] for s in ENS_SEEDS], 0)

        def evaluate(name, vL, tL, vS, tS, sized):
            cv = build_cands(va, vL, vS, gv, "long_short_usdchf")
            ct = build_cands(te, tL, tS, gt, "long_short_usdchf")
            thr = calib_thr(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
            sel = ct[ct["proba"].values >= thr]
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

        evaluate("V1_single", VL[42], TL[42], VS[42], TS[42], False)
        evaluate("ENSEMBLE", ensVL, ensTL, ensVS, ensTS, False)
        evaluate("ENSEMBLE_SIZED", ensVL, ensTL, ensVS, ensTS, True)

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
    (OUT / "ens_size.json").write_text(json.dumps(dict(spread=SPREAD, topN=TOPN, ens_seeds=ENS_SEEDS, results=res),
                                                   indent=2, default=str), encoding="utf-8")
    print(f"\n{'variant':16s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'tr/day':>7s}  {'PF 24/25/26'}")
    for v in variants:
        d = res[v]; pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else " n/a"
        yr = "/".join(str(d["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
        print(f"{v:16s} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>7.2f}  {yr}")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
