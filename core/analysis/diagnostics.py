"""
Model diagnostics: SHAP feature impact, per-regime performance,
confidence-percentile slicing, meta-labeling on rule-based primary signals.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ============================================================================
# REGIME DEFINITIONS — from existing features (no new computation needed)
# ============================================================================

def regime_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tag each row with regime labels for stratified analysis.

    Returns DataFrame with added columns:
      - trend_regime:  'bull' / 'bear' / 'neutral'
      - vol_regime:    'low_vol' / 'mid_vol' / 'high_vol'  (ATR percentile)
      - htf_aligned:   True if 1H trend matches own trend
      - regime_combo:  composite label (e.g. 'bull_low_vol_aligned')
    """
    out = df.copy()
    out['trend_regime'] = np.where(out['ema_alignment'] == 1, 'bull',
                                    np.where(out['ema_alignment'] == -1, 'bear', 'neutral'))
    out['vol_regime'] = pd.cut(out['atr_percentile_100'],
                                bins=[-0.01, 0.33, 0.67, 1.01],
                                labels=['low_vol', 'mid_vol', 'high_vol']).astype(str)
    # htf_1h_ema_alignment matches current ema_alignment
    if 'htf_1h_ema_alignment' in out.columns:
        out['htf_aligned'] = (out['htf_1h_ema_alignment'].fillna(0) == out['ema_alignment']) \
                              & (out['ema_alignment'] != 0)
    else:
        out['htf_aligned'] = False
    out['regime_combo'] = out['trend_regime'] + '_' + out['vol_regime'] + \
                          out['htf_aligned'].map({True: '_aligned', False: '_misaligned'})
    return out


# ============================================================================
# TRADING METRICS — shared utility
# ============================================================================

def _pf_wr(labels_triple: pd.Series, tp_R: float, sl_atr_mult: float = 1.0) -> dict:
    wins = int((labels_triple == 1).sum())
    losses = int((labels_triple == -1).sum())
    neutrals = int((labels_triple == 0).sum())
    total = wins + losses + neutrals
    win_R = tp_R * sl_atr_mult
    loss_R = sl_atr_mult
    wr = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    er = (wins * win_R - losses * loss_R) / total if total > 0 else 0.0
    pf = (wins * win_R) / (losses * loss_R) if losses > 0 else float('inf') if wins > 0 else 0.0
    return {'n': total, 'wins': wins, 'losses': losses, 'neutrals': neutrals,
             'win_rate': wr, 'expected_R': er, 'profit_factor': pf}


# ============================================================================
# Per-regime PF/WR
# ============================================================================

def performance_by_regime(
    df: pd.DataFrame,
    proba: np.ndarray,
    threshold: float,
    tp_R: float,
    regime_col: str = 'regime_combo',
    sl_atr_mult: float = 1.0,
    min_n: int = 200,
) -> pd.DataFrame:
    """
    Compute trading metrics per regime bucket.

    Args:
        df: DataFrame WITH regime columns already tagged (use regime_buckets first)
        proba: model probabilities aligned to df rows
        threshold: minimum probability to trade
        regime_col: which regime grouping to use
        min_n: skip regimes with fewer than this many bars

    Returns:
        DataFrame with regime, n, WR, PF, ER, trade_rate (one row per regime)
    """
    mask = proba >= threshold
    rows = []
    for regime, sub in df.groupby(regime_col):
        idx = sub.index
        sub_proba_mask = mask[df.index.get_indexer(idx)]
        traded_labels = sub['label'].iloc[sub_proba_mask.nonzero()[0]] if sub_proba_mask.any() else pd.Series(dtype=int)
        if len(traded_labels) < min_n:
            continue
        m = _pf_wr(traded_labels, tp_R, sl_atr_mult)
        m['regime'] = regime
        m['regime_bars_total'] = len(sub)
        m['trade_rate'] = len(traded_labels) / len(sub) if len(sub) > 0 else 0.0
        rows.append(m)
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values('profit_factor', ascending=False).reset_index(drop=True)
        cols = ['regime', 'n', 'win_rate', 'profit_factor', 'expected_R',
                 'wins', 'losses', 'neutrals', 'trade_rate', 'regime_bars_total']
        out = out[[c for c in cols if c in out.columns]]
    return out


# ============================================================================
# Top-N% Confidence Slicing
# ============================================================================

