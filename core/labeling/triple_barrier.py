"""
Triple Barrier Labeling — Marcos López de Prado method.

For each bar t, define three barriers from the entry price:
  - Upper (Take Profit): entry + tp_R * sl_atr_mult * ATR(t)
  - Lower (Stop Loss):   entry - sl_atr_mult * ATR(t)
  - Time:                t + time_barrier_bars

Label assigned based on which barrier price hits first:
  - +1 : Upper hit first (LONG would have won)
  - -1 : Lower hit first (LONG would have lost)
  -  0 : Time barrier hit (no clear move = neutral)

Labels are LONG-perspective. SHORT setups are inferred by negation in
training pipeline if needed.

The R multiplier (TP distance / SL distance) is critical:
  - R=1.5 → more wins (TP closer), lower expected value per winning trade
  - R=2.5 → fewer wins, higher expected value per winning trade

We compute labels for several R values and select per asset cluster.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..features.engineer import atr


def compute_triple_barrier_labels(
    ohlcv: pd.DataFrame,
    tp_R: float = 1.5,
    sl_atr_mult: float = 1.0,
    time_barrier_bars: int = 24,
    atr_length: int = 14,
) -> pd.DataFrame:
    """
    Vectorized triple barrier labeler.

    Args:
        ohlcv: DataFrame with [open, high, low, close] and DatetimeIndex
        tp_R: TP distance as multiple of SL distance (e.g. 1.5 = TP is 1.5x SL)
        sl_atr_mult: SL distance in ATR multiples (e.g. 1.0 = SL is 1 ATR below entry)
        time_barrier_bars: max bars to wait for TP or SL before assigning label 0
        atr_length: ATR period for volatility-normalized barriers

    Returns:
        DataFrame indexed identically to ohlcv with columns:
          - label: -1, 0, or +1
          - entry_price: close[t]
          - tp_price, sl_price: barrier levels
          - hit_bar_offset: how many bars later the label was determined (0..time_barrier_bars)
          - hit_type: 'tp', 'sl', 'time'
    """
    if ohlcv.empty:
        return pd.DataFrame()

    o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
    atr_series = atr(h, l, c, atr_length).values
    close_arr = c.values
    high_arr = h.values
    low_arr = l.values
    n = len(ohlcv)

    label = np.full(n, np.nan)
    entry = np.full(n, np.nan)
    tp_price = np.full(n, np.nan)
    sl_price = np.full(n, np.nan)
    hit_offset = np.full(n, -1, dtype=np.int32)
    hit_type = np.full(n, "", dtype=object)

    for t in range(n):
        if np.isnan(atr_series[t]) or atr_series[t] <= 0:
            continue
        if t + time_barrier_bars >= n:
            break  # not enough future bars

        e = close_arr[t]
        sl_dist = sl_atr_mult * atr_series[t]
        tp_dist = tp_R * sl_dist
        tp = e + tp_dist
        sl = e - sl_dist

        entry[t] = e
        tp_price[t] = tp
        sl_price[t] = sl

        end = t + 1 + time_barrier_bars
        # Iterate future bars
        for k in range(t + 1, end):
            if high_arr[k] >= tp and low_arr[k] <= sl:
                # Both touched in same bar — conservative: assume worst case (loss)
                # Standard Lopez de Prado: assume open determines first hit;
                # we use a conservative SL-first heuristic since it matches real
                # broker fill behavior in volatile bars.
                label[t] = -1
                hit_offset[t] = k - t
                hit_type[t] = "ambiguous_sl"
                break
            if high_arr[k] >= tp:
                label[t] = 1
                hit_offset[t] = k - t
                hit_type[t] = "tp"
                break
            if low_arr[k] <= sl:
                label[t] = -1
                hit_offset[t] = k - t
                hit_type[t] = "sl"
                break
        else:
            # Loop ended without hitting tp/sl -> time barrier
            label[t] = 0
            hit_offset[t] = time_barrier_bars
            hit_type[t] = "time"

    return pd.DataFrame({
        "label": label,
        "entry_price": entry,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "hit_bar_offset": hit_offset,
        "hit_type": hit_type,
    }, index=ohlcv.index)


def label_distribution(labels: pd.DataFrame) -> pd.Series:
    """Return count of each label class."""
    return labels["label"].value_counts(dropna=True).sort_index()


def expected_value_per_label_set(labels: pd.DataFrame, tp_R: float, sl_atr_mult: float = 1.0) -> dict:
    """
    Compute expected R-multiple per bar (theoretical edge if we entered every bar).

    A WIN nets +tp_R * sl_atr_mult R (in terms of risk units).
    A LOSS nets -sl_atr_mult R.
    A NEUTRAL nets 0 (closed at time barrier — actual PnL depends, here assumed flat).
    """
    dist = label_distribution(labels)
    total = dist.sum()
    if total == 0:
        return {"expected_R": 0.0, "win_rate": 0.0, "n": 0,
                 "wins": 0, "losses": 0, "neutrals": 0,
                 "profit_factor": 0.0}

    wins = int(dist.get(1, 0))
    losses = int(dist.get(-1, 0))
    neutrals = int(dist.get(0, 0))

    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    win_R = tp_R * sl_atr_mult
    loss_R = sl_atr_mult
    expected_R = (wins * win_R - losses * loss_R) / total
    profit_factor = (wins * win_R) / (losses * loss_R) if losses > 0 else float("inf")

    return {
        "n": int(total),
        "wins": wins,
        "losses": losses,
        "neutrals": neutrals,
        "win_rate": float(win_rate),
        "expected_R": float(expected_R),
        "profit_factor": float(profit_factor),
    }
