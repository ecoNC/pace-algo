"""
Phase 3: cutoff calibration on the LOCKED 9-feature ranker + NY/state gate.

Goal (HANDOFF 19d): find the proba cutoff that yields ~8-10 trades/day at the best
still-viable NET PF -- WITHOUT trading QUIET/SHOCK. We do NOT loosen the gate
(in_ny & tradeable); we only vary the proba cutoff on the gated universe.

Locked kernel = 9-feature LGBM ranker (see results/.../simplify.json, set "9").
Edge = SELECTION within a gated bad population (refuted: structural setups, ML-free).

Sweeps:
  * fixed quantiles q in {0.80, 0.85, 0.90, 0.93, 0.95, 0.97} on gated VAL proba
  * vol-adjusted: looser cutoff in EXPANSION, tighter in NORMAL (the gated universe
    only contains vol_regime NORMAL|EXPANSION, since QUIET/SHOCK are non-tradeable).
    Rationale: EXPANSION bars move more -> net edge/trade larger -> can afford lower
    selectivity; NORMAL bars are thinner -> stay strict.

Walk-forward (rolling quarters) x seeds, net@1.0pip, next-bar-open. Tier-1 5m, FVG-fixed.

Output: results/model_validation/phase3_cutoff_<UTC>/phase3.json
Run:    python scripts/phase3_cutoff.py
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

from setup_makeorbreak import barrier_R, pip_size
from model_validation_suite import build_extended, train_lgbm, predict
from core.state.market_state import classify_market_state, EXPANSION, NORMAL
from core.train.dataset import binary_label_for_long

# LOCKED 9-feature set (simplify.json -> subsets["9"]); fewer feats = higher net PF + lower std.
FEATURES_9 = [
    "hour_cos", "hour_sin", "rvol_20", "ema_20_dist_atr", "atr_pct",
    "htf_4h_rsi_14", "is_fx_market_open", "in_ny", "htf_4h_atr_percentile_100",
]
PAIRS = ["GBPUSD", "USDJPY", "USDCAD"]
SEEDS = [42, 7]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
SPREAD_PIP = 1.0

QUANTILES = [0.80, 0.85, 0.90, 0.93, 0.95, 0.97]
# vol-adjusted presets: (name, q_in_EXPANSION, q_in_NORMAL)
VOL_ADJ = [("voladj_88/95", 0.88, 0.95), ("voladj_85/93", 0.85, 0.93)]


def build_pool():
    """Tier-1 pool with gate flags + vol_regime + net long-R barrier. (FVG-fixed source.)"""
    from core.features.engineer import atr as atr_fn
    frames = []
    for p in PAIRS:
        ext = build_extended(p).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{p}_5m.parquet")
        st = classify_market_state(raw)
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        lr = barrier_R(raw["open"].values, raw["high"].values, raw["low"].values,
                       raw["close"].values, a, "long")
        lr = lr - (SPREAD_PIP * pip_size(p)) / np.where(a > 0, a, np.nan)
        ext["_in_ny"] = st["in_ny"].reindex(ext.index).values
        ext["_tradeable"] = st["tradeable"].reindex(ext.index).values
        ext["_vol_regime"] = st["vol_regime"].reindex(ext.index).values
        ext["_longR_net"] = pd.Series(lr, index=raw.index).reindex(ext.index).values
        ext["symbol"] = p
        frames.append(ext)
    pool = pd.concat(frames).sort_index()
    pool = pool.dropna(subset=FEATURES_9 + ["label"])
    return pool


def pf(rs):
    rs = rs[np.isfinite(rs)]
    if len(rs) < 10:
        return None
    gw = rs[rs > 0].sum(); gl = -rs[rs <= 0].sum()
    return float(gw / gl) if gl > 0 else 999.0


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase3_cutoff_{stamp}"
    OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    print(f"pool={len(pool):,}  features=9  pairs={PAIRS}  span_days={days}")

    # accumulators: spec_name -> {"pfs": [...per fold...], "ntr": total signals}
    specs = [f"q{int(q*100)}" for q in QUANTILES] + [n for n, _, _ in VOL_ADJ]
    acc = {s: {"pfs": [], "ntr": 0} for s in specs}

    for sd in SEEDS:
        for ts in FOLD_STARTS:
            te_s, te_e = ts, ts + pd.DateOffset(months=3)
            vs = ts - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]
            va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300:
                continue
            mdl = train_lgbm(tr[FEATURES_9].values.astype(np.float32),
                             binary_label_for_long(tr["label"]).values,
                             va[FEATURES_9].values.astype(np.float32),
                             binary_label_for_long(va["label"]).values, 100, None, sd)
            gate_v = va["_in_ny"].values & va["_tradeable"].values
            gate_t = te["_in_ny"].values & te["_tradeable"].values
            if gate_v.sum() < 100 or gate_t.sum() < 100:
                continue
            pv = predict(mdl, "lgbm", va[FEATURES_9].values.astype(np.float32))
            pt = predict(mdl, "lgbm", te[FEATURES_9].values.astype(np.float32))
            rnet = te["_longR_net"].values
            vreg_v = va["_vol_regime"].values
            vreg_t = te["_vol_regime"].values

            # fixed-quantile cutoffs
            for q in QUANTILES:
                cut = float(np.quantile(pv[gate_v], q))
                sig = (pt >= cut) & gate_t
                rs = rnet[sig]
                p = pf(rs)
                if p is not None:
                    acc[f"q{int(q*100)}"]["pfs"].append(p)
                acc[f"q{int(q*100)}"]["ntr"] += int(np.isfinite(rs).sum())

            # vol-adjusted cutoffs (split gated universe by NORMAL/EXPANSION)
            for name, q_exp, q_norm in VOL_ADJ:
                v_exp = gate_v & (vreg_v == EXPANSION)
                v_norm = gate_v & (vreg_v == NORMAL)
                if v_exp.sum() < 30 or v_norm.sum() < 30:
                    continue
                cut_exp = float(np.quantile(pv[v_exp], q_exp))
                cut_norm = float(np.quantile(pv[v_norm], q_norm))
                sig = gate_t & (
                    ((vreg_t == EXPANSION) & (pt >= cut_exp)) |
                    ((vreg_t == NORMAL) & (pt >= cut_norm)))
                rs = rnet[sig]
                p = pf(rs)
                if p is not None:
                    acc[name]["pfs"].append(p)
                acc[name]["ntr"] += int(np.isfinite(rs).sum())

    results = {}
    for s in specs:
        pfs = acc[s]["pfs"]
        results[s] = dict(
            net_pf_mean=round(float(np.mean(pfs)), 3) if pfs else None,
            net_pf_std=round(float(np.std(pfs)), 3) if pfs else None,
            folds=len(pfs),
            trades_per_day=round(acc[s]["ntr"] / (len(SEEDS) * days), 2),
        )

    (OUT / "phase3.json").write_text(json.dumps(
        dict(features=FEATURES_9, pairs=PAIRS, seeds=SEEDS, spread_pip=SPREAD_PIP,
             quantiles=QUANTILES, vol_adj=VOL_ADJ, results=results),
        indent=2, default=str), encoding="utf-8")

    print(f"\n{'spec':14s} {'net_PF':>7s} {'std':>6s} {'folds':>6s} {'trades/day':>11s}")
    for s in specs:
        d = results[s]
        pfm = f"{d['net_pf_mean']:.3f}" if d["net_pf_mean"] is not None else "  n/a"
        std = f"{d['net_pf_std']:.3f}" if d["net_pf_std"] is not None else " n/a"
        print(f"{s:14s} {pfm:>7s} {std:>6s} {d['folds']:>6d} {d['trades_per_day']:>11.2f}")
    print(f"\nTarget = ~8-10 trades/day at net PF still > 1.0 (ideally >= 1.10).")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
