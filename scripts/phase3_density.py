"""
Phase 3 (structural): how to reach ~8-10 trades/day at good net PF + WR + stability.

Cutoff-loosening was refuted (phase3_cutoff.py: edge lives only in the top ~3%).
So density must come from MORE high-quality candidates, not lower-quality ones.
This script tests the structural levers, all at TOP quality (no gate loosening):

  L1  SHORT side       -- we currently trade LONG only; adding shorts ~doubles
                          candidates at the same selectivity (symmetric barrier).
  L2  spread / cost    -- 1.0pip is retail-pessimistic; ECN raw is ~0.3-0.5 on these
                          majors in the London/NY overlap. Cost is the binding constraint.
  L3  more pairs       -- tier-1 (GBP/JPY/CAD) + conditional (NZD/CHF), NY-gated.
  L4  global top-N/day -- the direct formulation: each day take the N best-ranked
                          candidates across the WHOLE universe (pairs x directions).

Both long & short labels + barrier-R are derived from the SAME barrier_R(dir) for a
clean apples-to-apples symmetric comparison (TP 1.5 / SL 1.0 ATR, 24-bar, net of spread).
Walk-forward (rolling quarters) x seeds. Gate = in_ny & tradeable (unchanged).

Output: results/model_validation/phase3_density_<UTC>/density.json
Run:    python scripts/phase3_density.py
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

from setup_makeorbreak import barrier_R, pip_size, TP_R
from model_validation_suite import build_extended, train_lgbm, predict
from core.state.market_state import classify_market_state
from core.features.engineer import atr as atr_fn

FEATURES_9 = [
    "hour_cos", "hour_sin", "rvol_20", "ema_20_dist_atr", "atr_pct",
    "htf_4h_rsi_14", "is_fx_market_open", "in_ny", "htf_4h_atr_percentile_100",
]
PAIRS = ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF"]   # tier-1 + 2 conditional
SEEDS = [42, 7]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
SPREADS = [0.3, 0.5, 1.0]     # pip
Q = 0.97                       # top-quality cutoff (the only net-viable one for longs)
TOPN = [4, 6, 8, 10]           # global trades/day targets


def build_pool():
    """Combined Tier-1+conditional pool with per-direction gross barrier-R + labels + gate."""
    frames = []
    for p in PAIRS:
        ext = build_extended(p).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{p}_5m.parquet")
        st = classify_market_state(raw)
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        gL = barrier_R(raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values, a, "long")
        gS = barrier_R(raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values, a, "short")
        cost = pip_size(p) / np.where(a > 0, a, np.nan)   # per-pip spread cost in R units
        idx = raw.index
        ext["_grossR_long"] = pd.Series(gL, index=idx).reindex(ext.index).values
        ext["_grossR_short"] = pd.Series(gS, index=idx).reindex(ext.index).values
        ext["_cost"] = pd.Series(cost, index=idx).reindex(ext.index).values
        ext["_in_ny"] = st["in_ny"].reindex(ext.index).values
        ext["_tradeable"] = st["tradeable"].reindex(ext.index).values
        ext["_lab_long"] = (ext["_grossR_long"] > 0).astype(int)
        ext["_lab_short"] = (ext["_grossR_short"] > 0).astype(int)
        ext["symbol"] = p
        frames.append(ext)
    pool = pd.concat(frames).sort_index()
    pool = pool.dropna(subset=FEATURES_9 + ["_grossR_long", "_grossR_short", "_cost"])
    return pool


def netR(grossR, cost, spread_pip):
    return grossR - spread_pip * cost


def stats(rs):
    rs = rs[np.isfinite(rs)]
    if len(rs) < 10:
        return None
    w = int((rs > 0).sum()); gw = rs[rs > 0].sum(); gl = -rs[rs <= 0].sum()
    return dict(n=int(len(rs)), wr=round(w / len(rs), 3),
                pf=round(float(gw / gl), 3) if gl > 0 else 999.0)


def agg(pf_list):
    pf_list = [p for p in pf_list if p is not None]
    return (round(float(np.mean(pf_list)), 3), round(float(np.std(pf_list)), 3)) if pf_list else (None, None)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase3_density_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    print(f"pool={len(pool):,}  pairs={len(PAIRS)}  span_days={days}")

    X = lambda d: d[FEATURES_9].values.astype(np.float32)
    # accumulators
    # A) q97 long-only vs long+short, per spread: collect realized net-R across folds, + per-fold PF for std
    A = {s: {"long": {"R": [], "pf": []}, "ls": {"R": [], "pf": []}} for s in SPREADS}
    # B) global top-N/day, per spread per N: realized net-R across folds + per-fold PF
    B = {s: {n: {"R": [], "pf": []} for n in TOPN} for s in SPREADS}

    nfolds = 0
    for sd in SEEDS:
        for ts in FOLD_STARTS:
            te_s, te_e = ts, ts + pd.DateOffset(months=3); vs = ts - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300:
                continue
            gate_v = va["_in_ny"].values & va["_tradeable"].values
            gate_t = te["_in_ny"].values & te["_tradeable"].values
            if gate_v.sum() < 100 or gate_t.sum() < 100:
                continue
            mdl_L = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, 100, None, sd)
            mdl_S = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, 100, None, sd)
            pvL, ptL = predict(mdl_L, "lgbm", X(va)), predict(mdl_L, "lgbm", X(te))
            pvS, ptS = predict(mdl_S, "lgbm", X(va)), predict(mdl_S, "lgbm", X(te))
            cutL = float(np.quantile(pvL[gate_v], Q)); cutS = float(np.quantile(pvS[gate_v], Q))
            gLR, gSR, cost = te["_grossR_long"].values, te["_grossR_short"].values, te["_cost"].values
            sigL = (ptL >= cutL) & gate_t; sigS = (ptS >= cutS) & gate_t
            nfolds += 1

            for s in SPREADS:
                nlr = netR(gLR, cost, s); nsr = netR(gSR, cost, s)
                # long-only
                rl = nlr[sigL]; A[s]["long"]["R"].append(rl)
                st = stats(rl); A[s]["long"]["pf"].append(st["pf"] if st else None)
                # long+short: if both fire on a bar, keep higher-proba direction
                both = sigL & sigS
                takeL = sigL & ~(both & (ptS > ptL)); takeS = sigS & ~(both & (ptL >= ptS))
                rls = np.concatenate([nlr[takeL], nsr[takeS]])
                A[s]["ls"]["R"].append(rls)
                st = stats(rls); A[s]["ls"]["pf"].append(st["pf"] if st else None)

                # B) global top-N/day across universe (gated candidates, both dirs, dedup per symbol-bar)
                cand = []
                gi = np.where(gate_t)[0]
                day = te.index[gi].normalize()
                sym = te["symbol"].values[gi]
                cand_df = pd.DataFrame({
                    "day": np.r_[day, day], "sym": np.r_[sym, sym],
                    "proba": np.r_[ptL[gi], ptS[gi]],
                    "r": np.r_[nlr[gi], nsr[gi]],
                    "dir": ["L"] * len(gi) + ["S"] * len(gi),
                })
                # dedup: per (day,sym, bar) we only allow one direction -> keep higher proba per (index,sym)
                cand_df["row"] = np.r_[gi, gi]
                cand_df = cand_df.sort_values("proba", ascending=False).drop_duplicates(["row"])
                for n in TOPN:
                    picked = cand_df.groupby("day", group_keys=False).head(n)
                    rr = picked["r"].values
                    B[s][n]["R"].append(rr)
                    st = stats(rr); B[s][n]["pf"].append(st["pf"] if st else None)

    # ---- assemble ----
    def block(R_list, pf_list):
        allR = np.concatenate(R_list) if R_list else np.array([])
        st = stats(allR) or {"n": 0, "wr": None, "pf": None}
        pfm, pfs = agg(pf_list)
        return dict(trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                    net_pf=pfm, pf_std=pfs, wr=st["wr"], n=st["n"])

    res = {"q97_long_vs_longshort": {}, "global_topN_per_day": {}}
    for s in SPREADS:
        res["q97_long_vs_longshort"][f"{s}pip"] = {
            "long_only": block(A[s]["long"]["R"], A[s]["long"]["pf"]),
            "long_short": block(A[s]["ls"]["R"], A[s]["ls"]["pf"]),
        }
        res["global_topN_per_day"][f"{s}pip"] = {
            f"top{n}": block(B[s][n]["R"], B[s][n]["pf"]) for n in TOPN}

    (OUT / "density.json").write_text(json.dumps(
        dict(pairs=PAIRS, seeds=SEEDS, cutoff_q=Q, spreads=SPREADS, topN=TOPN,
             folds=nfolds, results=res), indent=2, default=str), encoding="utf-8")

    # ---- print ----
    print(f"\n=== L1+L2  q97, LONG-only vs LONG+SHORT  (5 pairs, per spread) ===")
    print(f"{'spread':8s} {'mode':12s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'trades/day':>11s}")
    for s in SPREADS:
        for mode, key in [("long-only", "long_only"), ("long+short", "long_short")]:
            d = res["q97_long_vs_longshort"][f"{s}pip"][key]
            pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else "  n/a"
            print(f"{s:<8} {mode:12s} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>11.2f}")
    print(f"\n=== L4  GLOBAL TOP-N/DAY across universe (5 pairs x long+short, per spread) ===")
    print(f"{'spread':8s} {'topN':6s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'trades/day':>11s}")
    for s in SPREADS:
        for n in TOPN:
            d = res["global_topN_per_day"][f"{s}pip"][f"top{n}"]
            pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else "  n/a"
            print(f"{s:<8} top{n:<3d} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} {d['trades_per_day']:>11.2f}")
    print(f"\nfolds={nfolds}.  Goal: ~8-10 trades/day at net PF >= ~1.10 with WR healthy + low std.")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
