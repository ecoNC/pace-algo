"""
Supported-Pairs lock — which FX pairs have a reliable LGBM-100 edge?

Two protocols, LGBM-100 (seed 7), same features/splits/labels:
  IN-POOL (time-OOS)  : train on ALL 7 pairs (production recipe), eval each pair
                        on its own TEST period (>= VAL_END). Production-relevant.
  LOPO (true OOS)     : per pair, train on the other 6, eval the held-out pair.
                        Cross-pair generalization signal.

Classification per pair (on IN-POOL, the production-relevant view):
  supported   : monotone tier separation AND PF@q97 >= 1.30 AND PF@q99 >= 1.50
  conditional : edge only at q99 (PF@q99 >= 1.50) OR PF@q97 in [1.10, 1.30)
  unsupported : otherwise
LOPO is reported alongside as a robustness flag (does it also generalize cold?).

Output: results/model_validation/supported_<UTC>/supported_pairs.json
Run: python scripts/supported_pairs.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import numpy as np

from audusd_investigation import fit_model, holdout_df, per_tier, TIERS
from model_validation_suite import FX_TRAIN_SYMBOLS, FX_HOLDOUT_SYMBOLS

OUT_BASE = REPO / "results" / "model_validation"
ALL_PAIRS = list(FX_TRAIN_SYMBOLS) + list(FX_HOLDOUT_SYMBOLS)  # 7 FX majors


def classify(t):
    pf97, pf99 = t["q97"]["pf"], t["q99"]["pf"]
    monotone = t["q97"]["pf"] >= t["q90"]["pf"] - 0.05 and t["q99"]["pf"] >= t["q97"]["pf"] - 0.10
    if monotone and pf97 >= 1.30 and pf99 >= 1.50:
        return "supported"
    if pf99 >= 1.50 or (1.10 <= pf97 < 1.30):
        return "conditional"
    return "unsupported"


def fmt(t):
    return "  ".join(f"{k}:PF{t[k]['pf']:.2f}/WR{t[k]['wr']:.2f}/n{t[k]['signals']}" for k in TIERS)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"supported_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)

    print(f"All FX pairs: {ALL_PAIRS}\n")

    # ── Protocol 1: IN-POOL (train on all 7, eval each on own test period) ──
    print("=== IN-POOL (production recipe: train on all 7, time-OOS per pair) ===")
    model_all, feat, cuts, _ = fit_model(ALL_PAIRS)
    print(f"cuts={ {k: round(v,4) for k,v in cuts.items()} }\n")
    inpool = {}
    for p in ALL_PAIRS:
        t, _, _ = per_tier(model_all, holdout_df(p, feat), feat, cuts)
        inpool[p] = t
        print(f"  {p:7s} {fmt(t)}")

    # ── Protocol 2: LOPO (train on other 6, eval held-out) ──
    print("\n=== LOPO (true OOS: train on other 6, eval held-out pair) ===")
    lopo = {}
    for p in ALL_PAIRS:
        others = [q for q in ALL_PAIRS if q != p]
        m, f2, c2, _ = fit_model(others)
        t, _, _ = per_tier(m, holdout_df(p, f2), f2, c2)
        lopo[p] = t
        print(f"  {p:7s} {fmt(t)}")

    # ── Classification ──
    print("\n=== SUPPORTED-PAIRS CLASSIFICATION (based on IN-POOL) ===")
    rows = {}
    for p in ALL_PAIRS:
        cls = classify(inpool[p])
        lopo_pos = inpool[p]["q97"]["pf"] >= 1.0 and lopo[p]["q97"]["pf"] >= 1.0
        rows[p] = dict(classification=cls,
                       inpool_q97_pf=inpool[p]["q97"]["pf"], inpool_q99_pf=inpool[p]["q99"]["pf"],
                       lopo_q97_pf=lopo[p]["q97"]["pf"], lopo_q99_pf=lopo[p]["q99"]["pf"],
                       generalizes_oos=bool(lopo[p]["q97"]["pf"] >= 1.0))
        flag = "[generalizes OOS]" if lopo[p]["q97"]["pf"] >= 1.0 else "[in-pool only / concept-shift]"
        print(f"  {p:7s} -> {cls.upper():12s} (in-pool q97 PF {inpool[p]['q97']['pf']:.2f}, q99 {inpool[p]['q99']['pf']:.2f})  {flag}")

    supported = [p for p in ALL_PAIRS if rows[p]["classification"] == "supported"]
    conditional = [p for p in ALL_PAIRS if rows[p]["classification"] == "conditional"]
    unsupported = [p for p in ALL_PAIRS if rows[p]["classification"] == "unsupported"]
    print(f"\n  SUPPORTED   : {supported}")
    print(f"  CONDITIONAL : {conditional}")
    print(f"  UNSUPPORTED : {unsupported}")

    payload = dict(cuts=cuts, inpool=inpool, lopo=lopo, classification=rows,
                   summary=dict(supported=supported, conditional=conditional, unsupported=unsupported))
    (out_dir / "supported_pairs.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
