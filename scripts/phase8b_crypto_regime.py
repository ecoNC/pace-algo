"""
Crypto approach B: REGIME-ROUTED edge (the mechanism test).

phase8a showed momentum wins in 2024-25 (trending) and mean-reversion wins in 2026
(choppy) — the regime flipped. A causal regime router should route each strategy to its
favorable regime and be positive ALL years.

Causal regime = state engine trend_regime (TREND_UP/DOWN = trending, RANGE = ranging),
computed with no lookahead. Then:
  - TREND bars  -> trend-following: long in TREND_UP, short in TREND_DOWN (triple-barrier R=1.5)
  - RANGE bars  -> mean-reversion: fade |close-ema20|/atr >= thr (reversion TP / continuation SL)
Measure raw R per year for each leg AND the COMBINED routed strategy. 5m. If combined is
positive all years incl 2026 -> regime routing is the crypto answer (then add ML selection).

Output: results/model_validation/phase8b_regime_<UTC>/regime.json
Run:    python scripts/phase8b_crypto_regime.py
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

from core.features.engineer import ema, atr as atr_fn
from core.state.market_state import classify_market_state, TREND_UP, TREND_DOWN, RANGE

SYMBOLS = ["BTCUSD", "ETHUSD"]
TF = "5m"
TB, COST = 24, 0.03
MR_THR, MR_TP, MR_SL = 1.5, 1.0, 2.0    # mean-reversion (from phase8a best 2026)
TF_TP, TF_SL = 1.5, 1.0                  # trend-follow R=1.5


def trail_barrier(o, h, l, c, a, i, d, tp_R, sl_R):
    entry = c[i]
    if d > 0:
        tp, sl = entry + tp_R * a, entry - sl_R * a
        for k in range(i + 1, i + 1 + TB):
            if l[k] <= sl: return -sl_R
            if h[k] >= tp: return tp_R
    else:
        tp, sl = entry - tp_R * a, entry + sl_R * a
        for k in range(i + 1, i + 1 + TB):
            if h[k] >= sl: return -sl_R
            if l[k] <= tp: return tp_R
    return 0.0


def build_legs(raw):
    a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
    e20 = ema(raw["close"], 20).values
    st = classify_market_state(raw)
    trend = st["trend_regime"].values
    o, h, l, c = raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values
    n = len(c)
    Rtf = np.full(n, np.nan); Rmr = np.full(n, np.nan)
    for i in range(n - TB - 1):
        av = a[i]
        if not np.isfinite(av) or av <= 0 or not np.isfinite(e20[i]): continue
        tr = trend[i]
        if tr in (TREND_UP, TREND_DOWN):                      # trend-follow
            d = 1 if tr == TREND_UP else -1
            Rtf[i] = trail_barrier(o, h, l, c, av, i, d, TF_TP, TF_SL)
        elif tr == RANGE:                                     # mean-reversion fade
            z = (c[i] - e20[i]) / av
            if z >= MR_THR:   Rmr[i] = trail_barrier(o, h, l, c, av, i, -1, MR_TP, MR_SL)
            elif z <= -MR_THR: Rmr[i] = trail_barrier(o, h, l, c, av, i, +1, MR_TP, MR_SL)
    return Rtf, Rmr, raw.index.year.values


def pf_wr(r, cost):
    r = r[np.isfinite(r)] - cost
    if len(r) < 20: return None
    w = int((r > 0).sum()); gw = r[r > 0].sum(); gl = -r[r <= 0].sum()
    return dict(n=int(len(r)), wr=round(w/len(r), 3), pf=round(float(gw/gl), 3) if gl > 0 else 999.0)


def by_year(R, Y, cost):
    out = {}
    for y in (2024, 2025, 2026):
        out[str(y)] = pf_wr(R[Y == y], cost)
    out["all"] = pf_wr(R, cost)
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase8b_regime_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    Rtf_all, Rmr_all, Y_all = [], [], []
    for s in SYMBOLS:
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{s}_{TF}.parquet")
        raw = raw[raw.index >= pd.Timestamp("2023-06-01", tz="UTC")]
        Rtf, Rmr, Y = build_legs(raw)
        Rtf_all.append(Rtf); Rmr_all.append(Rmr); Y_all.append(Y)
    Rtf = np.concatenate(Rtf_all); Rmr = np.concatenate(Rmr_all); Y = np.concatenate(Y_all)
    # combined routed: union of both legs (disjoint by regime)
    Rcomb = np.where(np.isfinite(Rtf), Rtf, Rmr)

    res = {"trend_follow_in_TREND": by_year(Rtf, Y, COST),
           "mean_rev_in_RANGE": by_year(Rmr, Y, COST),
           "COMBINED_routed": by_year(Rcomb, Y, COST)}
    (OUT / "regime.json").write_text(json.dumps(dict(cost=COST, params=dict(mr_thr=MR_THR, mr_tp=MR_TP, mr_sl=MR_SL, tf_tp=TF_TP, tf_sl=TF_SL), results=res), indent=2, default=str), encoding="utf-8")

    for leg, d in res.items():
        line = "  ".join(f"{y}:PF{(d[y] or {}).get('pf')}/WR{(d[y] or {}).get('wr')}/n{(d[y] or {}).get('n')}" for y in ("2024", "2025", "2026"))
        a = d["all"] or {}
        print(f"{leg:24s} all:PF{a.get('pf')}/WR{a.get('wr')}/n{a.get('n')}   {line}")
    c = res["COMBINED_routed"]
    allpos = all(c.get(y) and c[y]["pf"] > 1.0 for y in ("2024", "2025", "2026"))
    print(f"\nCOMBINED routed positive ALL years (raw, no ML): {allpos}")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
