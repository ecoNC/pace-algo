"""
Phase 10c: CLASS-OWNED features — the lever phase6c never had.

phase6c only SELECTED from the generic (FX-born) feature pool. Here we ENGINEER
class-specific candidates and measure their net-PF lift vs the generic pool under
the identical harness (pooled long+short ranker, home-session gate, walk-forward):

  index : overnight gap (ATR), opening-range position, prev-day H/L distance (ATR),
          minutes-since-session-open, day-of-week sin/cos
  metal : DXY context (1h/4h DXY return, DXY-EMA20 distance — real USDIDX data,
          prev completed bar, no lookahead), London-PM-fix window flag, dow sin/cos
  crypto: weekend flag, day-of-week sin/cos, funding-window flag (00/08/16 UTC),
          hours-to-next-funding

Arms per class: BASE (generic pool, top-9 by gain) vs BASE+CLASS (augmented pool,
top-9). Lift bar (locked rule): >= +0.05 net PF OOS, else the features are dead.

Output: results/model_validation/phase10c_class_feat_<UTC>/class_feat.json
Run:    python scripts/phase10c_class_features.py [index|metal|crypto] [tf] [R]
        (defaults: all classes, tf=5m, R=1.5; feed the phase10d winner when known)
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
from model_validation_suite import train_lgbm, predict
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from phase7c_crypto_htf import calib
from phase10d_class_tf_sweep import (CLASSES as IDX_MET_CLASSES, HOME_SESSION, load_tf,
                                     build_pool as build_pool_10d, add_barriers, cands,
                                     SEEDS, VAL_WEEKS, FOLD_STARTS, TOPN, NFEAT)

CLASSES = dict(IDX_MET_CLASSES)
CLASSES["crypto"] = ["BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD", "ADAUSD"]
for s in CLASSES["crypto"]:
    HOME_SESSION.setdefault(s, (0, 24))   # crypto: no session gate
COST = 0.05   # ATR-fraction spread (mid sweep point)
DATA = REPO / "data" / "processed_v2"


def session_feats(df, sym):
    """Index-class features from raw OHLC at df's TF (vectorized, causal)."""
    h0, _ = HOME_SESSION[sym]
    out = pd.DataFrame(index=df.index)
    a = df["_atr"].values
    day = df.index.normalize()
    hour = df.index.hour
    # day-of-week
    dow = df.index.dayofweek.values
    out["cl_dow_sin"] = np.sin(2 * np.pi * dow / 7); out["cl_dow_cos"] = np.cos(2 * np.pi * dow / 7)
    # prev-day high/low distance
    dhi = pd.Series(df["_h"].values, index=df.index).groupby(day).max()
    dlo = pd.Series(df["_l"].values, index=df.index).groupby(day).min()
    dcl = pd.Series(df["_c"].values, index=df.index).groupby(day).last()
    pday = pd.Series(day).map(dhi.shift(1)).values
    plo = pd.Series(day).map(dlo.shift(1)).values
    pcl = pd.Series(day).map(dcl.shift(1)).values
    c = df["_c"].values
    with np.errstate(invalid="ignore", divide="ignore"):
        out["cl_prev_high_dist"] = (pday - c) / a
        out["cl_prev_low_dist"] = (c - plo) / a
        # overnight gap: first home-session open of today vs prev day close
        sess = hour >= h0
        sopen = pd.Series(np.where(sess, df["_o"].values, np.nan), index=df.index).groupby(day).transform("first")
        out["cl_overnight_gap"] = (sopen.values - pcl) / a
        # opening range (first hour of home session): position of close in OR
        in_or = sess & (hour < h0 + 1)
        orh = pd.Series(np.where(in_or, df["_h"].values, np.nan), index=df.index).groupby(day).transform("max")
        orl = pd.Series(np.where(in_or, df["_l"].values, np.nan), index=df.index).groupby(day).transform("min")
        rng = (orh - orl).values
        out["cl_or_pos"] = np.where(rng > 0, (c - orl.values) / rng, np.nan)
    # minutes since session open
    out["cl_min_since_open"] = np.clip((hour - h0) * 60 + df.index.minute, 0, 24 * 60).astype(float)
    return out


def dxy_feats(index, tf):
    """Metal-class DXY context from USDIDX (prev completed bar -> causal)."""
    p = DATA / f"USDIDX_{tf if tf in ('5m','1h','4h') else '5m'}.parquet"
    if not p.exists(): return None
    dxy = pd.read_parquet(p)["close"].shift(1)   # previous completed bar only
    e20 = ema(dxy.dropna(), 20).reindex(dxy.index)
    bars_1h = {"5m": 12, "15m": 4, "30m": 2, "1h": 1}.get(tf, 12)
    out = pd.DataFrame({
        "cl_dxy_ret_1h": dxy.pct_change(bars_1h),
        "cl_dxy_ret_4h": dxy.pct_change(4 * bars_1h),
        "cl_dxy_ema20_dist": (dxy - e20) / e20,
    }, index=dxy.index)
    return out.reindex(index, method="ffill")


def crypto_feats(df):
    out = pd.DataFrame(index=df.index)
    dow = df.index.dayofweek.values; hour = df.index.hour.values
    out["cl_dow_sin"] = np.sin(2 * np.pi * dow / 7); out["cl_dow_cos"] = np.cos(2 * np.pi * dow / 7)
    out["cl_is_weekend"] = (dow >= 5).astype(float)
    out["cl_funding_win"] = np.isin(hour % 8, [7, 0]).astype(float)   # hour before + at 00/08/16
    out["cl_hrs_to_funding"] = (8 - (hour % 8)) % 8
    return out


