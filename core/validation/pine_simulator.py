"""
Pine-equivalent feature computation in pure Python (no pandas magic).

Goal: write each feature computation using ONLY basic arithmetic + loops
that translate 1:1 to Pine Script. Then compare the output bit-by-bit
to the pandas-based feature pipeline. Any deviation > 1e-5 is a bug we
must fix BEFORE Pine export, otherwise OOS performance will differ.

Mirrors core/features/engineer.py logic, but uses explicit recursion
matching Pine's bar-by-bar evaluation.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# BASIC SERIES — explicit loops, no pandas .ewm()/.rolling() magic
# ---------------------------------------------------------------------------

def pine_ema(values: np.ndarray, length: int) -> np.ndarray:
    """Pine's ta.ema — alpha = 2/(N+1), seeded with first value."""
    alpha = 2.0 / (length + 1)
    out = np.full(len(values), np.nan)
    if len(values) == 0:
        return out
    out[0] = values[0]
    for t in range(1, len(values)):
        out[t] = alpha * values[t] + (1 - alpha) * out[t - 1]
    return out


def pine_rma(values: np.ndarray, length: int) -> np.ndarray:
    """Pine's Wilder/RMA smoothing — alpha = 1/N, seeded with first value."""
    alpha = 1.0 / length
    out = np.full(len(values), np.nan)
    if len(values) == 0:
        return out
    out[0] = values[0]
    for t in range(1, len(values)):
        out[t] = alpha * values[t] + (1 - alpha) * out[t - 1]
    return out


def pine_sma(values: np.ndarray, length: int) -> np.ndarray:
    """Pine's ta.sma — simple moving average."""
    out = np.full(len(values), np.nan)
    for t in range(length - 1, len(values)):
        out[t] = float(np.mean(values[t - length + 1:t + 1]))
    return out


def pine_true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Pine's ta.tr — true range."""
    out = np.full(len(h), np.nan)
    if len(h) == 0:
        return out
    out[0] = h[0] - l[0]
    for t in range(1, len(h)):
        prev_c = c[t - 1]
        out[t] = max(h[t] - l[t], abs(h[t] - prev_c), abs(l[t] - prev_c))
    return out


def pine_atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, length: int) -> np.ndarray:
    """Pine's ta.atr(length)."""
    tr = pine_true_range(h, l, c)
    return pine_rma(tr, length)


def pine_rsi(c: np.ndarray, length: int) -> np.ndarray:
    """Pine's ta.rsi(length) — Wilder's RSI."""
    out = np.full(len(c), np.nan)
    if len(c) < 2:
        return out
    up = np.zeros(len(c))
    dn = np.zeros(len(c))
    for t in range(1, len(c)):
        diff = c[t] - c[t - 1]
        if diff > 0:
            up[t] = diff
        elif diff < 0:
            dn[t] = -diff
    roll_up = pine_rma(up, length)
    roll_dn = pine_rma(dn, length)
    for t in range(len(c)):
        if roll_dn[t] is None or np.isnan(roll_dn[t]) or roll_dn[t] == 0:
            if roll_up[t] is not None and not np.isnan(roll_up[t]) and roll_up[t] > 0:
                out[t] = 100.0
            else:
                out[t] = 50.0
        else:
            rs = roll_up[t] / roll_dn[t]
            out[t] = 100.0 - 100.0 / (1.0 + rs)
    return out


def pine_stoch_rsi_k(rsi_values: np.ndarray, length: int) -> np.ndarray:
    """StochRSI %K calculation."""
    out = np.full(len(rsi_values), np.nan)
    for t in range(length - 1, len(rsi_values)):
        window = rsi_values[t - length + 1:t + 1]
        lo = float(np.nanmin(window))
        hi = float(np.nanmax(window))
        if hi - lo > 0:
            out[t] = max(0.0, min(1.0, (rsi_values[t] - lo) / (hi - lo))) * 100.0
        else:
            out[t] = np.nan
    return out


def pine_roc(c: np.ndarray, length: int) -> np.ndarray:
    """Rate of Change."""
    out = np.full(len(c), np.nan)
    for t in range(length, len(c)):
        prev = c[t - length]
        if prev != 0:
            out[t] = (c[t] / prev - 1.0) * 100.0
    return out


