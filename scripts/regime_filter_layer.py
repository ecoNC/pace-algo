"""
Regime Filter Layer — data-driven selection test under walk-forward.

New priority (Nico): PF/WR is a SELECTION problem, not a model problem.
This tests which structurally-motivated regime gates (applied BEFORE the
model cutoff) improve PERSISTENT WR/PF on the Tier-1 core — judged by
CONSISTENCY across folds, not peak, to avoid curve-fitting.

Core: GBPUSD/USDJPY/USDCAD (walk-forward Tier-1), LGBM-100, q97, 10 folds.
Gates tested (single + combined), all structurally motivated:
  NY        : in_ny == 1                 (institutional liquidity window)
  vol_mid   : 0.30 <= atr_pctile <= 0.90 (exclude dead + extreme vol)
  trend     : adx_14 >= 20               (trending, not chop)
  htf_align : htf_1h_ema_alignment != 0  (HTF trend present)

Output: results/model_validation/regime_<UTC>/regime.json
Run: python scripts/regime_filter_layer.py
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

from model_validation_suite import build_extended, train_lgbm, predict, wr_pf_overlapping
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEED = 7
CORE = ["GBPUSD", "USDJPY", "USDCAD"]                       # Tier-1 core
POOL_PAIRS = ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF", "AUDUSD"]  # train pool (production recipe minus EUR)
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")


def gates(te):
    """Return dict of named boolean masks (regime gates) over the test frame."""
    n = len(te)
    g = {"baseline": np.ones(n, bool)}
    if "in_ny" in te.columns:
        g["NY"] = te["in_ny"].values == 1
    if "atr_percentile_100" in te.columns:
        a = te["atr_percentile_100"].values
        g["vol_mid"] = (a >= 0.30) & (a <= 0.90)
    if "adx_14" in te.columns:
        g["trend"] = te["adx_14"].values >= 20.0
    if "htf_1h_ema_alignment" in te.columns:
        g["htf_align"] = te["htf_1h_ema_alignment"].values != 0
    # combinations
    if "NY" in g and "trend" in g:
        g["NY+trend"] = g["NY"] & g["trend"]
    if "NY" in g and "vol_mid" in g:
        g["NY+vol_mid"] = g["NY"] & g["vol_mid"]
    if "trend" in g and "vol_mid" in g:
        g["trend+vol_mid"] = g["trend"] & g["vol_mid"]
    return g


def persistence(folds):
    pfs = [f["pf"] for f in folds if np.isfinite(f["pf"]) and f["n"] >= 10]
    wrs = [f["wr"] for f in folds if f["n"] >= 10]
    ns = [f["n"] for f in folds if f["n"] >= 10]
    if len(pfs) < 5:
        return None
    gt1 = sum(1 for x in pfs if x > 1.0)
    return dict(n_folds=len(pfs), pf_gt1=gt1, pf_gt1_pct=round(gt1/len(pfs), 2),
                pf_mean=round(float(np.mean(pfs)), 2), pf_min=round(float(np.min(pfs)), 2),
                pf_std=round(float(np.std(pfs)), 2), wr_mean=round(float(np.mean(wrs)), 3),
                avg_sig_fold=round(float(np.mean(ns)), 0))


def build_pool():
    fr = []
    for s in POOL_PAIRS:
        d = build_extended(s).copy(); d["symbol"] = s
        fr.append(d.astype({c: "float32" for c in d.select_dtypes("float64").columns}))
    pool = pd.concat(fr).sort_index()
    feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
    return pool.dropna(subset=feat + ["label"]), feat


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"regime_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, feat = build_pool()
    print(f"Core(eval)={CORE}  train_pool={POOL_PAIRS}  pool={len(pool):,}\n")

    cfg_folds = {}  # config -> list of per-fold {pf,wr,n}
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
        # restrict eval to CORE pairs
        te_core = te[te["symbol"].isin(CORE)]
        pt = predict(model, "lgbm", te_core[feat].values.astype(np.float32))
        lab = te_core["label"].values.astype(int)
        sig = pt >= q97
        g = gates(te_core)
        for name, mask in g.items():
            cfg_folds.setdefault(name, []).append(wr_pf_overlapping(lab[sig & mask]))

    print("=== REGIME GATE COMPARISON (Tier-1 core, q97, walk-forward) ===")
    print(f"{'config':14s} {'PF>1/folds':>11s} {'PFmean':>7s} {'PFmin':>6s} {'PFstd':>6s} {'WR':>5s} {'sig/fold':>9s}")
    out = {}
    for name in cfg_folds:
        d = persistence(cfg_folds[name]); out[name] = d
        if d:
            print(f"{name:14s} {str(d['pf_gt1'])+'/'+str(d['n_folds']):>11s} {d['pf_mean']:>7.2f} "
                  f"{d['pf_min']:>6.2f} {d['pf_std']:>6.2f} {d['wr_mean']:>5.2f} {d['avg_sig_fold']:>9.0f}")

    (out_dir / "regime.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
