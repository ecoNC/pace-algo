"""
Higher Timeframe (HTF) × Lower Timeframe (LTF) INTERACTION features.

Existing engineer.py already produces htf_1h_ema_alignment, htf_1h_rsi_14 etc.
But those sit side-by-side with LTF features — the model has to discover the
interaction. We can make this explicit by computing interaction terms directly.

Interaction features express questions like:
  - "Is the 5M trend in the same direction as the 1H trend?"
  - "Is the LTF RSI extreme while HTF agrees on direction?"
  - "Is LTF momentum aligned with HTF position?"
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_htf_interactions(
    ltf_features: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add HTF×LTF interaction features assuming the input DataFrame already has
    both LTF features (e.g. ema_alignment, rsi_14) and HTF features (e.g.
    htf_1h_ema_alignment, htf_1h_rsi_14, htf_1h_atr_percentile_100).

    Returns: DataFrame indexed identically, with new interaction columns.
    """
    out = pd.DataFrame(index=ltf_features.index)

    # ─── ALIGNMENT INTERACTION ───
    # 1 if both LTF and HTF are bull, -1 if both bear, 0 if mismatch
    if 'ema_alignment' in ltf_features and 'htf_1h_ema_alignment' in ltf_features:
        ltf_a = ltf_features['ema_alignment'].fillna(0)
        htf_a = ltf_features['htf_1h_ema_alignment'].fillna(0)
        # Strong agreement: both +1 OR both -1
        agree_bull = ((ltf_a == 1) & (htf_a == 1)).astype(float)
        agree_bear = ((ltf_a == -1) & (htf_a == -1)).astype(float)
        out['htf_ltf_agree_bull'] = agree_bull
        out['htf_ltf_agree_bear'] = agree_bear
        # Counter-trend setup: LTF bull but HTF bear (or mirror) — typical fade trade
        out['htf_ltf_counter_trend'] = ((ltf_a != 0) & (htf_a != 0) & (ltf_a != htf_a)).astype(float)
        # Net alignment score
        out['htf_ltf_alignment_score'] = ltf_a * htf_a  # +1 agree, -1 disagree, 0 neutral

    # ─── RSI POSITION RELATIVE TO HTF RSI ───
    if 'rsi_14' in ltf_features and 'htf_1h_rsi_14' in ltf_features:
        out['ltf_rsi_minus_htf_rsi'] = ltf_features['rsi_14'] - ltf_features['htf_1h_rsi_14']
        # Both oversold (potential reversal up)
        ltf_oversold = (ltf_features['rsi_14'] < 35).astype(float)
        htf_oversold = (ltf_features['htf_1h_rsi_14'] < 40).astype(float)
        out['both_rsi_oversold'] = ltf_oversold * htf_oversold
        # Both overbought
        ltf_overbought = (ltf_features['rsi_14'] > 65).astype(float)
        htf_overbought = (ltf_features['htf_1h_rsi_14'] > 60).astype(float)
        out['both_rsi_overbought'] = ltf_overbought * htf_overbought

    # ─── VOLATILITY ALIGNMENT ───
    if 'atr_percentile_100' in ltf_features and 'htf_1h_atr_percentile_100' in ltf_features:
        out['vol_pct_diff_htf'] = ltf_features['atr_percentile_100'] - ltf_features['htf_1h_atr_percentile_100']
        # Both in high vol regime (>0.7)
        out['both_high_vol'] = ((ltf_features['atr_percentile_100'] > 0.7) &
                                 (ltf_features['htf_1h_atr_percentile_100'] > 0.7)).astype(float)
        # Both in low vol regime (<0.3) — coiled spring setup
        out['both_low_vol'] = ((ltf_features['atr_percentile_100'] < 0.3) &
                                (ltf_features['htf_1h_atr_percentile_100'] < 0.3)).astype(float)

    # ─── TREND-IN-PULLBACK FEATURE ───
    # The classic "pullback within HTF trend": HTF bullish + LTF momentum just turned bearish
    if ('htf_1h_ema_alignment' in ltf_features and 'rsi_14' in ltf_features and
        'ema_20_dist_atr' in ltf_features):
        htf_bull = (ltf_features['htf_1h_ema_alignment'] == 1).astype(float)
        htf_bear = (ltf_features['htf_1h_ema_alignment'] == -1).astype(float)
        ltf_rsi_low = (ltf_features['rsi_14'] < 45).astype(float)
        ltf_rsi_high = (ltf_features['rsi_14'] > 55).astype(float)
        # Pullback in bull trend = HTF bull AND LTF RSI dipped low
        out['pullback_in_bull'] = htf_bull * ltf_rsi_low
        out['pullback_in_bear'] = htf_bear * ltf_rsi_high

    return out
