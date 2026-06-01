"""
Make-or-Break Setup Test (V2) — does a STRUCTURAL trigger select net-positive
where "every bar in state" loses (-0.19 R)?

Decides: rule-based viable (setup provides selectivity) vs model needed as selector.

Two structural setups (deterministic, confirmed-bar, no lookahead):
  A) Pullback-continuation: in TREND_UP/NY, pullback to EMA20 then reclaim close (long); mirror DOWN
  B) Liquidity-sweep reversal: sweep below confirmed swing-low + close back above (long); mirror

Net @1.0pip, next-bar logic via close-entry barrier (net-neutral proxy), Tier-1, per-year stability.
Baseline = state-aligned "every NY bar" (from state_edge_analysis): avgR ~ -0.15..-0.19, PF ~0.72-0.79.

Output: results/model_validation/setup_mob_<UTC>/setup_mob.json
Run: python scripts/setup_makeorbreak.py
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

from model_validation_suite import DATA_V2
from core.features.engineer import ema, atr as atr_fn
from core.state.market_state import classify_market_state, TREND_UP, TREND_DOWN, RANGE

PAIRS = ["GBPUSD", "USDJPY", "USDCAD"]
TB, TP_R, SL_R, SPREAD_PIP = 24, 1.5, 1.0, 1.0
PIVOT_L = 5
PULLBACK_K = 6


def pip_size(s): return 0.01 if s.endswith("JPY") else 0.0001


def barrier_R(o, h, l, c, atr, direction):
    n = len(c); R = np.full(n, np.nan)
    for i in range(n - TB - 1):
        a = atr[i]
        if not np.isfinite(a) or a <= 0: continue
        entry = c[i]; r = None
        if direction == "long":
            tp, sl = entry + TP_R * a, entry - SL_R * a
            for k in range(i + 1, i + 1 + TB):
                if l[k] <= sl: r = -SL_R; break
                if h[k] >= tp: r = TP_R; break
        else:
            tp, sl = entry - TP_R * a, entry + SL_R * a
            for k in range(i + 1, i + 1 + TB):
                if h[k] >= sl: r = -SL_R; break
                if l[k] <= tp: r = TP_R; break
        R[i] = 0.0 if r is None else r
    return R


def confirmed_swing(series, L=PIVOT_L, kind="low"):
    """Last confirmed pivot known by bar t (placed at confirmation bar i+L, ffilled). No lookahead."""
    arr = series.values; n = len(arr); piv = np.full(n, np.nan)
    for i in range(L, n - L):
        w = arr[i - L:i + L + 1]
        if (kind == "low" and arr[i] == w.min()) or (kind == "high" and arr[i] == w.max()):
            piv[i + L] = arr[i]
    return pd.Series(piv, index=series.index).ffill()


def pf_wr(rs):
    rs = rs[np.isfinite(rs)]
    if len(rs) < 15: return None
    w = int((rs > 0).sum()); gw = rs[rs > 0].sum(); gl = -rs[rs <= 0].sum()
    return dict(n=int(len(rs)), wr=round(w / len(rs), 3),
                pf=round(float(gw / gl), 3) if gl > 0 else 999.0, avg_R=round(float(rs.mean()), 4))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"setup_mob_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)

    acc = {"A_pullback": {"R": [], "yr": {}}, "B_sweep": {"R": [], "yr": {}}, "baseline_trend": {"R": []}}
    per_pair = {}
    for p in PAIRS:
        df = pd.read_parquet(DATA_V2 / f"{p}_5m.parquet")
        st = classify_market_state(df)
        c = df["close"]; e20 = ema(c, 20)
        a = atr_fn(df["high"], df["low"], df["close"], 14).values
        o, hi, lo, cl = df["open"].values, df["high"].values, df["low"].values, c.values
        longR = barrier_R(o, hi, lo, cl, a, "long") - (SPREAD_PIP * pip_size(p)) / np.where(a > 0, a, np.nan)
        shortR = barrier_R(o, hi, lo, cl, a, "short") - (SPREAD_PIP * pip_size(p)) / np.where(a > 0, a, np.nan)
        state = st["state"].values; ny = st["in_ny"].values; year = df.index.year.values
        e = e20.values
        sw_lo = confirmed_swing(df["low"], kind="low").values
        sw_hi = confirmed_swing(df["high"], kind="high").values

        pulled_below = pd.Series(lo <= e).rolling(PULLBACK_K).max().fillna(0).values.astype(bool)  # touched/below EMA20 in last K
        pulled_above = pd.Series(hi >= e).rolling(PULLBACK_K).max().fillna(0).values.astype(bool)
        prev_c = np.r_[np.nan, cl[:-1]]

        # Setup A: pullback-continuation (confirmed-bar reclaim)
        A_long = (state == TREND_UP) & ny & pulled_below & (cl > e) & (cl > prev_c)
        A_short = (state == TREND_DOWN) & ny & pulled_above & (cl < e) & (cl < prev_c)
        # Setup B: liquidity-sweep reversal (sweep confirmed swing then reclaim close)
        B_long = ny & np.isfinite(sw_lo) & (lo < sw_lo) & (cl > sw_lo)
        B_short = ny & np.isfinite(sw_hi) & (hi > sw_hi) & (cl < sw_hi)
        # baseline (state-aligned every NY trend bar)
        base = np.concatenate([longR[(state == TREND_UP) & ny], shortR[(state == TREND_DOWN) & ny]])

        A_R = np.concatenate([longR[A_long], shortR[A_short]])
        B_R = np.concatenate([longR[B_long], shortR[B_short]])
        acc["A_pullback"]["R"].append(A_R); acc["B_sweep"]["R"].append(B_R); acc["baseline_trend"]["R"].append(base)
        # per-year (setup A & B)
        for name, lmask, smask in [("A_pullback", A_long, A_short), ("B_sweep", B_long, B_short)]:
            for y in np.unique(year):
                ry = np.concatenate([longR[lmask & (year == y)], shortR[smask & (year == y)]])
                acc[name]["yr"].setdefault(int(y), []).append(ry)

        days = max(1, (df.index[-1] - df.index[0]).days)
        per_pair[p] = dict(
            A=pf_wr(A_R), A_trades_day=round(np.isfinite(A_R).sum() / days, 2),
            B=pf_wr(B_R), B_trades_day=round(np.isfinite(B_R).sum() / days, 2))

    print("=== MAKE-OR-BREAK: structural setups vs 'every-bar' baseline (Tier-1, net@1.0pip) ===")
    res = {}
    for name in ("baseline_trend", "A_pullback", "B_sweep"):
        allR = np.concatenate(acc[name]["R"])
        d = pf_wr(allR); res[name] = d
        if d:
            extra = ""
            if name in ("A_pullback", "B_sweep"):
                yrpf = {y: (pf_wr(np.concatenate(v)) or {}).get("pf") for y, v in sorted(acc[name]["yr"].items())}
                extra = f"  per-year PF: {yrpf}"
            print(f"  {name:16s} PF {d['pf']:>5.2f}  WR {d['wr']:.2f}  avgR {d['avg_R']:+.4f}  n {d['n']:>6d}{extra}")

    print("\n=== per pair (trades/day across all bars; NY-gated setups) ===")
    for p in PAIRS:
        pp = per_pair[p]
        a, b = pp["A"], pp["B"]
        print(f"  {p}: A pullback PF {a['pf'] if a else 'na':>4} ({pp['A_trades_day']}/d)  | B sweep PF {b['pf'] if b else 'na':>4} ({pp['B_trades_day']}/d)")

    (OUT / "setup_mob.json").write_text(json.dumps(dict(pooled=res, per_pair=per_pair), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