def confidence_percentile_sweep(
    labels_triple: pd.Series,
    proba: np.ndarray,
    tp_R: float,
    percentiles: list[float] | None = None,
    sl_atr_mult: float = 1.0,
) -> pd.DataFrame:
    """
    Take the TOP N% of bars by probability and report trading metrics.

    This is the cleanest way to see "if we ONLY trade our most confident
    setups, how much edge do we get?" — independent of threshold selection.
    """
    if percentiles is None:
        percentiles = [1, 2, 3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 75, 100]

    order = np.argsort(-proba)  # descending
    labels_sorted = labels_triple.iloc[order].values
    rows = []
    for pct in percentiles:
        n_top = max(1, int(len(proba) * pct / 100))
        sub_labels = pd.Series(labels_sorted[:n_top])
        m = _pf_wr(sub_labels, tp_R, sl_atr_mult)
        m['top_pct'] = pct
        m['n_selected'] = n_top
        m['proba_cutoff'] = float(proba[order[n_top - 1]])
        rows.append(m)
    out = pd.DataFrame(rows)
    cols = ['top_pct', 'n_selected', 'proba_cutoff', 'win_rate', 'profit_factor',
             'expected_R', 'wins', 'losses', 'neutrals']
    return out[[c for c in cols if c in out.columns]]


# ============================================================================
# Meta-Labeling — ML as Quality Filter on Rule-Based Primary
# ============================================================================

def rule_based_primary_signal(df: pd.DataFrame) -> pd.Series:
    """
    Simple rule-based primary LONG signal — emulates PaceAlgo v2.6 style:
      - Strong uptrend (EMA alignment +1)
      - ADX > 20 (trending market)
      - Pullback close to EMA20 (within 1 ATR)
      - RSI in healthy zone (30-70)
      - HTF (1H) also bullish

    Returns boolean Series — True = primary fires this bar.
    """
    cond_trend = df['ema_alignment'] == 1
    cond_adx = df['adx_14'] > 20
    cond_pullback = df['ema_20_dist_atr'].abs() < 1.0
    cond_rsi = df['rsi_14'].between(30, 70)
    cond_htf = df.get('htf_1h_ema_alignment', pd.Series([0]*len(df), index=df.index)).fillna(0) == 1
    return cond_trend & cond_adx & cond_pullback & cond_rsi & cond_htf


def meta_labeling_evaluation(
    df: pd.DataFrame,
    proba: np.ndarray,
    tp_R: float,
    ml_thresholds: list[float] | None = None,
    sl_atr_mult: float = 1.0,
) -> pd.DataFrame:
    """
    Test ML as a QUALITY FILTER on rule-based primary signals.

    Workflow:
      1. Identify bars where rule-based primary signal fires
      2. Evaluate baseline PF/WR of primary alone (no filter)
      3. For each ML threshold: filter primary signals to only those where
         ML confidence >= threshold
      4. Compute PF/WR of filtered set

    If ML filters poorly (low PF lift), meta-labeling doesn't help.
    If ML lifts PF significantly with reasonable trade survival rate,
    this is the V1 architecture (rule-based core + ML filter).
    """
    if ml_thresholds is None:
        ml_thresholds = [0.0, 0.30, 0.35, 0.38, 0.40, 0.42, 0.44, 0.46]

    primary_mask = rule_based_primary_signal(df).values
    primary_labels = df['label'].iloc[primary_mask.nonzero()[0]]
    primary_proba = proba[primary_mask]

    rows = []
    # Baseline: rule-based alone, no ML filter
    m_base = _pf_wr(primary_labels, tp_R, sl_atr_mult)
    m_base['ml_threshold'] = None
    m_base['note'] = 'PRIMARY ALONE (no ML filter)'
    m_base['n_primary'] = int(primary_mask.sum())
    m_base['trades_kept'] = int(primary_mask.sum())
    m_base['kept_pct'] = 1.0
    rows.append(m_base)

    # With ML filter
    for t in ml_thresholds:
        keep_mask = primary_proba >= t
        if keep_mask.sum() < 100:
            continue
        kept_labels = primary_labels.iloc[keep_mask.nonzero()[0]]
        m = _pf_wr(kept_labels, tp_R, sl_atr_mult)
        m['ml_threshold'] = t
        m['note'] = 'with ML filter'
        m['n_primary'] = int(primary_mask.sum())
        m['trades_kept'] = int(keep_mask.sum())
        m['kept_pct'] = float(keep_mask.sum() / primary_mask.sum())
        rows.append(m)

    out = pd.DataFrame(rows)
    cols = ['ml_threshold', 'note', 'n_primary', 'trades_kept', 'kept_pct',
             'win_rate', 'profit_factor', 'expected_R',
             'wins', 'losses', 'neutrals']
    return out[[c for c in cols if c in out.columns]]
