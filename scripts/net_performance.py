"""
NET performance — realistic execution test (the critical untested assumption).

All prior PF/WR were GROSS (close-entry, no spread). 5m FX with ~2-3 trades/day
and 1-ATR risk is spread-sensitive. This re-simulates the walk-forward OOS
signals on raw OHLCV with:
  - entry at NEXT bar open (live-realistic, not signal-bar close)
  - spread cost in pips (0 / 0.5 / 1.0 / 1.5), round-trip, charged in R units
  - SL-first conservative, 24-bar time barrier

Model: LGBM-100 + lean-4 (77 feats), seed 7, q97, supported+conditional pairs.

Output: results/model_validation/netperf_<UTC>/netperf.json
Run: python scripts/net_performance.py
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

from factor_lean import build_pool
from cross_asset_features import VAL_WEEKS, FOLD_STARTS
from model_validation_suite import train_lgbm, predict, DATA_V2
from core.features.engineer import atr as atr_fn
from core.train.dataset import binary_label_for_long

OUT_BASE = REPO / "results" / "model_validation"
SEED = 7
PAIRS = ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF", "AUDUSD"]
TIER1 = ["GBPUSD", "USDJPY", "USDCAD"]
SPREADS_PIPS = [0.0, 0.5, 1.0, 1.5]
TB = 24


def pip_size(sym):
    return 0.01 if sym.endswith("JPY") else 0.0001


def raw_arrays(sym):
    raw = pd.read_parquet(DATA_V2 / f"{sym}_5m.parquet")
    atr = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
    return (raw.index, raw["open"].values, raw["high"].values, raw["low"].values,
            raw["close"].values, atr)


def sim_trade(o, h, l, c, atr, i, entry, first_k, spread_price):
    risk = atr[i]
    if not np.isfinite(risk) or risk <= 0 or not np.isfinite(entry):
        return None
    tp = entry + 1.5 * risk; sl = entry - 1.0 * risk
    end = min(len(c), first_k + TB)
    r = None
    for k in range(first_k, end):
        if l[k] <= sl:
            r = -1.0; break
        if h[k] >= tp:
            r = 1.5; break
    if r is None:
        if end - 1 >= first_k:
            r = (c[end - 1] - entry) / risk
        else:
            return None
    return r - spread_price / risk      # round-trip spread cost in R


def pf_wr(rs):
    rs = [r for r in rs if r is not None]
    if not rs:
        return None
    w = sum(1 for r in rs if r > 0); ls = sum(1 for r in rs if r <= 0)
    gw = sum(r for r in rs if r > 0); gl = -sum(r for r in rs if r <= 0)
    pf = gw / gl if gl > 0 else float("inf")
    return dict(n=len(rs), wr=round(w / len(rs), 3), pf=round(pf, 3), total_R=round(sum(rs), 1))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"netperf_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    pool, base_feat, aug_feat = build_pool()
    print(f"pool={len(pool):,}  feats={len(aug_feat)} (77)  pairs={PAIRS}\n")

    # collect OOS signal timestamps per pair across walk-forward folds
    sig_times = {p: [] for p in PAIRS}
    for ts in FOLD_STARTS:
        test_start, test_end = ts, ts + pd.DateOffset(months=3)
        val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
        tr = pool[pool.index < val_start]; va = pool[(pool.index >= val_start) & (pool.index < test_start)]
        te = pool[(pool.index >= test_start) & (pool.index < test_end)]
        if len(tr) < 20000 or len(va) < 2000 or len(te) < 500:
            continue
        m = train_lgbm(tr[aug_feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                       va[aug_feat].values.astype(np.float32), binary_label_for_long(va["label"]).values, 100, None, SEED)
        q97 = float(np.quantile(predict(m, "lgbm", va[aug_feat].values.astype(np.float32)), 0.97))
        pt = predict(m, "lgbm", te[aug_feat].values.astype(np.float32))
        sig = te.index[pt >= q97]; sig_sym = te["symbol"].values[pt >= q97]
        for t, s in zip(sig, sig_sym):
            if s in sig_times:
                sig_times[s].append(t)

    # simulate per pair: close-entry-gross, open-entry-gross, open-entry-net@spreads
    results = {}
    print("=== NET PERFORMANCE per pair (q97, walk-forward OOS signals) ===")
    for p in PAIRS:
        idx, o, h, l, c, atr = raw_arrays(p)
        posmap = {t: k for k, t in enumerate(idx)}
        pipv = pip_size(p)
        close_g, open_g = [], []
        open_net = {sp: [] for sp in SPREADS_PIPS if sp > 0}
        for t in sig_times[p]:
            i = posmap.get(t)
            if i is None or i + 1 >= len(c):
                continue
            # close-entry gross (reference, ~ current sim): enter close[i], check from i+1
            close_g.append(sim_trade(o, h, l, c, atr, i, c[i], i + 1, 0.0))
            # open-entry: enter open[i+1], check from i+1
            entry = o[i + 1]
            open_g.append(sim_trade(o, h, l, c, atr, i, entry, i + 1, 0.0))
            for sp in open_net:
                open_net[sp].append(sim_trade(o, h, l, c, atr, i, entry, i + 1, sp * pipv))
        results[p] = dict(close_gross=pf_wr(close_g), open_gross=pf_wr(open_g),
                          open_net={f"{sp}pip": pf_wr(open_net[sp]) for sp in open_net})
        cg, og = results[p]["close_gross"], results[p]["open_gross"]
        n10 = results[p]["open_net"]["1.0pip"]
        if cg and og and n10:
            print(f"  {p:7s} close-gross PF{cg['pf']:.2f}  | open-gross PF{og['pf']:.2f}/WR{og['wr']:.2f}  "
                  f"| net@1.0pip PF{n10['pf']:.2f}/WR{n10['wr']:.2f}/totR{n10['total_R']}  (n={og['n']})")

    # Tier-1 pooled
    print("\n=== TIER-1 pooled (GBP/JPY/CAD) ===")
    def pooled(key, sp=None):
        rs = []
        for p in TIER1:
            idx, o, h, l, c, atr = raw_arrays(p); posmap = {t: k for k, t in enumerate(idx)}; pipv = pip_size(p)
            for t in sig_times[p]:
                i = posmap.get(t)
                if i is None or i + 1 >= len(c):
                    continue
                if key == "close":
                    rs.append(sim_trade(o, h, l, c, atr, i, c[i], i + 1, 0.0))
                else:
                    rs.append(sim_trade(o, h, l, c, atr, i, o[i + 1], i + 1, (sp or 0.0) * pipv))
        return pf_wr(rs)
    t1 = dict(close_gross=pooled("close"), open_gross=pooled("open", 0.0),
              open_net_05=pooled("open", 0.5), open_net_10=pooled("open", 1.0), open_net_15=pooled("open", 1.5))
    for k, v in t1.items():
        if v:
            print(f"  {k:14s} PF{v['pf']:.2f}  WR{v['wr']:.2f}  totR {v['total_R']}  n {v['n']}")

    payload = dict(seed=SEED, spreads_pips=SPREADS_PIPS, per_pair=results, tier1_pooled=t1)
    (out_dir / "netperf.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
