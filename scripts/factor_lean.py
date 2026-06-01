"""
Parsimonious factor set — low-dimensional signal hypothesis.

Deepened 10-feature family diluted the lift (+0.044 < lean +0.07). The signal
is low-dimensional. This tests a LEAN-4 set of conceptually distinct axes
(no redundant horizons), chosen by parsimony + importance, not combo-mining:
  idio_mom_20    idiosyncratic momentum
  usd_corr_50    pair-USD coupling direction
  usd_beta_50    pair-USD coupling magnitude
  usd_idx_vol_20 USD regime volatility (new, ranked #3)

3 seeds, standardized, +0.05 OOS gate.

Output: results/model_validation/factor_lean_<UTC>/factor_lean.json
Run: python scripts/factor_lean.py
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

from cross_asset_features import build_usd_index, POOL_PAIRS, CORE
from factor_features import factor_for_pair, walkforward, SEEDS
from model_validation_suite import build_extended
from core.train.dataset import NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
LEAN = ["idio_mom_20", "usd_corr_50", "usd_beta_50", "usd_idx_vol_20"]


def build_pool():
    usd_ret, _, R = build_usd_index()
    fr = []
    for s in POOL_PAIRS:
        ext = build_extended(s).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        ext["symbol"] = s
        fac = factor_for_pair(s, usd_ret, R)[LEAN].reindex(ext.index).astype("float32")
        fr.append(ext.join(fac))
    pool = pd.concat(fr).sort_index()
    base_feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and c not in LEAN]
    aug_feat = base_feat + LEAN
    pool = pool.dropna(subset=aug_feat + ["label"])
    return pool, base_feat, aug_feat


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"factor_lean_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, base_feat, aug_feat = build_pool()
    print(f"pool={len(pool):,}  base={len(base_feat)}  aug={len(aug_feat)} (+{LEAN})\n")

    print("=== MULTI-SEED LIFT (base vs +LEAN-4) ===")
    lifts, per_seed, gain_total = [], {}, None
    for sd in SEEDS:
        b, _ = walkforward(pool, base_feat, sd)
        a, g = walkforward(pool, aug_feat, sd, capture_gain=True)
        lift = round(a["pf_mean"] - b["pf_mean"], 3); lifts.append(lift)
        per_seed[sd] = dict(base=b, aug=a, lift=lift)
        gain_total = g if gain_total is None else gain_total + g
        print(f"  seed {sd}: {b['pf_mean']:.3f} -> {a['pf_mean']:.3f}  lift {lift:+.3f}  "
              f"(aug min {a['pf_min']:.2f} WR {a['wr_mean']:.3f} {a['pf_gt1']}/{a['n_folds']})")
    mean_lift = float(np.mean(lifts))
    verdict = "KEEP" if mean_lift >= 0.05 and min(lifts) >= 0.0 else "MARGINAL" if mean_lift >= 0.02 else "REJECT"
    print(f"\n  LIFT mean {mean_lift:+.3f}  std {np.std(lifts):.3f}  min {min(lifts):+.3f}  -> {verdict}")

    gs = gain_total / gain_total.sum(); order = np.argsort(-gs)
    rank_of = {aug_feat[i]: int(np.where(order == i)[0][0]) + 1 for i in range(len(aug_feat))}
    print("\n=== LEAN-4 importance ===")
    fi = []
    for f in LEAN:
        idx = aug_feat.index(f); fi.append(dict(feature=f, gain_share=round(float(gs[idx]), 4), rank=rank_of[f]))
        print(f"  {f:16s} gain {gs[idx]*100:5.2f}%  rank {rank_of[f]}/{len(aug_feat)}")

    payload = dict(seeds=SEEDS, lean=LEAN, per_seed=per_seed, lift_mean=round(mean_lift, 3),
                   lift_std=round(float(np.std(lifts)), 3), lift_min=round(float(min(lifts)), 3),
                   verdict=verdict, feature_importance=fi)
    (out_dir / "factor_lean.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