def pine_macd_hist(c: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> np.ndarray:
    """MACD histogram."""
    macd_line = pine_ema(c, fast) - pine_ema(c, slow)
    signal_line = pine_ema(macd_line, signal)
    return macd_line - signal_line


def pine_adx(h: np.ndarray, l: np.ndarray, c: np.ndarray, length: int) -> np.ndarray:
    """ADX as Pine's ta.dmi(adx component)."""
    up_move = np.zeros(len(h))
    down_move = np.zeros(len(h))
    plus_dm = np.zeros(len(h))
    minus_dm = np.zeros(len(h))
    for t in range(1, len(h)):
        up_move[t] = h[t] - h[t - 1]
        down_move[t] = l[t - 1] - l[t]
        if up_move[t] > down_move[t] and up_move[t] > 0:
            plus_dm[t] = up_move[t]
        if down_move[t] > up_move[t] and down_move[t] > 0:
            minus_dm[t] = down_move[t]
    tr = pine_true_range(h, l, c)
    atr_w = pine_rma(tr, length)
    plus_di = 100.0 * pine_rma(plus_dm, length) / atr_w
    minus_di = 100.0 * pine_rma(minus_dm, length) / atr_w
    dx = np.full(len(h), np.nan)
    for t in range(len(h)):
        denom = plus_di[t] + minus_di[t]
        if denom > 0:
            dx[t] = 100.0 * abs(plus_di[t] - minus_di[t]) / denom
    return pine_rma(dx, length)


def pine_rolling_max(values: np.ndarray, length: int) -> np.ndarray:
    """Pine's ta.highest(length)."""
    out = np.full(len(values), np.nan)
    for t in range(length - 1, len(values)):
        out[t] = float(np.nanmax(values[t - length + 1:t + 1]))
    return out


def pine_rolling_min(values: np.ndarray, length: int) -> np.ndarray:
    """Pine's ta.lowest(length)."""
    out = np.full(len(values), np.nan)
    for t in range(length - 1, len(values)):
        out[t] = float(np.nanmin(values[t - length + 1:t + 1]))
    return out


def pine_bb_width_pct(c: np.ndarray, length: int, mult: float = 2.0) -> np.ndarray:
    """Bollinger band width as fraction of mid-band."""
    mid = pine_sma(c, length)
    std = np.full(len(c), np.nan)
    for t in range(length - 1, len(c)):
        std[t] = float(np.std(c[t - length + 1:t + 1], ddof=1))
    out = np.full(len(c), np.nan)
    for t in range(len(c)):
        if mid[t] is not None and not np.isnan(mid[t]) and mid[t] != 0:
            out[t] = (mult * std[t] * 2.0) / mid[t]
    return out


def pine_atr_percentile(atr_values: np.ndarray, length: int = 100) -> np.ndarray:
    """Rolling rank as percentile (0-1) of current ATR within last `length` bars."""
    out = np.full(len(atr_values), np.nan)
    for t in range(length - 1, len(atr_values)):
        window = atr_values[t - length + 1:t + 1]
        valid = window[~np.isnan(window)]
        if len(valid) > 0:
            current = atr_values[t]
            if not np.isnan(current):
                out[t] = float((valid <= current).sum()) / len(valid)
    return out


def pine_realized_vol(c: np.ndarray, length: int) -> np.ndarray:
    """Annualized realized vol based on log returns."""
    log_ret = np.full(len(c), np.nan)
    for t in range(1, len(c)):
        if c[t - 1] > 0:
            log_ret[t] = math.log(c[t] / c[t - 1])
    out = np.full(len(c), np.nan)
    for t in range(length, len(c)):
        window = log_ret[t - length + 1:t + 1]
        valid = window[~np.isnan(window)]
        if len(valid) >= length // 2:
            out[t] = float(np.std(valid, ddof=1)) * math.sqrt(length)
    return out


# ---------------------------------------------------------------------------
# FULL FEATURE COMPUTATION — Pine-equivalent
# ---------------------------------------------------------------------------

def compute_features_pine(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the 15 SHAP-Top features using Pine-equivalent recursive math.

    Returns DataFrame indexed identically to input, with the 15 feature columns.
    """
    o = ohlcv["open"].values
    h = ohlcv["high"].values
    l = ohlcv["low"].values
    c = ohlcv["close"].values
    v = ohlcv["volume"].values

    atr14 = pine_atr(h, l, c, 14)
    safe_atr = np.where(atr14 > 0, atr14, np.nan)

    ema20 = pine_ema(c, 20)
    rsi14 = pine_rsi(c, 14)
    adx14 = pine_adx(h, l, c, 14)

    swing_lo = pine_rolling_min(l, 20)
    swing_hi = pine_rolling_max(h, 20)

    # Compute features
    feats = {}

    # 1. hour_sin / 2. hour_cos
    hours = np.array([t.hour + t.minute / 60.0 for t in ohlcv.index])
    feats['hour_sin'] = np.sin(2 * math.pi * hours / 24.0)
    feats['hour_cos'] = np.cos(2 * math.pi * hours / 24.0)

    # 3. dist_to_swing_low_atr / 4. dist_to_swing_high_atr
    feats['dist_to_swing_low_atr'] = (c - swing_lo) / safe_atr
    feats['dist_to_swing_high_atr'] = (swing_hi - c) / safe_atr

    # 5. realized_vol_20
    feats['realized_vol_20'] = pine_realized_vol(c, 20)

    # 6. atr_percentile_100
    feats['atr_percentile_100'] = pine_atr_percentile(atr14, 100)

    # 7. atr_pct = atr / close
    feats['atr_pct'] = atr14 / np.where(c > 0, c, np.nan)

    # 8. volume_z_score
    vol_avg = pine_sma(v, 20)
    vol_std = np.full(len(v), np.nan)
    for t in range(50 - 1, len(v)):
        vol_std[t] = float(np.std(v[t - 50 + 1:t + 1], ddof=1))
    feats['volume_z_score'] = (v - vol_avg) / np.where(vol_std > 0, vol_std, np.nan)

    # 9. ema_20_slope_atr = (ema20 - ema20[5]) / atr
    ema20_lag = np.concatenate([np.full(5, np.nan), ema20[:-5]])
    feats['ema_20_slope_atr'] = (ema20 - ema20_lag) / safe_atr

    # 10. momentum_composite = (rsi-50)/50 + tanh(macd_hist_atr)
    macd_hist = pine_macd_hist(c)
    macd_hist_atr = macd_hist / safe_atr
    feats['momentum_composite'] = (rsi14 - 50.0) / 50.0 + np.tanh(macd_hist_atr)

    # 11. rvol_20 = volume / sma(volume, 20)
    feats['rvol_20'] = v / np.where(vol_avg > 0, vol_avg, np.nan)

    # 12. adx_14
    feats['adx_14'] = adx14

    # 13. ema_20_dist_atr = (close - ema20) / atr
    feats['ema_20_dist_atr'] = (c - ema20) / safe_atr

    # 14. htf_1h_rsi_14 — placeholder, requires HTF (1H) data
    feats['htf_1h_rsi_14'] = np.full(len(c), np.nan)

    # 15. htf_1h_atr_percentile_100 — same
    feats['htf_1h_atr_percentile_100'] = np.full(len(c), np.nan)

    return pd.DataFrame(feats, index=ohlcv.index)


# ---------------------------------------------------------------------------
# TREE TRAVERSAL — exactly mirrors what Pine code will do
# ---------------------------------------------------------------------------

def evaluate_tree(tree_struct: dict, feature_values: np.ndarray, feature_to_idx: dict) -> float:
    """Recursively traverse one LightGBM tree."""
    node = tree_struct
    while 'split_feature' in node:
        feat_idx = node['split_feature']
        threshold = node['threshold']
        decision = node.get('decision_type', '<=')
        val = feature_values[feat_idx]
        if np.isnan(val):
            # LightGBM default: NaN goes left (or right, depending on setting)
            # We follow LightGBM's `default_left` flag
            if node.get('default_left', True):
                node = node['left_child']
            else:
                node = node['right_child']
            continue
        if decision == '<=':
            go_left = val <= threshold
        else:
            go_left = val < threshold
        node = node['left_child'] if go_left else node['right_child']
    return node['leaf_value']


def predict_forest_manual(model_dump: dict, features_matrix: np.ndarray) -> np.ndarray:
    """
    Manually traverse all trees, sum leaves, apply sigmoid.
    This mirrors EXACTLY what the Pine code will compute.

    Args:
        model_dump: lightgbm Booster.dump_model() output
        features_matrix: shape (N_samples, N_features), columns aligned to feature_names

    Returns:
        Probabilities, shape (N_samples,)
    """
    feature_names = model_dump['feature_names']
    feature_to_idx = {name: i for i, name in enumerate(feature_names)}
    trees = model_dump['tree_info']

    n_samples = features_matrix.shape[0]
    probas = np.zeros(n_samples)

    for sample_idx in range(n_samples):
        feat_vals = features_matrix[sample_idx]
        raw_score = 0.0
        for tree in trees:
            raw_score += evaluate_tree(tree['tree_structure'], feat_vals, feature_to_idx)
        # Sigmoid
        probas[sample_idx] = 1.0 / (1.0 + math.exp(-raw_score))

    return probas
