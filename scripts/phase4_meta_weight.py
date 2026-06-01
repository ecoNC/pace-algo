"""
Phase 4 batch 2b: the two theory-grounded levers for WR/PF.

  WEIGHTED : sample-uniqueness weights (Lopez de Prado) in training. 24-bar barriers on
             5m overlap heavily -> labels are not iid -> overfitting. Weight each row by
             label uniqueness (1/avg concurrency over its life) to de-bias -> better OOS.
  META     : meta-labeling. Primary ranker (long-9) proposes high-proba candidates; a
             secondary model (full-73 features) trained ONLY on those candidates predicts
             P(win) and re-ranks them -> filters conditional false positives -> precision.

Baseline = locked V1 (long + USDCHF-short, POOLED top10, ECN 0.5pip, long-9, seed 42).
Reports WR / PF / trades-day / std + per-year.

Output: results/model_validation/phase4_meta_weight_<UTC>/meta_weight.json
Run:    python scripts/phase4_meta_weight.py
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
import lightgbm as lgb

from phase3_density import build_pool, FEATURES_9, netR, stats, VAL_WEEKS, FOLD_STARTS
from phase3_selection_compare import calib_thr
from phase3_v1_config import build_cands
from phase3_short_features import feature_cols
from model_validation_suite import train_lgbm, predict, LGBM_BASE
from setup_makeorbreak import TB, TP_R, SL_R
from core.features.engineer import atr as atr_fn

SPREAD, TOPN, SEED = 0.5, 10, 42
GEN_MULT = 3.0   # meta candidate pool ~ 3x TOPN/day


def barrier_span(o, h, l, c, atr, direction):
    """Bars from entry to exit (TP/SL/time), per bar. Used for label-concurrency weighting."""
    n = len(c); span = np.full(n, np.nan)
    for i in range(n - TB - 1):
        a = atr[i]
        if not np.isfinite(a) or a <= 0: continue
        entry = c[i]; hit = TB
        if direction == "long":
            tp, sl = entry + TP_R * a, entry - SL_R * a
            for k in range(i + 1, i + 1 + TB):
                if l[k] <= sl or h[k] >= tp: hit = k - i; break
        else:
            tp, sl = entry - TP_R * a, entry + SL_R * a
            for k in range(i + 1, i + 1 + TB):
                if h[k] >= sl or l[k] <= tp: hit = k - i; break
        span[i] = hit
    return span


def uniqueness(span):
    """w_i = mean over the label's life of 1/concurrency. Normalized to mean 1."""
    n = len(span); conc = np.zeros(n + TB + 2)
    valid = np.where(np.isfinite(span))[0]
    for i in valid:
        s = int(span[i]); conc[i] += 1; conc[min(i + s, len(conc) - 1)] -= 1
    conc = np.cumsum(conc)
    w = np.full(n, np.nan)
    for i in valid:
        s = int(span[i]); seg = conc[i:i + s]
        seg = seg[seg > 0]
        w[i] = float(np.mean(1.0 / seg)) if len(seg) else 1.0
    m = np.nanmean(w[valid]) if len(valid) else 1.0
    return w / m if m > 0 else w


def train_w(Xtr, ytr, w, sd):
    return lgb.train(dict(LGBM_BASE, num_iterations=100, seed=sd),
                     lgb.Dataset(Xtr, label=ytr, weight=w), callbacks=[lgb.log_evaluation(period=0)])


