"""
Phase 6b: per-class models WITH the full FX quality stack.

phase6 (plain per-class) gave ~1.0-1.1, none at the 1.3 bar -- but it lacked the stack
that lifted FX from ~1.0 to 1.30-1.52, and used a too-broad adaptive gate. Here each
class gets the proven stack:
  - TIGHTER session: top-third highest-range UTC hours (learned per fold from train)
  - class-own top-9 features
  - long + short, POOLED top-N
  - META re-rank (full-feature secondary model on candidates)
  - proba-tiered sizing (0.5/1.0/1.5x)

Walk-forward, net @5% ATR, per-year. Verdict per class vs AI bar (PF>=1.3 + all years +).

Output: results/model_validation/phase6b_stack_<UTC>/perclass_stack.json
Run:    python scripts/phase6b_perclass_stack.py
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

from phase6_perclass import build_class, CLASSES, SEEDS, VAL_WEEKS, FOLD_STARTS, calib
from model_validation_suite import train_lgbm, predict

SPREAD_COST, TOPN, NFEAT, GEN_MULT, NEG = 0.05, 8, 9, 3.0, -1e9


def tighter_hours(tr):
    m = tr.groupby("_hour")["_range_raw"].mean()
    thr = np.quantile(m.values, 0.67)               # top third most active hours
    return set(m.index[m.values >= thr].tolist())


def tier_size(p):
    if len(p) < 3:
        return np.ones_like(p)
    q1, q2 = np.quantile(p, [1/3, 2/3])
    return np.where(p < q1, 0.5, np.where(p < q2, 1.0, 1.5))


def pf_sized(r, sz):
    r = np.asarray(r, float); ok = np.isfinite(r); r = r[ok]; sz = np.asarray(sz, float)[ok]
    if len(r) < 10:
        return None
    rr = r * sz; gw = rr[r > 0].sum(); gl = -rr[r <= 0].sum(); w = int((r > 0).sum())
    return dict(n=int(len(r)), wr=round(w/len(r), 3), pf=round(float(gw/gl), 3) if gl > 0 else 999.0)


def cands(df, ptL, ptS, gate):
    gi = np.where(gate)[0]; ts = df.index[gi]
    fr = [pd.DataFrame({"ts": ts, "proba": ptL[gi], "g": df["_grossR_long"].values[gi], "row": gi}),
          pd.DataFrame({"ts": ts, "proba": ptS[gi], "g": df["_grossR_short"].values[gi], "row": gi})]
    c = pd.concat(fr).sort_values("proba", ascending=False).drop_duplicates("row")
    c["day"] = c["ts"].dt.normalize(); c["year"] = c["ts"].dt.year
    return c


def eval_class(symbols):
    pool, feats = build_class(symbols)
    if pool is None or len(pool) < 20000:
        return None
    X = lambda d, f: d[f].values.astype(np.float32)
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = pool[pool.index < cut0]
    if len(tr0) < 5000:
        return None
    m0 = train_lgbm(X(tr0, feats), (tr0["_grossR_long"].values > 0).astype(int),
                    X(tr0, feats), (tr0["_grossR_long"].values > 0).astype(int), 100, None, 42)
    imp = pd.Series(m0.feature_importance(importance_type="gain"), index=feats).sort_values(ascending=False)
    top = list(imp.index[:NFEAT])
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    Rsel, Ssel = [], []; yr = {2024: {"r": [], "s": []}, 2025: {"r": [], "s": []}, 2026: {"r": [], "s": []}}
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            ah = tighter_hours(tr)
            gv = va["_tradeable"].values & va["_hour"].isin(ah).values
            gt = te["_tradeable"].values & te["_hour"].isin(ah).values
            if gv.sum() < 100 or gt.sum() < 100: continue
            yl = lambda d: (d["_grossR_long"].values > 0).astype(int); ys = lambda d: (d["_grossR_short"].values > 0).astype(int)
            mL = train_lgbm(X(tr, top), yl(tr), X(va, top), yl(va), 100, None, sd)
            mS = train_lgbm(X(tr, top), ys(tr), X(va, top), ys(va), 100, None, sd)
            pvL, ptL = predict(mL, "lgbm", X(va, top)), predict(mL, "lgbm", X(te, top))
            pvS, ptS = predict(mS, "lgbm", X(va, top)), predict(mS, "lgbm", X(te, top))
            # meta: generous primary candidates -> secondary full-feature re-rank
            gd = max(1, va.index[gv].normalize().nunique())
            genL = calib(pvL[gv], gd, TOPN * GEN_MULT); genS = calib(pvS[gv], gd, TOPN * GEN_MULT)
            trva = pool[pool.index < te_s]; gtrva = trva["_tradeable"].values & trva["_hour"].isin(ah).values
            cL = gtrva & (mL.predict(X(trva, top)) >= genL); cS = gtrva & (mS.predict(X(trva, top)) >= genS)
            if cL.sum() <= 200 or cS.sum() <= 200: continue
            meL = train_lgbm(X(trva[cL], feats), yl(trva[cL]), X(trva[cL], feats), yl(trva[cL]), 100, None, sd)
            meS = train_lgbm(X(trva[cS], feats), ys(trva[cS]), X(trva[cS], feats), ys(trva[cS]), 100, None, sd)
            def marr(d, pp, gen, me):
                c = (d["_tradeable"].values & d["_hour"].isin(ah).values) & (pp >= gen)
                out = np.full(len(d), NEG)
                if c.sum(): out[c] = me.predict(X(d[c], feats))
                return out
            cv = cands(va, marr(va, pvL, genL, meL), marr(va, pvS, genS, meS), gv)
            ct = cands(te, marr(te, ptL, genL, meL), marr(te, ptS, genS, meS), gt)
            thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
            sel = ct[ct["proba"].values >= thr]
            sz = tier_size(sel["proba"].values)
            Rsel.append(sel["g"].values); Ssel.append(sz)
            for y in yr:
                mk = sel["year"].values == y
                yr[y]["r"].append(sel["g"].values[mk]); yr[y]["s"].append(sz[mk])
    allR = np.concatenate(Rsel) if Rsel else np.array([]); allS = np.concatenate(Ssel) if Ssel else np.array([])
    st = pf_sized(allR - SPREAD_COST, allS) or {"n": 0, "wr": None, "pf": None}
    yrpf = {str(y): (pf_sized(np.concatenate(v["r"]) - SPREAD_COST, np.concatenate(v["s"])) or {"pf": None})["pf"] for y, v in yr.items()}
    return dict(features=top, trades_per_day=round(st["n"]/(len(SEEDS)*days), 2),
                net_pf=st["pf"], wr=st["wr"], pf_by_year=yrpf)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase6b_stack_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for cls, syms in CLASSES.items():
        print(f"[{cls}] ...", flush=True)
        try:
            res[cls] = eval_class(syms)
        except Exception as e:
            res[cls] = {"error": f"{type(e).__name__}: {e}"}
        r = res[cls]
        if r and r.get("net_pf") is not None:
            yp = r["pf_by_year"]; allpos = all(v and v > 1.0 for v in yp.values())
            print(f"   PF {r['net_pf']}  WR {r['wr']}  {r['trades_per_day']}/day  years {yp}  BAR={r['net_pf']>=1.3 and allpos}")
        else:
            print(f"   {r}")
    verdict = {}
    for cls, r in res.items():
        if r and r.get("net_pf") is not None:
            yp = r["pf_by_year"]; allpos = all(v and v > 1.0 for v in yp.values())
            verdict[cls] = dict(net_pf=r["net_pf"], all_years_pos=allpos, bar_pass=(r["net_pf"] >= 1.3 and allpos))
        else:
            verdict[cls] = None
    (OUT / "perclass_stack.json").write_text(json.dumps(dict(cost=SPREAD_COST, topn=TOPN, per_class=res, verdict=verdict), indent=2, default=str), encoding="utf-8")
    print(f"\n{'class':8s} {'net_PF':>7s} {'WR':>6s} {'tr/day':>7s} {'years':>22s} {'BAR':>5s}")
    for cls, r in res.items():
        if not r or r.get("net_pf") is None:
            print(f"{cls:8s}  (skip)"); continue
        yp = "/".join(str(r["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
        print(f"{cls:8s} {r['net_pf']:>7} {str(r['wr']):>6s} {r['trades_per_day']:>7.2f} {yp:>22s} {str(verdict[cls]['bar_pass']):>5s}")
    passed = [c for c, v in verdict.items() if v and v["bar_pass"]]
    print(f"\nClasses passing AI bar with full stack: {passed}")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
