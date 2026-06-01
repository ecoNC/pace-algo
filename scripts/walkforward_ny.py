"""
Hardening lever test: NY-session filter + pair-tiering under walk-forward.

From walkforward_stress.py we know: edge persists for GBPUSD/USDJPY/USDCAD,
and is far stronger in the NY session (PF 1.61 vs 1.14). This quantifies the
WR/PF lift of (a) NY filter, (b) Tier-1 pair restriction, under the SAME
10-fold walk-forward — and reports a single HARDENED TARGET SYSTEM.

No new architecture. Same LGBM-100, same folds, just signal gating.

Output: results/model_validation/wf_ny_<UTC>/wf_ny.json
Run: python scripts/walkforward_ny.py
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
PAIRS = list(FX_SUPPORTED_PAIRS) + list(FX_CONDITIONAL_PAIRS)
TIER1 = ["GBPUSD", "USDJPY", "USDCAD"]          # >=80% fold persistence
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")


def build_full_pool():
    fr = []
    for s in PAIRS:
        d = build_extended(s).copy(); d["symbol"] = s
        fr.append(d.astype({c: "float32" for c in d.select_dtypes("float64").columns}))
    pool = pd.concat(fr).sort_index()
    feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
    return pool.dropna(subset=feat + ["label"]), feat


def persistence(folds):
    pfs = [f["pf"] for f in folds if np.isfinite(f["pf"]) and f["n"] >= 10]
    wrs = [f["wr"] for f in folds if f["n"] >= 10]
    ns = [f["n"] for f in folds if f["n"] >= 10]
    if not pfs:
        return None
    gt1 = sum(1 for x in pfs if x > 1.0)
    return dict(n_folds=len(pfs), pf_gt1=gt1, pf_gt1_pct=round(gt1/len(pfs), 2),
                pf_mean=round(float(np.mean(pfs)), 2), pf_min=round(float(np.min(pfs)), 2),
                pf_std=round(float(np.std(pfs)), 2), wr_mean=round(float(np.mean(wrs)), 3),
                avg_signals_per_fold=round(float(np.mean(ns)), 1))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"wf_ny_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, feat = build_full_pool()
    print(f"Pairs={PAIRS}  Tier1={TIER1}  pool={len(pool):,}\n")

    # per (pair, variant) fold lists; variants: all-session vs NY-only
    pp = {p: {"all": [], "ny": []} for p in PAIRS}
    # hardened target system folds (Tier1 + NY, pooled per fold)
    sys_t1ny, sys_t1all, sys_allny = [], [], []

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
        pt = predict(model, "lgbm", te[feat].values.astype(np.float32))
        sym = te["symbol"].values; lab = te["label"].values.astype(int)
        ny = te["in_ny"].values == 1 if "in_ny" in te.columns else np.ones(len(te), bool)
        sig = pt >= q97

        for p in PAIRS:
            mp = sym == p
            pp[p]["all"].append(wr_pf_overlapping(lab[mp & sig]))
            pp[p]["ny"].append(wr_pf_overlapping(lab[mp & sig & ny]))
        t1 = np.isin(sym, TIER1)
        sys_t1ny.append(wr_pf_overlapping(lab[t1 & sig & ny]))
        sys_t1all.append(wr_pf_overlapping(lab[t1 & sig]))
        sys_allny.append(wr_pf_overlapping(lab[sig & ny]))

    print("=== PER PAIR: all-session vs NY-only (q97, walk-forward persistence) ===")
    per_pair_out = {}
    for p in PAIRS:
        a, n = persistence(pp[p]["all"]), persistence(pp[p]["ny"])
        per_pair_out[p] = dict(all_session=a, ny_only=n)
        if a and n:
            print(f"  {p:7s} ALL: PF{a['pf_mean']:.2f} {a['pf_gt1']}/{a['n_folds']} WR{a['wr_mean']:.2f}"
                  f"   | NY: PF{n['pf_mean']:.2f} {n['pf_gt1']}/{n['n_folds']} WR{n['wr_mean']:.2f} (sig/fold {n['avg_signals_per_fold']:.0f})")

    print("\n=== HARDENED TARGET SYSTEMS (pooled per fold) ===")
    systems = {"Tier1+NY": persistence(sys_t1ny), "Tier1_all": persistence(sys_t1all), "All6+NY": persistence(sys_allny)}
    for name, d in systems.items():
        if d:
            print(f"  {name:10s} PF mean {d['pf_mean']:.2f}  PF>1 {d['pf_gt1']}/{d['n_folds']} ({d['pf_gt1_pct']:.0%})  "
                  f"min {d['pf_min']:.2f}  std {d['pf_std']:.2f}  WR {d['wr_mean']:.2f}  sig/fold {d['avg_signals_per_fold']:.0f}")

    payload = dict(pairs=PAIRS, tier1=TIER1, per_pair=per_pair_out, systems=systems)
    (out_dir / "wf_ny.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
