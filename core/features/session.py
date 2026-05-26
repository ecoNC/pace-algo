"""
Session & Timing features.

All timestamps in UTC. Session windows reflect typical FX market liquidity:
  - Asia/Tokyo:   23:00 - 08:00 UTC
  - London:       08:00 - 17:00 UTC
  - New York:     13:00 - 22:00 UTC
  - London/NY overlap (killzone):  13:00 - 17:00 UTC  (highest liquidity)
  - Asia/London overlap:           08:00 - 09:00 UTC

Volatility-expansion features measure ATR vs its rolling baseline to detect
markets transitioning from quiet to active regimes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# SESSION FLAGS (boolean per bar)
# ---------------------------------------------------------------------------

def session_flags(index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Compute session boolean flags from UTC timestamps.

    Returns DataFrame with columns:
      - in_asia: 23:00-08:00 UTC
      - in_london: 08:00-17:00 UTC
      - in_ny: 13:00-22:00 UTC
      - in_london_ny_killzone: 13:00-17:00 UTC (overlap, peak liquidity)
      - in_asia_london_overlap: 08:00-09:00 UTC
      - in_us_open_killzone: 13:30-15:30 UTC (US session open volatility)
      - in_london_open_killzone: 08:00-10:00 UTC (London open volatility)
      - is_weekend_session: Sun 22:00 - Fri 22:00 (FX market hours flag)
    """
    hours = index.hour + index.minute / 60.0  # fractional hour 0-23.99
    dow = index.dayofweek  # 0=Mon, 6=Sun

    in_asia = ((hours >= 23) | (hours < 8))
    in_london = ((hours >= 8) & (hours < 17))
    in_ny = ((hours >= 13) & (hours < 22))
    in_killzone_ldn_ny = ((hours >= 13) & (hours < 17))
    in_asia_ldn_overlap = ((hours >= 8) & (hours < 9))
    in_us_open_kz = ((hours >= 13.5) & (hours < 15.5))
    in_ldn_open_kz = ((hours >= 8) & (hours < 10))

    # FX market hours: Sun 22:00 UTC to Fri 22:00 UTC
    fx_open = (
        ((dow == 6) & (hours >= 22)) |   # Sun >= 22:00
        ((dow >= 0) & (dow <= 4)) |       # Mon-Fri all day
        ((dow == 5) & (hours < 22))       # Sat impossible (would be Fri close)
    )
    # Note: dayofweek 5=Saturday — FX is closed Saturday entirely
    # Friday close = Fri 22:00 UTC ≈ NY close

    return pd.DataFrame({
        "in_asia": in_asia.astype(float),
        "in_london": in_london.astype(float),
        "in_ny": in_ny.astype(float),
        "in_london_ny_killzone": in_killzone_ldn_ny.astype(float),
        "in_asia_london_overlap": in_asia_ldn_overlap.astype(float),
        "in_us_open_killzone": in_us_open_kz.astype(float),
        "in_london_open_killzone": in_ldn_open_kz.astype(float),
        "is_fx_market_open": fx_open.astype(float),
    }, index=index)


# ---------------------------------------------------------------------------
# VOLATILITY EXPANSION DETECTION
# ---------------------------------------------------------------------------

def vol_expansion_features(atr_series: np.ndarray, lookback: int = 50) -> pd.DataFrame:
    """
    Detect markets transitioning between quiet and volatile regimes.

    Returns:
      - vol_expansion_ratio: current_atr / rolling_avg_atr(lookback)
        > 1.5 = expansion regime, < 0.7 = compression
      - vol_expanding: ratio > 1.2 (binary)
      - vol_contracting: ratio < 0.8 (binary)
      - bars_since_vol_spike: bars since last expansion event (>1.5x ratio)
    """
    n = len(atr_series)
    ratio = np.full(n, np.nan)
    avg = np.full(n, np.nan)

    for t in range(lookback - 1, n):
        window = atr_series[t - lookback + 1:t + 1]
        valid = window[~np.isnan(window)]
        if len(valid) > 0:
            avg[t] = float(np.mean(valid))
            if avg[t] > 0 and not np.isnan(atr_series[t]):
                ratio[t] = atr_series[t] / avg[t]

    expanding = (ratio > 1.2).astype(float)
    contracting = (ratio < 0.8).astype(float)

    # Bars since last vol spike (>1.5x ratio)
    bars_since = np.full(n, np.nan)
    last_spike_bar = -999
    for t in range(n):
        if not np.isnan(ratio[t]) and ratio[t] > 1.5:
            last_spike_bar = t
        if last_spike_bar >= 0:
            bars_since[t] = t - last_spike_bar
        else:
            bars_since[t] = 99.0  # never spiked

    return pd.DataFrame({
        "vol_expansion_ratio": ratio,
        "vol_expanding": expanding,
        "vol_contracting": contracting,
        "bars_since_vol_spike": np.clip(bars_since, 0, 99),
    })


# ---------------------------------------------------------------------------
# COMBINED COMPUTATION
# ---------------------------------------------------------------------------

def compute_session_features(ohlcv: pd.DataFrame, atr_series: np.ndarray) -> pd.DataFrame:
    """
    Compute all session + timing features.

    Args:
        ohlcv: DataFrame with DatetimeIndex (UTC)
        atr_series: ATR aligned to ohlcv

    Returns:
        DataFrame with session flags + vol expansion features
    """
    session_df = session_flags(ohlcv.index)
    vol_df = vol_expansion_features(atr_series)
    vol_df.index = ohlcv.index
    return pd.concat([session_df, vol_df], axis=1)
