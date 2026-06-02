"""
Phase 11c: THE crypto synthesis — regime-routed legs + ML/META selection + native
features, on clean Binance 4h perps at REAL fees.

Why this combination: phase11 (ML, no routing) is good 2024/25 but dies 2026 (0.94);
phase11b (routing, no ML) is good 2026 (1.14) but flat 2024/25. The failure modes are
complementary — routing fixes the regime flip, ML lifts the within-regime selection
(the FX-proven mechanism). v1's phase8c/d showed exactly this synthesis works on dirty
data at fantasy costs; this is the honest version.

Legs (phase8b, unchanged): TREND bars -> trend-follow; RANGE bars -> mean-rev fade.
Per leg: primary ranker (top-9 by gain incl. native feats) + META re-rank (full pool).
POOLED top-N/day across coins+legs, proba sizing, walk-forward x seeds,
fee_R = fee_frac * close / atr per bar, scenarios 0.05% / 0.10% round-trip.

Bar: net PF >= 1.3, all years positive, >=80% folds positive.

Output: results/model_validation/phase11c_routed_ml_<UTC>/routed_ml.json
Run:    python scripts/phase11c_crypto_routed_ml.py
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
from model_validation_suite import train_lgbm, predict
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from phase7c_crypto_htf import calib
from phase8d_crypto_optimized import trail, MR_THR, MR_TP, MR_SL, TF_TP, TF_SL
from phase11_crypto_v2 import build_pool, load, SYMBOLS, FEES, SEEDS, VAL_WEEKS, FOLD_STARTS

TF = "4h"
TB, NFEAT, GEN_MULT, NEG = 24, 9, 3.0, -1e9
TOPNS = [4, 6, 8]


def add_legs(pool):
    pool["_Rtf"] = np.nan; pool["_Rmr"] = np.nan
    for s in SYMBOLS:
        m = (pool["symbol"] == s).values; idx = pool.index[m]
        raw = load(s, TF)
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        e20 = ema(raw["close"], 20).values
        st = classify_market_state(raw); trg = st["trend_regime"].values
        o, h, l, c = raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values
        n = len(c); Rtf = np.full(n, np.nan); Rmr = np.full(n, np.nan)
        for i in range(n - TB - 1):
            av = a[i]
            if not np.isfinite(av) or av <= 0 or not np.isfinite(e20[i]): continue
            t = trg[i]
            if t in (TREND_UP, TREND_DOWN):
                Rtf[i] = trail(o, h, l, c, av, i, 1 if t == TREND_UP else -1, TF_TP, TF_SL)
            elif t == RANGE:
                z = (c[i] - e20[i]) / av
                if z >= MR_THR: Rmr[i] = trail(o, h, l, c, av, i, -1, MR_TP, MR_SL)
                elif z <= -MR_THR: Rmr[i] = trail(o, h, l, c, av, i, +1, MR_TP, MR_SL)
        S = lambda arr: pd.Series(arr, index=raw.index).reindex(idx).values
        pool.loc[m, "_Rtf"] = S(Rtf); pool.loc[m, "_Rmr"] = S(Rmr)
    return pool


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase11c_routed_ml_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool, base_feats, feats_all, used = build_pool(TF)
    pool = add_legs(pool)
    pool = pool.dropna(subset=["_fee_R"])
    X = lambda d, f: d[f].values.astype(np.float32)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    feats = [f for f in feats_all if pool[f].notna().mean() > 0.7]
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = pool[pool.index < cut0]

    def topfeat(Rcol):
        sub = tr0[np.isfinite(tr0[Rcol].values)].dropna(subset=feats)
        m = train_lgbm(X(sub, feats), (sub[Rcol].values > 0).astype(int),
                       X(sub, feats), (sub[Rcol].values > 0).astype(int), 100, None, 42)
        return list(pd.Series(m.feature_importance(importance_type="gain"), index=feats)
                    .sort_values(ascending=False).index[:NFEAT])
    topTF, topMR = topfeat("_Rtf"), topfeat("_Rmr")
    print(f"pool={len(pool):,} coins={len(used)} feats={len(feats)}")
    print(f"  trend top9:   {topTF}")
    print(f"  meanrev top9: {topMR}")

    acc = {(n, f): {"R": [], "S": [], "fold": [], "yr": {y: {"r": [], "s": []} for y in (2024, 2025, 2026)}}
           for n in TOPNS for f in FEES}
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 3000 or len(va) < 300 or len(te) < 200: continue

            def fitleg(Rcol, top):
                trL = tr[np.isfinite(tr[Rcol].values)].dropna(subset=top)
                vaL = va[np.isfinite(va[Rcol].values)].dropna(subset=top)
                if len(trL) < 1000 or len(vaL) < 80: return None
                y = lambda d: (d[Rcol].values > 0).astype(int)
                m = train_lgbm(X(trL, top), y(trL), X(vaL, top), y(vaL), 100, None, sd)
                trva = pool[pool.index < te_s]
                tv = trva[np.isfinite(trva[Rcol].values)].dropna(subset=top + feats)
                pv = m.predict(X(vaL, top)); gen = calib(pv, max(1, vaL.index.normalize().nunique()), 8 * GEN_MULT)
                cand = tv[m.predict(X(tv, top)) >= gen]
                if len(cand) < 200: return (m, None, top, gen)
                me = train_lgbm(X(cand, feats), (cand[Rcol].values > 0).astype(int),
                                X(cand, feats), (cand[Rcol].values > 0).astype(int), 100, None, sd)
                return (m, me, top, gen)
            legT = fitleg("_Rtf", topTF); legM = fitleg("_Rmr", topMR)
            if legT is None or legM is None: continue

            def candrows(df):
                rows = []
                for Rcol, leg in (("_Rtf", legT), ("_Rmr", legM)):
                    m, me, top, gen = leg
                    sub = df[np.isfinite(df[Rcol].values)].dropna(subset=top if me is None else top + feats)
                    if len(sub) == 0: continue
                    pp = m.predict(X(sub, top))
                    if me is not None:
                        score = np.full(len(sub), NEG); cm = pp >= gen
                        if cm.sum(): score[cm] = me.predict(X(sub[cm], feats))
                    else:
                        score = pp
                    rows.append(pd.DataFrame({"ts": sub.index, "proba": score, "g": sub[Rcol].values,
                                              "feeR": sub["_fee_R"].values}))
                c = pd.concat(rows); c["day"] = c["ts"].dt.normalize(); c["year"] = c["ts"].dt.year
                return c
            cv = candrows(va); ct = candrows(te)
            for n in TOPNS:
                thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), n)
                sel = ct[ct["proba"].values >= thr]; sz = tier_size(sel["proba"].values)
                yrs = sel["year"].values
                for f in FEES:
                    r = sel["g"].values - f * sel["feeR"].values
                    acc[(n, f)]["R"].append(r); acc[(n, f)]["S"].append(sz)
                    st = pf_wr_sized(r, sz)
                    if st: acc[(n, f)]["fold"].append(st["pf"])
                    for y in (2024, 2025, 2026):
                        mk = yrs == y
                        acc[(n, f)]["yr"][y]["r"].append(r[mk]); acc[(n, f)]["yr"][y]["s"].append(sz[mk])

    res = {}
    print(f"\n{'topN':5s} {'fee':7s} {'net_PF':>7s} {'WR':>6s} {'tr/day':>7s} {'folds+':>7s} {'years':>22s} {'BAR'}")
    for n in TOPNS:
        for f in FEES:
            d = acc[(n, f)]
            allR = np.concatenate(d["R"]) if d["R"] else np.array([])
            allS = np.concatenate(d["S"]) if d["S"] else np.array([])
            st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
            fpf = np.array(d["fold"])
            yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"]
                  for y, v in d["yr"].items()}
            allpos = all(v and v > 1.0 for v in yr.values())
            foldspos = round(float((fpf > 1).mean()), 2) if len(fpf) else None
            prof = dict(net_pf=st["pf"], wr=st["wr"], trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                        pct_folds_pos=foldspos, pf_by_year=yr, all_years_pos=allpos,
                        bar_pass=bool(st["pf"] and st["pf"] >= 1.3 and allpos and foldspos and foldspos >= 0.8))
            res[f"top{n}_fee{f}"] = prof
            yl = "/".join(str(yr[k]) for k in ("2024", "2025", "2026"))
            print(f"{n:<5d} {f:<7} {str(prof['net_pf']):>7s} {str(prof['wr']):>6s} {prof['trades_per_day']:>7.2f} "
                  f"{str(foldspos):>7s} {yl:>22s} {prof['bar_pass']}")
    (OUT / "routed_ml.json").write_text(json.dumps(dict(
        tf=TF, symbols=used, trendfeat=topTF, mrfeat=topMR, fees=FEES, topns=TOPNS,
        results=res), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
