"""
TP/SL-Ratio sweep under walk-forward — does the trade DEFINITION lift WR/PF?

Selection at the trade-structure level: re-label triple-barrier at tp_R in
{1.5, 2.0, 2.5, 3.0} (sl_atr_mult=1.0, time_barrier=24), retrain LGBM-100 per
R, evaluate persistent WR/PF on the Tier-1 core under the same 10-fold
walk-forward. Higher R -> lower WR but higher reward-per-win; net PF unknown.

Labels are cached to disk (data/processed_v2/labels_sweep/) so re-runs are fast
and survive timeouts. Features are R-independent (reused from extended cache).

Output: results/model_validation/tpsl_<UTC>/tpsl.json
Run: python scripts/tpsl_sweep.py
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

from model_validation_suite import build_extended, train_lgbm, predict, DATA_V2
from core.labeling import compute_triple_barrier_labels
from core.train.dataset import NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
LBL_DIR = DATA_V2 / "labels_sweep"; LBL_DIR.mkdir(parents=True, exist_ok=True)
SEED = 7
TF = "5m"
R_VALUES = [1.5, 2.0, 2.5, 3.0]
POOL_PAIRS = ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF", "AUDUSD"]
CORE = ["GBPUSD", "USDJPY", "USDCAD"]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")


def labels_for(sym, R):
    """Triple-barrier labels at tp_R=R, disk-cached."""
    out = LBL_DIR / f"{sym}_{TF}_R{R}.parquet"
    if out.exists():
        return pd.read_parquet(out)
    raw = pd.read_parquet(DATA_V2 / f"{sym}_{TF}.parquet")
    lab = compute_triple_barrier_labels(raw, tp_R=R, sl_atr_mult=1.0, time_barrier_bars=24)
    lab[["label"]].to_parquet(out)
    return lab[["label"]]


def pool_for_R(R, feat_cache):
    """Build pool with features (R-independent) + R-specific labels."""
    fr = []
    for s in POOL_PAIRS:
        ext = feat_cache[s]
        feats = ext.drop(columns=[c for c in ("label", "hit_bar_offset") if c in ext.columns])
        lab = labels_for(s, R)
        d = feats.join(lab, how="inner")
        d["symbol"] = s
        fr.append(d)
    pool = pd.concat(fr).sort_index()
    feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
    return pool.dropna(subset=feat + ["label"]), feat


def wr_pf(labels, win_r):
    w = int((labels == 1).sum()); l = int((labels == -1).sum())
    pf = (w * win_r) / l if l > 0 else (float("inf") if w > 0 else 0.0)
    wr = w / (w + l) if (w + l) > 0 else 0.0
    return dict(n=w + l, wr=round(wr, 4), pf=round(pf, 3))


def persistence(folds):
    pfs = [f["pf"] for f in folds if np.isfinite(f["pf"]) and f["n"] >= 10]
    wrs = [f["wr"] for f in folds if f["n"] >= 10]
    ns = [f["n"] for f in folds if f["n"] >= 10]
    if len(pfs) < 5:
        return None
    gt1 = sum(1 for x in pfs if x > 1.0)
    return dict(n_folds=len(pfs), pf_gt1=gt1, pf_mean=round(float(np.mean(pfs)), 2),
                pf_min=round(float(np.min(pfs)), 2), pf_std=round(float(np.std(pfs)), 2),
                wr_mean=round(float(np.mean(wrs)), 3), avg_sig_fold=round(float(np.mean(ns)), 0),
                exp_R=round(float(np.mean([(f["wr"]) for f in folds if f["n"] >= 10])), 3))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"tpsl_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading features (cached)...")
    feat_cache = {s: build_extended(s) for s in POOL_PAIRS}

    results = {}
    for R in R_VALUES:
        print(f"\n=== tp_R = {R} (labeling+training) ===")
        pool, feat = pool_for_R(R, feat_cache)
        folds = []
        for ts in FOLD_STARTS:
            test_start, test_end = ts, ts + pd.DateOffset(months=3)
            val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < val_start]; va = pool[(pool.index >= val_start) & (pool.index < test_start)]
            te = pool[(pool.index >= test_start) & (pool.index < test_end)]
            if len(tr) < 20000 or len(va) < 2000 or len(te) < 500:
                continue
            ytr = (tr["label"].values == 1).astype(int); yva = (va["label"].values == 1).astype(int)
            model = train_lgbm(tr[feat].values.astype(np.float32), ytr,
                               va[feat].values.astype(np.float32), yva, 100, None, SEED)
            q97 = float(np.quantile(predict(model, "lgbm", va[feat].values.astype(np.float32)), 0.97))
            tec = te[te["symbol"].isin(CORE)]
            pt = predict(model, "lgbm", tec[feat].values.astype(np.float32))
            lab = tec["label"].values[pt >= q97].astype(int)
            folds.append(wr_pf(lab, win_r=R))
        d = persistence(folds); results[f"R{R}"] = d
        if d:
            print(f"  R{R}: PF mean {d['pf_mean']:.2f}  PF>1 {d['pf_gt1']}/{d['n_folds']}  min {d['pf_min']:.2f}  "
                  f"std {d['pf_std']:.2f}  WR {d['wr_mean']:.2f}  sig/fold {d['avg_sig_fold']:.0f}")

    print("\n=== TP/SL SWEEP SUMMARY (Tier-1 core, walk-forward) ===")
    print(f"{'R':5s} {'PFmean':>7s} {'PF>1':>6s} {'PFmin':>6s} {'PFstd':>6s} {'WR':>5s} {'sig/fold':>9s}")
    for R in R_VALUES:
        d = results.get(f"R{R}")
        if d:
            print(f"{R:<5} {d['pf_mean']:>7.2f} {str(d['pf_gt1'])+'/'+str(d['n_folds']):>6s} {d['pf_min']:>6.2f} "
                  f"{d['pf_std']:>6.2f} {d['wr_mean']:>5.2f} {d['avg_sig_fold']:>9.0f}")

    (out_dir / "tpsl.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
