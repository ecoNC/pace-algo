"""Diagnostic analysis: SHAP, per-regime, percentile slicing, meta-labeling."""

from .diagnostics import (
    regime_buckets,
    performance_by_regime,
    confidence_percentile_sweep,
    rule_based_primary_signal,
    meta_labeling_evaluation,
)

__all__ = [
    "regime_buckets",
    "performance_by_regime",
    "confidence_percentile_sweep",
    "rule_based_primary_signal",
    "meta_labeling_evaluation",
]
