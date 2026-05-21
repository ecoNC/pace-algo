"""
Asset clustering — K-Means on per-symbol volatility/trend aggregates.

Goal: Data-driven detection of asset "personality" instead of hard-coded
ticker-string matching. The cluster assignment is later used to:
  - Pick TP-R multiplier per cluster (high-vol assets use smaller R, etc.)
  - Stratify backtest results
  - Optionally tune model thresholds per cluster
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score


# Features that characterize an asset's "personality"
# All are aggregates over the full feature-matrix history
CLUSTER_FEATURE_BUILDERS = {
    "vol_level":          lambda f: f["atr_pct"].mean(),
    "vol_volatility":     lambda f: f["atr_pct"].std(),
    "vol_realized":       lambda f: f["realized_vol_20"].mean(),
    "trend_strength":     lambda f: f["adx_14"].mean(),
    "pct_trending":       lambda f: (f["adx_14"] > 25).mean(),
    "bb_width_avg":       lambda f: f["bb_width_pct"].mean(),
    "volume_dispersion":  lambda f: f["volume_z_score"].abs().mean(),
}


def aggregate_asset_features(features: pd.DataFrame) -> dict:
    """Compute a single feature vector summarizing one asset's personality."""
    out = {}
    feats = features.dropna(subset=list({"atr_pct", "realized_vol_20", "adx_14",
                                          "bb_width_pct", "volume_z_score"}))
    for name, fn in CLUSTER_FEATURE_BUILDERS.items():
        try:
            out[name] = float(fn(feats))
        except Exception:
            out[name] = np.nan
    return out


def build_asset_profile_table(feature_files: list[Path]) -> pd.DataFrame:
    """
    Build a (symbol, tf) → 7-feature profile table from processed feature files.

    Args:
        feature_files: list of Parquet paths from notebook 02

    Returns:
        DataFrame with columns [symbol, tf, vol_level, ...] one row per file
    """
    rows = []
    for p in feature_files:
        df = pd.read_parquet(p)
        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else p.stem.split("_")[0]
        tf = df["timeframe"].iloc[0] if "timeframe" in df.columns else p.stem.split("_")[1]
        agg = aggregate_asset_features(df)
        agg["symbol"] = symbol
        agg["tf"] = tf
        rows.append(agg)
    return pd.DataFrame(rows)


def cluster_assets(profile_df: pd.DataFrame, k_range: range = range(2, 6),
                    random_state: int = 42) -> tuple[pd.DataFrame, dict]:
    """
    K-Means cluster the asset profile table.

    Args:
        profile_df: output of build_asset_profile_table()
        k_range: candidate k values to test via silhouette score
        random_state: seed for reproducibility

    Returns:
        (clustered_df, info) where
          clustered_df: profile_df with extra column 'cluster'
          info: dict with chosen_k, silhouette_per_k, cluster_centers
    """
    feature_cols = list(CLUSTER_FEATURE_BUILDERS.keys())
    X = profile_df[feature_cols].copy()
    X = X.fillna(X.median())

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    # Choose k by silhouette score
    silhouettes = {}
    for k in k_range:
        if k >= len(Xs):
            continue
        km = KMeans(n_clusters=k, n_init=10, random_state=random_state)
        labels = km.fit_predict(Xs)
        if len(set(labels)) < 2:
            continue
        silhouettes[k] = silhouette_score(Xs, labels)

    if not silhouettes:
        # Fallback: k=2
        chosen_k = 2
    else:
        chosen_k = max(silhouettes, key=silhouettes.get)

    final_km = KMeans(n_clusters=chosen_k, n_init=10, random_state=random_state)
    profile_df = profile_df.copy()
    profile_df["cluster"] = final_km.fit_predict(Xs)

    # Re-label clusters by ascending vol_level for interpretability
    cluster_vol = profile_df.groupby("cluster")["vol_level"].mean().sort_values()
    relabel = {old: new for new, old in enumerate(cluster_vol.index)}
    profile_df["cluster"] = profile_df["cluster"].map(relabel)

    # Cluster centers in ORIGINAL feature space (un-scaled)
    centers_scaled = final_km.cluster_centers_
    centers_unscaled = scaler.inverse_transform(centers_scaled)
    centers_df = pd.DataFrame(centers_unscaled, columns=feature_cols)
    # Relabel rows of centers to match
    inverse_relabel = {v: k for k, v in relabel.items()}
    centers_df = centers_df.iloc[[inverse_relabel[i] for i in range(chosen_k)]].reset_index(drop=True)

    info = {
        "chosen_k": chosen_k,
        "silhouette_per_k": silhouettes,
        "cluster_centers": centers_df,
        "feature_cols": feature_cols,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
    }
    return profile_df, info


def label_clusters_semantic(profile_df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign human-readable labels to clusters based on vol_level percentile.

    With k=2: low_vol / high_vol
    With k=3: low_vol / mid_vol / high_vol
    With k>=4: mostly uses quartile labels
    """
    profile_df = profile_df.copy()
    cluster_vol = profile_df.groupby("cluster")["vol_level"].mean().sort_values()
    n = len(cluster_vol)
    if n == 2:
        names = ["low_vol", "high_vol"]
    elif n == 3:
        names = ["low_vol", "mid_vol", "high_vol"]
    elif n == 4:
        names = ["low_vol", "mid_low_vol", "mid_high_vol", "high_vol"]
    else:
        names = [f"cluster_{i}" for i in range(n)]
    label_map = dict(zip(cluster_vol.index, names))
    profile_df["cluster_label"] = profile_df["cluster"].map(label_map)
    return profile_df
