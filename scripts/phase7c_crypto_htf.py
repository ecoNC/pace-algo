"""
Phase 7c: make CRYPTO work — higher timeframe (1h) + R-multiple sweep.

Why 5m crypto failed (phase7b): (1) fee drag — R=1.5 of a tiny 5m move is eaten by fees;
(2) 2025-26 choppy regime kills directional edge (research: trend-following punished,
mean-reversion favored in low-vol crypto regimes). Both point to HIGHER TF: a 1h R=1.5
move is large vs fixed fees, and structure is cleaner.

This builds a 1h-primary crypto feature set (htf context = 4h), sweeps the R-multiple
{1.0, 1.5, 2.0}, long+short ranker + proba sizing + vol gate + POOLED top-N, walk-forward.
Cost as ATR fraction (smaller on 1h: 0.01/0.03/0.05). Per-year robustness is the gate —
a crypto module MUST hold 2026 (where the 5m version decayed).

Output: results/model_validation/phase7c_crypto_htf_<UTC>/crypto_htf.json
Run:    python scripts/phase7c_crypto_htf.py
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

from core.labeling import compute_triple_barrier_labels
from core.features import (compute_features, attach_htf_context, compute_smc_features,
                           compute_session_features, compute_htf_interactions)
from core.features.engineer import atr as atr_fn
from core.train.dataset import NON_FEATURE_COLS
from core.state.market_state import classify_market_state
from model_validation_suite import train_lgbm, predict
from phase4_ensemble_sizing import tier_size, pf_wr_sized

SYMBOLS = ["BTCUSD", "ETHUSD"]
PRIMARY_TF, HTF = "1h", "4h"
SEEDS = [42, 7]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
R_MULTS = [1.0, 1.5, 2.0]
TB = 24                      # 24 bars = 24h on 1h
COSTS = [0.01, 0.03, 0.05]   # ATR fraction (lower on 1h vs 5m)
TOPN, NFEAT = 6, 9
EXTDIR = REPO / "data" / "processed_v2" / "extended"


def barrier(o, h, l, c, atr, direction, tp_R, sl_R=1.0, tb=TB):
    n = len(c); R = np.full(n, np.nan)
    for i in range(n - tb - 1):
        a = atr[i]
        if not np.isfinite(a) or a <= 0: continue
        entry = c[i]; r = None
        if direction == "long":
            tp, sl = entry + tp_R * a, entry - sl_R * a
            for k in range(i + 1, i + 1 + tb):
                if l[k] <= sl: r = -sl_R; break
                if h[k] >= tp: r = tp_R; break
        else:
            tp, sl = entry - tp_R * a, entry + sl_R * a
            for k in range(i + 1, i + 1 + tb):
                if h[k] >= sl: r = -sl_R; break
                if l[k] <= tp: r = tp_R; break
        R[i] = 0.0 if r is None else r
    return R


def build_1h(sym):
    """1h-primary crypto features with 4h HTF context (cached). Feature columns only."""
    cache = EXTDIR / f"{sym}_1h_htf_extended.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{sym}_{PRIMARY_TF}.parquet")
    h4 = pd.read_parquet(REPO / "data" / "processed_v2" / f"{sym}_{HTF}.parquet")
    base = compute_features(raw)
    f4 = compute_features(h4)
    base = attach_htf_context(base, f4, f4)   # 4h in both htf slots (populated, no NaN slot)
    atr14 = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
    ema_align = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
    ext = pd.concat([base, compute_smc_features(raw, atr14, ema_align),
                     compute_session_features(raw, atr14), compute_htf_interactions(base)], axis=1)
    ext.to_parquet(cache, compression="zstd")
    return ext


def build_pool():
    frames = []
    for sym in SYMBOLS:
        ext = build_1h(sym).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{sym}_{PRIMARY_TF}.parquet")
        st = classify_market_state(raw)
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        ext["_atr"] = pd.Series(a, index=raw.index).reindex(ext.index).values
        ext["_o"] = raw["open"].reindex(ext.index).values; ext["_h"] = raw["high"].reindex(ext.index).values
        ext["_l"] = raw["low"].reindex(ext.index).values; ext["_c"] = raw["close"].reindex(ext.index).values
        ext["_tradeable"] = st["tradeable"].reindex(ext.index).values
        ext["symbol"] = sym
        frames.append(ext)
    pool = pd.concat(frames).sort_index()
    feats = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"
             and c != "label" and not c.startswith("_")]
    pool = pool.dropna(subset=feats + ["_atr", "_c"])
    return pool, feats


def add_barriers(pool, tp_R):
    """Per-symbol gross long/short R for this R-multiple."""
    gL = np.full(len(pool), np.nan); gS = np.full(len(pool), np.nan)
    for sym in SYMBOLS:
        m = (pool["symbol"] == sym).values
        sub = pool[m]
        o, h, l, c, a = sub["_o"].values, sub["_h"].values, sub["_l"].values, sub["_c"].values, sub["_atr"].values
        gL[m] = barrier(o, h, l, c, a, "long", tp_R)
        gS[m] = barrier(o, h, l, c, a, "short", tp_R)
    return gL, gS


def cands(df, ptL, ptS, gate, gL, gS):
    gi = np.where(gate)[0]; ts = df.index[gi]
    fr = [pd.DataFrame({"ts": ts, "proba": ptL[gi], "g": gL[gi], "row": gi}),
          pd.DataFrame({"ts": ts, "proba": ptS[gi], "g": gS[gi], "row": gi})]
    c = pd.concat(fr).sort_values("proba", ascending=False).drop_duplicates("row")
    c["day"] = c["ts"].dt.normalize(); c["year"] = c["ts"].dt.year
    return c


def calib(p, gdays, per_day):
    n = len(p)
    if n == 0 or gdays == 0: return np.inf
    return float(np.quantile(p, min(max(1 - per_day * gdays / n, 0.0), 0.9995)))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase7c_crypto_htf_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool, feats = build_pool()
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d, f: d[f].values.astype(np.float32)
    print(f"pool(1h)={len(pool):,}  feats={len(feats)}")

    res = {}
    for tp_R in R_MULTS:
        gLp, gSp = add_barriers(pool, tp_R)
        pool["_gL"] = gLp; pool["_gS"] = gSp
        p = pool.dropna(subset=["_gL", "_gS"])
        cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = p[p.index < cut0]
        m0 = train_lgbm(X(tr0, feats), (tr0["_gL"].values > 0).astype(int), X(tr0, feats), (tr0["_gL"].values > 0).astype(int), 100, None, 42)
        imp = pd.Series(m0.feature_importance(importance_type="gain"), index=feats).sort_values(ascending=False)
        top = list(imp.index[:NFEAT])
        acc = {c: {"R": [], "S": [], "fold": [], "yr": {2024: {"r": [], "s": []}, 2025: {"r": [], "s": []}, 2026: {"r": [], "s": []}}} for c in COSTS}
        for sd in SEEDS:
            for ts0 in FOLD_STARTS:
                te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
                tr = p[p.index < vs]; va = p[(p.index >= vs) & (p.index < te_s)]; te = p[(p.index >= te_s) & (p.index < te_e)]
                if len(tr) < 3000 or len(va) < 300 or len(te) < 200: continue
                gv = va["_tradeable"].values; gt = te["_tradeable"].values
                if gv.sum() < 80 or gt.sum() < 80: continue
                yl = lambda d: (d["_gL"].values > 0).astype(int); ys = lambda d: (d["_gS"].values > 0).astype(int)
                mL = train_lgbm(X(tr, top), yl(tr), X(va, top), yl(va), 100, None, sd)
                mS = train_lgbm(X(tr, top), ys(tr), X(va, top), ys(va), 100, None, sd)
                cv = cands(va, predict(mL, "lgbm", X(va, top)), predict(mS, "lgbm", X(va, top)), gv, va["_gL"].values, va["_gS"].values)
                ct = cands(te, predict(mL, "lgbm", X(te, top)), predict(mS, "lgbm", X(te, top)), gt, te["_gL"].values, te["_gS"].values)
                thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
                sel = ct[ct["proba"].values >= thr]; sz = tier_size(sel["proba"].values); yrs = sel["year"].values
                for c in COSTS:
                    r = sel["g"].values - c
                    acc[c]["R"].append(r); acc[c]["S"].append(sz)
                    st = pf_wr_sized(r, sz)
                    if st: acc[c]["fold"].append(st["pf"])
                    for y in (2024, 2025, 2026):
                        mk = yrs == y; acc[c]["yr"][y]["r"].append(sel["g"].values[mk] - c); acc[c]["yr"][y]["s"].append(sz[mk])
        rr = {}
        for c in COSTS:
            allR = np.concatenate(acc[c]["R"]) if acc[c]["R"] else np.array([]); allS = np.concatenate(acc[c]["S"]) if acc[c]["S"] else np.array([])
            st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
            fpf = np.array(acc[c]["fold"]); yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"] for y, v in acc[c]["yr"].items()}
            allpos = all(v and v > 1.0 for v in yr.values())
            rr[f"{c}ATR"] = dict(net_pf=st["pf"], wr=st["wr"], trades_per_day=round(st["n"]/(len(SEEDS)*days), 2),
                                 pct_folds_pos=round(float((fpf > 1).mean()), 2) if len(fpf) else None,
                                 pf_by_year=yr, bar_pass=(st["pf"] is not None and st["pf"] >= 1.3 and allpos))
        res[f"R{tp_R}"] = dict(features=top, costs=rr)
        print(f"\n--- R={tp_R} (1h, top9={top[:4]}...) ---")
        for c in COSTS:
            d = rr[f"{c}ATR"]; yr = "/".join(str(d["pf_by_year"][k]) for k in ("2024", "2025", "2026"))
            print(f"  cost{c}: PF {d['net_pf']}  WR {d['wr']}  {d['trades_per_day']}/day  folds+ {d['pct_folds_pos']}  yrs {yr}  BAR={d['bar_pass']}")

    (OUT / "crypto_htf.json").write_text(json.dumps(dict(tf=PRIMARY_TF, htf=HTF, r_mults=R_MULTS, costs=COSTS, results=res), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
