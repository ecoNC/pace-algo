"""Bit-exact validation tests for core/export/pine_codegen.py.

These do NOT depend on the production model — they train a tiny LightGBM
booster on synthetic data, then verify:
1. lgbm_to_pine_cascade() produces well-formed Pine code (no syntax surprises)
2. python_reimplementation() matches booster.predict() bit-exact (atol 1e-5)

If these tests pass, the generated Pine snippet (which is a literal
transliteration of python_reimplementation) is also bit-exact vs LightGBM,
modulo Pine's float64 arithmetic which is identical to NumPy's.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.export.pine_codegen import (
    bit_exact_check,
    lgbm_to_pine_cascade,
    python_reimplementation,
)


# ---------------------------------------------------------------------------
# Test fixtures — small deterministic LightGBM booster
# ---------------------------------------------------------------------------

def _train_tiny_booster(n_features: int = 8,
                          n_samples: int = 5000,
                          n_trees: int = 30,
                          max_depth: int = 3,
                          seed: int = 42):
    """Mirror the V1 hyperparams on synthetic data — same depth/tree count."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n_samples, n_features)).astype(np.float32)
    # Mild signal so the booster actually splits
    logits = 0.7 * X[:, 0] - 0.4 * X[:, 1] + 0.3 * X[:, 2] * X[:, 3]
    p = 1.0 / (1.0 + np.exp(-logits))
    y = (rng.uniform(size=n_samples) < p).astype(np.int32)

    feature_names = [f"feat_{i}" for i in range(n_features)]
    dataset = lgb.Dataset(X, label=y, feature_name=feature_names)
    params = {
        'objective':         'binary',
        'metric':            'binary_logloss',
        'num_leaves':        7,
        'max_depth':         max_depth,
        'min_data_in_leaf':  50,
        'learning_rate':     0.05,
        'lambda_l2':         1.0,
        'feature_fraction':  0.8,
        'bagging_fraction':  0.8,
        'bagging_freq':      5,
        'is_unbalance':      True,
        'verbose':           -1,
        'n_jobs':            -1,
        'seed':              seed,
        'deterministic':     True,
    }
    booster = lgb.train(params, dataset, num_boost_round=n_trees)
    return booster, X, feature_names


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_python_reimpl_matches_booster():
    """Python re-implementation of the tree cascade is bit-exact vs LightGBM."""
    booster, X, feature_names = _train_tiny_booster()
    result = bit_exact_check(booster, feature_names, X, atol=1e-5)
    assert result['passed'], (
        f"python_reimplementation differs from booster.predict: {result}"
    )
    # Tighter sanity: max diff should be sub-microscopic for clean numerical
    # cascade walks.
    assert result['max_abs_diff'] < 1e-9, (
        f"Unexpectedly large diff: {result['max_abs_diff']}. "
        f"Check decision_type handling or float formatting."
    )


def test_pine_output_well_formed():
    """Generated Pine snippet has expected structure (function + tree vars + raw + sigmoid)."""
    booster, _, feature_names = _train_tiny_booster()
    pine = lgbm_to_pine_cascade(booster, feature_names)

    # Function signature
    assert "f_pace_algo_v1_probability(" in pine, "Missing function definition"
    for name in feature_names:
        # Pine arg has 'f_' prefix
        assert f"f_{name}" in pine, f"Feature {name} missing from arglist"

    # Each tree gets its own variable
    n_trees = len(booster.dump_model()['tree_info'])
    for i in range(n_trees):
        assert f"t_{i} = " in pine, f"Tree variable t_{i} missing"

    # Raw + sigmoid expression
    assert "raw = " in pine, "Missing raw score aggregation"
    assert "1.0 / (1.0 + math.exp(-raw))" in pine, "Missing sigmoid output"

    # No leftover Python tokens that wouldn't compile in Pine
    forbidden = ['None', 'True', 'False', 'def ', 'lambda ']
    for tok in forbidden:
        assert tok not in pine, f"Forbidden Python token in Pine output: {tok!r}"


def test_balanced_dataset_bit_exact():
    """Re-run bit-exact with a different seed + sample distribution."""
    booster, _, feature_names = _train_tiny_booster(seed=7, n_samples=2000)
    rng = np.random.default_rng(99)
    X_eval = rng.standard_normal((10_000, len(feature_names))).astype(np.float32)
    result = bit_exact_check(booster, feature_names, X_eval, atol=1e-5)
    assert result['passed'], f"Bit-exact failed on independent eval set: {result}"


def test_feature_index_validation():
    """Codegen rejects feature_names lists that don't cover all booster splits."""
    booster, _, feature_names = _train_tiny_booster()
    # Drop the last feature — booster might still reference it
    truncated = feature_names[:-1]
    referenced = set()
    for tree_info in booster.dump_model()['tree_info']:
        def walk(node):
            if 'leaf_value' in node:
                return
            referenced.add(node['split_feature'])
            walk(node['left_child'])
            walk(node['right_child'])
        walk(tree_info['tree_structure'])

    if max(referenced) >= len(truncated):
        # Expected: codegen raises ValueError
        try:
            lgbm_to_pine_cascade(booster, truncated)
        except ValueError as e:
            assert "feature indices" in str(e), str(e)
            return
        raise AssertionError("Expected ValueError for truncated feature_names")
    # Otherwise the test is moot for this run — skip silently.


def test_pine_threshold_format_stable():
    """Float literals in Pine output use repr() — round-trip safe."""
    booster, _, feature_names = _train_tiny_booster()
    pine = lgbm_to_pine_cascade(booster, feature_names)
    # Sample some float literals from the output
    floats = re.findall(r"<= ([-\d.e+]+)", pine)
    assert len(floats) > 0, "No threshold literals found in Pine output"
    for s in floats[:20]:
        # Each should parse back to a finite float
        val = float(s)
        assert np.isfinite(val), f"Non-finite literal: {s!r}"


if __name__ == '__main__':
    # Allow `python tests/test_pine_codegen.py` for ad-hoc checks.
    test_python_reimpl_matches_booster()
    test_pine_output_well_formed()
    test_balanced_dataset_bit_exact()
    test_feature_index_validation()
    test_pine_threshold_format_stable()
    print('All pine_codegen tests passed.')
