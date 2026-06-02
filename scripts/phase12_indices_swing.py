"""
Phase 12: INDICES on swing timeframes — mechanism test of documented anomalies.

phase10d closed indices INTRADAY (15m-1h). The documented index anomalies live on
DAILY structure and were never tested here:
  TOM      : turn-of-month long (last 4 + first 3 trading days)   [documented]
  DIPBUY   : daily close < EMA20 - 1*ATR -> long, exit EMA20 touch or 10d, SL 2*ATR
  RIPFADE  : mirror short (close > EMA20 + 1*ATR)                 [short-side probe]
  TREND5   : close > EMA50 & EMA50 rising -> hold long (regime persistence)

Deterministic, no ML (mechanism first — ML only if a pulse exists). Daily bars
resampled from 4h Dukascopy parquets (UTC calendar day), 9 indices pooled + per-symbol.
Net cost 0.02/0.05 ATR-fraction per round trip. Per-year PF is the gate.

Output: results/model_validation/phase12_idx_swing_<UTC>/idx_swing.json
Run:    python scripts/phase12_indices_swing.py
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

SYMBOLS = ["SPX500", "NAS100", "US30", "US2000", "GER40", "UK100", "FRA40", "EUSTX50", "JPN225", "HKG33"]
COSTS = [0.02, 0.05]
DATA = REPO / "data" / "processed_v2"


def daily(sym):
    p = DATA / f"{sym}_4h.parquet"
    if not p.exists(): return None
    raw = pd.read_parquet(p)
    d = raw.resample("1D").agg({"open": "first", "high": "max", "low": "min",
                                "close": "last", "volume": "sum"}).dropna(subset=["close"])
    return d


def trade_R(d, entries, direction, sl_mult=2.0, max_hold=10, exit_ema=True):
    """Entry next open after signal; exit on EMA20 touch / SL / max_hold. R = pnl / (sl_mult*ATR)."""
    o, h, l, c = d["open"].values, d["high"].values, d["low"].values, d["close"].values
    a = atr_fn(d["high"], d["low"], d["close"], 14).values
    e20 = ema(d["close"], 20).values
    n = len(c); out = []
    i = 0
    sig = np.where(entries)[0]
    si = 0
    while si < len(sig):
        i = sig[si]
        if i + 1 >= n or not np.isfinite(a[i]) or a[i] <= 0: si += 1; continue
        entry = o[i + 1]; risk = sl_mult * a[i]
        sl = entry - risk if direction > 0 else entry + risk
        r = None
        for k in range(i + 1, min(i + 1 + max_hold, n)):
            if direction > 0 and l[k] <= sl: r = -1.0; break
            if direction < 0 and h[k] >= sl: r = -1.0; break
            if exit_ema and np.isfinite(e20[k]):
                if direction > 0 and h[k] >= e20[k] and e20[k] > entry:
                    r = (e20[k] - entry) / risk; break
                if direction < 0 and l[k] <= e20[k] and e20[k] < entry:
                    r = (entry - e20[k]) / risk; break
        if r is None:
            k = min(i + max_hold, n - 1)
            r = ((c[k] - entry) if direction > 0 else (entry - c[k])) / risk
        out.append((d.index[i + 1], r))
        # skip overlapping signals until exit bar
        nxt = si
        while nxt < len(sig) and sig[nxt] <= k: nxt += 1
        si = nxt
    return out


def tom_R(d):
    """Turn-of-month: long close of T-4 -> close of T+3. One R = 2*ATR risk unit."""
    a = atr_fn(d["high"], d["low"], d["close"], 14).values
    c = d["close"].values
    mon = d.index.to_period("M")
    out = []
    for m in mon.unique():
        idx = np.where(mon == m)[0]
        if len(idx) < 8: continue
        i_in = idx[-4]
        nxt = np.where(mon == m + 1)[0]
        if len(nxt) < 3: continue
        i_out = nxt[2]
        if not np.isfinite(a[i_in]) or a[i_in] <= 0: continue
        out.append((d.index[i_in], (c[i_out] - c[i_in]) / (2 * a[i_in])))
    return out


def pf_wr(rs):
    rs = np.array([r for _, r in rs], dtype=float)
    rs = rs[np.isfinite(rs)]
    if len(rs) < 15: return None
    gw = rs[rs > 0].sum(); gl = -rs[rs <= 0].sum()
    return dict(n=int(len(rs)), wr=round(float((rs > 0).mean()), 3),
                pf=round(float(gw / gl), 3) if gl > 0 else 999.0)


def per_year(trades, cost):
    res = {}
    arr = [(ts, r - cost) for ts, r in trades]
    for y in (2022, 2023, 2024, 2025, 2026):
        res[str(y)] = pf_wr([(ts, r) for ts, r in arr if ts.year == y])
    res["all"] = pf_wr(arr)
    return res


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase12_idx_swing_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    strategies = {"TOM": [], "DIPBUY": [], "RIPFADE": [], "TREND5": []}
    per_sym = {}
    for sym in SYMBOLS:
        d = daily(sym)
        if d is None or len(d) < 400: continue
        a = atr_fn(d["high"], d["low"], d["close"], 14).values
        e20 = ema(d["close"], 20).values
        e50 = ema(d["close"], 50).values
        c = d["close"].values
        with np.errstate(invalid="ignore"):
            dip = c < e20 - 1.0 * a
            rip = c > e20 + 1.0 * a
            e50_rising = np.r_[False, np.diff(e50) > 0]
            tr5 = (c > e50) & e50_rising & ~np.r_[False, ((c > e50) & e50_rising)[:-1]]  # fresh cross/start
        legs = {
            "TOM": tom_R(d),
            "DIPBUY": trade_R(d, dip, +1),
            "RIPFADE": trade_R(d, rip, -1),
            "TREND5": trade_R(d, tr5, +1, sl_mult=2.0, max_hold=20, exit_ema=False),
        }
        per_sym[sym] = {k: (pf_wr([(ts, r - 0.02) for ts, r in v]) or {}).get("pf") for k, v in legs.items()}
        for k, v in legs.items(): strategies[k].extend(v)

    res = {"pooled": {}, "per_symbol_pf@0.02": per_sym}
    print(f"{'strategy':10s} {'cost':6s} {'all_PF':>7s} {'WR':>6s} {'n':>6s}   per-year PF")
    for k, v in strategies.items():
        res["pooled"][k] = {}
        for cost in COSTS:
            py = per_year(v, cost)
            res["pooled"][k][f"{cost}"] = py
            al = py["all"] or {}
            yl = " ".join(f"{y}:{(py[str(y)] or {}).get('pf')}" for y in (2022, 2023, 2024, 2025, 2026))
            print(f"{k:10s} {cost:<6} {str(al.get('pf')):>7s} {str(al.get('wr')):>6s} {str(al.get('n')):>6s}   {yl}")
    (OUT / "idx_swing.json").write_text(json.dumps(dict(symbols=SYMBOLS, costs=COSTS, results=res),
                                                   indent=2, default=str), encoding="utf-8")
    print(f"\nPulse-Kriterium: all-PF deutlich >1 UND kein Jahr klar <1. Done -> {OUT}")


if __name__ == "__main__":
    main()
