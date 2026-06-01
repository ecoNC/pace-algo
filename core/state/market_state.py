"""
Market State Engine (PaceAlgo V2) — deterministic regime classifier.

The CORE of the state-driven system. Maps closed-bar OHLCV to a small set of
discrete, explainable market states. NO ML, NO lookahead, NO repaint.

Guarantees (enforced by tests/test_market_state.py):
  * No lookahead: state at bar t is a pure function of data[:t+1]. Appending
    future bars never changes a past state.
  * Deterministic: same input -> same output, every run.
  * Explainable: every state is a transparent threshold on EMA/ADX/ATR-percentile.

Two orthogonal axes -> one discrete state:
  Trend regime (EMA20/50/200 alignment + ADX):  TREND_UP | TREND_DOWN | RANGE
  Volatility regime (ATR percentile, 100-bar):  QUIET | NORMAL | EXPANSION | SHOCK
  -> state = SHOCK / QUIET (no-trade) else TREND_UP / TREND_DOWN / RANGE

Session (NY/London/Asia, UTC hours) is computed alongside for the Filter Layer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.features.engineer import ema, atr, adx

# trend regimes
TREND_UP = "TREND_UP"
TREND_DOWN = "TREND_DOWN"
RANGE = "RANGE"
# volatility regimes
QUIET = "QUIET"
NORMAL = "NORMAL"
EXPANSION = "EXPANSION"
SHOCK = "SHOCK"
# actionable state set (what the Setup Engine consumes)
STATES = [TREND_UP, TREND_DOWN, RANGE, QUIET, SHOCK]
TRADEABLE_STATES = {TREND_UP, TREND_DOWN, RANGE}

DEFAULT_PARAMS = dict(
    ema_fast=20, ema_mid=50, ema_slow=200,
    adx_len=14, adx_trend=20.0, adx_range=18.0,
    atr_len=14, atr_lookback=100,
    vol_quiet=0.33, vol_expansion=0.70, vol_shock=0.97,
)


def _sessions(index: pd.DatetimeIndex):
    """UTC-hour session flags (closed-bar timestamp). Naive index treated as UTC."""
    hours = index.hour.values  # tz-aware -> local-to-tz; our data is UTC
    in_ny = (hours >= 13) & (hours < 22)
    in_london = (hours >= 7) & (hours < 16)
    in_asia = (hours >= 22) | (hours < 7)
    session = np.where(in_ny, "NY", np.where(in_london, "LONDON",
                       np.where(in_asia, "ASIA", "OFF")))
    overlap = in_london & in_ny  # 13-16 UTC London/NY overlap (highest liquidity)
    return in_ny, in_london, overlap, session


def classify_market_state(ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    """
    Classify each bar's market state.

    Args:
        ohlcv: DataFrame with [open, high, low, close] (+ optional volume), DatetimeIndex (UTC).
        params: override DEFAULT_PARAMS.

    Returns:
        DataFrame (same index) with debuggable columns:
          ema_align (-1/0/+1), adx, atr_pctile (0-1),
          trend_regime, vol_regime, in_ny, in_london, ny_london_overlap, session,
          state, tradeable
        Warmup bars (insufficient history) -> state QUIET, tradeable False.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    h, l, c = ohlcv["high"], ohlcv["low"], ohlcv["close"]

    e_fast = ema(c, p["ema_fast"])
    e_mid = ema(c, p["ema_mid"])
    e_slow = ema(c, p["ema_slow"])
    ema_align = np.where((e_fast > e_mid) & (e_mid > e_slow), 1,
                np.where((e_fast < e_mid) & (e_mid < e_slow), -1, 0)).astype(float)

    adx_v = adx(h, l, c, p["adx_len"])
    atr_v = atr(h, l, c, p["atr_len"])
    # causal percentile: rank of CURRENT atr within trailing `atr_lookback` window
    atr_pctile = atr_v.rolling(p["atr_lookback"], min_periods=p["atr_lookback"]).rank(pct=True)

    adx_np = adx_v.values
    al = ema_align
    trend = np.full(len(ohlcv), RANGE, dtype=object)
    trend[(al == 1) & (adx_np >= p["adx_trend"])] = TREND_UP
    trend[(al == -1) & (adx_np >= p["adx_trend"])] = TREND_DOWN
    # everything else (adx below trend thr, or ema not aligned) stays RANGE

    pct = atr_pctile.values
    vol = np.full(len(ohlcv), NORMAL, dtype=object)
    vol[pct < p["vol_quiet"]] = QUIET
    vol[pct >= p["vol_expansion"]] = EXPANSION
    vol[pct >= p["vol_shock"]] = SHOCK

    # combined state: vol veto first (no-trade zones), else trend
    state = np.where(vol == SHOCK, SHOCK,
            np.where(vol == QUIET, QUIET, trend))
    # warmup (NaN inputs) -> QUIET (no-trade)
    warm = np.isnan(adx_np) | np.isnan(pct) | np.isnan(atr_v.values)
    state = np.where(warm, QUIET, state).astype(object)
    tradeable = np.isin(state, list(TRADEABLE_STATES))

    in_ny, in_london, overlap, session = _sessions(ohlcv.index)

    return pd.DataFrame({
        "ema_align": al,
        "adx": adx_np,
        "atr_pctile": pct,
        "trend_regime": trend,
        "vol_regime": vol,
        "in_ny": in_ny,
        "in_london": in_london,
        "ny_london_overlap": overlap,
        "session": session,
        "state": state,
        "tradeable": tradeable,
    }, index=ohlcv.index)


if __name__ == "__main__":  # quick debug/inspection on real data if present
    import sys
    from pathlib import Path
    repo = Path(__file__).parent.parent.parent
    p = repo / "data" / "processed_v2" / "GBPUSD_5m.parquet"
    if p.exists():
        df = pd.read_parquet(p)
        st = classify_market_state(df)
        print("State distribution (GBPUSD 5m):")
        print(st["state"].value_counts(normalize=True).round(3).to_string())
        print("\nTradeable share:", round(st["tradeable"].mean(), 3))
        print("NY-session share:", round(st["in_ny"].mean(), 3))
        print("Tradeable & NY share:", round((st["tradeable"] & st["in_ny"]).mean(), 3))
    else:
        print("no local data; module import OK")
