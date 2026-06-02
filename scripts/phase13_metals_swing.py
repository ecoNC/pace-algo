"""
Phase 13: METALS on daily swing structure — same gauntlet as indices (phase12).

Metals differ from indices: no structural upward drift -> shorts get a fair test here.
Strategies (daily, native 1d 2015-2026, gold + silver pooled):
  DIPBUY_bull : close < EMA20-1*ATR & close > EMA200 -> long  (the index winner)
  RIPFADE_bear: close > EMA20+1*ATR & close < EMA200 -> short (mirror)
  TREND_L/S   : fresh EMA50-cross with rising/falling EMA50 -> trend persistence
  BREAKOUT    : close > prev 20d high & close > EMA200 -> long (metals momentum)

Per-year PF 2015-2026, costs 0.02/0.05 ATR round trip. Pulse first, grid/holdout
split only if something is alive.

Output: results/model_validation/phase13_metals_swing_<UTC>/metals_swing.json
Run:    python scripts/phase13_metals_swing.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import numpy as np
import pandas as pd

from core.data.dukascopy_fetcher import fetch_dukascopy_ohlcv
from core.features.engineer import ema, atr as atr_fn
from phase12_indices_swing import trade_R, pf_wr

SYMBOLS = ["XAUUSD", "XAGUSD"]
START = datetime(2015, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 5, 31, tzinfo=timezone.utc)
DATA = REPO / "data" / "processed_v2"
COSTS = [0.02, 0.05]


def get_daily(sym):
    p = DATA / f"{sym}_1d.parquet"
    if p.exists():
        return pd.read_parquet(p)
    print(f"  fetching {sym} 1d...", end="", flush=True)
    df = fetch_dukascopy_ohlcv(sym, "1d", START, END)
    if df.empty:
        print(" EMPTY"); return None
    df.to_parquet(p)
    print(f" OK {len(df):,}")
    return df


def per_year_pf(trades, cost):
    out = {}
    net = [(ts, r - cost) for ts, r in trades]
    for y in range(2015, 2027):
        out[str(y)] = (pf_wr([(ts, r) for ts, r in net if ts.year == y]) or {}).get("pf")
    out["all"] = pf_wr(net) or {}
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase13_metals_swing_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    strategies = {"DIPBUY_bull": [], "RIPFADE_bear": [], "TREND_L": [], "TREND_S": [], "BREAKOUT": []}
    for sym in SYMBOLS:
        d = get_daily(sym)
        if d is None or len(d) < 500: continue
        a = atr_fn(d["high"], d["low"], d["close"], 14).values
        e20 = ema(d["close"], 20).values
        e50 = ema(d["close"], 50).values
        e200 = ema(d["close"], 200).values
        c, h = d["close"].values, d["high"].values
        hh20 = pd.Series(h, index=d.index).rolling(20).max().shift(1).values
        with np.errstate(invalid="ignore"):
            dip = (c < e20 - 1.0 * a) & (c > e200)
            rip = (c > e20 + 1.0 * a) & (c < e200)
            e50_up = np.r_[False, np.diff(e50) > 0]
            e50_dn = np.r_[False, np.diff(e50) < 0]
            trL = (c > e50) & e50_up & ~np.r_[False, ((c > e50) & e50_up)[:-1]]
            trS = (c < e50) & e50_dn & ~np.r_[False, ((c < e50) & e50_dn)[:-1]]
            bo = (c > hh20) & (c > e200)
        strategies["DIPBUY_bull"].extend(trade_R(d, dip, +1))
        strategies["RIPFADE_bear"].extend(trade_R(d, rip, -1))
        strategies["TREND_L"].extend(trade_R(d, trL, +1, sl_mult=2.0, max_hold=20, exit_ema=False))
        strategies["TREND_S"].extend(trade_R(d, trS, -1, sl_mult=2.0, max_hold=20, exit_ema=False))
        strategies["BREAKOUT"].extend(trade_R(d, bo, +1, sl_mult=2.0, max_hold=20, exit_ema=False))
    res = {}
    for k, v in strategies.items():
        res[k] = {}
        for cost in COSTS:
            py = per_year_pf(v, cost)
            res[k][str(cost)] = py
            al = py["all"]
            yl = " ".join(f"{y}:{py[str(y)]}" for y in range(2015, 2027) if py[str(y)] is not None)
            print(f"{k:13s} cost={cost}: PF {al.get('pf')}  WR {al.get('wr')}  n={al.get('n')}")
            print(f"               {yl}")
    (OUT / "metals_swing.json").write_text(json.dumps(dict(symbols=SYMBOLS, costs=COSTS, results=res),
                                                      indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
