"""
Feature engineering for PaceAlgo ML.

All features are ATR-normalized or dimensionless so the model learns
universal market structure rather than asset-specific price levels.

Feature groups (~28 features total):
  - Trend (7):       EMA distances, slopes, alignment, ADX
  - Momentum (5):    RSI, StochRSI, ROC, MACD-hist normalized
  - Volatility (5):  ATR%, ATR percentile, BB width, vol compression, realized vol
  - Structure (4):   distance to swing H/L, BOS bullish/bearish
  - Volume (2):      relative volume, volume z-score
  - Session (2):     hour sin/cos (cyclical encoding)
  - HTF (3):         placeholders — populated by core.features.htf
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# BASIC INDICATORS (pandas-only, no TA-Lib dependency)
# ─────────────────────────────────────────────────────────────────────────────

def ema(s: pd.Series, length: int) -> pd.Series:
    return s.ewm(span=length, adjust=False).mean()


def sma(s: pd.Series, length: int) -> pd.Series:
    return s.rolling(window=length, min_periods=length).mean()


def true_range(h: pd.Series, l: pd.Series, c: pd.Series) -> pd.Series:
    prev_close = c.shift(1)
    return pd.concat([(h - l), (h - prev_close).abs(), (l - prev_close).abs()],
                      axis=1).max(axis=1)


def atr(h: pd.Series, l: pd.Series, c: pd.Series, length: int = 14) -> pd.Series:
    tr = true_range(h, l, c)
    return tr.ewm(alpha=1.0 / length, adjust=False).mean()


def rsi(s: pd.Series, length: int = 14) -> pd.Series:
    delta = s.diff()
    up = delta.clip(lower=0)
    dn = (-delta).clip(lower=0)
    roll_up = up.ewm(alpha=1.0 / length, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1.0 / length, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    return out.fillna(50.0)


def stoch_rsi_k(rsi_vals: pd.Series, length: int = 14) -> pd.Series:
    lo = rsi_vals.rolling(length, min_periods=length).min()
    hi = rsi_vals.rolling(length, min_periods=length).max()
    denom = (hi - lo).replace(0, np.nan)
    return ((rsi_vals - lo) / denom).clip(0, 1) * 100.0


def roc(s: pd.Series, length: int = 10) -> pd.Series:
    return (s / s.shift(length) - 1.0) * 100.0


def macd_hist(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    macd_line = ema(s, fast) - ema(s, slow)
    signal_line = ema(macd_line, signal)
    return macd_line - signal_line


def bb_width(s: pd.Series, length: int = 20, mult: float = 2.0) -> pd.Series:
    """Bollinger band width as fraction of mid-band."""
    mid = sma(s, length)
    std = s.rolling(window=length, min_periods=length).std()
    return (mult * std * 2.0) / mid.replace(0, np.nan)


def realized_vol(close: pd.Series, length: int = 20) -> pd.Series:
    """Annualized realized volatility based on log returns."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(length, min_periods=length).std() * np.sqrt(length)


def adx(h: pd.Series, l: pd.Series, c: pd.Series, length: int = 14) -> pd.Series:
    """Wilder's ADX."""
    up_move = h.diff()
    down_move = -l.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = true_range(h, l, c)
    atr_w = tr.ewm(alpha=1.0 / length, adjust=False).mean()
    plus_di = 100.0 * pd.Series(plus_dm, index=h.index).ewm(alpha=1.0 / length, adjust=False).mean() / atr_w
    minus_di = 100.0 * pd.Series(minus_dm, index=h.index).ewm(alpha=1.0 / length, adjust=False).mean() / atr_w
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1.0 / length, adjust=False).mean()