def augment_weights(pool):
    pool = pool.copy(); pool["_w_long"] = np.nan; pool["_w_short"] = np.nan
    for p in pool["symbol"].unique():
        m = (pool["symbol"] == p).values; idx = pool.index[m]
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{p}_5m.parquet")
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        o, hi, lo, cl = raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values
        for d, col in [("long", "_w_long"), ("short", "_w_short")]:
            w = uniqueness(barrier_span(o, hi, lo, cl, a, d))
            pool.loc[m, col] = pd.Series(w, index=raw.index).reindex(idx).values
    return pool


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase4_meta_weight_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = augment_weights(build_pool())
    feats_full = feature_cols(pool)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d, f=FEATURES_9: d[f].values.astype(np.float32)
    print(f"pool={len(pool):,}  full_features={len(feats_full)}")

    variants = ["V1_baseline", "WEIGHTED", "META"]
    acc = {v: {"R": [], "pf": [], "yr": {}} for v in variants}

    def record(name, sel):
        r = netR(sel["gR"].values, sel["cost"].values, SPREAD)
        acc[name]["R"].append(r); st = stats(r); acc[name]["pf"].append(st["pf"] if st else None)
        yrs = sel["ts"].dt.year.values
        for y in (2024, 2025, 2026):
            mk = yrs == y
            acc[name]["yr"].setdefault(y, []).append(netR(sel["gR"].values[mk], sel["cost"].values[mk], SPREAD))

    def select(va_cands, te_cands):
        thr = calib_thr(va_cands["proba"].values, max(1, va_cands["day"].nunique()), TOPN)
        return te_cands[te_cands["proba"].values >= thr]

    for ts0 in FOLD_STARTS:
        te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
        te = pool[(pool.index >= te_s) & (pool.index < te_e)]
        if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
        gv = va["_in_ny"].values & va["_tradeable"].values
        gt = te["_in_ny"].values & te["_tradeable"].values
        if gv.sum() < 100 or gt.sum() < 100: continue

        # --- primary (baseline) ---
        mL = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, 100, None, SEED)
        mS = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, 100, None, SEED)
        pvL, ptL = predict(mL, "lgbm", X(va)), predict(mL, "lgbm", X(te))
        pvS, ptS = predict(mS, "lgbm", X(va)), predict(mS, "lgbm", X(te))
        record("V1_baseline", select(build_cands(va, pvL, pvS, gv, "long_short_usdchf"),
                                     build_cands(te, ptL, ptS, gt, "long_short_usdchf")))

        # --- WEIGHTED primary ---
        wmL = train_w(X(tr), tr["_lab_long"].values, tr["_w_long"].fillna(1).values, SEED)
        wmS = train_w(X(tr), tr["_lab_short"].values, tr["_w_short"].fillna(1).values, SEED)
        record("WEIGHTED", select(build_cands(va, wmL.predict(X(va)), wmS.predict(X(va)), gv, "long_short_usdchf"),
                                  build_cands(te, wmL.predict(X(te)), wmS.predict(X(te)), gt, "long_short_usdchf")))

        # --- META: re-rank primary candidates by a full-73 secondary model ---
        # meta training set = gated candidates in (tr+va) with primary proba >= generous cut
        trva = pool[(pool.index < te_s)]
        gtrva = trva["_in_ny"].values & trva["_tradeable"].values
        pL_trva = mL.predict(X(trva)); pS_trva = mS.predict(X(trva))
        genL = calib_thr(pvL[gv], max(1, va.index[gv].normalize().nunique()), TOPN * GEN_MULT)
        genS = calib_thr(pvS[gv], max(1, va.index[gv].normalize().nunique()), TOPN * GEN_MULT)
        candL = gtrva & (pL_trva >= genL); candS = gtrva & (pS_trva >= genS)
        metaL = train_lgbm(X(trva[candL], feats_full), trva["_lab_long"].values[candL],
                           X(trva[candL], feats_full), trva["_lab_long"].values[candL], 100, None, SEED) if candL.sum() > 200 else None
        metaS = train_lgbm(X(trva[candS], feats_full), trva["_lab_short"].values[candS],
                           X(trva[candS], feats_full), trva["_lab_short"].values[candS], 100, None, SEED) if candS.sum() > 200 else None
        if metaL is not None and metaS is not None:
            NEG = -1e9
            def meta_arr(df, primP, gen, meta):
                cand = (df["_in_ny"].values & df["_tradeable"].values) & (primP >= gen)
                out = np.full(len(df), NEG)
                if cand.sum():
                    out[cand] = meta.predict(X(df[cand], feats_full))
                return out
            record("META", select(
                build_cands(va, meta_arr(va, pvL, genL, metaL), meta_arr(va, pvS, genS, metaS), gv, "long_short_usdchf"),
                build_cands(te, meta_arr(te, ptL, genL, metaL), meta_arr(te, ptS, genS, metaS), gt, "long_short_usdchf")))

    def block(d):
        allR = np.concatenate(d["R"]) if d["R"] else np.array([])
        st = stats(allR) or {"n": 0, "wr": None, "pf": None}
        pfl = [p for p in d["pf"] if p is not None]
        yr = {str(y): (stats(np.concatenate(v)) or {"pf": None})["pf"] for y, v in d["yr"].items()}
        return dict(trades_per_day=round(st["n"] / days, 2),
                    net_pf=round(float(np.mean(pfl)), 3) if pfl else None,
                    pf_std=round(float(np.std(pfl)), 3) if pfl else None, wr=st["wr"], pf_by_year=yr)

    res = {v: block(acc[v]) for v in variants}
    (OUT / "meta_weight.json").write_text(json.dumps(dict(spread=SPREAD, topN=TOPN, results=res),
                                                      indent=2, default=str), encoding="utf-8")
    print(f"\n{'variant':14s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'tr/day':>7s}  {'PF 24/25/26'}")
    for v in variants:
        d = res[v]; pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else " n/a"
        yr = "/".join(str(d["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
        print(f"{v:14s} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>7.2f}  {yr}")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
