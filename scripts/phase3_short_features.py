"""
Phase 3: does the SHORT side get broadly viable with its OWN feature selection?

The locked 9 features were chosen by gain-importance on the LONG label. Shorts may
rank on different drivers. Here we (1) derive the SHORT's own top-9 by gain-importance
on the short label, then (2) compare the SHORT ranker under long's-9 vs short's-own-9,
broken down per-pair x per-year at q97, net@0.5pip. Walk-forward.

Decision: adopt short-specific features only if they lift the weak pairs (GBPUSD,
USDCAD) and the 2026 decay without hurting the strong ones.

Output: results/model_validation/phase3_short_feat_<UTC>/short_feat.json
Run:    python scripts/phase3_short_features.py
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

from phase3_density import build_pool, FEATURES_9 as LONG9, netR, stats, SEEDS, VAL_WEEKS, FOLD_STARTS
from model_validation_suite import train_lgbm, predict
from core.train.dataset import NON_FEATURE_COLS

SPREAD, Q = 0.5, 0.97


def feature_cols(pool):
    return [c for c in pool.columns if c not in NON_FEATURE_COLS
            and c != "symbol" and c != "label" and not c.startswith("_")]


def breakdown(rows, key_idx):
    out = {}
    for k in sorted(set(r[key_idx] for r in rows)):
        rs = np.array([r[2] for r in rows if r[key_idx] == k])
        st = stats(rs)
        out[str(k)] = st if st else {"n": int(len(rs)), "wr": None, "pf": None}
    return out


def eval_short(pool, feats, X):
    """Walk-forward SHORT ranker @q97; return realized net-R rows tagged (sym, year)."""
    rows = []
    for sd in SEEDS:
        for ts in FOLD_STARTS:
            te_s, te_e = ts, ts + pd.DateOffset(months=3); vs = ts - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            gate_v = va["_in_ny"].values & va["_tradeable"].values
            gate_t = te["_in_ny"].values & te["_tradeable"].values
            if gate_v.sum() < 100 or gate_t.sum() < 100: continue
            m = train_lgbm(X(tr, feats), tr["_lab_short"].values, X(va, feats), va["_lab_short"].values, 100, None, sd)
            pv, pt = predict(m, "lgbm", X(va, feats)), predict(m, "lgbm", X(te, feats))
            cut = float(np.quantile(pv[gate_v], Q))
            sig = (pt >= cut) & gate_t
            r = netR(te["_grossR_short"].values, te["_cost"].values, SPREAD)
            sym = te["symbol"].values; yr = te.index.year.values
            for i in np.where(sig & np.isfinite(r))[0]:
                rows.append((sym[i], int(yr[i]), float(r[i])))
    return rows


def summarize(rows):
    return {"overall": stats(np.array([r[2] for r in rows])),
            "by_pair": breakdown(rows, 0), "by_year": breakdown(rows, 1)}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase3_short_feat_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    feats_full = feature_cols(pool)
    pool = pool.dropna(subset=feats_full)
    X = lambda d, f: d[f].values.astype(np.float32)
    print(f"pool={len(pool):,}  full_features={len(feats_full)}")

    # SHORT's own top-9 via gain importance on pre-first-fold window
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS)
    tr0 = pool[pool.index < cut0]
    m0 = train_lgbm(X(tr0, feats_full), tr0["_lab_short"].values,
                    X(tr0, feats_full), tr0["_lab_short"].values, 100, None, 42)
    imp = pd.Series(m0.feature_importance(importance_type="gain"), index=feats_full).sort_values(ascending=False)
    SHORT9 = list(imp.index[:9])
    print(f"SHORT top-9 (own):  {SHORT9}")
    print(f"LONG  9 (baseline): {LONG9}")
    print(f"overlap: {sorted(set(SHORT9) & set(LONG9))}")

    res = {"short9_features": SHORT9, "long9_features": LONG9,
           "short_with_long9": summarize(eval_short(pool, LONG9, X)),
           "short_with_short9": summarize(eval_short(pool, SHORT9, X))}
    (OUT / "short_feat.json").write_text(json.dumps(dict(spread=SPREAD, cutoff_q=Q, results=res),
                                                    indent=2, default=str), encoding="utf-8")

    for tag, key in [("SHORT w/ LONG-9 (baseline)", "short_with_long9"),
                     ("SHORT w/ SHORT-9 (own)", "short_with_short9")]:
        b = res[key]; o = b["overall"]
        print(f"\n=== {tag} ===")
        print(f"  overall: PF {o['pf']}  WR {o['wr']}  n {o['n']}")
        print(f"  by pair  ", "  ".join(f"{k}:PF{v['pf']}/WR{v['wr']}/n{v['n']}" for k, v in b["by_pair"].items()))
        print(f"  by year  ", "  ".join(f"{k}:PF{v['pf']}/WR{v['wr']}/n{v['n']}" for k, v in b["by_year"].items()))
    print(f"\nAdopt SHORT-9 only if it lifts GBPUSD/USDCAD shorts + 2026 without hurting USDCHF/USDJPY.")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
