"""
Harden the cross-asset feature lift before building on it.

  1. Standardized pipeline: dropna on base_feat + NEW_FEATS + label, so base and
     +cross-asset are evaluated on IDENTICAL rows (clean comparison).
  2. Multi-seed (42/1/7): is the +0.10 PF lift seed-robust or variance?
  3. Feature importance: do the 5 new features rank structurally among the 78
     (gain share), or are they noise?

Output: results/model_validation/crossasset_harden_<UTC>/harden.json
Run: python scripts/cross_asset_harden.py
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

from cross_asset_features import (build_usd_index, cross_asset_for_pair, NEW_FEATS,
                                   POOL_PAIRS, CORE, VAL_WEEKS, FOLD_STARTS)
from model_validation_suite import build_extended, train_lgbm, predict, wr_pf_overlapping
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEEDS = [42, 1, 7]


def build_aug_pool():
    usd_ret, usd_breadth, R = build_usd_index()
    fr = []
    for s in POOL_PAIRS:
        ext = build_extended(s).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        ext["symbol"] = s
        ca = cross_asset_for_pair(s, usd_ret, usd_breadth, R).reindex(ext.index).astype("float32")
        fr.append(ext.join(ca))
    pool = pd.concat(fr).sort_index()
    base_feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and c not in NEW_FEATS]
    aug_feat = base_feat + NEW_FEATS
    pool = pool.dropna(subset=aug_feat + ["label"])   # identical rows for base & aug
    return pool, base_feat, aug_feat


def walkforward(pool, feat, seed, capture_gain=False):
    folds, gain_acc = [], None
    for ts in FOLD_STARTS:
        test_start, test_end = ts, ts + pd.DateOffset(months=3)
        val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < val_start]; va = pool[(pool.index >= val_start) & (pool.index < test_start)]
        te = pool[(pool.index >= test_start) & (pool.index < test_end)]
        if len(tr) < 20000 or len(va) < 2000 or len(te) < 500:
            continue
        model = train_lgbm(tr[feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                           va[feat].values.astype(np.float32), binary_label_for_long(va["label"]).values,
                           100, None, seed)
        q97 = float(np.quantile(predict(model, "lgbm", va[feat].values.astype(np.float32)), 0.97))
        tec = te[te["symbol"].isin(CORE)]
        pt = predict(model, "lgbm", tec[feat].values.astype(np.float32))
        folds.append(wr_pf_overlapping(tec["label"].values[pt >= q97].astype(int)))
        if capture_gain:
            g = model.feature_importance(importance_type="gain")
            gain_acc = g if gain_acc is None else gain_acc + g
    pfs = [f["pf"] for f in folds if np.isfinite(f["pf"]) and f["n"] >= 10]
    wrs = [f["wr"] for f in folds if f["n"] >= 10]
    res = dict(pf_mean=round(float(np.mean(pfs)), 3), pf_gt1=sum(1 for x in pfs if x > 1.0),
               n_folds=len(pfs), pf_min=round(float(np.min(pfs)), 3),
               pf_std=round(float(np.std(pfs)), 3), wr_mean=round(float(np.mean(wrs)), 4))
    return res, gain_acc


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"crossasset_harden_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, base_feat, aug_feat = build_aug_pool()
    print(f"Standardized pool={len(pool):,}  base={len(base_feat)}  aug={len(aug_feat)}\n")

    print("=== MULTI-SEED LIFT (standardized, identical rows) ===")
    lifts, per_seed = [], {}
    gain_total = None
    for sd in SEEDS:
        b, _ = walkforward(pool, base_feat, sd)
        a, g = walkforward(pool, aug_feat, sd, capture_gain=True)
        lift = round(a["pf_mean"] - b["pf_mean"], 3); lifts.append(lift)
        per_seed[sd] = dict(base=b, aug=a, lift=lift)
        gain_total = g if gain_total is None else gain_total + g
        print(f"  seed {sd}: base PF {b['pf_mean']:.3f} -> aug {a['pf_mean']:.3f}  lift {lift:+.3f}  "
              f"(aug min {a['pf_min']:.2f}, WR {a['wr_mean']:.3f}, {a['pf_gt1']}/{a['n_folds']})")
    print(f"\n  LIFT mean {np.mean(lifts):+.3f}  std {np.std(lifts):.3f}  min {min(lifts):+.3f}  "
          f"-> {'ROBUST' if min(lifts) >= 0.02 else 'FRAGILE'}")

    # Feature importance (gain share, averaged over seeds*folds via accumulation)
    print("\n=== FEATURE IMPORTANCE: rank of 5 new features among 78 (gain share) ===")
    gs = gain_total / gain_total.sum()
    order = np.argsort(-gs)
    rank_of = {aug_feat[i]: int(np.where(order == i)[0][0]) + 1 for i in range(len(aug_feat))}
    fi = []
    for f in NEW_FEATS:
        idx = aug_feat.index(f)
        fi.append(dict(feature=f, gain_share=round(float(gs[idx]), 4), rank=rank_of[f]))
        print(f"  {f:20s} gain_share {gs[idx]*100:5.2f}%  rank {rank_of[f]}/78")
    top10 = [aug_feat[i] for i in order[:10]]
    print(f"\n  Top-10 features overall: {top10}")

    payload = dict(seeds=SEEDS, per_seed=per_seed,
                   lift_mean=round(float(np.mean(lifts)), 3), lift_std=round(float(np.std(lifts)), 3),
                   lift_min=round(float(min(lifts)), 3),
                   verdict="ROBUST" if min(lifts) >= 0.02 else "FRAGILE",
                   feature_importance=fi, top10_overall=top10)
    (out_dir / "harden.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
