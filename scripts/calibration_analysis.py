"""
Calibration deep-dive — LGBM-100 (production recipe).

Makes the probability VALUE interpretable as a real probability (for tier
definition + later risk/sizing). Calibrators fit on VAL, evaluated on TEST.

  - raw vs Platt (sigmoid) vs Isotonic regression: ECE + reliability table
  - per supported pair: raw vs isotonic ECE
  - confirms: monotone calibration preserves quantile tier membership
    (WR/PF per tier unchanged; only the probability number changes)

Model: LGBM-100 seed 7, trained on FX_PRODUCTION_TRAIN_PAIRS (ANN-020 recipe).

Output: results/model_validation/calibration_<UTC>/calibration.json
Run: python scripts/calibration_analysis.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

from model_validation_suite import build_extended, train_lgbm, predict, ece_reliability, TRAIN_END, VAL_END
from core.config import FX_PRODUCTION_TRAIN_PAIRS, FX_SUPPORTED_PAIRS
from core.train.dataset import walk_forward_split, binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEED = 7
import pandas as pd


def build_pool(symbols):
    fr = []
    for s in symbols:
        d = build_extended(s).copy(); d["symbol"] = s
        fr.append(d.astype({c: "float32" for c in d.select_dtypes("float64").columns}))
    return pd.concat(fr).sort_index()


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"calibration_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)

    pool = build_pool(FX_PRODUCTION_TRAIN_PAIRS)
    feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
    pc = pool.dropna(subset=feat + ["label"])
    tr, va, te = walk_forward_split(pc, TRAIN_END, VAL_END)
    Xtr, ytr = tr[feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values
    Xva, yva = va[feat].values.astype(np.float32), binary_label_for_long(va["label"]).values
    Xte, yte = te[feat].values.astype(np.float32), binary_label_for_long(te["label"]).values
    print(f"Train pool={FX_PRODUCTION_TRAIN_PAIRS}  train={len(tr):,} val={len(va):,} test={len(te):,}")

    model = train_lgbm(Xtr, ytr, Xva, yva, 100, None, SEED)
    pv, pt = predict(model, "lgbm", Xva), predict(model, "lgbm", Xte)

    # Fit calibrators on VAL
    platt = LogisticRegression(C=1e6, solver="lbfgs").fit(pv.reshape(-1, 1), yva)
    iso = IsotonicRegression(out_of_bounds="clip").fit(pv, yva)
    pt_platt = platt.predict_proba(pt.reshape(-1, 1))[:, 1]
    pt_iso = iso.predict(pt)

    ece_raw, rel_raw = ece_reliability(pt, yte)
    ece_platt, _ = ece_reliability(pt_platt, yte)
    ece_iso, rel_iso = ece_reliability(pt_iso, yte)
    print(f"\n=== ECE on TEST (lower=better) ===")
    print(f"  raw      ECE={ece_raw:.4f}")
    print(f"  Platt    ECE={ece_platt:.4f}")
    print(f"  Isotonic ECE={ece_iso:.4f}")

    print("\n=== Reliability (raw): bin mean_pred vs actual ===")
    for r in rel_raw:
        print(f"  bin{r['bin']} n={r['n']:6d} pred={r['mean_pred']:.3f} actual={r['frac_pos']:.3f}")

    # Monotonicity check: does isotonic preserve top-q97 membership?
    q97_raw = pt >= np.quantile(pv, 0.97)
    q97_iso = pt_iso >= np.quantile(iso.predict(pv), 0.97)
    overlap = float((q97_raw & q97_iso).sum() / max(1, q97_raw.sum()))
    print(f"\n=== Monotonicity: top-q97 membership overlap raw vs isotonic = {overlap:.3f} ===")

    # Per supported pair: raw vs isotonic ECE
    print("\n=== Per supported pair ECE (raw -> isotonic) ===")
    per_pair = {}
    for p in FX_SUPPORTED_PAIRS:
        h = build_extended(p).dropna(subset=feat + ["label"])
        h = h[h.index >= VAL_END]
        ph = predict(model, "lgbm", h[feat].values.astype(np.float32))
        yh = binary_label_for_long(h["label"]).values
        e_raw, _ = ece_reliability(ph, yh)
        e_iso, _ = ece_reliability(iso.predict(ph), yh)
        per_pair[p] = dict(ece_raw=round(e_raw, 4), ece_iso=round(e_iso, 4), n=int(len(h)))
        print(f"  {p:7s} raw={e_raw:.4f} -> iso={e_iso:.4f}")

    payload = dict(seed=SEED, train_pairs=FX_PRODUCTION_TRAIN_PAIRS,
                   ece=dict(raw=round(ece_raw, 4), platt=round(ece_platt, 4), isotonic=round(ece_iso, 4)),
                   reliability_raw=rel_raw, reliability_isotonic=rel_iso,
                   q97_membership_overlap=round(overlap, 4), per_pair=per_pair)
    (out_dir / "calibration.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
