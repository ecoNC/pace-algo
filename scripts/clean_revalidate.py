"""
Clean re-validation (post-FVG-fix): does Lean-4 still lift NET on 30m?

All prior absolute numbers ran on the biased 10% sample. This re-checks the
headline claim (lean-4 cross-asset lift) on CLEAN, full data, at 30m, NET of
spread, walk-forward x 3 seeds. base-73 vs base-73 + lean-4.

Output: results/model_validation/revalidate_<UTC>/revalidate.json
Run: python scripts/clean_revalidate.py
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

from confirm_30m import (build_30m, sim_net, pf_wr, persist, pip_size,
                         PAIRS, TIER1, SPREADS, VAL_WEEKS, FOLD_STARTS)
from core.features import build_usd_strength, compute_cross_asset_features, CROSS_ASSET_FEATURES
from model_validation_suite import train_lgbm, predict
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEEDS = [42, 1, 7]


def build():
    exts, closes = {}, {}
    for s in PAIRS:
        e, c = build_30m(s); exts[s] = e; closes[s] = c
    usd_ret, R = build_usd_strength(closes)
    for s in PAIRS:
        ca = compute_cross_asset_features(s, usd_ret, R)[CROSS_ASSET_FEATURES].reindex(exts[s].index)
        exts[s] = exts[s].join(ca)
    pool = pd.concat(exts.values()).sort_index()
    aug = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and not c.startswith("_")]
    base = [c for c in aug if c not in CROSS_ASSET_FEATURES]
    pool = pool.dropna(subset=aug + ["label"])
    return pool, base, aug


def net_wf(pool, feat, seed, spread):
    folds = []
    for ts in FOLD_STARTS:
        test_start, test_end = ts, ts + pd.DateOffset(months=3)
        val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < val_start]; va = pool[(pool.index >= val_start) & (pool.index < test_start)]
        te = pool[(pool.index >= test_start) & (pool.index < test_end)]
        if len(tr) < 5000 or len(va) < 500 or len(te) < 300:
            continue
        m = train_lgbm(tr[feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                       va[feat].values.astype(np.float32), binary_label_for_long(va["label"]).values, 100, None, seed)
        q97 = float(np.quantile(predict(m, "lgbm", va[feat].values.astype(np.float32)), 0.97))
        te = te.copy(); te["_sig"] = predict(m, "lgbm", te[feat].values.astype(np.float32)) >= q97
        rs = []
        for p in TIER1:
            sub = te[te["symbol"] == p]
            if len(sub) >= 50:
                rs += sim_net(sub, spread * pip_size(p))
        r = pf_wr(rs)
        if r and r["n"] >= 10:
            folds.append(r["pf"])
    return folds


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"revalidate_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, base_feat, aug_feat = build()
    print(f"CLEAN 30m pool={len(pool):,}  base={len(base_feat)}  aug(+lean4)={len(aug_feat)}\n")

    out = {}
    for spread in SPREADS:
        print(f"--- spread {spread} pip (Tier-1 pooled net) ---")
        per = {}
        for name, feat in [("base73", base_feat), ("base73+lean4", aug_feat)]:
            lifts = []
            agg_folds = []
            for sd in SEEDS:
                agg_folds += net_wf(pool, feat, sd, spread)
            d = persist(agg_folds)
            per[name] = d
            if d:
                print(f"  {name:14s} PF mean {d['pf_mean']:.3f}  PF>1 {d['pf_gt1']}/{d['n']}  min {d['pf_min']:.2f}  std {d['pf_std']:.2f}")
        if per.get("base73") and per.get("base73+lean4"):
            lift = round(per["base73+lean4"]["pf_mean"] - per["base73"]["pf_mean"], 3)
            print(f"  -> lean-4 NET lift @ {spread}pip: {lift:+.3f}")
            per["lean4_net_lift"] = lift
        out[f"{spread}pip"] = per
        print()

    (out_dir / "revalidate.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Done -> {out_dir}")


if __name__ == "__main__":
    main()
