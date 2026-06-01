"""
Crypto approach A: MEAN-REVERSION edge diagnostic (fundamentally different from all prior).

Everything we tried was directional/momentum (triple-barrier needs a move in the trade's
direction) and decayed in 2026. Research: in choppy/low-vol crypto regimes (2025-26),
mean-reversion beats momentum. So test the OPPOSITE: fade extremes, bet on reversion.

Pure hypothesis test (NO ML): when price is stretched from EMA20 (|z| = |close-ema20|/atr
>= thr), FADE it (short the overbought, long the oversold), with a reversion barrier
(TP toward mean, SL on continuation). Measure raw PF/WR PER YEAR (esp 2026) across
thresholds, TP/SL configs, and TFs. If 2026 is positive here, mean-reversion is the path.

Output: results/model_validation/phase8a_meanrev_<UTC>/meanrev.json
Run:    python scripts/phase8a_crypto_meanrev.py
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

SYMBOLS = ["BTCUSD", "ETHUSD"]
TFS = ["5m", "1h"]
THRESHOLDS = [1.0, 1.5, 2.0]            # stretch in ATR to call "extreme"
TPSL = [(1.0, 1.5), (0.75, 1.5), (1.0, 2.0)]  # (reversion TP, continuation SL) in ATR
TB = 24
COST = 0.03                              # ATR fraction


def meanrev_R(o, h, l, c, atrv, ema20, thr, tp_R, sl_R, tb=TB):
    """Fade extremes; realized R of the reversion trade per bar (NaN if no signal)."""
    n = len(c); R = np.full(n, np.nan); side = np.full(n, 0)
    for i in range(n - tb - 1):
        a = atrv[i]
        if not np.isfinite(a) or a <= 0 or not np.isfinite(ema20[i]): continue
        z = (c[i] - ema20[i]) / a
        if z >= thr:        # overbought -> fade short
            entry = c[i]; tp = entry - tp_R * a; sl = entry + sl_R * a; d = -1
        elif z <= -thr:     # oversold -> fade long
            entry = c[i]; tp = entry + tp_R * a; sl = entry - sl_R * a; d = +1
        else:
            continue
        r = None
        for k in range(i + 1, i + 1 + tb):
            if d > 0:
                if l[k] <= sl: r = -sl_R; break
                if h[k] >= tp: r = tp_R; break
            else:
                if h[k] >= sl: r = -sl_R; break
                if l[k] <= tp: r = tp_R; break
        R[i] = 0.0 if r is None else r; side[i] = d
    return R, side


def stats_year(R, years, cost):
    out = {}
    for y in (2024, 2025, 2026):
        r = R[(years == y) & np.isfinite(R)] - cost
        if len(r) < 20:
            out[str(y)] = None; continue
        w = int((r > 0).sum()); gw = r[r > 0].sum(); gl = -r[r <= 0].sum()
        out[str(y)] = dict(n=int(len(r)), wr=round(w/len(r), 3), pf=round(float(gw/gl), 3) if gl > 0 else 999.0)
    rall = R[np.isfinite(R)] - cost
    w = int((rall > 0).sum()); gw = rall[rall > 0].sum(); gl = -rall[rall <= 0].sum()
    out["all"] = dict(n=int(len(rall)), wr=round(w/len(rall), 3), pf=round(float(gw/gl), 3) if gl > 0 else 999.0) if len(rall) >= 20 else None
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase8a_meanrev_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for tf in TFS:
        # pool both symbols
        parts = []
        for s in SYMBOLS:
            raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{s}_{tf}.parquet")
            raw = raw[raw.index >= pd.Timestamp("2023-06-01", tz="UTC")]  # focus recent regimes
            parts.append(raw)
        for thr in THRESHOLDS:
            for tp_R, sl_R in TPSL:
                Rs, Ys = [], []
                for raw in parts:
                    a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
                    e20 = ema(raw["close"], 20).values
                    R, side = meanrev_R(raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values, a, e20, thr, tp_R, sl_R)
                    Rs.append(R); Ys.append(raw.index.year.values)
                R = np.concatenate(Rs); Y = np.concatenate(Ys)
                key = f"{tf}_z{thr}_tp{tp_R}_sl{sl_R}"
                sy = stats_year(R, Y, COST)
                res[key] = sy
                a = sy.get("all") or {}
                yline = "  ".join(f"{y}:PF{(sy[y] or {}).get('pf')}/n{(sy[y] or {}).get('n')}" for y in ("2024", "2025", "2026"))
                print(f"{key:28s} all:PF{a.get('pf')}/WR{a.get('wr')}/n{a.get('n')}   {yline}")
    (OUT / "meanrev.json").write_text(json.dumps(dict(cost=COST, tb=TB, results=res), indent=2, default=str), encoding="utf-8")
    # highlight configs with all-3-years PF>1
    good = [k for k, v in res.items() if all(v.get(y) and v[y]["pf"] > 1.0 for y in ("2024", "2025", "2026"))]
    print(f"\nConfigs positive in ALL years (2024/25/26): {good}")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
