"""
Local Pine export for v2 model → deploy_pine/pace_algo_v1.pine

Loads the pre-trained fx_v2_lgbm_seed7_100trees model, recomputes VAL cutoffs,
generates Pine code, patches skeleton, runs bit-exact check.

Run: py -3 scripts/pine_export_v2.py
"""
from __future__ import annotations

import gc
import json
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import lightgbm as lgb

from core.config import FX_TRAIN_SYMBOLS
from core.train.dataset import walk_forward_split, binary_label_for_long, NON_FEATURE_COLS
from core.export import pine_codegen as pcg
from core.export.pine_codegen import (
    lgbm_to_pine_cascade, extract_feature_usage, estimate_pine_ops,
    bit_exact_check, feature_registry_hash, used_feature_list_hash,
)
from core.export.pine_features import render_feature_engine, FEATURE_REGISTRY

# ── Config ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).parent.parent
DATA_EXT      = PROJECT_ROOT / "data" / "processed_v2" / "extended"
ARTIFACTS     = PROJECT_ROOT / "artifacts" / "models"
OUTPUT_DIR    = PROJECT_ROOT / "results" / "nb15c"
SKELETON_PATH = PROJECT_ROOT / "deploy_pine" / "pace_algo_v1_skeleton.pine"
OUTPUT_PINE   = PROJECT_ROOT / "deploy_pine" / "pace_algo_v1.pine"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TF               = "5m"
PRODUCTION_SEED  = 7
MODEL_NAME       = f"fx_v2_lgbm_seed{PRODUCTION_SEED}_100trees_2026-05-31.txt"
MODEL_PATH       = ARTIFACTS / MODEL_NAME

# Updated split dates (must match retrain_v2.py)
from datetime import timezone as _tz
TRAIN_END = datetime(2025, 1, 1, tzinfo=_tz.utc)
VAL_END   = datetime(2025, 7, 1, tzinfo=_tz.utc)

RUN_DATE      = datetime.now(timezone.utc).strftime("%Y-%m-%d")
RUN_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
try:
    GIT_COMMIT = subprocess.check_output(
        ["git", "-C", str(PROJECT_ROOT), "rev-parse", "--short", "HEAD"], text=True
    ).strip()
except Exception:
    GIT_COMMIT = "unknown"
EXPERIMENT_ID = f"nb15c_v2_{RUN_TIMESTAMP}_{GIT_COMMIT}"

print(f"EXPERIMENT_ID: {EXPERIMENT_ID}")
print(f"Model:         {MODEL_NAME}")
print(f"pine_codegen:  v{pcg.__version__}")
print(f"Registry:      {len(FEATURE_REGISTRY)} features")

# ── S1: Load Extended Data + VAL Split ────────────────────────────────────────

print("\n=== S1: Load Data ===")

def load_ext(sym: str) -> pd.DataFrame | None:
    p = DATA_EXT / f"{sym}_{TF}_extended.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    if "hit_bar_offset" not in df.columns:
        df["hit_bar_offset"] = 24
    return df

missing = [s for s in FX_TRAIN_SYMBOLS if load_ext(s) is None]
if missing:
    raise SystemExit(f"Missing extended files: {missing} — run retrain_v2.py first")

frames = []
for sym in FX_TRAIN_SYMBOLS:
    d = load_ext(sym)
    d["symbol"] = sym
    frames.append(d.astype({c: "float32" for c in d.select_dtypes("float64").columns}))
pool = pd.concat(frames, axis=0).sort_index()
del frames; gc.collect()

FEATURE_COLS = [c for c in load_ext(FX_TRAIN_SYMBOLS[0]).columns
                if c not in NON_FEATURE_COLS and c != "symbol"]
print(f"Features: {len(FEATURE_COLS)}")

pool_c = pool.dropna(subset=FEATURE_COLS + ["label"])
train_df, val_df, test_df = walk_forward_split(pool_c, TRAIN_END, VAL_END)
print(f"Train: {len(train_df):,}  Val: {len(val_df):,}  Test: {len(test_df):,}")

