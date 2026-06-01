"""
Phase 4 (quality): improve WR/PF via (a) trend-alignment gate, (b) dynamic exits.

Baseline = locked V1: long + USDCHF-short, POOLED top10, ECN 0.5pip, long-9 features.
Each lever is evaluated under the SAME selection machinery so trades/day is held ~const
(threshold recalibrated per variant) -> a WR/PF lift means the kept trades are genuinely
better, not just fewer.

LEVERS
  trend gate (soft) : long not allowed in TREND_DOWN; short not allowed in TREND_UP.
  trend gate (hard) : long only in TREND_UP; short only in TREND_DOWN.
  exit BE           : breakeven-stop -- once +1R reached, SL -> entry (time = mark-to-close).
  exit TRAIL        : ATR(1.0) trailing stop after +1R (time = mark-to-close).
  (static_mtm shown as the apples-to-apples exit anchor; v1 0-on-time is the product anchor.)

Output: results/model_validation/phase4_gate_exits_<UTC>/gate_exits.json
Run:    python scripts/phase4_gate_exits.py
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

from phase3_density import build_pool, FEATURES_9, netR, stats, SEEDS, VAL_WEEKS, FOLD_STARTS
from phase3_selection_compare import calib_thr
from setup_makeorbreak import pip_size, TB, TP_R, SL_R
from model_validation_suite import train_lgbm, predict
from core.state.market_state import classify_market_state, TREND_UP, TREND_DOWN

SPREAD, TOPN = 0.5, 10


def barrier_dyn(o, h, l, c, atr, direction, mode):
    """Gross R per bar with managed exit. mode: static|be|trail. time-barrier = mark-to-close."""
    n = len(c); R = np.full(n, np.nan)
    for i in range(n - TB - 1):
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        entry = c[i]; r = None
        if direction == "long":
            tp = entry + TP_R * a; sl = entry - SL_R * a; be_trig = entry + a; armed = False; trail = sl
            for k in range(i + 1, i + 1 + TB):
                if mode != "static" and not armed and h[k] >= be_trig:
                    armed = True; sl = max(sl, entry)
                if mode == "trail" and armed:
                    trail = max(trail, h[k] - a); sl = max(sl, trail)
                if l[k] <= sl:
                    r = (sl - entry) / a; break
                if h[k] >= tp:
                    r = TP_R; break
            if r is None:
                r = (c[i + TB] - entry) / a
        else:
            tp = entry - TP_R * a; sl = entry + SL_R * a; be_trig = entry - a; armed = False; trail = sl
            for k in range(i + 1, i + 1 + TB):
                if mode != "static" and not armed and l[k] <= be_trig:
                    armed = True; sl = min(sl, entry)
                if mode == "trail" and armed:
                    trail = min(trail, l[k] + a); sl = min(sl, trail)
                if h[k] >= sl:
                    r = (entry - sl) / a; break
                if l[k] <= tp:
                    r = TP_R; break
            if r is None:
                r = (entry - c[i + TB]) / a
        R[i] = r
    return R


def augment(pool):
    """Add per-bar trend regime + dynamic-exit gross R arrays per direction."""
    pool = pool.copy()
    for col in ["_trend", "_be_long", "_be_short", "_tr_long", "_tr_short", "_st_long", "_st_short"]:
        pool[col] = np.nan
    pool["_trend"] = pool["_trend"].astype(object)
    for p in pool["symbol"].unique():
        m = (pool["symbol"] == p).values
        idx = pool.index[m]
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{p}_5m.parquet")
        st = classify_market_state(raw)
        from core.features.engineer import atr as atr_fn
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        o, hi, lo, cl = raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values
        arr = {}
        for d in ("long", "short"):
            for mode, key in [("static", "_st"), ("be", "_be"), ("trail", "_tr")]:
                arr[f"{key}_{d}"] = pd.Series(barrier_dyn(o, hi, lo, cl, a, d, mode), index=raw.index)
        tr = st["trend_regime"]
        pool.loc[m, "_trend"] = tr.reindex(idx).values
        for key, s in arr.items():
            pool.loc[m, key] = s.reindex(idx).values
    return pool


def build_cands(df, ptL, ptS, gate, gate_mode, gross_long, gross_short):
    """USDCHF-short config candidates with optional trend-align gate. Returns ts/day/year/proba/gR/cost."""
    gi = np.where(gate)[0]
    sym = df["symbol"].values[gi]; trend = df["_trend"].values[gi]
    ts = df.index[gi]; cost = df["_cost"].values[gi]
    gL = df[gross_long].values[gi]; gS = df[gross_short].values[gi]
    # long leg (all pairs)
    okL = np.ones(len(gi), bool)
    # short leg (USDCHF only)
    okS = (sym == "USDCHF")
    if gate_mode == "soft":
        okL &= (trend != TREND_DOWN); okS &= (trend != TREND_UP)
    elif gate_mode == "hard":
        okL &= (trend == TREND_UP); okS &= (trend == TREND_DOWN)
    fr = [pd.DataFrame({"ts": ts[okL], "proba": ptL[gi][okL], "gR": gL[okL], "cost": cost[okL], "row": gi[okL]}),
          pd.DataFrame({"ts": ts[okS], "proba": ptS[gi][okS], "gR": gS[okS], "cost": cost[okS], "row": gi[okS]})]
    cand = pd.concat(fr).sort_values("proba", ascending=False).drop_duplicates("row")
    cand["day"] = cand["ts"].dt.normalize(); cand["year"] = cand["ts"].dt.year
    return cand


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase4_gate_exits_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = augment(build_pool())
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d: d[FEATURES_9].values.astype(np.float32)
    print(f"pool={len(pool):,}  span_days={days}")

    # variants: (gate_mode, gross_long_col, gross_short_col)
    variants = {
        "V1_baseline":      ("none", "_grossR_long", "_grossR_short"),
        "gate_soft":        ("soft", "_grossR_long", "_grossR_short"),
        "gate_hard":        ("hard", "_grossR_long", "_grossR_short"),
        "exit_static_mtm":  ("none", "_st_long", "_st_short"),
        "exit_BE":          ("none", "_be_long", "_be_short"),
        "exit_TRAIL":       ("none", "_tr_long", "_tr_short"),
        "gate_soft+exit_BE":("soft", "_be_long", "_be_short"),
    }
    acc = {v: {"R": [], "pf": [], "yr": {}} for v in variants}

    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            gv = va["_in_ny"].values & va["_tradeable"].values
            gt = te["_in_ny"].values & te["_tradeable"].values
            if gv.sum() < 100 or gt.sum() < 100: continue
            mL = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, 100, None, sd)
            mS = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, 100, None, sd)
            pvL, ptL = predict(mL, "lgbm", X(va)), predict(mL, "lgbm", X(te))
            pvS, ptS = predict(mS, "lgbm", X(va)), predict(mS, "lgbm", X(te))
            for v, (gmode, gl, gs) in variants.items():
                cv = build_cands(va, pvL, pvS, gv, gmode, gl, gs)
                ct = build_cands(te, ptL, ptS, gt, gmode, gl, gs)
                thr = calib_thr(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
                sel = ct[ct["proba"].values >= thr]
                r = netR(sel["gR"].values, sel["cost"].values, SPREAD)
                acc[v]["R"].append(r); st = stats(r); acc[v]["pf"].append(st["pf"] if st else None)
                for y in (2024, 2025, 2026):
                    ry = netR(sel[sel["year"] == y]["gR"].values, sel[sel["year"] == y]["cost"].values, SPREAD)
                    acc[v]["yr"].setdefault(y, []).append(ry)

    def block(d):
        allR = np.concatenate(d["R"]) if d["R"] else np.array([])
        st = stats(allR) or {"n": 0, "wr": None, "pf": None}
        pfl = [p for p in d["pf"] if p is not None]
        yr = {str(y): (stats(np.concatenate(v)) or {"pf": None})["pf"] for y, v in d["yr"].items()}
        return dict(trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                    net_pf=round(float(np.mean(pfl)), 3) if pfl else None,
                    pf_std=round(float(np.std(pfl)), 3) if pfl else None, wr=st["wr"], pf_by_year=yr)

    res = {v: block(acc[v]) for v in variants}
    (OUT / "gate_exits.json").write_text(json.dumps(dict(spread=SPREAD, topN=TOPN, results=res),
                                                     indent=2, default=str), encoding="utf-8")
    print(f"\n{'variant':20s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'tr/day':>7s}  {'PF 24/25/26'}")
    for v in variants:
        d = res[v]; pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else " n/a"
        yr = "/".join(str(d["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
        print(f"{v:20s} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>7.2f}  {yr}")
    print(f"\nLift vs V1_baseline = better WR/PF at same ~10/day. Done -> {OUT}")


if __name__ == "__main__":
    main()
