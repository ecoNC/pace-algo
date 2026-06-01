"""
Phase 6: PER-ASSET-CLASS tailored models (the ANN-009 router test).

Universal failed; the plan is now one model per asset class WITH class-appropriate
structure. For each class (fx / crypto / metal / index) we give it:
  - its OWN top-N features (gain-importance on that class's pre-fold train window)
  - an ADAPTIVE activity-window session gate: the high-range UTC hours learned PER FOLD
    from train (auto = NY for FX, RTH for indices, US-active for crypto/metals). No
    hardcoded session, no lookahead.
  - the vol-regime gate (QUIET/SHOCK = no-trade), long+short, POOLED top-N, R=1.5.

Walk-forward, net @ {0, 5%, 10%} ATR cost, per-year. Verdict per class vs the per-class
AI bar: net PF >= 1.3 (@5% ATR) AND all years positive.

Output: results/model_validation/phase6_perclass_<UTC>/perclass.json
Run:    python scripts/phase6_perclass.py
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

from setup_makeorbreak import barrier_R
from model_validation_suite import build_extended, train_lgbm, predict
from core.state.market_state import classify_market_state
from core.features.engineer import atr as atr_fn
from core.train.dataset import NON_FEATURE_COLS

CLASSES = {
    "fx":     ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF"],
    "crypto": ["BTCUSD", "ETHUSD"],
    "metal":  ["XAUUSD", "XAGUSD"],
    "index":  ["SPX500", "NAS100"],
}
SEEDS = [42, 7]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
COSTS = [0.0, 0.05, 0.10]
TOPN = 8
NFEAT = 9


def build_class(symbols):
    frames = []
    for s in symbols:
        ext = build_extended(s)
        if ext is None or ext.empty:
            continue
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{s}_5m.parquet")
        st = classify_market_state(raw)
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        idx = raw.index
        gL = barrier_R(raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values, a, "long")
        gS = barrier_R(raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values, a, "short")
        ext["_tradeable"] = st["tradeable"].reindex(ext.index).values
        ext["_grossR_long"] = pd.Series(gL, index=idx).reindex(ext.index).values
        ext["_grossR_short"] = pd.Series(gS, index=idx).reindex(ext.index).values
        ext["_hour"] = ext.index.hour
        ext["_range_raw"] = pd.Series((raw["high"] - raw["low"]).values, index=idx).reindex(ext.index).values
        ext["symbol"] = s
        frames.append(ext)
    if not frames:
        return None, None
    pool = pd.concat(frames).sort_index()
    feats = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"
             and c != "label" and not c.startswith("_")]
    pool = pool.dropna(subset=feats + ["_grossR_long", "_grossR_short", "_range_raw"])
    return pool, feats


def active_hours(tr):
    """High-range UTC hours learned from train (>= median hourly mean range). Adaptive session."""
    m = tr.groupby("_hour")["_range_raw"].mean()
    return set(m.index[m.values >= np.median(m.values)].tolist())


def stats_cost(grossR, cost):
    r = grossR - cost; r = r[np.isfinite(r)]
    if len(r) < 10:
        return None
    w = int((r > 0).sum()); gw = r[r > 0].sum(); gl = -r[r <= 0].sum()
    return dict(n=int(len(r)), wr=round(w / len(r), 3), pf=round(float(gw / gl), 3) if gl > 0 else 999.0)


def calib(p, gdays, per_day):
    n = len(p)
    if n == 0 or gdays == 0:
        return np.inf
    return float(np.quantile(p, min(max(1 - per_day * gdays / n, 0.0), 0.9995)))


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
    # class-own top-N features via gain importance on pre-first-fold train
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS)
    tr0 = pool[pool.index < cut0]
    if len(tr0) < 5000:
        return None
    m0 = train_lgbm(X(tr0, feats), (tr0["_grossR_long"].values > 0).astype(int),
                    X(tr0, feats), (tr0["_grossR_long"].values > 0).astype(int), 100, None, 42)
    imp = pd.Series(m0.feature_importance(importance_type="gain"), index=feats).sort_values(ascending=False)
    top = list(imp.index[:NFEAT])
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    sel_g = []; yr_g = {2024: [], 2025: [], 2026: []}
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            ah = active_hours(tr)
            gv = va["_tradeable"].values & va["_hour"].isin(ah).values
            gt = te["_tradeable"].values & te["_hour"].isin(ah).values
            if gv.sum() < 100 or gt.sum() < 100: continue
            mL = train_lgbm(X(tr, top), (tr["_grossR_long"].values > 0).astype(int), X(va, top), (va["_grossR_long"].values > 0).astype(int), 100, None, sd)
            mS = train_lgbm(X(tr, top), (tr["_grossR_short"].values > 0).astype(int), X(va, top), (va["_grossR_short"].values > 0).astype(int), 100, None, sd)
            cv = cands(va, predict(mL, "lgbm", X(va, top)), predict(mS, "lgbm", X(va, top)), gv)
            ct = cands(te, predict(mL, "lgbm", X(te, top)), predict(mS, "lgbm", X(te, top)), gt)
            thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
            sel = ct[ct["proba"].values >= thr]
            sel_g.append(sel["g"].values)
            for y in yr_g:
                yr_g[y].append(sel[sel["year"] == y]["g"].values)
    allg = np.concatenate(sel_g) if sel_g else np.array([])
    out = {"features": top, "active_hours_last": sorted(ah),
           "trades_per_day": round(len(allg[np.isfinite(allg)]) / (len(SEEDS) * days), 2)}
    for c in COSTS:
        out[f"cost{c}"] = stats_cost(allg, c)
    out["pf_by_year_5pct"] = {str(y): (stats_cost(np.concatenate(v), 0.05) or {"pf": None})["pf"] for y, v in yr_g.items()}
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase6_perclass_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for cls, syms in CLASSES.items():
        print(f"[{cls}] {syms} ...", flush=True)
        try:
            res[cls] = eval_class(syms)
        except Exception as e:
            res[cls] = {"error": f"{type(e).__name__}: {e}"}
        r = res[cls]
        if r and "cost0.05" in r and r["cost0.05"]:
            c5 = r["cost0.05"]
            yrs = r["pf_by_year_5pct"]
            allpos = all(v is not None and v > 1.0 for v in yrs.values())
            print(f"   PF@5% {c5['pf']}  WR {c5['wr']}  {r['trades_per_day']}/day  years {yrs}  bar_pass={c5['pf']>=1.3 and allpos}")
        else:
            print(f"   {r}")

    verdict = {}
    for cls, r in res.items():
        if r and r.get("cost0.05"):
            yrs = r["pf_by_year_5pct"]
            allpos = all(v is not None and v > 1.0 for v in yrs.values())
            verdict[cls] = dict(pf5=r["cost0.05"]["pf"], wr=r["cost0.05"]["wr"],
                                all_years_pos=allpos, bar_pass=(r["cost0.05"]["pf"] >= 1.3 and allpos))
        else:
            verdict[cls] = None
    (OUT / "perclass.json").write_text(json.dumps(dict(topn=TOPN, nfeat=NFEAT, costs=COSTS,
        per_class=res, verdict=verdict), indent=2, default=str), encoding="utf-8")

    print(f"\n{'class':8s} {'PF_gross':>8s} {'PF_5%':>6s} {'PF_10%':>7s} {'WR':>6s} {'tr/day':>7s} {'years(5%)':>22s} {'BAR':>5s}")
    for cls, r in res.items():
        if not r or not r.get("cost0.05"):
            print(f"{cls:8s}  (skip/err)"); continue
        g = r.get("cost0.0") or {}; c5 = r["cost0.05"]; c10 = r.get("cost0.1") or {}
        yrs = "/".join(str(r["pf_by_year_5pct"].get(str(y))) for y in (2024, 2025, 2026))
        print(f"{cls:8s} {str(g.get('pf')):>8s} {c5['pf']:>6} {str(c10.get('pf')):>7s} {c5['wr']:>6} {r['trades_per_day']:>7.2f} {yrs:>22s} {str(verdict[cls]['bar_pass']):>5s}")
    passed = [c for c, v in verdict.items() if v and v["bar_pass"]]
    print(f"\nClasses passing per-class AI bar (PF>=1.3 @5% + all years +): {passed}")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