X_train = train_df[FEATURE_COLS].values.astype(np.float32)
y_train = binary_label_for_long(train_df["label"]).values
X_val   = val_df[FEATURE_COLS].values.astype(np.float32)
X_test  = test_df[FEATURE_COLS].values.astype(np.float32)
del pool, pool_c; gc.collect()

# ── S2: Load Model ─────────────────────────────────────────────────────────────

print("\n=== S2: Load Model ===")
if not MODEL_PATH.exists():
    raise SystemExit(f"Model not found: {MODEL_PATH} — run retrain_v2.py first")

booster = lgb.Booster(model_file=str(MODEL_PATH))
n_trees = booster.num_trees()
print(f"Loaded: {MODEL_NAME}  trees={n_trees}")
if n_trees != 100:
    raise SystemExit(f"V1 LOCK VIOLATION: expected 100 trees, got {n_trees}")

# ── S3: VAL Cutoffs ────────────────────────────────────────────────────────────

print("\n=== S3: VAL Cutoffs ===")
proba_val = booster.predict(X_val)
CUTOFF_STANDARD = float(np.quantile(proba_val, 0.90))
CUTOFF_HIGH     = float(np.quantile(proba_val, 0.97))
CUTOFF_PREMIUM  = float(np.quantile(proba_val, 0.99))

unique_4dp = len(np.unique(np.round(proba_val, 4)))
print(f"VAL proba range: [{proba_val.min():.4f}, {proba_val.max():.4f}]")
print(f"Unique VAL probs (4dp): {unique_4dp}")
print(f"CUTOFF_STANDARD = {CUTOFF_STANDARD:.4f}  (q90)")
print(f"CUTOFF_HIGH     = {CUTOFF_HIGH:.4f}  (q97)")
print(f"CUTOFF_PREMIUM  = {CUTOFF_PREMIUM:.4f}  (q99)")

if unique_4dp < 50:
    raise SystemExit(f"SANITY FAIL: only {unique_4dp} unique probs — model may be degenerate (early_stopping regression?)")
if not (CUTOFF_PREMIUM >= CUTOFF_HIGH >= CUTOFF_STANDARD):
    raise SystemExit(f"Cutoffs not monotone: P={CUTOFF_PREMIUM}, H={CUTOFF_HIGH}, S={CUTOFF_STANDARD}")

# ── S4: Feature Usage ──────────────────────────────────────────────────────────

print("\n=== S4: Feature Usage ===")
usage = extract_feature_usage(booster, FEATURE_COLS)
print(f"Features in training: {len(FEATURE_COLS)}")
print(f"Features used:        {usage['n_features_referenced']}")
print(f"Features unused:      {len(usage['unused_features'])}")
print("\nTop 10 by split_count:")
for d in usage["details"][:10]:
    print(f"  {d['feature_name']:35s} splits={d['split_count']:3d}  trees={d['used_in_tree_count']:3d}  gain={d['avg_gain']:.4f}")
print(f"\nUnused: {usage['unused_features'][:5]}{'...' if len(usage['unused_features'])>5 else ''}")

usage_path = OUTPUT_DIR / "feature_usage.json"
with open(usage_path, "w") as f:
    json.dump(usage, f, indent=2, default=str)

# ── S5: Pine Feature Engine ────────────────────────────────────────────────────

print("\n=== S5: Pine Feature Engine ===")
used = usage["used_features"]
engine = render_feature_engine(used)

if engine["dropped_features"]:
    print(f"SOFT-FAIL: {len(engine['dropped_features'])} features without Pine impl (substituted 0.0):")
    for f in engine["dropped_features"]:
        print(f"  - {f}")
else:
    print(f"All {len(used)} used features have Pine implementations.")

print(f"Feature engine: implemented={len(used)-len(engine['dropped_features'])}  dropped={len(engine['dropped_features'])}")

