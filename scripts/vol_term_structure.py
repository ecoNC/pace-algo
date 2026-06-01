"""
Feature frontier #2: Volatility Term-Structure — INCREMENTAL test over Lean-4.

The key question for release-ready potential: does VTS add ON TOP of the
already-validated Lean-4 factor set, or is it redundant? Compares
  (base + Lean-4)            <- validated reference
  (base + Lean-4 + VTS)      <- does VTS add more?
3 seeds, walk-forward, +0.05 gate on the INCREMENTAL lift, + importance.

VTS family (cross-horizon vol relationships, distinct from per-horizon vol):
  vts_5m_1h    atr%(5m)/atr%(1h)     short-vs-medium vol
  vts_1h_4h    atr%(1h)/atr%(4h)     medium-vs-long vol
  vts_slope    (atr%4h-atr%5m)/atr%5m  term-structure slope
  volofvol_20  CoV of atr%(5m) over 20 bars
  atr_accel_5  atr%(5m)/atr%(5m)[5]-1  short-term vol acceleration

Output: results/model_validation/vts_<UTC>/vts.json
Run: python scripts/vol_term_structure.py
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

from cross_asset_features import build_usd_index, POOL_PAIRS, CORE, VAL_WEEKS, FOLD_STARTS
from factor_features import factor_for_pair, walkforward, SEEDS
from factor_lean import LEAN
from model_validation_suite import build_extended, DATA_V2
from core.features.engineer import atr as atr_fn
from core.train.dataset import NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
TF = "5m"
VTS = ["vts_5m_1h", "vts_1h_4h", "vts_slope", "volofvol_20", "atr_accel_5"]
EPS = 1e-9


def atr_pct(sym, tf):
    raw = pd.read_parquet(DATA_V2 / f"{sym}_{tf}.parquet")
    return (atr_fn(raw["high"], raw["low"], raw["close"], 14) / raw["close"]).rename(f"atr_{tf}")


def vts_for_pair(sym, index):
    a5 = atr_pct(sym, "5m").reindex(index)
    a1 = atr_pct(sym, "1h").reindex(index, method="ffill")
    a4 = atr_pct(sym, "4h").reindex(index, method="ffill")
    df = pd.DataFrame(index=index)
    df["vts_5m_1h"] = a5 / (a1 + EPS)
    df["vts_1h_4h"] = a1 / (a4 + EPS)
    df["vts_slope"] = (a4 - a5) / (a5 + EPS)
    df["volofvol_20"] = a5.rolling(20).std() / (a5.rolling(20).mean() + EPS)
    df["atr_accel_5"] = a5 / (a5.shift(5) + EPS) - 1.0
    return df


def build_pool():
    usd_ret, _, R = build_usd_index()
    fr = []
    for s in POOL_PAIRS:
        ext = build_extended(s).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        ext["symbol"] = s
        fac = factor_for_pair(s, usd_ret, R)[LEAN].reindex(ext.index).astype("float32")
        vts = vts_for_pair(s, ext.index).astype("float32")
        fr.append(ext.join(fac).join(vts))
    pool = pd.concat(fr).sort_index()
    base = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and c not in LEAN and c not in VTS]
    feat_ref = base + LEAN            # validated reference
    feat_aug = base + LEAN + VTS      # + VTS
    pool = pool.dropna(subset=feat_aug + ["label"])
    return pool, feat_ref, feat_aug


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"vts_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, feat_ref, feat_aug = build_pool()
    print(f"pool={len(pool):,}  ref(base+lean4)={len(feat_ref)}  aug(+VTS)={len(feat_aug)}\n")

    print("=== INCREMENTAL VTS over Lean-4 (multi-seed walk-forward) ===")
    lifts, per_seed, gain_total = [], {}, None
    for sd in SEEDS:
        ref, _ = walkforward(pool, feat_ref, sd)
        aug, g = walkforward(pool, feat_aug, sd, capture_gain=True)
        lift = round(aug["pf_mean"] - ref["pf_mean"], 3); lifts.append(lift)
        per_seed[sd] = dict(ref=ref, aug=aug, lift=lift)
        gain_total = g if gain_total is None else gain_total + g
        print(f"  seed {sd}: lean4 {ref['pf_mean']:.3f} -> +VTS {aug['pf_mean']:.3f}  incr {lift:+.3f}  "
              f"(aug min {aug['pf_min']:.2f} WR {aug['wr_mean']:.3f} {aug['pf_gt1']}/{aug['n_folds']})")
    mean_lift = float(np.mean(lifts))
    verdict = "KEEP" if mean_lift >= 0.05 and min(lifts) >= 0.0 else "MARGINAL" if mean_lift >= 0.02 else "REJECT"
    print(f"\n  INCREMENTAL LIFT mean {mean_lift:+.3f}  std {np.std(lifts):.3f}  min {min(lifts):+.3f}  -> {verdict}")

    gs = gain_total / gain_total.sum(); order = np.argsort(-gs)
    rank_of = {feat_aug[i]: int(np.where(order == i)[0][0]) + 1 for i in range(len(feat_aug))}
    print("\n=== VTS importance (rank among full set) ===")
    fi = []
    for f in VTS:
        idx = feat_aug.index(f); fi.append(dict(feature=f, gain_share=round(float(gs[idx]), 4), rank=rank_of[f]))
        print(f"  {f:14s} gain {gs[idx]*100:5.2f}%  rank {rank_of[f]}/{len(feat_aug)}")

    payload = dict(seeds=SEEDS, vts=VTS, per_seed=per_seed, incr_lift_mean=round(mean_lift, 3),
                   incr_lift_std=round(float(np.std(lifts)), 3), incr_lift_min=round(float(min(lifts)), 3),
                   verdict=verdict, feature_importance=fi)
    (out_dir / "vts.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
