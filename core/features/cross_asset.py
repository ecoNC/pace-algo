"""
Cross-asset / currency-factor features (PaceAlgo FX V1).

Validated 2026-06-01 via walk-forward (scripts/factor_lean.py + per-pair confirm):
robust +0.154 PF lift over the 73-feature base, broad-based across all 6 pairs
(6/6 positive), all 4 features structurally top-8/77. See:
  results/model_validation/factor_lean_*  and  factor_perpair_*

Unlike the per-symbol feature builders (engineer/market_structure/session), these
require the FULL FX panel (all pairs) to build a USD-strength index, then attach
per-pair factor features. Lean set (low-dimensional — deepening to 10 features
diluted the lift; see scripts/factor_features.py):

  idio_mom_20     idiosyncratic momentum (pair move minus USD-beta * USD move, 20-bar sum)
  usd_corr_50     rolling corr of pair return to USD index (how USD-driven, 50-bar)
  usd_beta_50     rolling beta of pair return to USD index (coupling magnitude)
  usd_idx_vol_20  USD-index return volatility (broad USD regime vol, 20-bar)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# USD direction per pair: +1 if USD is BASE (USDxxx) -> +return = USD strengthening;
#                         -1 if USD is QUOTE (xxxUSD) -> -return = USD strengthening.
USD_SIGN = {
    "USDJPY": 1, "USDCHF": 1, "USDCAD": 1,
    "EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "NZDUSD": -1,
}

CROSS_ASSET_FEATURES = ["idio_mom_20", "usd_corr_50", "usd_beta_50", "usd_idx_vol_20"]

_EPS = 1e-12


def build_usd_strength(closes: dict[str, pd.Series]) -> tuple[pd.Series, pd.DataFrame]:
    """
    Build the USD-strength index from a panel of pair close series.

    Args:
        closes: {symbol: close Series (DatetimeIndex)} for FX majors in USD_SIGN.
    Returns:
        usd_ret: per-bar USD-strength log-return (sign-adjusted mean across pairs)
        R:       DataFrame of per-pair SIGNED log-returns (USD-strengthening convention)
    """
    rets = {}
    for s, c in closes.items():
        if s in USD_SIGN:
            rets[s] = np.log(c / c.shift(1)) * USD_SIGN[s]
    R = pd.DataFrame(rets).dropna(how="all")
    usd_ret = R.mean(axis=1)
    return usd_ret, R


def compute_cross_asset_features(symbol: str, usd_ret: pd.Series, R: pd.DataFrame) -> pd.DataFrame:
    """
    Per-pair currency-factor features, indexed like usd_ret.

    Args:
        symbol:  pair to compute features for (must be in R / USD_SIGN)
        usd_ret: USD-strength index returns (from build_usd_strength)
        R:       signed-return panel (from build_usd_strength)
    Returns:
        DataFrame with columns CROSS_ASSET_FEATURES.
    """
    pr = R[symbol] * USD_SIGN[symbol]                      # pair's own (raw) log-return
    beta50 = pr.rolling(50).cov(usd_ret) / (usd_ret.rolling(50).var() + _EPS)
    idio = pr - beta50 * usd_ret                           # idiosyncratic (USD-neutralised) return
    out = pd.DataFrame(index=usd_ret.index)
    out["idio_mom_20"] = idio.rolling(20).sum()
    out["usd_corr_50"] = pr.rolling(50).corr(usd_ret)
    out["usd_beta_50"] = beta50
    out["usd_idx_vol_20"] = usd_ret.rolling(20).std()
    return out


def attach_cross_asset(pool: pd.DataFrame, closes: dict[str, pd.Series],
                       symbol_col: str = "symbol") -> pd.DataFrame:
    """
    Attach cross-asset features to a stacked multi-symbol pool (production path).

    Args:
        pool:   stacked DataFrame with DatetimeIndex and a symbol column.
        closes: {symbol: close Series} for the full FX panel.
    Returns:
        pool with CROSS_ASSET_FEATURES columns added (per-row, per-symbol aligned).
    """
    usd_ret, R = build_usd_strength(closes)
    per_sym = {s: compute_cross_asset_features(s, usd_ret, R) for s in R.columns}
    parts = []
    for s, grp in pool.groupby(symbol_col, sort=False):
        feats = per_sym[s].reindex(grp.index)
        parts.append(grp.join(feats))
    return pd.concat(parts).sort_index()