# ── S6: Tree Cascade ──────────────────────────────────────────────────────────

print("\n=== S6: Tree Cascade ===")
pine_cascade = lgbm_to_pine_cascade(booster, FEATURE_COLS)
cascade_lines = pine_cascade.count("\n")
print(f"Cascade: {cascade_lines} lines, {len(pine_cascade):,} bytes")
print("First 4 lines:")
for line in pine_cascade.split("\n")[:4]:
    print(f"  {line}")

# ── S7: Patch Skeleton ─────────────────────────────────────────────────────────

print("\n=== S7: Patch Skeleton ===")
skeleton = SKELETON_PATH.read_text(encoding="utf-8")

# Build the replacement block (feature engine + cascade)
replacement_block = (
    f"// === BUILD 2 INSERT: V1 Feature Engine + Tree Cascade ===\n"
    f"// Source: {EXPERIMENT_ID}, booster seed={PRODUCTION_SEED}, {n_trees} trees\n"
    f"// pine_codegen v{pcg.__version__} - auto-generated, DO NOT EDIT\n\n"
    f"{engine['helpers'].rstrip()}\n\n"
    f"{engine['htf'].rstrip()}\n\n"
    f"{engine['features'].rstrip()}\n\n"
    f"{pine_cascade.rstrip()}"
)

PLACEHOLDER_START = "f_signal_probability_placeholder() =>"
old_call = "probability = f_signal_probability_placeholder()"
new_call  = f"probability = f_pace_algo_v1_probability({engine['feature_arg_list']})"

if PLACEHOLDER_START not in skeleton:
    raise SystemExit("PLACEHOLDER_START not found in skeleton — check deploy_pine/pace_algo_v1_skeleton.pine")
if old_call not in skeleton:
    raise SystemExit(f"old_call not found in skeleton: {old_call}")

ps = skeleton.index(PLACEHOLDER_START)
pe = skeleton.index(old_call) + len(old_call)
patched = skeleton[:ps] + replacement_block + "\n\n" + new_call + skeleton[pe:]

# Patch cutoffs (skeleton defaults: 0.55 / 0.60 / 0.65)
patched = patched.replace("var float CUTOFF_STANDARD = 0.55", f"var float CUTOFF_STANDARD = {CUTOFF_STANDARD:.4f}", 1)
patched = patched.replace("var float CUTOFF_HIGH     = 0.60", f"var float CUTOFF_HIGH     = {CUTOFF_HIGH:.4f}", 1)
patched = patched.replace("var float CUTOFF_PREMIUM  = 0.65", f"var float CUTOFF_PREMIUM  = {CUTOFF_PREMIUM:.4f}", 1)
print(f"Cutoffs patched: STANDARD={CUTOFF_STANDARD:.4f}  HIGH={CUTOFF_HIGH:.4f}  PREMIUM={CUTOFF_PREMIUM:.4f}")

# Sanity: no placeholder strings left
LEFTOVERS = ["f_signal_probability_placeholder", "CUTOFF_STANDARD = 0.55",
             "CUTOFF_HIGH     = 0.60", "CUTOFF_PREMIUM  = 0.65"]
remaining = [l for l in LEFTOVERS if l in patched]
if remaining:
    raise SystemExit(f"Placeholders still present after patch: {remaining}")

OUTPUT_PINE.write_text(patched, encoding="utf-8")
print(f"Pine written: {OUTPUT_PINE}  ({len(patched):,} bytes, {patched.count(chr(10))} lines)")

# ── S8: Budget Check ──────────────────────────────────────────────────────────

print("\n=== S8: Budget Check ===")
budget = estimate_pine_ops(patched, pine_budget_per_bar=5000, request_security_budget=40)
print(f"ops/bar:        {budget['ops_estimate']:,}  ({budget['ops_pct_of_budget']:.1%} of 5000)")
print(f"request.security: {budget['request_security_calls']}/{budget['request_security_budget']}  ({budget['request_security_pct_of_budget']:.1%})")
print(f"function_count: {budget['function_count']}")
print(f"total lines:    {budget['n_lines']:,}")
print(f"total bytes:    {budget['n_bytes']:,}")
if budget["ops_pct_of_budget"] > 0.90:
    print("WARN: ops > 90% budget — TradingView may reject. Consider feature reduction.")
