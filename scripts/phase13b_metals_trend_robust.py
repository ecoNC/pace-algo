"""
Phase 13b: metals TREND_L robustness — grid + full per-year (lower n threshold).

phase13: gold/silver long trend-persistence PF 1.50 (n=155) — the only metals pulse.
Grid: EMA {30,50,70} x SL {1.5,2.0,2.5} x hold {10,20,30}; per-year PF with n>=8;
split half1 2015-2020 vs half2 2021-2026 (time-stability).

Run: python scripts/phase13b_metals_trend_robust.py
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

from core.features.engineer import ema, atr as atr_fn
from phase12_indices_swing import trade_R
from phase13_metals_swing import get_daily, SYMBOLS

EMAS = [30, 50, 70]
SLS = [1.5, 2.0, 2.5]
HOLDS = [10, 20, 30]


def pf(rs):
    rs = np.array(rs); rs = rs[np.isfinite(rs)]
    if len(rs) < 8: return None, len(rs)
    gw = rs[rs > 0].sum(); gl = -rs[rs <= 0].sum()
    return (round(float(gw / gl), 3) if gl > 0 else 999.0), len(rs)


def run(ema_n, sl, hold):
    trades = []
    for sym in SYMBOLS:
        d = get_daily(sym)
        a = atr_fn(d["high"], d["low"], d["close"], 14).values
        eN = ema(d["close"], ema_n).values
        c = d["close"].values
        with np.errstate(invalid="ignore"):
            up = np.r_[False, np.diff(eN) > 0]
            sig = (c > eN) & up & ~np.r_[False, ((c > eN) & up)[:-1]]
        trades.extend(trade_R(d, sig, +1, sl_mult=sl, max_hold=hold, exit_ema=False))
    return trades


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase13b_mtl_trend_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    grid = {}; pfs = []
    print("=== grid @0.02 ===")
    for en in EMAS:
        for sl in SLS:
            for hold in HOLDS:
                tr = run(en, sl, hold)
                p, n = pf([r - 0.02 for _, r in tr])
                grid[f"ema{en}_sl{sl}_h{hold}"] = dict(pf=p, n=n)
                if p: pfs.append(p)
                print(f"  ema={en} sl={sl} hold={hold}: PF {p} n={n}")
    pfs = np.array(pfs)
    base = run(50, 2.0, 20)
    print("\n=== base per-year (n>=8) + halves @0.02 ===")
    yr = {}
    for y in range(2015, 2027):
        p, n = pf([r - 0.02 for ts, r in base if ts.year == y])
        yr[str(y)] = dict(pf=p, n=n)
        if n: print(f"  {y}: PF {p} (n={n})")
    h1, _ = pf([r - 0.02 for ts, r in base if ts.year <= 2020])
    h2, _ = pf([r - 0.02 for ts, r in base if ts.year >= 2021])
    summary = dict(grid_cells=len(pfs), grid_pct_gt1=round(float((pfs > 1).mean()), 2),
                   grid_median=round(float(np.median(pfs)), 3), grid_min=round(float(pfs.min()), 3),
                   half_2015_2020=h1, half_2021_2026=h2)
    print(f"\nhalf1 15-20: PF {h1} | half2 21-26: PF {h2}")
    print(f"grid: {summary['grid_pct_gt1']:.0%} >1, median {summary['grid_median']}, min {summary['grid_min']}")
    (OUT / "mtl_trend.json").write_text(json.dumps(dict(grid=grid, per_year=yr, summary=summary),
                                                   indent=2, default=str), encoding="utf-8")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
