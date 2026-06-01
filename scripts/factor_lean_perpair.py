"""
Per-pair confirmation of the Lean-4 factor lift (selection-bias check).

Is the +0.154 pooled lift broad-based across pairs, or concentrated in one?
Per pair (Tier-1 + Conditional), walk-forward base vs +Lean-4, 3 seeds.

Output: results/model_validation/factor_perpair_<UTC>/perpair.json
Run: python scripts/factor_lean_perpair.py
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

from factor_lean import build_pool, LEAN
from factor_features import SEEDS
from cross_asset_features import VAL_WEEKS, FOLD_STARTS
from model_validation_suite import train_lgbm, predict, wr_pf_overlapping
from core.train.dataset import binary_label_for_long

EVAL_PAIRS = ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF", "AUDUSD"]
OUT_BASE = REPO / "results" / "model_validation"


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"factor_perpair_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, base_feat, aug_feat = build_pool()
    print(f"pool={len(pool):,}  base={len(base_feat)} aug={len(aug_feat)}  LEAN={LEAN}\n")

    # per pair: lists of fold PFs (across seeds) for base and aug
    acc = {p: {"base": [], "aug": [], "base_wr": [], "aug_wr": []} for p in EVAL_PAIRS}

    for sd in SEEDS:
        for ts in FOLD_STARTS:
            test_start, test_end = ts, ts + pd.DateOffset(months=3)
            val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < val_start]; va = pool[(pool.index >= val_start) & (pool.index < test_start)]
            te = pool[(pool.index >= test_start) & (pool.index < test_end)]
            if len(tr) < 20000 or len(va) < 2000 or len(te) < 500:
                continue
            ytr = binary_label_for_long(tr["label"]).values; yva = binary_label_for_long(va["label"]).values
            mb = train_lgbm(tr[base_feat].values.astype(np.float32), ytr, va[base_feat].values.astype(np.float32), yva, 100, None, sd)
            ma = train_lgbm(tr[aug_feat].values.astype(np.float32), ytr, va[aug_feat].values.astype(np.float32), yva, 100, None, sd)
            qb = float(np.quantile(predict(mb, "lgbm", va[base_feat].values.astype(np.float32)), 0.97))
            qa = float(np.quantile(predict(ma, "lgbm", va[aug_feat].values.astype(np.float32)), 0.97))
            for p in EVAL_PAIRS:
                tp = te[te["symbol"].values == p]
                if len(tp) < 100:
                    continue
                lab = tp["label"].values.astype(int)
                pb = predict(mb, "lgbm", tp[base_feat].values.astype(np.float32))
                pa = predict(ma, "lgbm", tp[aug_feat].values.astype(np.float32))
                rb = wr_pf_overlapping(lab[pb >= qb]); ra = wr_pf_overlapping(lab[pa >= qa])
                if rb["n"] >= 10:
                    acc[p]["base"].append(rb["pf"]); acc[p]["base_wr"].append(rb["wr"])
                if ra["n"] >= 10:
                    acc[p]["aug"].append(ra["pf"]); acc[p]["aug_wr"].append(ra["wr"])

    print("=== PER-PAIR LEAN-4 LIFT (q97, walk-forward, mean over seeds*folds) ===")
    print(f"{'pair':7s} {'base_PF':>8s} {'aug_PF':>8s} {'lift':>7s} {'base_WR':>8s} {'aug_WR':>8s}")
    out = {}
    for p in EVAL_PAIRS:
        b = [x for x in acc[p]["base"] if np.isfinite(x)]; a = [x for x in acc[p]["aug"] if np.isfinite(x)]
        if not b or not a:
            continue
        bpf, apf = float(np.mean(b)), float(np.mean(a))
        out[p] = dict(base_pf=round(bpf, 3), aug_pf=round(apf, 3), lift=round(apf - bpf, 3),
                      base_wr=round(float(np.mean(acc[p]["base_wr"])), 3), aug_wr=round(float(np.mean(acc[p]["aug_wr"])), 3),
                      n_obs=len(a))
        d = out[p]
        print(f"{p:7s} {d['base_pf']:>8.3f} {d['aug_pf']:>8.3f} {d['lift']:>+7.3f} {d['base_wr']:>8.3f} {d['aug_wr']:>8.3f}")

    lifts = [out[p]["lift"] for p in out]
    pos = sum(1 for x in lifts if x > 0)
    print(f"\n  pairs with positive lift: {pos}/{len(lifts)}   mean lift {np.mean(lifts):+.3f}   min {min(lifts):+.3f}")
    verdict = "broad-based" if pos >= len(lifts) - 1 and min(lifts) > -0.05 else "concentrated"
    print(f"  VERDICT: {verdict}")

    payload = dict(seeds=SEEDS, lean=LEAN, per_pair=out,
                   pairs_positive=pos, n_pairs=len(lifts), mean_lift=round(float(np.mean(lifts)), 3),
                   min_lift=round(float(min(lifts)), 3), verdict=verdict)
    (out_dir / "perpair.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
