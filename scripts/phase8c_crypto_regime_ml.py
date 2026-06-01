"""
Crypto regime-routed ML module (the synthesis).

phase8a/8b: momentum wins in trending regimes, mean-reversion wins in choppy (2026).
Raw legs ~0.95-1.0; the edge needs ML SELECTION (like FX: raw 0.7 -> ML 1.3). This builds
the routed ML module:
  - TREND bars (state trend_regime in UP/DOWN): trend-follow ranker (label = trend trade wins)
  - RANGE bars: mean-reversion ranker (label = fade reverts)
  - POOLED top-N across both legs + proba sizing. Walk-forward, per-year, cost-swept.

Goal: ML lifts both legs so the routed module is all-years-positive incl 2026 (where the
MR leg is already raw-strong, 1.21). If robust -> crypto module candidate.

Output: results/model_validation/phase8c_regime_ml_<UTC>/regime_ml.json
Run:    python scripts/phase8c_crypto_regime_ml.py
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

from core.features.engineer import ema, atr as atr_fn
from core.state.market_state import classify_market_state, TREND_UP, TREND_DOWN, RANGE
from core.train.dataset import NON_FEATURE_COLS
from phase6_perclass import build_class, SEEDS, VAL_WEEKS, FOLD_STARTS, calib
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from model_validation_suite import train_lgbm, predict

SYMBOLS = ["BTCUSD", "ETHUSD"]
TB, NFEAT, TOPN = 24, 9, 8
MR_THR, MR_TP, MR_SL = 1.5, 1.0, 2.0
TF_TP, TF_SL = 1.5, 1.0
COSTS = [0.02, 0.05]


def trail(o, h, l, c, a, i, d, tp_R, sl_R):
    entry = c[i]
    if d > 0:
        tp, sl = entry + tp_R * a, entry - sl_R * a
        for k in range(i + 1, i + 1 + TB):
            if l[k] <= sl: return -sl_R
            if h[k] >= tp: return tp_R
    else:
        tp, sl = entry - tp_R * a, entry + sl_R * a
        for k in range(i + 1, i + 1 + TB):
            if h[k] >= sl: return -sl_R
            if l[k] <= tp: return tp_R
    return 0.0


def augment(pool):
    pool = pool.copy()
    for col in ["_Rtf", "_Rmr", "_isTrend", "_isRange"]:
        pool[col] = np.nan
    for s in SYMBOLS:
        m = (pool["symbol"] == s).values; idx = pool.index[m]
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{s}_5m.parquet")
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        e20 = ema(raw["close"], 20).values
        st = classify_market_state(raw); tr = st["trend_regime"].values
        o, h, l, c = raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values
        n = len(c); Rtf = np.full(n, np.nan); Rmr = np.full(n, np.nan)
        for i in range(n - TB - 1):
            av = a[i]
            if not np.isfinite(av) or av <= 0 or not np.isfinite(e20[i]): continue
            t = tr[i]
            if t in (TREND_UP, TREND_DOWN):
                Rtf[i] = trail(o, h, l, c, av, i, 1 if t == TREND_UP else -1, TF_TP, TF_SL)
            elif t == RANGE:
                z = (c[i] - e20[i]) / av
                if z >= MR_THR: Rmr[i] = trail(o, h, l, c, av, i, -1, MR_TP, MR_SL)
                elif z <= -MR_THR: Rmr[i] = trail(o, h, l, c, av, i, +1, MR_TP, MR_SL)
        S = lambda arr: pd.Series(arr, index=raw.index).reindex(idx).values
        pool.loc[m, "_Rtf"] = S(Rtf); pool.loc[m, "_Rmr"] = S(Rmr)
        pool.loc[m, "_isTrend"] = S(np.isin(tr, [TREND_UP, TREND_DOWN]).astype(float))
        pool.loc[m, "_isRange"] = S((tr == RANGE).astype(float))
    return pool


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase8c_regime_ml_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool, feats = build_class(SYMBOLS)
    pool = augment(pool)
    X = lambda d, f: d[f].values.astype(np.float32)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    # feature selection per leg (pre-first-fold)
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = pool[pool.index < cut0]
    def topfeat(mask_col, R_col):
        sub = tr0[np.isfinite(tr0[R_col].values)]
        if len(sub) < 3000: return feats[:NFEAT]
        m = train_lgbm(X(sub, feats), (sub[R_col].values > 0).astype(int), X(sub, feats), (sub[R_col].values > 0).astype(int), 100, None, 42)
        return list(pd.Series(m.feature_importance(importance_type="gain"), index=feats).sort_values(ascending=False).index[:NFEAT])
    topTF = topfeat("_isTrend", "_Rtf"); topMR = topfeat("_isRange", "_Rmr")
    print(f"pool={len(pool):,}  trendfeat={topTF[:3]}...  mrfeat={topMR[:3]}...")

    acc = {c: {"R": [], "S": [], "yr": {2024: {"r": [], "s": []}, 2025: {"r": [], "s": []}, 2026: {"r": [], "s": []}}} for c in COSTS}
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]; te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            trT = tr[np.isfinite(tr["_Rtf"].values)]; trM = tr[np.isfinite(tr["_Rmr"].values)]
            vaT = va[np.isfinite(va["_Rtf"].values)]; vaM = va[np.isfinite(va["_Rmr"].values)]
            if len(trT) < 2000 or len(trM) < 1000 or len(vaT) < 200 or len(vaM) < 100: continue
            mT = train_lgbm(X(trT, topTF), (trT["_Rtf"].values > 0).astype(int), X(vaT, topTF), (vaT["_Rtf"].values > 0).astype(int), 100, None, sd)
            mM = train_lgbm(X(trM, topMR), (trM["_Rmr"].values > 0).astype(int), X(vaM, topMR), (vaM["_Rmr"].values > 0).astype(int), 100, None, sd)

            def candrows(df):
                isT = np.isfinite(df["_Rtf"].values); isM = np.isfinite(df["_Rmr"].values)
                rows = []
                if isT.sum():
                    sub = df[isT]; rows.append(pd.DataFrame({"ts": sub.index, "proba": predict(mT, "lgbm", X(sub, topTF)), "g": sub["_Rtf"].values}))
                if isM.sum():
                    sub = df[isM]; rows.append(pd.DataFrame({"ts": sub.index, "proba": predict(mM, "lgbm", X(sub, topMR)), "g": sub["_Rmr"].values}))
                c = pd.concat(rows); c["day"] = c["ts"].dt.normalize(); c["year"] = c["ts"].dt.year
                return c
            cv = candrows(va); ct = candrows(te)
            thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
            sel = ct[ct["proba"].values >= thr]; sz = tier_size(sel["proba"].values); yrs = sel["year"].values
            for c in COSTS:
                r = sel["g"].values - c
                acc[c]["R"].append(r); acc[c]["S"].append(sz)
                for y in (2024, 2025, 2026):
                    mk = yrs == y; acc[c]["yr"][y]["r"].append(sel["g"].values[mk] - c); acc[c]["yr"][y]["s"].append(sz[mk])

    res = {}
    for c in COSTS:
        allR = np.concatenate(acc[c]["R"]) if acc[c]["R"] else np.array([]); allS = np.concatenate(acc[c]["S"]) if acc[c]["S"] else np.array([])
        st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
        yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"] for y, v in acc[c]["yr"].items()}
        allpos = all(v and v > 1.0 for v in yr.values())
        res[f"{c}ATR"] = dict(net_pf=st["pf"], wr=st["wr"], trades_per_day=round(st["n"]/(len(SEEDS)*days), 2), pf_by_year=yr, bar_pass=(st["pf"] is not None and st["pf"] >= 1.3 and allpos), all_years_pos=allpos)
    (OUT / "regime_ml.json").write_text(json.dumps(dict(trendfeat=topTF, mrfeat=topMR, costs=COSTS, results=res), indent=2, default=str), encoding="utf-8")
    print(f"\n{'cost':6s} {'net_PF':>7s} {'WR':>6s} {'tr/day':>7s} {'years':>22s} {'allpos':>7s} {'BAR'}")
    for c in COSTS:
        d = res[f"{c}ATR"]; yr = "/".join(str(d["pf_by_year"][k]) for k in ("2024", "2025", "2026"))
        print(f"{c:<6} {str(d['net_pf']):>7s} {str(d['wr']):>6s} {d['trades_per_day']:>7.2f} {yr:>22s} {str(d['all_years_pos']):>7s} {d['bar_pass']}")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
