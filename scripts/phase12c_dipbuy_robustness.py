"""
Phase 12c: DIPBUY>EMA200 robustness battery — is the pulse real or a parameter fluke?

Checks (all pooled daily, 10 indices, cost 0.02/0.05):
  1. Parameter grid: dip threshold {0.75, 1.0, 1.25, 1.5} x SL {1.5, 2.0, 2.5}
     x max_hold {5, 10, 15}. A real edge is FLAT across the grid, not a spike.
  2. Per-symbol: PF per index at the base config — breadth, not 1-2 carriers.
  3. Regime-EMA sensitivity: EMA {150, 200, 250}.
Verdict bar: >=70% of grid cells PF>1 @0.02, median PF >= 1.2, >=7/10 symbols PF>1.

Output: results/model_validation/phase12c_dip_robust_<UTC>/dip_robust.json
Run:    python scripts/phase12c_dipbuy_robustness.py
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
from phase12_indices_swing import SYMBOLS, daily, trade_R, per_year, pf_wr

DIP_THR = [0.75, 1.0, 1.25, 1.5]
SL_MULT = [1.5, 2.0, 2.5]
MAX_HOLD = [5, 10, 15]
REGIME_EMA = [150, 200, 250]


def signals(d, thr, ema_n):
    a = atr_fn(d["high"], d["low"], d["close"], 14).values
    e20 = ema(d["close"], 20).values
    er = ema(d["close"], ema_n).values
    c = d["close"].values
    with np.errstate(invalid="ignore"):
        return (c < e20 - thr * a) & (c > er)


def run(thr=1.0, sl=2.0, hold=10, ema_n=200):
    trades = []
    for sym in SYMBOLS:
        d = daily(sym)
        if d is None or len(d) < 400: continue
        trades.extend(trade_R(d, signals(d, thr, ema_n), +1, sl_mult=sl, max_hold=hold))
    return trades


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase12c_dip_robust_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)

    # 1) parameter grid
    grid = {}
    pfs = []
    print("=== grid (dip_thr x sl x hold) @0.02 ===")
    for thr in DIP_THR:
        for sl in SL_MULT:
            for hold in MAX_HOLD:
                tr = run(thr=thr, sl=sl, hold=hold)
                st = pf_wr([(ts, r - 0.02) for ts, r in tr]) or {}
                grid[f"thr{thr}_sl{sl}_h{hold}"] = st
                if st.get("pf"): pfs.append(st["pf"])
                print(f"  thr={thr} sl={sl} hold={hold}: PF {st.get('pf')} n={st.get('n')}")
    pfs = np.array(pfs)
    grid_sum = dict(cells=len(pfs), pct_pf_gt1=round(float((pfs > 1).mean()), 2),
                    median_pf=round(float(np.median(pfs)), 3),
                    min_pf=round(float(pfs.min()), 3), max_pf=round(float(pfs.max()), 3))

    # 2) per-symbol at base config
    print("\n=== per-symbol (base config) @0.02 ===")
    psym = {}
    for sym in SYMBOLS:
        d = daily(sym)
        if d is None or len(d) < 400: continue
        tr = trade_R(d, signals(d, 1.0, 200), +1)
        st = pf_wr([(ts, r - 0.02) for ts, r in tr]) or {}
        psym[sym] = st
        print(f"  {sym}: PF {st.get('pf')} WR {st.get('wr')} n={st.get('n')}")
    sym_pfs = [v.get("pf") for v in psym.values() if v.get("pf")]
    sym_sum = dict(n_symbols=len(sym_pfs), n_pf_gt1=sum(1 for p in sym_pfs if p > 1))

    # 3) regime EMA sensitivity (+ per-year at base)
    print("\n=== regime EMA sensitivity @0.02 ===")
    rsens = {}
    for en in REGIME_EMA:
        tr = run(ema_n=en)
        py = per_year(tr, 0.02)
        rsens[f"ema{en}"] = py
        al = py["all"] or {}
        yl = " ".join(f"{y}:{(py[str(y)] or {}).get('pf')}" for y in (2023, 2024, 2025, 2026))
        print(f"  EMA{en}: PF {al.get('pf')} n={al.get('n')}   {yl}")

    verdict = dict(grid=grid_sum, symbols=sym_sum,
                   bar_pass=bool(grid_sum["pct_pf_gt1"] >= 0.7 and grid_sum["median_pf"] >= 1.2
                                 and sym_sum["n_pf_gt1"] >= 7))
    (OUT / "dip_robust.json").write_text(json.dumps(dict(
        grid=grid, per_symbol=psym, regime_sens=rsens, verdict=verdict), indent=2, default=str), encoding="utf-8")
    print(f"\nVERDICT: {json.dumps(verdict)}")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
