"""
Feature frontier #1: Cross-Asset / USD-strength factor features.

The current model sees each pair in isolation (no currency-factor view).
This engineers a USD-strength index from all 7 pairs and derived features,
adds them to the 73, retrains LGBM-100, and tests under walk-forward whether
they lift PERSISTENT WR/PF on the Tier-1 core. Locked rule: keep only if
>= +0.05 PF OOS lift.

New features (per bar, merged onto each pair):
  usd_mom_5, usd_mom_20   broad USD momentum (sign-adjusted mean log-return)
  usd_breadth_20          fraction of USD pairs moving USD-up (agreement)
  pair_usd_corr_50        rolling corr of pair return to USD index (USD-driven?)
  pair_idio_mom_20        pair momentum minus its USD-beta * USD move (idiosyncratic)

Output: results/model_validation/crossasset_<UTC>/crossasset.json
Run: python scripts/cross_asset_features.py
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

from model_validation_suite import build_extended, train_lgbm, predict, wr_pf_overlapping, DATA_V2
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEED = 7
TF = "5m"
ALL7 = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD"]
POOL_PAIRS = ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF", "AUDUSD"]
CORE = ["GBPUSD", "USDJPY", "USDCAD"]
# USD sign: +1 if USD is BASE (USDxxx) -> +ret = USD up; -1 if USD is QUOTE (xxxUSD)
USD_SIGN = {"USDJPY": 1, "USDCHF": 1, "USDCAD": 1, "EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "NZDUSD": -1}
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
NEW_FEATS = ["usd_mom_5", "usd_mom_20", "usd_breadth_20", "pair_usd_corr_50", "pair_idio_mom_20"]


def build_usd_index():
    """USD-strength index (sign-adjusted mean log-return) on the common 5m grid."""
    rets = {}
    for s in ALL7:
        c = pd.read_parquet(DATA_V2 / f"{s}_{TF}.parquet")["close"]
        rets[s] = np.log(c / c.shift(1)) * USD_SIGN[s]   # +ve = USD strengthening
    R = pd.DataFrame(rets).dropna(how="all")
    usd_ret = R.mean(axis=1)                              # broad USD return per bar
    usd_breadth = (R > 0).mean(axis=1)                    # fraction of pairs USD-up
    return usd_ret, usd_breadth, R


def cross_asset_for_pair(sym, usd_ret, usd_breadth, R):
    """Per-pair cross-asset features, indexed like the pair."""
    pr = R[sym] * USD_SIGN[sym]                           # pair's own (un-signed) log-return
    df = pd.DataFrame(index=usd_ret.index)
    df["usd_mom_5"] = usd_ret.rolling(5).sum()
    df["usd_mom_20"] = usd_ret.rolling(20).sum()
    df["usd_breadth_20"] = usd_breadth.rolling(20).mean()
    df["pair_usd_corr_50"] = pr.rolling(50).corr(usd_ret)
    beta = (pr.rolling(50).cov(usd_ret)) / (usd_ret.rolling(50).var() + 1e-12)
    df["pair_idio_mom_20"] = (pr - beta * usd_ret).rolling(20).sum()
    return df


def build_pools():
    usd_ret, usd_breadth, R = build_usd_index()
    base_fr, aug_fr = [], []
    for s in POOL_PAIRS:
        ext = build_extended(s).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        ext["symbol"] = s
        base_fr.append(ext.copy())
        ca = cross_asset_for_pair(s, usd_ret, usd_breadth, R).reindex(ext.index)
        aug = ext.join(ca.astype("float32"))
        aug_fr.append(aug)
    return pd.concat(base_fr).sort_index(), pd.concat(aug_fr).sort_index()


def walkforward(pool, feat):
    folds = []
    for ts in FOLD_STARTS:
        test_start, test_end = ts, ts + pd.DateOffset(months=3)
        val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < val_start]; va = pool[(pool.index >= val_start) & (pool.index < test_start)]
        te = pool[(pool.index >= test_start) & (pool.index < test_end)]
        if len(tr) < 20000 or len(va) < 2000 or len(te) < 500:
            continue
        model = train_lgbm(tr[feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                           va[feat].values.astype(np.float32), binary_label_for_long(va["label"]).values,
                           100, None, SEED)
        q97 = float(np.quantile(predict(model, "lgbm", va[feat].values.astype(np.float32)), 0.97))
        tec = te[te["symbol"].isin(CORE)]
        pt = predict(model, "lgbm", tec[feat].values.astype(np.float32))
        folds.append(wr_pf_overlapping(tec["label"].values[pt >= q97].astype(int)))
    pfs = [f["pf"] for f in folds if np.isfinite(f["pf"]) and f["n"] >= 10]
    wrs = [f["wr"] for f in folds if f["n"] >= 10]
    return dict(n_folds=len(pfs), pf_gt1=sum(1 for x in pfs if x > 1.0),
                pf_mean=round(float(np.mean(pfs)), 3), pf_min=round(float(np.min(pfs)), 3),
                pf_std=round(float(np.std(pfs)), 3), wr_mean=round(float(np.mean(wrs)), 4))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"crossasset_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    print("Building pools (base 73 vs +cross-asset)...")
    base_pool, aug_pool = build_pools()
    base_feat = [c for c in base_pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
    aug_feat = base_feat + NEW_FEATS
    print(f"base feat={len(base_feat)}  aug feat={len(aug_feat)} (+{NEW_FEATS})\n")

    base = walkforward(base_pool, base_feat)
    aug = walkforward(aug_pool, aug_feat)
    lift = round(aug["pf_mean"] - base["pf_mean"], 3)

    print("=== CROSS-ASSET FEATURE TEST (Tier-1 core, walk-forward) ===")
    print(f"  baseline(73)   PF mean {base['pf_mean']:.3f}  PF>1 {base['pf_gt1']}/{base['n_folds']}  min {base['pf_min']:.2f}  std {base['pf_std']:.3f}  WR {base['wr_mean']:.3f}")
    print(f"  +cross-asset   PF mean {aug['pf_mean']:.3f}  PF>1 {aug['pf_gt1']}/{aug['n_folds']}  min {aug['pf_min']:.2f}  std {aug['pf_std']:.3f}  WR {aug['wr_mean']:.3f}")
    print(f"  PF lift = {lift:+.3f}  (locked rule: keep iff >= +0.05)")
    verdict = "KEEP" if lift >= 0.05 else "REJECT"
    print(f"  VERDICT: {verdict}")

    payload = dict(baseline=base, cross_asset=aug, pf_lift=lift, verdict=verdict, new_features=NEW_FEATS)
    (out_dir / "crossasset.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
