"""
Phase 12b: DIPBUY conditioned on bull regime (the obvious fix for 2022).

phase12: pooled daily DIPBUY is 4-years-positive (2023-26) but fails in the 2022 bear.
Variants: bull = close > EMA200  |  bull = EMA50 rising. Short mirror in bear regime
(DIPSELL: rip-fade only when close < EMA200) as the honest short-side probe.

Run: python scripts/phase12b_dipbuy_regime.py
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

from core.features.engineer import ema, atr as atr_fn
from phase12_indices_swing import SYMBOLS, daily, trade_R, per_year

VARIANTS = ["DIPBUY_gt_EMA200", "DIPBUY_EMA50_rising", "RIPFADE_lt_EMA200"]


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase12b_dip_regime_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for name in VARIANTS:
        trades = []
        for sym in SYMBOLS:
            d = daily(sym)
            if d is None or len(d) < 400: continue
            a = atr_fn(d["high"], d["low"], d["close"], 14).values
            e20 = ema(d["close"], 20).values
            e50 = ema(d["close"], 50).values
            e200 = ema(d["close"], 200).values
            c = d["close"].values
            with np.errstate(invalid="ignore"):
                dip = c < e20 - 1.0 * a
                rip = c > e20 + 1.0 * a
                bull200 = c > e200
                bull50 = np.r_[False, np.diff(e50) > 0]
            if name == "DIPBUY_gt_EMA200":
                trades.extend(trade_R(d, dip & bull200, +1))
            elif name == "DIPBUY_EMA50_rising":
                trades.extend(trade_R(d, dip & bull50, +1))
            else:
                trades.extend(trade_R(d, rip & ~bull200, -1))
        res[name] = {}
        for cost in (0.02, 0.05):
            py = per_year(trades, cost)
            res[name][str(cost)] = py
            al = py["all"] or {}
            yl = " ".join(f"{y}:{(py[str(y)] or {}).get('pf')}" for y in (2022, 2023, 2024, 2025, 2026))
            print(f"{name:22s} cost={cost}: PF {al.get('pf')}  WR {al.get('wr')}  n={al.get('n')}   {yl}")
    (OUT / "dip_regime.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
