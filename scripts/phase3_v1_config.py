"""
Phase 3 FINAL: pick the V1 config. POOLED selection (the winning, lookahead-free
mechanic) at target ~8 and ~10 trades/day, comparing three short policies:

  long_only            : longs only (robust everywhere, but density-capped)
  long_short_all       : long + short on all 5 pairs (pooled down-weights weak shorts)
  long_short_usdchf    : long + short ONLY on USDCHF (the one robust short)

All on long-9 features (short-specific features were refuted). Per spread profile
(0.3/0.5/1.0pip). Reports PF / WR / trades-day / std + per-year stability.

Output: results/model_validation/phase3_v1_<UTC>/v1_config.json
Run:    python scripts/phase3_v1_config.py
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

from phase3_density import build_pool, FEATURES_9, netR, stats, SEEDS, VAL_WEEKS, FOLD_STARTS, SPREADS
from phase3_selection_compare import calib_thr
from model_validation_suite import train_lgbm, predict

TOPN = [8, 10]
CONFIGS = ["long_only", "long_short_all", "long_short_usdchf"]


def build_cands(df, ptL, ptS, gate, cfg):
    """Pooled candidate frame per config: ts, day, proba, gR(chosen dir), cost, year."""
    gi = np.where(gate)[0]
    sym = df["symbol"].values[gi]
    ts = df.index[gi]
    frames = [pd.DataFrame({"ts": ts, "proba": ptL[gi], "gR": df["_grossR_long"].values[gi],
                            "cost": df["_cost"].values[gi], "row": gi})]
    if cfg != "long_only":
        keep = np.ones(len(gi), bool) if cfg == "long_short_all" else (sym == "USDCHF")
        frames.append(pd.DataFrame({"ts": ts[keep], "proba": ptS[gi][keep],
                                    "gR": df["_grossR_short"].values[gi][keep],
                                    "cost": df["_cost"].values[gi][keep], "row": gi[keep]}))
    cand = pd.concat(frames)
    cand = cand.sort_values("proba", ascending=False).drop_duplicates("row")
    cand["day"] = cand["ts"].dt.normalize(); cand["year"] = cand["ts"].dt.year
    return cand


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase3_v1_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d: d[FEATURES_9].values.astype(np.float32)
    print(f"pool={len(pool):,}  span_days={days}")

    acc = {c: {s: {n: {"R": [], "pf": [], "yr": {}} for n in TOPN} for s in SPREADS} for c in CONFIGS}

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
            for cfg in CONFIGS:
                cv = build_cands(va, pvL, pvS, gv, cfg); ct = build_cands(te, ptL, ptS, gt, cfg)
                val_days = max(1, cv["day"].nunique())
                for n in TOPN:
                    thr = calib_thr(cv["proba"].values, val_days, n)
                    sel = ct[ct["proba"].values >= thr]
                    for s in SPREADS:
                        r = netR(sel["gR"].values, sel["cost"].values, s)
                        acc[cfg][s][n]["R"].append(r)
                        st = stats(r); acc[cfg][s][n]["pf"].append(st["pf"] if st else None)
                        for y in (2024, 2025, 2026):
                            ry = netR(sel[sel["year"] == y]["gR"].values, sel[sel["year"] == y]["cost"].values, s)
                            acc[cfg][s][n]["yr"].setdefault(y, []).append(ry)

    def block(d):
        allR = np.concatenate(d["R"]) if d["R"] else np.array([])
        st = stats(allR) or {"n": 0, "wr": None, "pf": None}
        pfl = [p for p in d["pf"] if p is not None]
        yr = {str(y): (stats(np.concatenate(v)) or {"pf": None})["pf"] for y, v in d["yr"].items()}
        return dict(trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                    net_pf=round(float(np.mean(pfl)), 3) if pfl else None,
                    pf_std=round(float(np.std(pfl)), 3) if pfl else None,
                    wr=st["wr"], pf_by_year=yr)

    res = {c: {f"{s}pip": {f"top{n}": block(acc[c][s][n]) for n in TOPN} for s in SPREADS} for c in CONFIGS}
    (OUT / "v1_config.json").write_text(json.dumps(dict(configs=CONFIGS, spreads=SPREADS, topN=TOPN,
                                                         features=FEATURES_9, results=res), indent=2, default=str), encoding="utf-8")

    for s in SPREADS:
        print(f"\n=== spread {s}pip ===")
        print(f"{'config':20s} {'N':4s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'tr/day':>7s}  {'PF 24/25/26'}")
        for c in CONFIGS:
            for n in TOPN:
                d = res[c][f"{s}pip"][f"top{n}"]
                pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else " n/a"
                yr = "/".join(str(d["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
                print(f"{c:20s} {n:<4d} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>7.2f}  {yr}")
    print(f"\nPick highest PF at ~8-10/day with WR>0.5, low std, AND all years positive (stability).")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
