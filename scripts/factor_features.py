"""
Feature frontier #1b: deepened factor-decomposition family.

Hardening showed pair_usd_corr_50 (#3) and pair_idio_mom_20 (#6) are structural;
broad-USD momentum was noise. This expands precisely the winning direction and
prunes the noise, then retests (3 seeds, standardized, +0.05 OOS gate).

Family (10): idio_mom_{5,10,20,50}, usd_corr_{20,50,100}, usd_beta_50,
             usd_beta_chg_20, usd_idx_vol_20.

Output: results/model_validation/factor_<UTC>/factor.json
Run: python scripts/factor_features.py
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

from cross_asset_features import build_usd_index, USD_SIGN, POOL_PAIRS, CORE, VAL_WEEKS, FOLD_STARTS
from model_validation_suite import build_extended, train_lgbm, predict, wr_pf_overlapping
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEEDS = [42, 1, 7]
FAMILY = ["idio_mom_5", "idio_mom_10", "idio_mom_20", "idio_mom_50",
          "usd_corr_20", "usd_corr_50", "usd_corr_100",
          "usd_beta_50", "usd_beta_chg_20", "usd_idx_vol_20"]


def factor_for_pair(sym, usd_ret, R):
    pr = R[sym] * USD_SIGN[sym]                       # pair own log-return
    beta50 = pr.rolling(50).cov(usd_ret) / (usd_ret.rolling(50).var() + 1e-12)
    idio = pr - beta50 * usd_ret                      # idiosyncratic return
    df = pd.DataFrame(index=usd_ret.index)
    for h in (5, 10, 20, 50):
        df[f"idio_mom_{h}"] = idio.rolling(h).sum()
    for w in (20, 50, 100):
        df[f"usd_corr_{w}"] = pr.rolling(w).corr(usd_ret)
    df["usd_beta_50"] = beta50
    df["usd_beta_chg_20"] = beta50 - beta50.shift(20)
    df["usd_idx_vol_20"] = usd_ret.rolling(20).std()
    return df


def build_pool():
    usd_ret, _, R = build_usd_index()
    fr = []
    for s in POOL_PAIRS:
        ext = build_extended(s).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        ext["symbol"] = s
        fac = factor_for_pair(s, usd_ret, R).reindex(ext.index).astype("float32")
        fr.append(ext.join(fac))
    pool = pd.concat(fr).sort_index()
    base_feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and c not in FAMILY]
    aug_feat = base_feat + FAMILY
    pool = pool.dropna(subset=aug_feat + ["label"])
    return pool, base_feat, aug_feat


def walkforward(pool, feat, seed, capture_gain=False):
    folds, gain = [], None
    for ts in FOLD_STARTS:
        test_start, test_end = ts, ts + pd.DateOffset(months=3)
        val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < val_start]; va = pool[(pool.index >= val_start) & (pool.index < test_start)]
        te = pool[(pool.index >= test_start) & (pool.index < test_end)]
        if len(tr) < 20000 or len(va) < 2000 or len(te) < 500:
            continue
        m = train_lgbm(tr[feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                       va[feat].values.astype(np.float32), binary_label_for_long(va["label"]).values, 100, None, seed)
        q97 = float(np.quantile(predict(m, "lgbm", va[feat].values.astype(np.float32)), 0.97))
        tec = te[te["symbol"].isin(CORE)]
        pt = predict(m, "lgbm", tec[feat].values.astype(np.float32))
        folds.append(wr_pf_overlapping(tec["label"].values[pt >= q97].astype(int)))
        if capture_gain:
            g = m.feature_importance(importance_type="gain"); gain = g if gain is None else gain + g
    pfs = [f["pf"] for f in folds if np.isfinite(f["pf"]) and f["n"] >= 10]
    wrs = [f["wr"] for f in folds if f["n"] >= 10]
    return dict(pf_mean=round(float(np.mean(pfs)), 3), pf_gt1=sum(1 for x in pfs if x > 1.0),
                n_folds=len(pfs), pf_min=round(float(np.min(pfs)), 3), pf_std=round(float(np.std(pfs)), 3),
                wr_mean=round(float(np.mean(wrs)), 4)), gain


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"factor_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, base_feat, aug_feat = build_pool()
    print(f"pool={len(pool):,}  base={len(base_feat)}  aug={len(aug_feat)} (+{len(FAMILY)} factor feats)\n")

    print("=== MULTI-SEED LIFT (base vs +factor family) ===")
    lifts, per_seed, gain_total = [], {}, None
    for sd in SEEDS:
        b, _ = walkforward(pool, base_feat, sd)
        a, g = walkforward(pool, aug_feat, sd, capture_gain=True)
        lift = round(a["pf_mean"] - b["pf_mean"], 3); lifts.append(lift)
        per_seed[sd] = dict(base=b, aug=a, lift=lift)
        gain_total = g if gain_total is None else gain_total + g
        print(f"  seed {sd}: {b['pf_mean']:.3f} -> {a['pf_mean']:.3f}  lift {lift:+.3f}  "
              f"(aug min {a['pf_min']:.2f} WR {a['wr_mean']:.3f} {a['pf_gt1']}/{a['n_folds']})")
    print(f"\n  LIFT mean {np.mean(lifts):+.3f}  std {np.std(lifts):.3f}  min {min(lifts):+.3f}  "
          f"vs prior +0.07  -> {'KEEP' if np.mean(lifts) >= 0.05 else 'MARGINAL' if np.mean(lifts) >= 0.02 else 'REJECT'}")

    gs = gain_total / gain_total.sum()
    order = np.argsort(-gs)
    rank_of = {aug_feat[i]: int(np.where(order == i)[0][0]) + 1 for i in range(len(aug_feat))}
    print("\n=== FACTOR FAMILY importance (rank among aug feats) ===")
    fi = []
    for f in FAMILY:
        idx = aug_feat.index(f)
        fi.append(dict(feature=f, gain_share=round(float(gs[idx]), 4), rank=rank_of[f]))
        print(f"  {f:18s} gain {gs[idx]*100:5.2f}%  rank {rank_of[f]}/{len(aug_feat)}")
    print(f"\n  Top-12 overall: {[aug_feat[i] for i in order[:12]]}")

    payload = dict(seeds=SEEDS, per_seed=per_seed, lift_mean=round(float(np.mean(lifts)), 3),
                   lift_std=round(float(np.std(lifts)), 3), lift_min=round(float(min(lifts)), 3),
                   family=FAMILY, feature_importance=fi, top12=[aug_feat[i] for i in order[:12]])
    (out_dir / "factor.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
