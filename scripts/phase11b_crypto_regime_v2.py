"""
Phase 11b: regime-routing (v1's 2026-fix) on CLEAN Binance data at REAL perp fees.

phase11 showed: native features lift (+0.08) but 2026 decays. phase8b showed: regime
routing fixes 2026 — but was costed at 0.03R on 5m, where REAL perp fees are ~0.7R/trade
(fee*price/ATR). This is the honest mechanism test of the synthesis:
  TREND bars -> trend-follow; RANGE bars -> mean-rev fade (phase8b legs, unchanged)
  on 1h and 4h Binance perps, 8 coins, fee_R = fee_frac * close / atr PER BAR.

If the routed mechanism is all-years-positive at real fees on a TF -> add ML selection
(phase11c). If not -> crypto closes honestly in the registry.

Output: results/model_validation/phase11b_regime_v2_<UTC>/regime_v2.json
Run:    python scripts/phase11b_crypto_regime_v2.py
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

from core.features.engineer import atr as atr_fn
from phase8b_crypto_regime import build_legs

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT"]
TFS = ["1h", "4h"]
FEES = [0.0005, 0.0010]
DATA = REPO / "data" / "binance"


def pf_wr(r):
    r = r[np.isfinite(r)]
    if len(r) < 20: return None
    w = int((r > 0).sum()); gw = r[r > 0].sum(); gl = -r[r <= 0].sum()
    return dict(n=int(len(r)), wr=round(w / len(r), 3), pf=round(float(gw / gl), 3) if gl > 0 else 999.0)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase11b_regime_v2_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for tf in TFS:
        Rtf_all, Rmr_all, fee_all, Y_all = [], [], [], []
        for s in SYMBOLS:
            raw = pd.read_parquet(DATA / f"{s}_{tf}.parquet")
            raw = raw[raw.index >= pd.Timestamp("2023-06-01", tz="UTC")]
            Rt, Rm, Y = build_legs(raw)
            a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
            feeR = raw["close"].values / np.where(a > 0, a, np.nan)   # x fee_frac
            Rtf_all.append(Rt); Rmr_all.append(Rm); fee_all.append(feeR); Y_all.append(Y)
        Rt = np.concatenate(Rtf_all); Rm = np.concatenate(Rmr_all)
        feeR = np.concatenate(fee_all); Y = np.concatenate(Y_all)
        Rcomb = np.where(np.isfinite(Rt), Rt, Rm)
        d = {}
        for f in FEES:
            legs = {}
            for name, R in [("trend", Rt), ("meanrev", Rm), ("COMBINED", Rcomb)]:
                net = R - f * feeR
                yr = {str(y): pf_wr(net[Y == y]) for y in (2024, 2025, 2026)}
                yr["all"] = pf_wr(net)
                legs[name] = yr
            c = legs["COMBINED"]
            allpos = all(c[str(y)] and c[str(y)]["pf"] > 1.0 for y in (2024, 2025, 2026))
            legs["all_years_pos"] = allpos
            d[f"fee{f}"] = legs
            a_ = c["all"] or {}
            line = "  ".join(f"{y}:PF{(c[str(y)] or {}).get('pf')}" for y in (2024, 2025, 2026))
            print(f"[{tf}] fee={f}: COMBINED all:PF{a_.get('pf')}/WR{a_.get('wr')}/n{a_.get('n')}  {line}  allpos={allpos}")
        res[tf] = d
    (OUT / "regime_v2.json").write_text(json.dumps(dict(symbols=SYMBOLS, fees=FEES, results=res),
                                                   indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
