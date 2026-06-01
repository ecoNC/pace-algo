"""
Walk-Forward + Regime Stress — temporal robustness hardening.

The blind spot so far: a SINGLE time split. This tests whether the edge
PERSISTS over time, not just on one window.

Protocol (LGBM-100, supported+conditional pairs, EURUSD excluded):
  - Expanding-window walk-forward: ~quarterly OOS test folds.
    For each fold: TRAIN = data before val window; VAL = 26 weeks before test
    (for q97/q99 cutoffs); TEST = the quarter. Retrain per fold.
  - Per supported pair x fold: q97/q99 PF / WR / n.
  - Persistence score per pair: % folds PF>1, min PF, PF std (consistency > peak).
  - Regime stress (pooled OOS): PF/WR by ATR-percentile tercile (low/mid/high
    volatility) and by NY vs non-NY session.

This is a HARDENING measurement, not a new system. No ADRs, no architecture.

Output: results/model_validation/walkforward_<UTC>/walkforward.json
Run: python scripts/walkforward_stress.py
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
from core.config import FX_SUPPORTED_PAIRS, FX_CONDITIONAL_PAIRS
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEED = 7
PAIRS = list(FX_SUPPORTED_PAIRS) + list(FX_CONDITIONAL_PAIRS)  # production pairs, EURUSD excluded
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")  # quarterly OOS starts


def build_full_pool():
    fr = []
    for s in PAIRS:
        d = build_extended(s).copy(); d["symbol"] = s
        fr.append(d.astype({c: "float32" for c in d.select_dtypes("float64").columns}))
    pool = pd.concat(fr).sort_index()
    feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
    return pool.dropna(subset=feat + ["label"]), feat


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"walkforward_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)

    pool, feat = build_full_pool()
    print(f"Pairs={PAIRS}  pool={len(pool):,}  feat={len(feat)}  folds={len(FOLD_STARTS)}\n")

    # per-pair per-fold results + pooled regime collectors
    per_pair = {p: [] for p in PAIRS}
    reg_atr, reg_lab, reg_proba, reg_ny = [], [], [], []

    for i, ts in enumerate(FOLD_STARTS):
        test_start = ts
        test_end = ts + pd.DateOffset(months=3)
        val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < val_start]
        va = pool[(pool.index >= val_start) & (pool.index < test_start)]
        te = pool[(pool.index >= test_start) & (pool.index < test_end)]
        if len(tr) < 20000 or len(va) < 2000 or len(te) < 500:
            continue
        model = train_lgbm(tr[feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                           va[feat].values.astype(np.float32), binary_label_for_long(va["label"]).values,
                           100, None, SEED)
        pv = predict(model, "lgbm", va[feat].values.astype(np.float32))
        q97, q99 = float(np.quantile(pv, 0.97)), float(np.quantile(pv, 0.99))
        pt = predict(model, "lgbm", te[feat].values.astype(np.float32))

        fold_lab = f"{str(test_start.date())}"
        line = [f"fold {fold_lab}"]
        for p in PAIRS:
            m = te["symbol"].values == p
            if m.sum() < 100:
                continue
            pr, lab = pt[m], te["label"].values[m].astype(int)
            r97 = wr_pf_overlapping(lab[pr >= q97]); r99 = wr_pf_overlapping(lab[pr >= q99])
            per_pair[p].append(dict(fold=fold_lab, q97_pf=r97["pf"], q97_wr=r97["wr"], q97_n=r97["n"],
                                    q99_pf=r99["pf"], q99_wr=r99["wr"], q99_n=r99["n"]))
            line.append(f"{p}:q97 PF{r97['pf']:.2f}/n{r97['n']}")
        # regime collectors (q97 signal bars only, pooled)
        sig = pt >= q97
        if "atr_percentile_100" in te.columns:
            reg_atr.append(te["atr_percentile_100"].values[sig])
        reg_proba.append(pt[sig]); reg_lab.append(te["label"].values[sig].astype(int))
        if "in_ny" in te.columns:
            reg_ny.append(te["in_ny"].values[sig])
        print("  " + "  ".join(line))

    # ── Persistence per pair ──
    print("\n=== PERSISTENCE per pair (q97 across folds) ===")
    persistence = {}
    for p in PAIRS:
        rows = per_pair[p]
        pfs = [r["q97_pf"] for r in rows if np.isfinite(r["q97_pf"])]
        wrs = [r["q97_wr"] for r in rows]
        if not pfs:
            continue
        gt1 = sum(1 for x in pfs if x > 1.0)
        persistence[p] = dict(n_folds=len(pfs), folds_pf_gt1=gt1, pf_gt1_pct=round(gt1/len(pfs), 2),
                              pf_mean=round(float(np.mean(pfs)), 2), pf_min=round(float(np.min(pfs)), 2),
                              pf_std=round(float(np.std(pfs)), 2), wr_mean=round(float(np.mean(wrs)), 3))
        d = persistence[p]
        print(f"  {p:7s} folds={d['n_folds']:2d}  PF>1 in {d['folds_pf_gt1']}/{d['n_folds']} ({d['pf_gt1_pct']:.0%})  "
              f"PF mean={d['pf_mean']:.2f} min={d['pf_min']:.2f} std={d['pf_std']:.2f}  WR={d['wr_mean']:.2f}")

    # ── Regime stress (pooled q97 signals) ──
    print("\n=== REGIME STRESS (pooled q97 signals) ===")
    regime = {}
    if reg_atr:
        atr = np.concatenate(reg_atr); lab = np.concatenate(reg_lab)
        lo, hi = np.quantile(atr, [0.333, 0.667])
        for name, mask in [("low_vol", atr <= lo), ("mid_vol", (atr > lo) & (atr <= hi)), ("high_vol", atr > hi)]:
            r = wr_pf_overlapping(lab[mask]); regime[name] = r
            print(f"  {name:9s} PF{r['pf']:.2f}/WR{r['wr']:.2f}/n{r['n']}")
    if reg_ny:
        ny = np.concatenate(reg_ny); lab = np.concatenate(reg_lab)
        for name, mask in [("NY_session", ny == 1), ("non_NY", ny == 0)]:
            r = wr_pf_overlapping(lab[mask]); regime[name] = r
            print(f"  {name:9s} PF{r['pf']:.2f}/WR{r['wr']:.2f}/n{r['n']}")

    payload = dict(pairs=PAIRS, fold_starts=[str(d.date()) for d in FOLD_STARTS],
                   per_pair_folds=per_pair, persistence=persistence, regime_stress=regime)
    (out_dir / "walkforward.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
