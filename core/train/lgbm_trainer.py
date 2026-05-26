"""
LightGBM training pipeline.

Trains a binary classifier predicting P(TP-first-hit | features).
Hyperparameters constrained to Pine-export budget (max 30 trees, depth 3).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    confusion_matrix, log_loss,
)


def train_lgbm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    params: dict[str, Any] | None = None,
    early_stopping_rounds: int = 10,
) -> lgb.Booster:
    """
    Train LightGBM with validation-based early stopping.

    Args:
        X_train, y_train: training features and binary labels
        X_val, y_val: validation features and binary labels
        params: LightGBM params (uses defaults if None)
        early_stopping_rounds: stop if val loss doesn't improve

    Returns:
        Trained Booster
    """
    if params is None:
        params = {
            "objective":            "binary",
            "metric":               "binary_logloss",
            "num_leaves":           7,
            "max_depth":            3,
            "min_data_in_leaf":     200,
            "learning_rate":        0.05,
            "num_iterations":       100,   # capped, early stopping selects best
            "lambda_l2":            1.0,
            "feature_fraction":     0.8,
            "bagging_fraction":     0.8,
            "bagging_freq":         5,
            "is_unbalance":         True,   # class weight balanced
            "verbose":              -1,
            "n_jobs":               -1,
        }

    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    model = lgb.train(
        params,
        train_data,
        valid_sets=[train_data, val_data],
        valid_names=["train", "val"],
        callbacks=[lgb.early_stopping(early_stopping_rounds, verbose=False),
                    lgb.log_evaluation(period=0)],
    )
    return model


def evaluate_classifier(
    model: lgb.Booster,
    X: pd.DataFrame,
    y: pd.Series,
    threshold: float = 0.5,
) -> dict[str, float]:
    """
    Compute classifier metrics at a given probability threshold.

    Returns: dict with auc, precision, recall, f1, accuracy, n_positive_predictions,
             actual_positive_rate, predicted_positive_rate.
    """
    p = model.predict(X)
    y_pred = (p >= threshold).astype(int)

    out: dict[str, float] = {}
    try:
        out["auc"] = float(roc_auc_score(y, p))
    except Exception:
        out["auc"] = float("nan")
    out["log_loss"] = float(log_loss(y, np.clip(p, 1e-8, 1 - 1e-8)))
    out["precision"] = float(precision_score(y, y_pred, zero_division=0))
    out["recall"] = float(recall_score(y, y_pred, zero_division=0))
    out["f1"] = float(f1_score(y, y_pred, zero_division=0))
    out["accuracy"] = float((y == y_pred).mean())
    out["n_total"] = int(len(y))
    out["n_actual_positive"] = int(y.sum())
    out["n_predicted_positive"] = int(y_pred.sum())
    out["actual_positive_rate"] = float(y.mean())
    out["predicted_positive_rate"] = float(y_pred.mean())

    tn, fp, fn, tp = confusion_matrix(y, y_pred, labels=[0, 1]).ravel()
    out["tn"] = int(tn); out["fp"] = int(fp); out["fn"] = int(fn); out["tp"] = int(tp)
    return out


def trading_metrics_from_predictions(
    y_triple: pd.Series,
    proba: np.ndarray,
    threshold: float,
    tp_R: float,
    sl_atr_mult: float = 1.0,
) -> dict[str, float]:
    """
    Compute trading metrics assuming we trade ONLY when proba >= threshold.

    Uses the original 3-class label (+1/0/-1) so neutral outcomes don't
    inflate stats. Each +1 wins tp_R*sl_atr_mult R, each -1 loses sl_atr_mult R,
    each 0 is treated as flat (0 R).
    """
    mask = proba >= threshold
    if mask.sum() == 0:
        return {"n_trades": 0, "win_rate": 0.0, "expected_R": 0.0,
                 "profit_factor": 0.0, "trade_rate": 0.0}

    traded = y_triple[mask]
    wins = int((traded == 1).sum())
    losses = int((traded == -1).sum())
    neutrals = int((traded == 0).sum())
    total = wins + losses + neutrals

    win_R = tp_R * sl_atr_mult
    loss_R = sl_atr_mult
    if losses == 0:
        pf = float("inf") if wins > 0 else 0.0
    else:
        pf = (wins * win_R) / (losses * loss_R)
    wr = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    er = (wins * win_R - losses * loss_R) / total if total > 0 else 0.0

    return {
        "n_trades": int(total),
        "wins": wins,
        "losses": losses,
        "neutrals": neutrals,
        "win_rate": float(wr),
        "expected_R": float(er),
        "profit_factor": float(pf),
        "trade_rate": float(mask.sum() / len(proba)),
    }


def sweep_threshold(
    y_triple: pd.Series,
    proba: np.ndarray,
    tp_R: float,
    thresholds: list[float] | None = None,
    sl_atr_mult: float = 1.0,
) -> pd.DataFrame:
    """
    Sweep over multiple threshold values, computing PF/WR/n_trades for each.

    Returns DataFrame with one row per threshold — useful for choosing the
    operating point that balances trade frequency vs profit factor.
    """
    if thresholds is None:
        thresholds = [0.30, 0.35, 0.40, 0.42, 0.44, 0.46, 0.48, 0.50, 0.52, 0.55,
                       0.58, 0.60, 0.62, 0.65, 0.68, 0.70, 0.75, 0.80]
    rows = []
    for t in thresholds:
        m = trading_metrics_from_predictions(y_triple, proba, t, tp_R, sl_atr_mult)
        m["threshold"] = t
        rows.append(m)
    return pd.DataFrame(rows)
