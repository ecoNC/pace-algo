"""
phase9b: leak-free re-validation of the crypto module (2-coin control + 6-coin).

phase9's PF 5.2 was a validation leak: meta trained on train+val, but selection threshold
calibrated on the SAME val (in-sample meta scores) -> inflated at 6-coin density. FIX:
  - primary `m`: train on TRAIN (< vs)
  - meta `me`:   train on TRAIN-only candidates (< vs)   [was: trva incl val]
  - threshold:   calibrate on VALIDATION (vs..te_s), where m AND me are out-of-sample
  - test:        out-of-sample for everything
2-coin run is the control (must reproduce phase8d ~1.11); 6-coin is the real test of
"do more coins help".

Output: results/model_validation/phase9b_fixed_<UTC>/fixed.json
Run:    python scripts/phase9b_crypto_fixed.py
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

TB, NFEAT, GEN_MULT, NEG = 24, 9, 3.0, -1e9
MR_THR, MR_TP, MR_SL = 1.5, 1.0, 2.0
TF_TP, TF_SL = 1.5, 1.0
COST, TOPN = 0.05, 8
RUNS = {"2coin": (["BTCUSD", "ETHUSD"], "crypto_regime_aug.parquet"),
        "6coin": (["BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD", "ADAUSD"], "crypto6_aug.parquet")}


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


def get_pool(symbols, cachename):
    pool, feats = build_class(symbols)
    cache = REPO / "data" / "processed_v2" / "extended" / cachename
    if cache.exists():
        aug = pd.read_parquet(cache)
        pool["_Rtf"] = aug["_Rtf"].reindex(pool.index).values
        pool["_Rmr"] = aug["_Rmr"].reindex(pool.index).values
        return pool, feats
    pool["_Rtf"] = np.nan; pool["_Rmr"] = np.nan
    for s in symbols:
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
            if t in (TREND_UP, TREND_DOWN): Rtf[i] = trail(o, h, l, c, av, i, 1 if t == TREND_UP else -1, TF_TP, TF_SL)
            elif t == RANGE:
                z = (c[i] - e20[i]) / av
                if z >= MR_THR: Rmr[i] = trail(o, h, l, c, av, i, -1, MR_TP, MR_SL)
                elif z <= -MR_THR: Rmr[i] = trail(o, h, l, c, av, i, +1, MR_TP, MR_SL)
        S = lambda arr: pd.Series(arr, index=raw.index).reindex(idx).values
        pool.loc[m, "_Rtf"] = S(Rtf); pool.loc[m, "_Rmr"] = S(Rmr)
    pool[["_Rtf", "_Rmr"]].to_parquet(cache)
    return pool, feats


def run(symbols, cachename):
    pool, feats = get_pool(symbols, cachename)
    X = lambda d, f: d[f].values.astype(np.float32)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = pool[pool.index < cut0]
    def topfeat(Rcol):
        sub = tr0[np.isfinite(tr0[Rcol].values)]
        mm = train_lgbm(X(sub, feats), (sub[Rcol].values > 0).astype(int), X(sub, feats), (sub[Rcol].values > 0).astype(int), 100, None, 42)
        return list(pd.Series(mm.feature_importance(importance_type="gain"), index=feats).sort_values(ascending=False).index[:NFEAT])
    topTF, topMR = topfeat("_Rtf"), topfeat("_Rmr")
    R, S, fold, yr = [], [], [], {2024: {"r": [], "s": []}, 2025: {"r": [], "s": []}, 2026: {"r": [], "s": []}}
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]; te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            def fitleg(Rcol, top):
                trL = tr[np.isfinite(tr[Rcol].values)]
                if len(trL) < 1500: return None
                y = lambda d: (d[Rcol].values > 0).astype(int)
                m = train_lgbm(X(trL, top), y(trL), X(trL, top), y(trL), 100, None, sd)
                # LEAK FIX: meta candidates from TRAIN only (m is OOS on val/test)
                pv_tr = m.predict(X(trL, top)); gen = calib(pv_tr, max(1, trL.index.normalize().nunique()), TOPN * GEN_MULT)
                cand = trL[m.predict(X(trL, top)) >= gen]
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
            cv = candrows(va); ct = candrows(te)                  # threshold from VAL (meta OOS)
            thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
            sel = ct[ct["proba"].values >= thr]; sz = tier_size(sel["proba"].values); yrs = sel["year"].values
            r = sel["g"].values - COST
            R.append(r); S.append(sz); st = pf_wr_sized(r, sz)
            if st: fold.append(st["pf"])
            for y in (2024, 2025, 2026):
                mk = yrs == y; yr[y]["r"].append(sel["g"].values[mk] - COST); yr[y]["s"].append(sz[mk])
    allR = np.concatenate(R) if R else np.array([]); allS = np.concatenate(S) if S else np.array([])
    st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
    fpf = np.array(fold); yrpf = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"] for y, v in yr.items()}
    allpos = all(v and v > 1.0 for v in yrpf.values())
    return dict(net_pf=st["pf"], wr=st["wr"], trades_per_day=round(st["n"]/(len(SEEDS)*days), 2),
                pct_folds_pos=round(float((fpf > 1).mean()), 2) if len(fpf) else None, pf_by_year=yrpf,
                all_years_pos=allpos, bar_pass=(st["pf"] is not None and st["pf"] >= 1.3 and allpos))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase9b_fixed_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for name, (syms, cache) in RUNS.items():
        print(f"[{name}] {syms} ...", flush=True)
        res[name] = run(syms, cache)
        d = res[name]; yl = "/".join(str(d["pf_by_year"][k]) for k in ("2024", "2025", "2026"))
        print(f"   net_PF {d['net_pf']}  WR {d['wr']}  {d['trades_per_day']}/day  folds+ {d['pct_folds_pos']}  yrs {yl}  allpos {d['all_years_pos']}  BAR {d['bar_pass']}")
    (OUT / "fixed.json").write_text(json.dumps(dict(cost=COST, topn=TOPN, results=res), indent=2, default=str), encoding="utf-8")
    print(f"\n(2coin should reproduce ~1.11 = leak fixed & control OK; 6coin = real 'more coins' answer)")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
