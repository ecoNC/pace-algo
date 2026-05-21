"""Training pipelines for PaceAlgo ML."""

from .dataset import (
    load_features_and_labels,
    stack_symbols,
    get_feature_columns,
    walk_forward_split,
    binary_label_for_long,
    NON_FEATURE_COLS,
)
from .lgbm_trainer import (
    train_lgbm,
    evaluate_classifier,
    trading_metrics_from_predictions,
    sweep_threshold,
)

__all__ = [
    "load_features_and_labels",
    "stack_symbols",
    "get_feature_columns",
    "walk_forward_split",
    "binary_label_for_long",
    "NON_FEATURE_COLS",
    "train_lgbm",
    "evaluate_classifier",
    "trading_metrics_from_predictions",
    "sweep_threshold",
]
