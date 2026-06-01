"""
Phase 3 gating check: is the SHORT edge broad-based or concentrated?

Before locking long+short, break down each direction's realized quality at q97 by
PAIR (5) and by YEAR (2024/25/26). A direction we lock must show edge across most
pairs and years -- not ride one pair. Walk-forward, net@0.5pip (+ gross for context).

Reuses the symmetric machinery in phase3_density.py.
Output: results/model_validation/phase3_short_robust_<UTC>/short_robust.json
Run:    python scripts/phase3_short_robustness.py
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

from phase3_density import build_pool, FEATURES_9, netR, stats, PAIRS, SEEDS, VAL_WEEKS, FOLD_STARTS, Q
from model_validation_suite import train_lgbm, predict

SPREAD = 0.5   # ECN-mid for the breakdown


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase3_short_robust_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    X = lambda d: d[FEATURES_9].values.astype(np.float32)
    print(f"pool={len(pool):,}  spread={SPREAD}pip")

    # collect realized net-R tagged by (dir, symbol, year)
    rec = {"long": [], "short": []}   # list of (symbol, year, netR)
    for sd in SEEDS:
        for ts in FOLD_STARTS:
            te_s, te_e = ts, ts + pd.DateOffset(months=3); vs = ts - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            gate_v = va["_in_ny"].values & va["_tradeable"].values
            gate_t = te["_in_ny"].values & te["_tradeable"].values
            if gate_v.sum() < 100 or gate_t.sum() < 100: continue
            cost = te["_cost"].values; sym = te["symbol"].values; yr = te.index.year.values
            for d, lab, gross in [("long", "_lab_long", "_grossR_long"), ("short", "_lab_short", "_grossR_short")]:
                m = train_lgbm(X(tr), tr[lab].values, X(va), va[lab].values, 100, None, sd)
                pv = predict(m, "lgbm", X(va)); pt = predict(m, "lgbm", X(te))
                cut = float(np.quantile(pv[gate_v], Q))
                sig = (pt >= cut) & gate_t
                r = netR(te[gross].values, cost, SPREAD)
                idx = np.where(sig & np.isfinite(r))[0]
                for i in idx:
                    rec[d].append((sym[i], int(yr[i]), float(r[i])))

    def breakdown(rows, key_idx):
        out = {}
        keys = sorted(set(r[key_idx] for r in rows))
        for k in keys:
            rs = np.array([r[2] for r in rows if r[key_idx] == k])
            st = stats(rs)
            out[str(k)] = st if st else {"n": int(len(rs)), "wr": None, "pf": None}
        return out

    res = {}
    for d in ("long", "short"):
        rows = rec[d]
        allst = stats(np.array([r[2] for r in rows]))
        res[d] = {"overall": allst, "by_pair": breakdown(rows, 0), "by_year": breakdown(rows, 1)}

    (OUT / "short_robust.json").write_text(json.dumps(
        dict(spread=SPREAD, cutoff_q=Q, pairs=PAIRS, results=res), indent=2, default=str), encoding="utf-8")

    for d in ("long", "short"):
        print(f"\n=== {d.upper()} ranker @q97, net@{SPREAD}pip ===")
        o = res[d]["overall"]; print(f"  overall: PF {o['pf']}  WR {o['wr']}  n {o['n']}")
        print(f"  {'by pair':10s}", "  ".join(f"{k}:PF{v['pf']}/WR{v['wr']}/n{v['n']}" for k, v in res[d]["by_pair"].items()))
        print(f"  {'by year':10s}", "  ".join(f"{k}:PF{v['pf']}/WR{v['wr']}/n{v['n']}" for k, v in res[d]["by_year"].items()))
    print(f"\nDecision rule: lock SHORT only if PF>~1.1 on >=4/5 pairs AND all years positive.")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
