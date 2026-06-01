"""
Phase 3 deployment: compare LOOKAHEAD-FREE selection mechanics for ~8-10 trades/day.

phase3_density's "global top-N/day" is hindsight (picks the day's best N in retrospect).
Here we measure two deployable, causal mechanics and show the hindsight ceiling:

  POOLED    : single proba threshold across all pairs+directions, calibrated on the
              VALIDATION window to yield ~N/day, applied causally to test. Easiest to
              ship (per-pair threshold), no cross-symbol live ranking.
  CAUSAL_CAP: looser val-calibrated threshold (pooled) + a hard cap of N trades/day,
              filled in TIME ORDER (take up to N best-so-far each day). Realizes
              "my N best per day" without hindsight. Needs a live daily counter.
  CEILING   : hindsight top-N/day (optimistic upper bound, for reference only).

Long+short, 5 pairs, walk-forward, per spread profile (0.3/0.5/1.0pip). Reuses
phase3_density machinery.

Output: results/model_validation/phase3_select_<UTC>/select.json
Run:    python scripts/phase3_selection_compare.py
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

from phase3_density import build_pool, FEATURES_9, netR, stats, SEEDS, VAL_WEEKS, FOLD_STARTS, SPREADS, PAIRS
from model_validation_suite import train_lgbm, predict

TOPN = [8, 10]
CAP_POOL_MULT = 2.5   # causal-cap draws from a ~2.5N/day candidate pool, then caps at N


def candidates(df, ptL, ptS, gate, gLcol="_grossR_long", gScol="_grossR_short"):
    """Gated long+short candidates, deduped per bar to the higher-proba direction.
       Returns DataFrame: ts, day, proba, gR (gross R of chosen dir), cost."""
    gi = np.where(gate)[0]
    n = len(gi)
    ts = df.index[gi]
    proba = np.r_[ptL[gi], ptS[gi]]
    gR = np.r_[df[gLcol].values[gi], df[gScol].values[gi]]
    row = np.r_[gi, gi]
    c = df["_cost"].values[gi]
    cand = pd.DataFrame({"ts": np.r_[ts, ts], "proba": proba, "gR": gR,
                         "cost": np.r_[c, c], "row": row})
    cand = cand.sort_values("proba", ascending=False).drop_duplicates("row")
    cand["day"] = cand["ts"].dt.normalize()
    return cand


def calib_thr(val_proba, val_days, per_day):
    n = len(val_proba)
    if n == 0 or val_days == 0:
        return np.inf
    q = 1.0 - (per_day * val_days) / n
    return float(np.quantile(val_proba, min(max(q, 0.0), 0.9995)))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase3_select_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d: d[FEATURES_9].values.astype(np.float32)
    print(f"pool={len(pool):,}  span_days={days}")

    # acc[mech][spread][N] = {"R":[per-fold arrays], "pf":[per-fold pf]}
    mechs = ["pooled", "causal_cap", "ceiling"]
    acc = {m: {s: {n: {"R": [], "pf": []} for n in TOPN} for s in SPREADS} for m in mechs}

    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            gate_v = va["_in_ny"].values & va["_tradeable"].values
            gate_t = te["_in_ny"].values & te["_tradeable"].values
            if gate_v.sum() < 100 or gate_t.sum() < 100: continue
            mL = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, 100, None, sd)
            mS = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, 100, None, sd)
            cv = candidates(va, predict(mL, "lgbm", X(va)), predict(mS, "lgbm", X(va)), gate_v)
            ct = candidates(te, predict(mL, "lgbm", X(te)), predict(mS, "lgbm", X(te)), gate_t)
            val_days = max(1, cv["day"].nunique())
            te_days = max(1, ct["day"].nunique())

            for n in TOPN:
                thr_pooled = calib_thr(cv["proba"].values, val_days, n)
                thr_loose = calib_thr(cv["proba"].values, val_days, n * CAP_POOL_MULT)
                for s in SPREADS:
                    r_all = netR(ct["gR"].values, ct["cost"].values, s)
                    # POOLED
                    mask = ct["proba"].values >= thr_pooled
                    rp = r_all[mask]; acc["pooled"][s][n]["R"].append(rp)
                    st = stats(rp); acc["pooled"][s][n]["pf"].append(st["pf"] if st else None)
                    # CAUSAL CAP
                    sub = ct[ct["proba"].values >= thr_loose].sort_values("ts")
                    k = sub.groupby("day").cumcount()
                    cap = sub[k.values < n]
                    rc = netR(cap["gR"].values, cap["cost"].values, s)
                    acc["causal_cap"][s][n]["R"].append(rc)
                    st = stats(rc); acc["causal_cap"][s][n]["pf"].append(st["pf"] if st else None)
                    # CEILING (hindsight top-N/day)
                    top = ct.sort_values("proba", ascending=False).groupby("day", group_keys=False).head(n)
                    rh = netR(top["gR"].values, top["cost"].values, s)
                    acc["ceiling"][s][n]["R"].append(rh)
                    st = stats(rh); acc["ceiling"][s][n]["pf"].append(st["pf"] if st else None)

    def block(d):
        allR = np.concatenate(d["R"]) if d["R"] else np.array([])
        st = stats(allR) or {"n": 0, "wr": None, "pf": None}
        pfl = [p for p in d["pf"] if p is not None]
        return dict(trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                    net_pf=round(float(np.mean(pfl)), 3) if pfl else None,
                    pf_std=round(float(np.std(pfl)), 3) if pfl else None,
                    wr=st["wr"], n=st["n"])

    res = {m: {f"{s}pip": {f"top{n}": block(acc[m][s][n]) for n in TOPN} for s in SPREADS} for m in mechs}
    (OUT / "select.json").write_text(json.dumps(
        dict(pairs=PAIRS, seeds=SEEDS, spreads=SPREADS, topN=TOPN, cap_pool_mult=CAP_POOL_MULT,
             results=res), indent=2, default=str), encoding="utf-8")

    for s in SPREADS:
        print(f"\n=== spread {s}pip ===")
        print(f"{'mechanic':12s} {'N':4s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'trades/day':>11s}")
        for m in mechs:
            for n in TOPN:
                d = res[m][f"{s}pip"][f"top{n}"]
                pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else "  n/a"
                print(f"{m:12s} {n:<4d} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>11.2f}")
    print(f"\nPOOLED & CAUSAL_CAP are lookahead-free (deployable). CEILING is hindsight (reference).")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
