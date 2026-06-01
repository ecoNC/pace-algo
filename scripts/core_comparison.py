"""
Final-Core head-to-head: lgbm_noes_100 vs xgb_100.

Synthesizes the validation matrix (results/model_validation/<latest>/audit.json)
into a decision table across Nico's dimensions:
  robustness (per-pair PF/WR at q90/q97/q99), seed stability, cross-pair
  generalization, calibration (ECE + reliability), reproducibility.
Inference/Pine complexity is assessed qualitatively in the printed notes.

Run: python scripts/core_comparison.py
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).parent.parent
BASE = REPO / "results" / "model_validation"

# newest non-audusd matrix dir with audit.json
dirs = sorted([d for d in BASE.iterdir() if d.is_dir() and (d / "audit.json").exists()
               and not d.name.startswith("audusd")], reverse=True)
audit = json.loads((dirs[0] / "audit.json").read_text(encoding="utf-8"))
print(f"Source: {dirs[0].name}\n")

PAIRS = ["GBPUSD", "AUDUSD", "USDCHF", "USDCAD"]
TIERS = ["q90", "q97", "q99"]


def rows_for(variant):
    return [r for r in audit if r["variant"] == variant]


def agg(variant):
    rs = rows_for(variant)
    out = {"seeds": len(rs)}
    # diagnostics mean
    for k in ("num_trees", "effective_trees", "diag_unique_probs", "diag_ece",
              "diag_q90", "diag_q97", "diag_q99"):
        out[k] = float(np.mean([r[k] for r in rs]))
    # seed drift
    out["q99_std"] = float(np.std([r["diag_q99"] for r in rs]))
    out["probamean_std"] = float(np.std([r["diag_proba_mean"] for r in rs]))
    # per-pair per-tier PF/WR mean over seeds
    out["holdout"] = {}
    for p in PAIRS:
        out["holdout"][p] = {}
        for t in TIERS:
            pfs = [r["holdout"][p][t]["pf"] for r in rs if np.isfinite(r["holdout"][p][t]["pf"])]
            wrs = [r["holdout"][p][t]["wr"] for r in rs]
            ns = [r["holdout"][p][t]["n"] for r in rs]
            out["holdout"][p][t] = (float(np.mean(pfs)) if pfs else float("inf"),
                                    float(np.mean(wrs)), float(np.mean(ns)))
    # regime cv
    cvs = [r["regime"]["pf_cv"] for r in rs if r["regime"]["pf_cv"] is not None]
    out["regime_cv"] = float(np.mean(cvs)) if cvs else None
    return out


L = agg("lgbm_noes_100")
X = agg("xgb_100")

print("=== STRUCTURAL / DIAGNOSTICS (mean over seeds) ===")
print(f"{'metric':22s} {'LGBM-100':>12s} {'XGB-100':>12s}")
for k, lab in [("effective_trees", "eff_trees"), ("diag_unique_probs", "uniq_probs"),
               ("diag_q90", "q90"), ("diag_q97", "q97"), ("diag_q99", "q99"),
               ("diag_ece", "ECE")]:
    print(f"{lab:22s} {L[k]:>12.4f} {X[k]:>12.4f}")

print("\n=== SEED STABILITY (std over seeds, lower=better) ===")
print(f"{'q99_std':22s} {L['q99_std']:>12.5f} {X['q99_std']:>12.5f}")
print(f"{'proba_mean_std':22s} {L['probamean_std']:>12.5f} {X['probamean_std']:>12.5f}")
print(f"{'regime_pf_cv':22s} {L['regime_cv']:>12.3f} {X['regime_cv']:>12.3f}")

print("\n=== CROSS-PAIR ROBUSTNESS — PF (mean over seeds) ===")
print(f"{'pair/tier':14s} " + "  ".join(f"{t:>14s}" for t in TIERS))
for model, name in [(L, "LGBM-100"), (X, "XGB-100")]:
    print(f"-- {name} --")
    for p in PAIRS:
        cells = []
        for t in TIERS:
            pf, wr, n = model["holdout"][p][t]
            cells.append(f"PF{pf:4.2f}/WR{wr:.2f}/n{int(n):3d}")
        print(f"  {p:11s} " + "  ".join(cells))

# scoring: count pairs with PF>1 at q97 + q99, avg PF across pairs at q97
def score(model):
    q97_pos = sum(1 for p in PAIRS if model["holdout"][p]["q97"][0] > 1.0)
    q99_pos = sum(1 for p in PAIRS if model["holdout"][p]["q99"][0] > 1.0)
    avg_q97 = np.mean([min(model["holdout"][p]["q97"][0], 10) for p in PAIRS])
    avg_q99 = np.mean([min(model["holdout"][p]["q99"][0], 10) for p in PAIRS])
    return q97_pos, q99_pos, avg_q97, avg_q99

lq = score(L); xq = score(X)
print("\n=== SCORECARD ===")
print(f"{'metric':28s} {'LGBM-100':>12s} {'XGB-100':>12s}")
print(f"{'pairs PF>1 @ q97 (of 4)':28s} {lq[0]:>12d} {xq[0]:>12d}")
print(f"{'pairs PF>1 @ q99 (of 4)':28s} {lq[1]:>12d} {xq[1]:>12d}")
print(f"{'avg PF @ q97 (cap 10)':28s} {lq[2]:>12.2f} {xq[2]:>12.2f}")
print(f"{'avg PF @ q99 (cap 10)':28s} {lq[3]:>12.2f} {xq[3]:>12.2f}")
print(f"{'seed q99_std (lower better)':28s} {L['q99_std']:>12.5f} {X['q99_std']:>12.5f}")
print(f"{'regime_pf_cv (lower better)':28s} {L['regime_cv']:>12.3f} {X['regime_cv']:>12.3f}")
