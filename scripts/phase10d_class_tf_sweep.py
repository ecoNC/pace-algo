"""
Phase 10d: TF x R-multiple sweep for INDICES + METALS with class-appropriate gates.

What phase6c could not see: it searched session windows on 5m at R=1.5 only. phase7c
showed for crypto that TF/R interact with costs — but indices/metals never got that
sweep. New axes here:
  - TF: 15m / 30m / 1h (15m/30m resampled from 5m)
  - R:  1.0 / 1.5 / 2.0 / 3.0  (24-bar time barrier, SL 1 ATR)
  - Gate: per-symbol HOME session (US RTH for US indices, Xetra for DAX, TSE for
    Nikkei, London PM+NY for metals) AND vol-tradeable state — the fair, class-owned
    analogue of FX's NY gate.

Universe (whatever parquets exist locally are used; missing symbols are skipped):
  index: SPX500 NAS100 US30 US2000 GER40 UK100 FRA40 EUSTX50 JPN225 HKG33
  metal: XAUUSD XAGUSD

Pipeline per class: pooled long+short LGBM ranker (top-9 by gain, selected pre-2024),
POOLED top-N/day, proba sizing, walk-forward rolling quarters x seeds, costs as ATR
fraction sweep. Bar: net PF >= 1.3, all years positive.

Output: results/model_validation/phase10d_class_tf_<UTC>/class_tf.json
Run:    python scripts/phase10d_class_tf_sweep.py [index|metal]
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

from core.features import (compute_features, attach_htf_context, compute_smc_features,
                           compute_session_features, compute_htf_interactions)
from core.features.engineer import atr as atr_fn
from core.train.dataset import NON_FEATURE_COLS
from core.state.market_state import classify_market_state
from model_validation_suite import train_lgbm, predict
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from phase7c_crypto_htf import barrier, calib

CLASSES = {
    "index": ["SPX500", "NAS100", "US30", "US2000", "GER40", "UK100", "FRA40", "EUSTX50", "JPN225", "HKG33"],
    "metal": ["XAUUSD", "XAGUSD"],
}
# per-symbol HOME session, UTC hours [start, end)
HOME_SESSION = {
    "SPX500": (14, 21), "NAS100": (14, 21), "US30": (14, 21), "US2000": (14, 21),
    "GER40": (8, 16), "UK100": (8, 16), "FRA40": (8, 16), "EUSTX50": (8, 16),
    "JPN225": (0, 6), "HKG33": (2, 8),
    "XAUUSD": (12, 21), "XAGUSD": (12, 21),   # London PM fix window + NY
}
TFS = ["15m", "30m", "1h"]
R_MULTS = [1.0, 1.5, 2.0, 3.0]
COSTS = [0.02, 0.05, 0.10]    # spread as ATR fraction
SEEDS = [42, 7]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
TOPN, NFEAT, TB = 6, 9, 24
DATA = REPO / "data" / "processed_v2"
EXTDIR = DATA / "extended"


def load_tf(sym, tf):
    """Raw OHLCV at tf; 15m/30m resampled from the 5m parquet."""
    if tf in ("1h", "4h", "5m"):
        p = DATA / f"{sym}_{tf}.parquet"
        return pd.read_parquet(p) if p.exists() else None
    base = load_tf(sym, "5m")
    if base is None: return None
    rule = {"15m": "15min", "30m": "30min"}[tf]
    o = base.resample(rule).agg({"open": "first", "high": "max", "low": "min",
                                 "close": "last", "volume": "sum"}).dropna(subset=["close"])
    return o


def build_ext(sym, tf):
    """Feature frame at tf with 1h+4h HTF context (cached)."""
    cache = EXTDIR / f"{sym}_{tf}_p10d_extended.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    raw = load_tf(sym, tf)
    h1, h4 = load_tf(sym, "1h"), load_tf(sym, "4h")
    if raw is None or h1 is None or h4 is None or len(raw) < 5000: return None
    base = compute_features(raw)
    base = attach_htf_context(base, compute_features(h1), compute_features(h4))
    atr14 = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
    ema_align = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
    ext = pd.concat([base, compute_smc_features(raw, atr14, ema_align),
                     compute_session_features(raw, atr14), compute_htf_interactions(base)], axis=1)
    EXTDIR.mkdir(parents=True, exist_ok=True)
    ext.to_parquet(cache, compression="zstd")
    return ext


def build_pool(cls, tf):
    frames, used = [], []
    for sym in CLASSES[cls]:
        ext = build_ext(sym, tf)
        if ext is None: continue
        ext = ext.copy().astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        raw = load_tf(sym, tf)
        st = classify_market_state(raw)
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        for col, vals in [("_atr", a), ("_o", raw["open"].values), ("_h", raw["high"].values),
                          ("_l", raw["low"].values), ("_c", raw["close"].values)]:
            ext[col] = pd.Series(vals, index=raw.index).reindex(ext.index).values
        ext["_tradeable"] = st["tradeable"].reindex(ext.index).values
        h0, h1 = HOME_SESSION[sym]
        ext["_home"] = (ext.index.hour >= h0) & (ext.index.hour < h1)
        ext["symbol"] = sym
        frames.append(ext); used.append(sym)
    if not frames: return None, [], []
    pool = pd.concat(frames).sort_index()
    feats = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"
             and c != "label" and not c.startswith("_")]
    pool = pool.dropna(subset=feats + ["_atr", "_c"])
    return pool, feats, used


def add_barriers(pool, used, tp_R):
    gL = np.full(len(pool), np.nan); gS = np.full(len(pool), np.nan)
    for sym in used:
        m = (pool["symbol"] == sym).values
        sub = pool[m]
        o, h, l, c, a = sub["_o"].values, sub["_h"].values, sub["_l"].values, sub["_c"].values, sub["_atr"].values
        gL[m] = barrier(o, h, l, c, a, "long", tp_R, 1.0, TB)
        gS[m] = barrier(o, h, l, c, a, "short", tp_R, 1.0, TB)
    return gL, gS


def cands(df, ptL, ptS, gate, gL, gS):
    gi = np.where(gate)[0]; ts = df.index[gi]
    fr = [pd.DataFrame({"ts": ts, "proba": ptL[gi], "g": gL[gi], "row": gi}),
          pd.DataFrame({"ts": ts, "proba": ptS[gi], "g": gS[gi], "row": gi})]
    c = pd.concat(fr).sort_values("proba", ascending=False).drop_duplicates("row")
    c["day"] = c["ts"].dt.normalize(); c["year"] = c["ts"].dt.year
    return c


def run_class(cls):
    out = {}
    for tf in TFS:
        pool, feats, used = build_pool(cls, tf)
        if pool is None:
            print(f"[{cls} {tf}] no data yet — skipped"); continue
        days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
        X = lambda d, f: d[f].values.astype(np.float32)
        print(f"\n[{cls} {tf}] pool={len(pool):,} syms={used}")
        for tp_R in R_MULTS:
            gLp, gSp = add_barriers(pool, used, tp_R)
            pool["_gL"] = gLp; pool["_gS"] = gSp
            p = pool.dropna(subset=["_gL", "_gS"])
            cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = p[p.index < cut0]
            if len(tr0) < 5000:
                print(f"  R={tp_R}: too little pre-2024 train"); continue
            m0 = train_lgbm(X(tr0, feats), (tr0["_gL"].values > 0).astype(int),
                            X(tr0, feats), (tr0["_gL"].values > 0).astype(int), 100, None, 42)
            imp = pd.Series(m0.feature_importance(importance_type="gain"), index=feats).sort_values(ascending=False)
            top = list(imp.index[:NFEAT])
            acc = {c: {"R": [], "S": [], "fold": [],
                       "yr": {y: {"r": [], "s": []} for y in (2024, 2025, 2026)}} for c in COSTS}
            for sd in SEEDS:
                for ts0 in FOLD_STARTS:
                    te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
                    tr = p[p.index < vs]; va = p[(p.index >= vs) & (p.index < te_s)]
                    te = p[(p.index >= te_s) & (p.index < te_e)]
                    if len(tr) < 3000 or len(va) < 300 or len(te) < 200: continue
                    gv = va["_home"].values & va["_tradeable"].values
                    gt = te["_home"].values & te["_tradeable"].values
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
                            mk = yrs == y
                            acc[c]["yr"][y]["r"].append(sel["g"].values[mk] - c); acc[c]["yr"][y]["s"].append(sz[mk])
            rr = {}
            for c in COSTS:
                allR = np.concatenate(acc[c]["R"]) if acc[c]["R"] else np.array([])
                allS = np.concatenate(acc[c]["S"]) if acc[c]["S"] else np.array([])
                st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
                fpf = np.array(acc[c]["fold"])
                yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"]
                      for y, v in acc[c]["yr"].items()}
                allpos = all(v and v > 1.0 for v in yr.values())
                rr[f"{c}ATR"] = dict(net_pf=st["pf"], wr=st["wr"],
                                     trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                                     pct_folds_pos=round(float((fpf > 1).mean()), 2) if len(fpf) else None,
                                     pf_by_year=yr, bar_pass=(st["pf"] is not None and st["pf"] >= 1.3 and allpos))
            out[f"{tf}_R{tp_R}"] = dict(symbols=used, features=top, costs=rr)
            for c in COSTS:
                d = rr[f"{c}ATR"]; yr = "/".join(str(d["pf_by_year"][k]) for k in ("2024", "2025", "2026"))
                print(f"  {tf} R={tp_R} cost{c}: PF {d['net_pf']}  WR {d['wr']}  {d['trades_per_day']}/day  "
                      f"folds+ {d['pct_folds_pos']}  yrs {yr}  BAR={d['bar_pass']}")
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else None
    classes = [which] if which in CLASSES else list(CLASSES)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase10d_class_tf_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {cls: run_class(cls) for cls in classes}
    (OUT / "class_tf.json").write_text(json.dumps(dict(
        tfs=TFS, r_mults=R_MULTS, costs=COSTS, seeds=SEEDS, home_sessions=HOME_SESSION,
        results=res), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