def metal_extra(df):
    out = pd.DataFrame(index=df.index)
    out["cl_london_fix"] = ((df.index.hour == 14) | (df.index.hour == 15)).astype(float)
    return out


def run_class(cls, tf, tp_R):
    pool, feats, used = build_pool_10d(cls, tf) if cls in IDX_MET_CLASSES else (None, None, None)
    if cls == "crypto":
        # reuse 10d builder by temporarily registering crypto in its CLASSES
        from phase10d_class_tf_sweep import CLASSES as C10D
        C10D["crypto"] = CLASSES["crypto"]
        pool, feats, used = build_pool_10d("crypto", tf)
    if pool is None:
        print(f"[{cls} {tf}] no data — skipped"); return None
    # ---- class features ----
    cl = []
    for sym in used:
        m = (pool["symbol"] == sym).values
        sub = pool[m]
        if cls == "index":
            f = session_feats(sub, sym)
        elif cls == "metal":
            f = session_feats(sub, sym)
            f = pd.concat([f, metal_extra(sub)], axis=1)
            d = dxy_feats(sub.index, tf)
            if d is not None: f = pd.concat([f, d], axis=1)
        else:
            f = crypto_feats(sub)
        f["symbol"] = sym
        cl.append(f)
    clf = pd.concat(cl).sort_index()
    cl_cols = [c for c in clf.columns if c != "symbol"]
    for c in cl_cols:
        pool[c] = clf[c].values  # same row order: both sorted by index with same symbol partition
    gLp, gSp = add_barriers(pool, used, tp_R)
    pool["_gL"] = gLp; pool["_gS"] = gSp
    p = pool.dropna(subset=["_gL", "_gS"])
    X = lambda d, f: d[f].values.astype(np.float32)
    days = max(1, (p.index[-1] - FOLD_STARTS[0]).days)
    arms = {"BASE": feats, "BASE+CLASS": feats + cl_cols}
    res = {}
    for arm, fpool in arms.items():
        cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = p[p.index < cut0]
        tr0f = tr0.dropna(subset=fpool)
        m0 = train_lgbm(X(tr0f, fpool), (tr0f["_gL"].values > 0).astype(int),
                        X(tr0f, fpool), (tr0f["_gL"].values > 0).astype(int), 100, None, 42)
        imp = pd.Series(m0.feature_importance(importance_type="gain"), index=fpool).sort_values(ascending=False)
        top = list(imp.index[:NFEAT])
        acc = {"R": [], "S": [], "fold": [], "yr": {y: {"r": [], "s": []} for y in (2024, 2025, 2026)}}
        for sd in SEEDS:
            for ts0 in FOLD_STARTS:
                te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
                sub = p.dropna(subset=top)
                tr = sub[sub.index < vs]; va = sub[(sub.index >= vs) & (sub.index < te_s)]
                te = sub[(sub.index >= te_s) & (sub.index < te_e)]
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
                r = sel["g"].values - COST
                acc["R"].append(r); acc["S"].append(sz)
                st = pf_wr_sized(r, sz)
                if st: acc["fold"].append(st["pf"])
                for y in (2024, 2025, 2026):
                    mk = yrs == y
                    acc["yr"][y]["r"].append(r[mk]); acc["yr"][y]["s"].append(sz[mk])
        allR = np.concatenate(acc["R"]) if acc["R"] else np.array([])
        allS = np.concatenate(acc["S"]) if acc["S"] else np.array([])
        st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
        fpf = np.array(acc["fold"])
        yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"]
              for y, v in acc["yr"].items()}
        res[arm] = dict(top_features=top, net_pf=st["pf"], wr=st["wr"],
                        trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                        pct_folds_pos=round(float((fpf > 1).mean()), 2) if len(fpf) else None,
                        pf_by_year=yr,
                        n_class_feats_in_top=sum(1 for t in top if t.startswith("cl_")))
        print(f"  [{cls} {tf} R={tp_R}] {arm:11s}: PF {st['pf']}  WR {st['wr']}  "
              f"{res[arm]['trades_per_day']}/day  class-feats-in-top9: {res[arm]['n_class_feats_in_top']}  "
              f"yrs {'/'.join(str(yr[k]) for k in ('2024','2025','2026'))}")
    if res.get("BASE", {}).get("net_pf") and res.get("BASE+CLASS", {}).get("net_pf"):
        lift = round(res["BASE+CLASS"]["net_pf"] - res["BASE"]["net_pf"], 3)
        res["lift"] = lift; res["lift_pass"] = lift >= 0.05
        print(f"  => lift {lift:+.3f}  (bar +0.05: {'PASS' if res['lift_pass'] else 'fail'})")
    return dict(symbols=used, tf=tf, R=tp_R, arms=res)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else None
    tf = sys.argv[2] if len(sys.argv) > 2 else "5m"
    tp_R = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
    classes = [which] if which in CLASSES else list(CLASSES)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase10c_class_feat_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for cls in classes:
        print(f"\n=== {cls} ===")
        r = run_class(cls, tf, tp_R)
        if r: res[cls] = r
    (OUT / "class_feat.json").write_text(json.dumps(dict(cost=COST, results=res), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
