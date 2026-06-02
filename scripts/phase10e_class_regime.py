"""
Phase 10e: apply the REGIME-ROUTING mechanism (phase8b — it made crypto robust +
all-years-positive) to INDICES and METALS.

Mechanism (causal, no lookahead — state engine trend_regime):
  TREND bars -> trend-follow (long TREND_UP / short TREND_DOWN, R=1.5)
  RANGE bars -> mean-reversion fade (|close-ema20|/atr >= thr)

Class twist vs phase8b: trades only count inside the symbol's HOME session (the
class-owned gate — crypto needed none, session markets do). Raw R, no ML — this is
the MECHANISM test; ML selection comes on top only if the mechanism is positive.

Output: results/model_validation/phase10e_class_regime_<UTC>/class_regime.json
Run:    python scripts/phase10e_class_regime.py
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

from phase8b_crypto_regime import build_legs, by_year
from phase10d_class_tf_sweep import CLASSES, HOME_SESSION

TF = "5m"
COST = 0.03   # ATR fraction (same reference as phase8b for comparability)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase10e_class_regime_{stamp}"
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for cls, syms in CLASSES.items():
        Rtf_all, Rmr_all, Y_all = [], [], []
        used = []
        for s in syms:
            p = REPO / "data" / "processed_v2" / f"{s}_{TF}.parquet"
            if not p.exists(): continue
            raw = pd.read_parquet(p)
            raw = raw[raw.index >= pd.Timestamp("2023-06-01", tz="UTC")]
            if len(raw) < 10000: continue
            Rtf, Rmr, Y = build_legs(raw)
            h0, h1 = HOME_SESSION[s]
            home = (raw.index.hour >= h0) & (raw.index.hour < h1)
            Rtf = np.where(home, Rtf, np.nan); Rmr = np.where(home, Rmr, np.nan)
            Rtf_all.append(Rtf); Rmr_all.append(Rmr); Y_all.append(Y)
            used.append(s)
        if not Rtf_all:
            print(f"[{cls}] no data yet — skipped"); continue
        Rtf = np.concatenate(Rtf_all); Rmr = np.concatenate(Rmr_all); Y = np.concatenate(Y_all)
        Rcomb = np.where(np.isfinite(Rtf), Rtf, Rmr)
        d = {"symbols": used,
             "trend_follow_in_TREND": by_year(Rtf, Y, COST),
             "mean_rev_in_RANGE": by_year(Rmr, Y, COST),
             "COMBINED_routed": by_year(Rcomb, Y, COST)}
        res[cls] = d
        print(f"\n=== {cls} ({used}) ===")
        for leg in ("trend_follow_in_TREND", "mean_rev_in_RANGE", "COMBINED_routed"):
            dd = d[leg]
            line = "  ".join(f"{y}:PF{(dd[y] or {}).get('pf')}/n{(dd[y] or {}).get('n')}" for y in ("2024", "2025", "2026"))
            a = dd["all"] or {}
            print(f"{leg:24s} all:PF{a.get('pf')}/WR{a.get('wr')}/n{a.get('n')}   {line}")
        c = d["COMBINED_routed"]
        allpos = all(c.get(y) and c[y] and c[y]["pf"] > 1.0 for y in ("2024", "2025", "2026"))
        print(f"COMBINED routed positive ALL years (raw, no ML): {allpos}")
    (OUT / "class_regime.json").write_text(json.dumps(dict(cost=COST, tf=TF, results=res),
                                                      indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
