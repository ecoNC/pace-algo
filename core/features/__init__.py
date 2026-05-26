"""Feature engineering for PaceAlgo ML."""

from .engineer import (
    compute_features,
    attach_macro,
    attach_htf_context,
)
from .asset_cluster import (
    aggregate_asset_features,
    build_asset_profile_table,
    cluster_assets,
    label_clusters_semantic,
    CLUSTER_FEATURE_BUILDERS,
)
from .market_structure import (
    compute_smc_features,
    confirmed_swing_highs,
    confirmed_swing_lows,
    detect_sweep_up,
    detect_sweep_down,
    equal_highs,
    equal_lows,
    strict_bos_choch,
    detect_fvg,
)
from .session import (
    session_flags,
    vol_expansion_features,
    compute_session_features,
)
from .htf_interaction import (
    compute_htf_interactions,
)

__all__ = [
    "compute_features",
    "attach_macro",
    "attach_htf_context",
    "aggregate_asset_features",
    "build_asset_profile_table",
    "cluster_assets",
    "label_clusters_semantic",
    "CLUSTER_FEATURE_BUILDERS",
    "compute_smc_features",
    "confirmed_swing_highs",
    "confirmed_swing_lows",
    "detect_sweep_up",
    "detect_sweep_down",
    "equal_highs",
    "equal_lows",
    "strict_bos_choch",
    "detect_fvg",
    "session_flags",
    "vol_expansion_features",
    "compute_session_features",
    "compute_htf_interactions",
]
