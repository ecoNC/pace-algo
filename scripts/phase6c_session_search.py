"""
Phase 6c: find each class's EDGE-bearing session by net-PF (not by range).

phase6b's lesson: range-based auto-session picks the most volatile hours, not the
edge-bearing ones -> even FX collapsed (1.30 NY -> 0.96 range-hours). The right method is
how NY was found for FX: pick the session window that maximizes VALIDATION net-PF, applied
causally to test (no lookahead). This gives every class a fair, PF-based session.

Per class, per fold: train primary long/short (class-own top-9), evaluate candidate
session windows on gated validation, pick the best by val net-PF, apply to test. Plus
proba sizing. (Meta deferred — session is the dominant factor; add later if a class clears.)

Output: results/model_validation/phase6c_session_<UTC>/session_search.json
Run:    python scripts/phase6c_session_search.py
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

SPREAD_COST, TOPN, NFEAT = 0.05, 8, 9
# candidate session windows (UTC hour start inclusive, end exclusive); FULL = 24/7
WINDOWS = {
    "NY_13_22": (13, 22), "US_RTH_14_21": (14, 21), "LDN_NY_8_22": (8, 22),
    "LDN_7_16": (7, 16), "US_PM_16_22": (16, 22), "EU_US_12_21": (12, 21),
    "ASIA_0_9": (0, 9), "FULL": (0, 24),
}


def in_window(hours, w):
    s, e = w
    return (hours >= s) & (hours < e) if e <= 24 else (hours >= s)


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


def select(va_c, te_c):
    thr = calib(va_c["proba"].values, max(1, va_c["day"].nunique()), TOPN)
    return te_c[te_c["proba"].values >= thr]


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
    win_pick = {}
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            yl = lambda d: (d["_grossR_long"].values > 0).astype(int); ys = lambda d: (d["_grossR_short"].values > 0).astype(int)
            mL = train_lgbm(X(tr, top), yl(tr), X(va, top), yl(va), 100, None, sd)
            mS = train_lgbm(X(tr, top), ys(tr), X(va, top), ys(va), 100, None, sd)
            pvL, ptL = predict(mL, "lgbm", X(va, top)), predict(mL, "lgbm", X(te, top))
            pvS, ptS = predict(mS, "lgbm", X(va, top)), predict(mS, "lgbm", X(te, top))
            vh = va["_hour"].values; th = te["_hour"].values
            vtr = va["_tradeable"].values; ttr = te["_tradeable"].values
            # pick window by validation net-PF (sized)
            best_w, best_pf = None, -1
            for wn, w in WINDOWS.items():
                gv = vtr & in_window(vh, w)
                if gv.sum() < 100: continue
                cv = cands(va, pvL, pvS, gv)
                thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
                s = cv[cv["proba"].values >= thr]
                st = pf_sized(s["g"].values - SPREAD_COST, tier_size(s["proba"].values))
                if st and st["pf"] > best_pf:
                    best_pf, best_w = st["pf"], wn
            if best_w is None: continue
            win_pick[best_w] = win_pick.get(best_w, 0) + 1
            w = WINDOWS[best_w]
            gv = vtr & in_window(vh, w); gt = ttr & in_window(th, w)
            if gt.sum() < 100: continue
            sel = select(cands(va, pvL, pvS, gv), cands(te, ptL, ptS, gt))
            sz = tier_size(sel["proba"].values)
            Rsel.append(sel["g"].values); Ssel.append(sz)
            for y in yr:
                mk = sel["year"].values == y
                yr[y]["r"].append(sel["g"].values[mk]); yr[y]["s"].append(sz[mk])
    allR = np.concatenate(Rsel) if Rsel else np.array([]); allS = np.concatenate(Ssel) if Ssel else np.array([])
    st = pf_sized(allR - SPREAD_COST, allS) or {"n": 0, "wr": None, "pf": None}
    yrpf = {str(y): (pf_sized(np.concatenate(v["r"]) - SPREAD_COST, np.concatenate(v["s"])) or {"pf": None})["pf"] for y, v in yr.items()}
    return dict(features=top, windows_picked=win_pick, trades_per_day=round(st["n"]/(len(SEEDS)*days), 2),
                net_pf=st["pf"], wr=st["wr"], pf_by_year=yrpf)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase6c_session_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
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
            print(f"   PF {r['net_pf']}  WR {r['wr']}  {r['trades_per_day']}/day  win {r['windows_picked']}  years {yp}  BAR={r['net_pf']>=1.3 and allpos}")
        else:
            print(f"   {r}")
    verdict = {}
    for cls, r in res.items():
        if r and r.get("net_pf") is not None:
            yp = r["pf_by_year"]; allpos = all(v and v > 1.0 for v in yp.values())
            verdict[cls] = dict(net_pf=r["net_pf"], all_years_pos=allpos, bar_pass=(r["net_pf"] >= 1.3 and allpos))
        else:
            verdict[cls] = None
    (OUT / "session_search.json").write_text(json.dumps(dict(cost=SPREAD_COST, windows=WINDOWS, per_class=res, verdict=verdict), indent=2, default=str), encoding="utf-8")
    print(f"\n{'class':8s} {'net_PF':>7s} {'WR':>6s} {'tr/day':>7s} {'years':>22s} {'BAR':>5s}")
    for cls, r in res.items():
        if not r or r.get("net_pf") is None:
            print(f"{cls:8s}  (skip)"); continue
        yp = "/".join(str(r["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
        print(f"{cls:8s} {r['net_pf']:>7} {str(r['wr']):>6s} {r['trades_per_day']:>7.2f} {yp:>22s} {str(verdict[cls]['bar_pass']):>5s}")
    passed = [c for c, v in verdict.items() if v and v["bar_pass"]]
    print(f"\nClasses passing AI bar with PF-chosen session: {passed}")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
