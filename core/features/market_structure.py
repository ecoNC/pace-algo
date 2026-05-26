"""
Smart Money Concepts (SMC) market-structure features.

All features are ATR-normalized or boolean. No hardcoded prices. No look-ahead.

Components:
  - Swing High/Low detection (parameter: swing_length)
  - Liquidity Sweeps (stop-hunt patterns)
  - Equal Highs/Lows (liquidity pools)
  - Strict BOS / CHoCH (trend continuation vs. reversal)
  - Fair Value Gaps (FVG, 3-candle imbalances)

Note: These features focus on PRICE-ACTION STRUCTURE. They are
deliberately additive to the existing trend/momentum/volatility features
so SHAP can distinguish their incremental contribution.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# SWING DETECTION — confirmed swings only (no look-ahead)
# ---------------------------------------------------------------------------

def confirmed_swing_highs(h: np.ndarray, length: int = 5) -> np.ndarray:
    """
    For each bar t, return the LAST CONFIRMED swing high known by time t.
    A swing high at bar k is confirmed at bar k+length when no higher high
    appears in the [k-length, k+length] window centered on k.

    Returns array of confirmed swing high VALUES at each bar (forward-filled).
    Bars before the first confirmed swing high are NaN.
    """
    n = len(h)
    out = np.full(n, np.nan)
    last_value = np.nan
    for t in range(length, n - length):
        center = h[t]
        is_swing = True
        for k in range(t - length, t + length + 1):
            if k != t and h[k] >= center:
                is_swing = False
                break
        if is_swing:
            last_value = center
        # We only "know" this swing high at bar t+length (forward confirmation)
        # So fill out[t+length] forward
    # Forward-only fill: rebuild correctly
    out2 = np.full(n, np.nan)
    last = np.nan
    for t in range(n):
        # Check if bar (t-length) is a confirmed swing high known at time t
        k = t - length
        if length <= k <= n - 1 - length:
            center = h[k]
            is_swing = True
            for j in range(max(0, k - length), min(n, k + length + 1)):
                if j != k and h[j] > center:
                    is_swing = False
                    break
                # Use > (strict) so plateaus don't double-count
            if is_swing:
                last = center
        out2[t] = last
    return out2


def confirmed_swing_lows(l: np.ndarray, length: int = 5) -> np.ndarray:
    """Mirror of confirmed_swing_highs for lows."""
    n = len(l)
    out = np.full(n, np.nan)
    last = np.nan
    for t in range(n):
        k = t - length
        if length <= k <= n - 1 - length:
            center = l[k]
            is_swing = True
            for j in range(max(0, k - length), min(n, k + length + 1)):
                if j != k and l[j] < center:
                    is_swing = False
                    break
            if is_swing:
                last = center
        out[t] = last
    return out


# ---------------------------------------------------------------------------
# LIQUIDITY SWEEP DETECTION
# ---------------------------------------------------------------------------

def detect_sweep_up(h: np.ndarray, c: np.ndarray, swing_high: np.ndarray,
                     close_back_within: int = 3) -> np.ndarray:
    """
    Sweep-up signal: bar broke above the prior swing high then closed BELOW it
    within `close_back_within` bars. Returns array of bar offsets (0 = sweep
    happened this bar, 1 = 1 bar ago, etc.) or NaN if no recent sweep.
    """
    n = len(h)
    out = np.full(n, np.nan)
    for t in range(n):
        if np.isnan(swing_high[t]):
            continue
        # Look back up to close_back_within+1 bars for a sweep
        for offset in range(close_back_within + 1):
            k = t - offset
            if k < 1:
                break
            # The swing high known at bar k-1 (BEFORE the sweep candle)
            prev_swing = swing_high[k - 1]
            if np.isnan(prev_swing):
                continue
            if h[k] > prev_swing and c[k] < prev_swing:
                out[t] = float(offset)
                break
    return out


def detect_sweep_down(l: np.ndarray, c: np.ndarray, swing_low: np.ndarray,
                       close_back_within: int = 3) -> np.ndarray:
    """Mirror of detect_sweep_up."""
    n = len(l)
    out = np.full(n, np.nan)
    for t in range(n):
        if np.isnan(swing_low[t]):
            continue
        for offset in range(close_back_within + 1):
            k = t - offset
            if k < 1:
                break
            prev_swing = swing_low[k - 1]
            if np.isnan(prev_swing):
                continue
            if l[k] < prev_swing and c[k] > prev_swing:
                out[t] = float(offset)
                break
    return out


# ---------------------------------------------------------------------------
# EQUAL HIGHS / LOWS (liquidity pools)
# ---------------------------------------------------------------------------

def equal_highs(swing_high: np.ndarray, atr: np.ndarray,
                  tol_atr: float = 0.3, lookback_swings: int = 5) -> np.ndarray:
    """
    Returns 1.0 if current swing high is within `tol_atr` ATRs of a previous
    swing high (within last `lookback_swings` distinct swing values), else 0.0.
    NaN if not enough data.
    """
    n = len(swing_high)
    out = np.full(n, np.nan)
    # Build distinct swing high history
    history = []
    last_sh = np.nan
    for t in range(n):
        sh = swing_high[t]
        if np.isnan(sh):
            out[t] = 0.0
            continue
        if not np.isnan(last_sh) and sh != last_sh:
            history.append(last_sh)
            if len(history) > lookback_swings:
                history.pop(0)
        last_sh = sh
        if np.isnan(atr[t]) or atr[t] <= 0:
            out[t] = 0.0
            continue
        threshold = tol_atr * atr[t]
        has_equal = False
        for prev_sh in history:
            if abs(sh - prev_sh) <= threshold:
                has_equal = True
                break
        out[t] = 1.0 if has_equal else 0.0
    return out


def equal_lows(swing_low: np.ndarray, atr: np.ndarray,
                tol_atr: float = 0.3, lookback_swings: int = 5) -> np.ndarray:
    """Mirror of equal_highs."""
    n = len(swing_low)
    out = np.full(n, np.nan)
    history = []
    last_sl = np.nan
    for t in range(n):
        sl = swing_low[t]
        if np.isnan(sl):
            out[t] = 0.0
            continue
        if not np.isnan(last_sl) and sl != last_sl:
            history.append(last_sl)
            if len(history) > lookback_swings:
                history.pop(0)
        last_sl = sl
        if np.isnan(atr[t]) or atr[t] <= 0:
            out[t] = 0.0
            continue
        threshold = tol_atr * atr[t]
        has_equal = False
        for prev_sl in history:
            if abs(sl - prev_sl) <= threshold:
                has_equal = True
                break
        out[t] = 1.0 if has_equal else 0.0
    return out


# ---------------------------------------------------------------------------
# STRICT BOS / CHoCH
# ---------------------------------------------------------------------------

def strict_bos_choch(c: np.ndarray, swing_high: np.ndarray, swing_low: np.ndarray,
                       ema_alignment: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    BOS = trend continuation (close > prev swing high AND uptrend, or mirror).
    CHoCH = trend reversal (close < prev swing low BUT was uptrend).

    Returns (bos_up, bos_down, choch_to_down, choch_to_up).
    """
    n = len(c)
    bos_up = np.zeros(n)
    bos_down = np.zeros(n)
    choch_dn = np.zeros(n)
    choch_up = np.zeros(n)
    for t in range(1, n):
        sh = swing_high[t - 1]
        sl = swing_low[t - 1]
        align = ema_alignment[t]
        # BOS up: bull alignment + breach prev swing high
        if not np.isnan(sh) and c[t] > sh:
            if align == 1:
                bos_up[t] = 1.0
            elif align == -1:
                choch_up[t] = 1.0
        # BOS down: bear alignment + breach prev swing low
        if not np.isnan(sl) and c[t] < sl:
            if align == -1:
                bos_down[t] = 1.0
            elif align == 1:
                choch_dn[t] = 1.0
    return bos_up, bos_down, choch_dn, choch_up


