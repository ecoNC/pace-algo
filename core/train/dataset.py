"""
Training dataset assembly.

Merges per-symbol/TF feature parquets with the corresponding label parquets
into a single training-ready DataFrame. Handles:
  - Loading from /content/processed/
  - Joining features + labels on timestamp index
  - Symbol/TF stacking with categorical encoding
  - Walk-forward time-based train/val/test splits (NO random shuffling)
  - Hold-out symbol filtering
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# Columns that are NOT features (identifiers, metadata)
NON_FEATURE_COLS = {"symbol", "timeframe", "label", "entry_price", "tp_price",
                     "sl_price", "hit_bar_offset", "hit_type"}


def load_features_and_labels(
    data_processed: Path,
    symbol: str,
    tf: str,
    R: float,
) -> pd.DataFrame:
    """
    Load and join features + labels for one (symbol, tf, R) combo.

    Returns DataFrame with feature columns + 'label' column.
    Rows where label is NaN (e.g. last 24 bars without forward horizon) are dropped.
    """
    feat_path = data_processed / f"{symbol}_{tf}_features.parquet"
    label_path = data_processed / f"labels_{symbol}_{tf}_R{R}.parquet"

    if not feat_path.exists() or not label_path.exists():
        return pd.DataFrame()

    feats = pd.read_parquet(feat_path)
    labels = pd.read_parquet(label_path)

    # Join on index — features should already have symbol/tf cols from NB 02
    merged = feats.join(labels[["label"]], how="inner")
    # Drop rows where label is NaN (end-of-series — no future bars)
    merged = merged.dropna(subset=["label"])
    merged["label"] = merged["label"].astype(int)
    return merged


def stack_symbols(
    data_processed: Path,
    symbols: list[str],
    tfs: list[str],
    R: float,
    drop_holdout: list[str] | None = None,
) -> pd.DataFrame:
    """
    Stack training data from multiple (symbol, tf) combos into one big DataFrame.

    Args:
        data_processed: Path to /content/processed/
        symbols: list of symbols to include
        tfs: list of timeframes (e.g. ['5m', '15m'])
        R: triple-barrier R value (which label file to use)
        drop_holdout: symbols to EXCLUDE (development hold-out set)

    Returns:
        Stacked DataFrame with all combos, indexed by (timestamp), with
        original columns + a multi-index-style 'symbol' + 'timeframe' for grouping.
    """
    drop = set(drop_holdout or [])
    frames = []
    for sym in symbols:
        if sym in drop:
            continue
        for tf in tfs:
            df = load_features_and_labels(data_processed, sym, tf, R)
            if df.empty:
                continue
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=0).sort_index()


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return list of column names that are features (numeric, excluding identifiers)."""
    return [c for c in df.columns if c not in NON_FEATURE_COLS]


def walk_forward_split(
    df: pd.DataFrame,
    train_end: datetime,
    val_end: datetime,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Time-based train/val/test split. NO random shuffling — preserves time order.

    Args:
        df: stacked DataFrame with DatetimeIndex (UTC)
        train_end: cutoff for training data (everything before this is train)
        val_end: cutoff for validation (train_end ≤ time < val_end is val)
                 everything from val_end onward is test

    Returns:
        (train_df, val_df, test_df)
    """
    train_end_ts = pd.Timestamp(train_end).tz_localize("UTC") if train_end.tzinfo is None \
                                                                else pd.Timestamp(train_end)
    val_end_ts = pd.Timestamp(val_end).tz_localize("UTC") if val_end.tzinfo is None \
                                                              else pd.Timestamp(val_end)

    train = df[df.index < train_end_ts]
    val = df[(df.index >= train_end_ts) & (df.index < val_end_ts)]
    test = df[df.index >= val_end_ts]
    return train, val, test


def binary_label_for_long(y_triple: pd.Series) -> pd.Series:
    """
    Convert triple-barrier label {+1, 0, -1} to binary {0, 1} for long-trade classification.
      +1 (TP first)     -> 1 (long would win)
       0 (time barrier) -> 0 (no clear signal — treat as not-a-trade)
      -1 (SL first)     -> 0 (long would lose)
    """
    return (y_triple == 1).astype(int)