elif budget["ops_pct_of_budget"] > 0.70:
    print("NOTE: ops > 70% budget — acceptable, TV compiler is source of truth.")

# ── S9: Bit-Exact Check ───────────────────────────────────────────────────────

print("\n=== S9: Bit-Exact Check ===")
N_SAMPLES = 10_000
sample_idx = np.random.default_rng(42).choice(len(X_test), min(N_SAMPLES, len(X_test)), replace=False)
X_check = X_test[sample_idx]

check = bit_exact_check(booster, FEATURE_COLS, X_check, atol=1e-5)
print(f"n_samples:    {check['n_samples']}")
print(f"max_abs_diff: {check['max_abs_diff']:.2e}")
print(f"rmse:         {check['rmse']:.2e}")
print(f"passed:       {check['passed']}")
if not check["passed"]:
    raise SystemExit(f"BIT-EXACT FAILED: max_abs_diff={check['max_abs_diff']:.2e} > 1e-5")

bit_exact_path = OUTPUT_DIR / "bit_exact.json"
with open(bit_exact_path, "w") as f:
    json.dump(check, f, indent=2, default=str)

# ── S10: Snapshot JSON ────────────────────────────────────────────────────────

print("\n=== S10: Snapshot ===")
feat_reg_hash = feature_registry_hash(FEATURE_REGISTRY)
used_hash     = used_feature_list_hash(used)

snapshot = {
    "experiment_id":          EXPERIMENT_ID,
    "run_date":               RUN_DATE,
    "git_commit":             GIT_COMMIT,
    "production_seed":        PRODUCTION_SEED,
    "model_name":             MODEL_NAME,
    "n_trees":                n_trees,
    "feature_cols_training":  FEATURE_COLS,
    "feature_cols_used":      used,
    "feature_cols_unused":    usage["unused_features"],
    "dropped_features":       engine["dropped_features"],
    "cutoffs": {
        "CUTOFF_STANDARD": CUTOFF_STANDARD,
        "CUTOFF_HIGH":     CUTOFF_HIGH,
        "CUTOFF_PREMIUM":  CUTOFF_PREMIUM,
    },
    "bit_exact": {
        "passed":       check["passed"],
        "max_abs_diff": check["max_abs_diff"],
        "rmse":         check["rmse"],
    },
    "budget": {
        "ops_estimate":    budget["ops_estimate"],
        "ops_pct":         budget["ops_pct_of_budget"],
        "request_security": budget["request_security_calls"],
        "n_lines":          budget["n_lines"],
    },
    "feature_registry_hash":  feat_reg_hash,
    "used_feature_list_hash": used_hash,
    "pine_codegen_version":   pcg.__version__,
}

snapshot_path = OUTPUT_DIR / f"snapshot_{RUN_DATE}.json"
with open(snapshot_path, "w") as f:
    json.dump(snapshot, f, indent=2, default=str)
print(f"Snapshot: {snapshot_path}")
print(f"feature_registry_hash:  {feat_reg_hash}")
print(f"used_feature_list_hash: {used_hash}")

print(f"""
=== DONE ===
Pine file: {OUTPUT_PINE}
Bit-exact: passed={check['passed']}  max_diff={check['max_abs_diff']:.2e}
Budget:    ops={budget['ops_estimate']} ({budget['ops_pct_of_budget']:.0%})  lines={budget['n_lines']}
Cutoffs:   STD={CUTOFF_STANDARD:.4f}  HIGH={CUTOFF_HIGH:.4f}  PREM={CUTOFF_PREMIUM:.4f}
Dropped:   {engine['dropped_features']}
""")
