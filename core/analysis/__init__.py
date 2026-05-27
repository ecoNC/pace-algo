"""Diagnostic analysis: SHAP, per-regime, percentile slicing, meta-labeling,
product metrics, quality check."""

from .diagnostics import (
    regime_buckets,
    performance_by_regime,
    confidence_percentile_sweep,
    rule_based_primary_signal,
    meta_labeling_evaluation,
)
from .product_metrics import (
    signals_per_day,
    signal_density,
    trade_duration_stats,
    alert_frequency,
    max_burst_signals_per_hour,
    session_share,
    session_dependency_score,
    chart_cleanliness,
    pine_ux_score,
    compute_product_metrics_bundle,
    evaluate_product_thresholds,
    TF_BARS_PER_DAY,
)
from .quality_check import (
    check_quality_anchor,
    format_quality_report,
)

__all__ = [
    "regime_buckets",
    "performance_by_regime",
    "confidence_percentile_sweep",
    "rule_based_primary_signal",
    "meta_labeling_evaluation",
    "signals_per_day",
    "signal_density",
    "trade_duration_stats",
    "alert_frequency",
    "max_burst_signals_per_hour",
    "session_share",
    "session_dependency_score",
    "chart_cleanliness",
    "pine_ux_score",
    "compute_product_metrics_bundle",
    "evaluate_product_thresholds",
    "TF_BARS_PER_DAY",
    "check_quality_anchor",
    "format_quality_report",
]
