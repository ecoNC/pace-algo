"""
Crypto module push: 6 coins + cross-sectional relative-strength feature.

phase8 solved robustness (regime-routing, all-years-positive) but PF was thin (~1.11) on
BTC+ETH only. This adds 4 coins (XRP/LTC/BCH/ADA) for more training data + a CROSS-SECTIONAL
feature (each coin's trailing return z-scored vs the basket) — the documented robust crypto
edge (relative strength). Same regime-routed ML (trend-follow in TREND, mean-rev in RANGE)
+ meta + sizing.

Walk-forward, per-year + per-fold robustness, cost {0.02,0.05}, top-N {6,8}.

Output: results/model_validation/phase9_crypto6_<UTC>/crypto6.json
Run:    python scripts/phase9_crypto_morecoins.py
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
from phase6_perclass import build_class, SEEDS, VAL_WEEKS, FOLD_STARTS, calib
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from model_validation_suite import train_lgbm, predict

SYMBOLS = ["BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD", "ADAUSD"]
TB, NFEAT, GEN_MULT, NEG = 24, 9, 3.0, -1e9
MR_THR, MR_TP, MR_SL = 1.5, 1.0, 2.0
TF_TP, TF_SL = 1.5, 1.0
XS_LOOKBACK = 48                  # 48*5m = 4h trailing return for relative strength
COSTS = [0.02, 0.05]
TOPNS = [6, 8]
CACHE = REPO / "data" / "processed_v2" / "extended" / "crypto6_aug.parquet"


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


def cross_sectional():
    """Per-coin trailing-return z-score vs the basket, on the 5m grid. {sym: Series}."""
    rets = {}
    for s in SYMBOLS:
        c = pd.read_parquet(REPO / "data" / "processed_v2" / f"{s}_5m.parquet")["close"]
        rets[s] = c.pct_change(XS_LOOKBACK)
    wide = pd.DataFrame(rets).sort_index()
    mu = wide.mean(axis=1); sd = wide.std(axis=1).replace(0, np.nan)
    xs = wide.sub(mu, axis=0).div(sd, axis=0)
    return {s: xs[s] for s in SYMBOLS}


def get_pool():
    pool, feats = build_class(SYMBOLS)
    xs = cross_sectional()
    pool["xs_strength"] = np.nan
    for s in SYMBOLS:
        m = (pool["symbol"] == s).values
        pool.loc[m, "xs_strength"] = xs[s].reindex(pool.index[m]).values
    feats = feats + ["xs_strength"]
    if CACHE.exists():
        aug = pd.read_parquet(CACHE)
        pool["_Rtf"] = aug["_Rtf"].reindex(pool.index).values
        pool["_Rmr"] = aug["_Rmr"].reindex(pool.index).values
        return pool, feats
    pool["_Rtf"] = np.nan; pool["_Rmr"] = np.nan
    for s in SYMBOLS:
        m = (pool["symbol"] == s).values; idx = pool.index[m]
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{s}_5m.parquet")
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values; e20 = ema(raw["close"], 20).values
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
    pool[["_Rtf", "_Rmr"]].to_parquet(CACHE)
    return pool, feats


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase9_crypto6_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool, feats = get_pool()
    pool = pool.dropna(subset=["xs_strength"])
    X = lambda d, f: d[f].values.astype(np.float32)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = pool[pool.index < cut0]
    def topfeat(Rcol):
        sub = tr0[np.isfinite(tr0[Rcol].values)]
        m = train_lgbm(X(sub, feats), (sub[Rcol].values > 0).astype(int), X(sub, feats), (sub[Rcol].values > 0).astype(int), 100, None, 42)
        return list(pd.Series(m.feature_importance(importance_type="gain"), index=feats).sort_values(ascending=False).index[:NFEAT])
    topTF, topMR = topfeat("_Rtf"), topfeat("_Rmr")
    xs_in = ("xs_strength" in topTF, "xs_strength" in topMR)
    print(f"pool={len(pool):,}  coins={len(SYMBOLS)}  xs_in_top9(TF,MR)={xs_in}\n  TF={topTF[:4]}  MR={topMR[:4]}")

    acc = {(n, c): {"R": [], "S": [], "fold": [], "yr": {2024: {"r": [], "s": []}, 2025: {"r": [], "s": []}, 2026: {"r": [], "s": []}}} for n in TOPNS for c in COSTS}
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]; te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 8000 or len(va) < 800 or len(te) < 500: continue
            def fitleg(Rcol, top):
                trL = tr[np.isfinite(tr[Rcol].values)]; vaL = va[np.isfinite(va[Rcol].values)]
                if len(trL) < 2000 or len(vaL) < 150: return None
                y = lambda d: (d[Rcol].values > 0).astype(int)
                m = train_lgbm(X(trL, top), y(trL), X(vaL, top), y(vaL), 100, None, sd)
                trva = pool[pool.index < te_s]; tv = trva[np.isfinite(trva[Rcol].values)]
                pv = m.predict(X(vaL, top)); gen = calib(pv, max(1, vaL.index.normalize().nunique()), 8 * GEN_MULT)
                cand = tv[m.predict(X(tv, top)) >= gen]
                me = train_lgbm(X(cand, feats), y(cand), X(cand, feats), y(cand), 100, None, sd) if len(cand) >= 300 else None
                return (m, me, top, gen)
            legT, legM = fitleg("_Rtf", topTF), fitleg("_Rmr", topMR)
            if legT is None or legM is None: continue
            def candrows(df):
                rows = []
                for Rcol, leg in (("_Rtf", legT), ("_Rmr", legM)):
                    m, me, top, gen = leg
                    sub = df[np.isfinite(df[Rcol].values)]
                    if len(sub) == 0: continue
                    pp = m.predict(X(sub, top))
                    if me is not None:
                        score = np.full(len(sub), NEG); cm = pp >= gen
                        if cm.sum(): score[cm] = me.predict(X(sub[cm], feats))
                    else:
                        score = pp
                    rows.append(pd.DataFrame({"ts": sub.index, "proba": score, "g": sub[Rcol].values}))
                c = pd.concat(rows); c["day"] = c["ts"].dt.normalize(); c["year"] = c["ts"].dt.year
                return c
            cv = candrows(va); ct = candrows(te)
            for n in TOPNS:
                thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), n)
                sel = ct[ct["proba"].values >= thr]; sz = tier_size(sel["proba"].values); yrs = sel["year"].values
                for c in COSTS:
                    r = sel["g"].values - c
                    acc[(n, c)]["R"].append(r); acc[(n, c)]["S"].append(sz)
                    st = pf_wr_sized(r, sz)
                    if st: acc[(n, c)]["fold"].append(st["pf"])
                    for y in (2024, 2025, 2026):
                        mk = yrs == y; acc[(n, c)]["yr"][y]["r"].append(sel["g"].values[mk] - c); acc[(n, c)]["yr"][y]["s"].append(sz[mk])

    res = {}
    print(f"\n{'topN':5s} {'cost':5s} {'net_PF':>7s} {'WR':>6s} {'tr/day':>7s} {'folds+':>7s} {'years':>22s} {'allpos':>7s} {'BAR'}")
    for n in TOPNS:
        for c in COSTS:
            d = acc[(n, c)]
            allR = np.concatenate(d["R"]) if d["R"] else np.array([]); allS = np.concatenate(d["S"]) if d["S"] else np.array([])
            st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
            fpf = np.array(d["fold"]); yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"] for y, v in d["yr"].items()}
            allpos = all(v and v > 1.0 for v in yr.values())
            prof = dict(net_pf=st["pf"], wr=st["wr"], trades_per_day=round(st["n"]/(len(SEEDS)*days), 2),
                        pct_folds_pos=round(float((fpf > 1).mean()), 2) if len(fpf) else None, pf_by_year=yr,
                        all_years_pos=allpos, bar_pass=(st["pf"] is not None and st["pf"] >= 1.3 and allpos))
            res[f"top{n}_{c}ATR"] = prof
            yl = "/".join(str(yr[k]) for k in ("2024", "2025", "2026"))
            print(f"{n:<5d} {c:<5} {str(prof['net_pf']):>7s} {str(prof['wr']):>6s} {prof['trades_per_day']:>7.2f} {str(prof['pct_folds_pos']):>7s} {yl:>22s} {str(allpos):>7s} {prof['bar_pass']}")
    (OUT / "crypto6.json").write_text(json.dumps(dict(symbols=SYMBOLS, xs_in_top=xs_in, trendfeat=topTF, mrfeat=topMR, results=res), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