# ---------------------------------------------------------------------------
# FAIR VALUE GAPS (FVG)
# ---------------------------------------------------------------------------

def detect_fvg(h: np.ndarray, l: np.ndarray, c: np.ndarray, atr: np.ndarray,
                min_size_atr: float = 0.1,
                lookback: int = 20) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    3-candle pattern detection:
      Bullish FVG at bar k: candle[k-2].high < candle[k].low (and gap > min_size_atr * atr[k])
        -> gap zone is [candle[k-2].high, candle[k].low]
      Bearish FVG at bar k: candle[k-2].low > candle[k].high

    For each bar t, returns:
      bull_active (1.0 if any unfilled bullish FVG in last `lookback` bars)
      bear_active
      dist_to_bull_fvg_atr (close to lower edge of nearest unfilled bullish FVG above? signed)
      dist_to_bear_fvg_atr
      bull_fvg_size_atr (size of nearest unfilled bullish FVG)
      bear_fvg_size_atr
    """
    n = len(h)
    bull_active = np.zeros(n)
    bear_active = np.zeros(n)
    dist_bull = np.full(n, np.nan)
    dist_bear = np.full(n, np.nan)
    size_bull = np.full(n, np.nan)
    size_bear = np.full(n, np.nan)

    # Track active (unfilled) FVGs
    # Each entry: (created_bar, lower, upper, size, is_bullish)
    active_fvgs: list[tuple[int, float, float, float, bool]] = []

    for t in range(2, n):
        if np.isnan(atr[t]) or atr[t] <= 0:
            continue

        # New FVG candidate at bar t (using bars t-2, t-1, t)
        # Bullish: h[t-2] < l[t]
        if h[t - 2] < l[t]:
            gap = l[t] - h[t - 2]
            if gap > min_size_atr * atr[t]:
                active_fvgs.append((t, h[t - 2], l[t], gap, True))
        # Bearish: l[t-2] > h[t]
        if l[t - 2] > h[t]:
            gap = l[t - 2] - h[t]
            if gap > min_size_atr * atr[t]:
                active_fvgs.append((t, h[t], l[t - 2], gap, False))

        # Filter out filled or expired FVGs
        kept = []
        for created, lo, hi, sz, is_bull in active_fvgs:
            if t - created > lookback:
                continue  # expired
            # Is this FVG still unfilled?
            # Bullish FVG is filled when low <= bottom-of-gap (price came back into gap)
            # Bearish FVG is filled when high >= top-of-gap
            if is_bull and l[t] <= lo:
                continue
            if (not is_bull) and h[t] >= hi:
                continue
            kept.append((created, lo, hi, sz, is_bull))
        active_fvgs = kept

        # Compute features
        bull_fvgs = [x for x in active_fvgs if x[4]]
        bear_fvgs = [x for x in active_fvgs if not x[4]]

        if bull_fvgs:
            bull_active[t] = 1.0
            # Nearest bullish FVG to current close
            nearest = min(bull_fvgs, key=lambda x: abs(c[t] - (x[1] + x[2]) / 2))
            dist_bull[t] = (c[t] - (nearest[1] + nearest[2]) / 2) / atr[t]
            size_bull[t] = nearest[3] / atr[t]
        if bear_fvgs:
            bear_active[t] = 1.0
            nearest = min(bear_fvgs, key=lambda x: abs(c[t] - (x[1] + x[2]) / 2))
            dist_bear[t] = (c[t] - (nearest[1] + nearest[2]) / 2) / atr[t]
            size_bear[t] = nearest[3] / atr[t]

    return bull_active, bear_active, dist_bull, dist_bear, size_bull, size_bear


# ---------------------------------------------------------------------------
# COMBINED COMPUTATION
# ---------------------------------------------------------------------------

def compute_smc_features(ohlcv: pd.DataFrame, atr_series: np.ndarray,
                          ema_alignment_series: np.ndarray,
                          swing_length: int = 5) -> pd.DataFrame:
    """
    Compute all SMC features in one pass.

    Args:
        ohlcv: DataFrame with [open, high, low, close, volume] and DatetimeIndex
        atr_series: ATR array aligned to ohlcv (typically atr14 from engineer.py)
        ema_alignment_series: +1/0/-1 trend alignment array
        swing_length: pivot length for swing detection (default 5 = swing point if
                       no higher high/lower low in 5 bars either side)

    Returns DataFrame indexed identically with new SMC features.
    """
    h = ohlcv["high"].values
    l = ohlcv["low"].values
    c = ohlcv["close"].values

    # Confirmed swings
    sh = confirmed_swing_highs(h, length=swing_length)
    sl = confirmed_swing_lows(l, length=swing_length)

    # Sweeps
    sweep_up = detect_sweep_up(h, c, sh)
    sweep_down = detect_sweep_down(l, c, sl)

    # Equal H/L
    eqh = equal_highs(sh, atr_series)
    eql = equal_lows(sl, atr_series)

    # BOS / CHoCH
    bos_up, bos_down, choch_dn, choch_up = strict_bos_choch(c, sh, sl, ema_alignment_series)

    # FVGs
    bull_act, bear_act, dist_bull, dist_bear, size_bull, size_bear = detect_fvg(
        h, l, c, atr_series, min_size_atr=0.1, lookback=20
    )

    # Distances of confirmed swings to current close, ATR-normalized
    safe_atr = np.where(atr_series > 0, atr_series, np.nan)
    dist_to_sh_atr = (sh - c) / safe_atr  # positive = swing high above current close
    dist_to_sl_atr = (c - sl) / safe_atr  # positive = current close above swing low

    out = pd.DataFrame({
        # Liquidity sweep features
        "sweep_up_recent": (~np.isnan(sweep_up)).astype(float),
        "sweep_down_recent": (~np.isnan(sweep_down)).astype(float),
        "bars_since_sweep_up": np.where(np.isnan(sweep_up), 99.0, sweep_up),
        "bars_since_sweep_down": np.where(np.isnan(sweep_down), 99.0, sweep_down),
        # Equal H/L (liquidity pools)
        "eqhigh_present": eqh,
        "eqlow_present": eql,
        # Distances to confirmed swings
        "dist_to_sh_atr_conf": dist_to_sh_atr,
        "dist_to_sl_atr_conf": dist_to_sl_atr,
        # Strict BOS / CHoCH
        "bos_up_strict": bos_up,
        "bos_down_strict": bos_down,
        "choch_to_down": choch_dn,
        "choch_to_up": choch_up,
        # FVG features
        "fvg_bull_active": bull_act,
        "fvg_bear_active": bear_act,
        "dist_to_bull_fvg_atr": dist_bull,
        "dist_to_bear_fvg_atr": dist_bear,
        "fvg_bull_size_atr": size_bull,
        "fvg_bear_size_atr": size_bear,
    }, index=ohlcv.index)

    return out