def swing_levels(h: pd.Series, l: pd.Series, lookback: int = 10) -> tuple[pd.Series, pd.Series]:
    """Most recent swing high & low within lookback window."""
    return h.rolling(window=lookback, min_periods=lookback).max(), \
           l.rolling(window=lookback, min_periods=lookback).min()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FEATURE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all features from raw OHLCV DataFrame.

    Args:
        df: DataFrame with columns [open, high, low, close, volume]
            (extra columns like 'turnover', 'trades' are ignored)
            Index must be a UTC DatetimeIndex.

    Returns:
        DataFrame indexed identically with ~28 feature columns.
        Rows with insufficient history (NaN due to lookback) are kept;
        downstream code must drop NaN before training.
    """
    if df.empty:
        return pd.DataFrame()

    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    out = pd.DataFrame(index=df.index)

    # ─── Base indicators (reused across features) ───
    atr14 = atr(h, l, c, 14)
    safe_atr = atr14.replace(0, np.nan)

    ema_20 = ema(c, 20)
    ema_50 = ema(c, 50)
    ema_200 = ema(c, 200)

    rsi_14 = rsi(c, 14)
    adx_14 = adx(h, l, c, 14)

    swing_hi, swing_lo = swing_levels(h, l, lookback=20)
    swing_hi_50, swing_lo_50 = swing_levels(h, l, lookback=50)

    # ─── TREND (7) ───
    out["ema_20_dist_atr"] = (c - ema_20) / safe_atr
    out["ema_50_dist_atr"] = (c - ema_50) / safe_atr
    out["ema_200_dist_atr"] = (c - ema_200) / safe_atr
    out["ema_20_slope_atr"] = (ema_20 - ema_20.shift(5)) / safe_atr
    out["ema_alignment"] = np.where(
        (ema_20 > ema_50) & (ema_50 > ema_200), 1.0,
        np.where((ema_20 < ema_50) & (ema_50 < ema_200), -1.0, 0.0),
    )
    out["adx_14"] = adx_14
    out["adx_slope"] = adx_14 - adx_14.shift(5)

    # ─── MOMENTUM (5) ───
    out["rsi_14"] = rsi_14
    out["stoch_rsi_k"] = stoch_rsi_k(rsi_14, 14)
    out["roc_10"] = roc(c, 10)
    out["macd_hist_atr"] = macd_hist(c, 12, 26, 9) / safe_atr
    out["momentum_composite"] = (out["rsi_14"] - 50.0) / 50.0 + np.tanh(out["macd_hist_atr"])

    # ─── VOLATILITY (5) ───
    out["atr_pct"] = atr14 / c.replace(0, np.nan)
    out["atr_percentile_100"] = atr14.rolling(100, min_periods=100).rank(pct=True)
    out["bb_width_pct"] = bb_width(c, 20, 2.0)
    bb_w_avg = out["bb_width_pct"].rolling(20, min_periods=20).mean()
    out["vol_compression"] = out["bb_width_pct"] / bb_w_avg.replace(0, np.nan)
    out["realized_vol_20"] = realized_vol(c, 20)

    # ─── STRUCTURE (4) ───
    out["dist_to_swing_high_atr"] = (swing_hi - c) / safe_atr
    out["dist_to_swing_low_atr"] = (c - swing_lo) / safe_atr
    # Break of Structure: close above prior swing high (over lookback 50)
    out["bos_bullish"] = (c > swing_hi_50.shift(1)).astype(float)
    out["bos_bearish"] = (c < swing_lo_50.shift(1)).astype(float)

    # ─── VOLUME (2) ───
    vol_avg = sma(v, 20)
    out["rvol_20"] = v / vol_avg.replace(0, np.nan)
    vol_std = v.rolling(50, min_periods=50).std()
    out["volume_z_score"] = (v - vol_avg) / vol_std.replace(0, np.nan)

    # ─── SESSION (2) — Cyclical hour encoding ───
    hours = df.index.hour + df.index.minute / 60.0
    out["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
    out["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)

    return out


def attach_macro(features: pd.DataFrame, macro_daily: pd.DataFrame) -> pd.DataFrame:
    """
    Forward-fill daily macro series into intraday feature matrix.

    Args:
        features: feature DataFrame indexed by intraday UTC timestamps
        macro_daily: daily DataFrame with columns like VIX_close, DXY_close, TNX_close

    Returns:
        features DataFrame with appended macro columns.
    """
    if macro_daily.empty:
        return features

    macro = macro_daily.copy()
    # Normalize column names: VIX_close -> vix_level etc.
    rename = {}
    for col in macro.columns:
        if col.endswith("_close"):
            rename[col] = f"{col[:-6].lower()}_level"
    macro = macro.rename(columns=rename)

    # CRITICAL: VIX/DXY/TNX from yfinance have slightly different timestamps
    # (different market hours / timezones) which creates internal NaN gaps
    # after pd.concat. We collapse to one row per calendar day and ffill each
    # series independently BEFORE computing pct_change — otherwise pct_change
    # cascades the gaps and we lose ~80% of intraday bars to NaN.
    macro.index = macro.index.normalize()  # Round all timestamps to midnight UTC
    macro = macro.groupby(macro.index).last()  # Collapse duplicates per day
    macro = macro.sort_index()
    # Now ffill each series — no more inter-ticker NaN gaps
    macro = macro.ffill()

    # Now safe to compute change features (fill_method=None silences pandas 2.x FutureWarning)
    if "vix_level" in macro.columns:
        macro["vix_chg_5d"] = macro["vix_level"].pct_change(5, fill_method=None)
    if "dxy_level" in macro.columns:
        macro["dxy_chg_5d"] = macro["dxy_level"].pct_change(5, fill_method=None)
    if "tnx_level" in macro.columns:
        macro["tnx_chg_5d"] = macro["tnx_level"].pct_change(5, fill_method=None)

    # CRITICAL: prevent look-ahead leakage. yfinance daily close is the
    # END-of-day value, not available during the trading day. A 5M bar
    # at 10:00 UTC cannot see today's macro close. Shift by 1 day so
    # today's row uses YESTERDAY's macro close (and chg_5d uses past 5
    # closed days vs today, exactly as it would be in live trading).
    macro = macro.shift(1)

    # Forward-fill onto intraday index
    macro_ff = macro.reindex(features.index.union(macro.index)).sort_index().ffill()
    macro_ff = macro_ff.reindex(features.index)
    return pd.concat([features, macro_ff], axis=1)


def attach_htf_context(features: pd.DataFrame, htf_1h: pd.DataFrame,
                         htf_4h: pd.DataFrame) -> pd.DataFrame:
    """
    Add HTF context features (1H + 4H trend/regime).

    Args:
        features: lower-TF feature DataFrame (e.g. 5M)
        htf_1h: feature DataFrame from 1H computation of same symbol
        htf_4h: feature DataFrame from 4H computation of same symbol

    Returns:
        features DataFrame with appended HTF columns.
    """
    if htf_1h is None or htf_1h.empty or htf_4h is None or htf_4h.empty:
        return features

    # Select context columns from HTF
    cols_to_propagate = ["ema_alignment", "rsi_14", "atr_percentile_100"]

    htf_1h_sub = htf_1h[[c for c in cols_to_propagate if c in htf_1h.columns]].copy()
    htf_1h_sub.columns = [f"htf_1h_{c}" for c in htf_1h_sub.columns]

    htf_4h_sub = htf_4h[[c for c in cols_to_propagate if c in htf_4h.columns]].copy()
    htf_4h_sub.columns = [f"htf_4h_{c}" for c in htf_4h_sub.columns]

    # CRITICAL no-look-ahead shift: A 1H bar indexed at 12:00 UTC contains
    # OHLCV from 12:00-13:00 — its close is only known after 13:00. Without
    # this shift, ffill would let a 5M bar at 12:35 "see" the 13:00 1H close,
    # creating massive look-ahead leakage (inflated backtest PF, useless in
    # live trading). shift(1) makes the 12:00 1H values only available from
    # the 13:00 row onward, matching how Pine Script with lookahead_off would
    # see HTF data in production.
    htf_1h_sub = htf_1h_sub.shift(1)
    htf_4h_sub = htf_4h_sub.shift(1)

    # Forward-fill onto lower-TF index
    htf_1h_ff = htf_1h_sub.reindex(features.index.union(htf_1h_sub.index)).sort_index().ffill()
    htf_1h_ff = htf_1h_ff.reindex(features.index)
    htf_4h_ff = htf_4h_sub.reindex(features.index.union(htf_4h_sub.index)).sort_index().ffill()
    htf_4h_ff = htf_4h_ff.reindex(features.index)

    return pd.concat([features, htf_1h_ff, htf_4h_ff], axis=1)
