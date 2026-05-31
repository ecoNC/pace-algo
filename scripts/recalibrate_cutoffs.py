"""
Cutoff Recalibration Script — PaceAlgo V1

Fetches 3 months of recent EURUSD 5m data, runs it through the existing
V1 booster, and computes new q90/q97/q99 cutoffs from the live distribution.
Updates deploy_pine/pace_algo_v1.pine with the new values.

Run: py -3 scripts/recalibrate_cutoffs.py
"""
import sys, glob, json, re, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import lightgbm as lgb

from core.features.engineer import compute_features
from core.train.dataset import NON_FEATURE_COLS

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SYMBOL    = "EURUSD"
TF        = "5m"
MONTHS    = 3          # how much recent data to use for calibration
QUANTILES = (0.90, 0.97, 0.99)

# ---------------------------------------------------------------------------
# Step 1 — Load booster
# ---------------------------------------------------------------------------
models = sorted(glob.glob(str(ROOT / "artifacts" / "models" / "*.txt")))
if not models:
    # Try downloading from GitHub as fallback
    print("No local model found — checking GitHub artifacts...")
    sys.exit("Please run NB15c in Colab first to generate the model, or place .txt model in artifacts/models/")

model_path = models[-1]
booster = lgb.Booster(model_file=model_path)
print(f"Booster loaded: {Path(model_path).name}")
print(f"  Trees: {booster.num_trees()}  Features: {booster.num_feature()}")

# Load feature order from snapshot
snap_path = ROOT / "results" / "nb15c" / "snapshot.json"
snap = json.load(open(snap_path, encoding="utf-8"))
FEATURE_COLS = snap["feature_cols_training"]
print(f"  Feature cols from snapshot: {len(FEATURE_COLS)}")

# ---------------------------------------------------------------------------
# Step 2 — Fetch recent data
# ---------------------------------------------------------------------------
from core.data.dukascopy_fetcher import fetch_dukascopy_ohlcv

end   = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
start = end - timedelta(days=MONTHS * 31)

print(f"\nFetching {SYMBOL} {TF} from {start.date()} to {end.date()} ...")
try:
    df = fetch_dukascopy_ohlcv(SYMBOL, TF, start, end)
    print(f"  Fetched {len(df):,} bars")
except Exception as e:
    sys.exit(f"Fetch failed: {e}\nCheck internet connection and dukascopy-python install.")

if len(df) < 500:
    sys.exit(f"Only {len(df)} bars fetched — too few for reliable calibration.")

# ---------------------------------------------------------------------------
# Step 3 — Compute features
# ---------------------------------------------------------------------------
print("\nComputing features...")
feat_df = compute_features(df)
feat_df["symbol"] = SYMBOL

# Keep only rows where all FEATURE_COLS are present
available = [c for c in FEATURE_COLS if c in feat_df.columns]
missing   = [c for c in FEATURE_COLS if c not in feat_df.columns]
if missing:
    print(f"  WARNING: {len(missing)} features not in engineer output: {missing}")
    print("  These will be filled with 0.0 (same as current Pine fallback)")

feat_df_clean = feat_df.dropna(subset=[c for c in available])
print(f"  Clean rows: {len(feat_df_clean):,} (dropped {len(feat_df) - len(feat_df_clean):,} NaN rows)")

# Build feature matrix with correct column order
X = np.zeros((len(feat_df_clean), len(FEATURE_COLS)), dtype=np.float32)
for i, col in enumerate(FEATURE_COLS):
    if col in feat_df_clean.columns:
        X[:, i] = feat_df_clean[col].values.astype(np.float32)

# ---------------------------------------------------------------------------
# Step 4 — Predict + compute new cutoffs
# ---------------------------------------------------------------------------
print("\nPredicting probabilities...")
probas = booster.predict(X)
print(f"  Probability stats:")
print(f"    n={len(probas):,}  mean={probas.mean():.4f}  std={probas.std():.4f}")
print(f"    min={probas.min():.4f}  max={probas.max():.4f}")

new_cutoffs = [float(np.quantile(probas, q)) for q in QUANTILES]
cutoff_std, cutoff_high, cutoff_prem = new_cutoffs

print(f"\n  New cutoffs (from {MONTHS}-month live distribution):")
print(f"    CUTOFF_STANDARD (q90) = {cutoff_std:.4f}  [was {snap['cutoffs']['CUTOFF_STANDARD']:.4f}]")
print(f"    CUTOFF_HIGH     (q97) = {cutoff_high:.4f}  [was {snap['cutoffs']['CUTOFF_HIGH']:.4f}]")
print(f"    CUTOFF_PREMIUM  (q99) = {cutoff_prem:.4f}  [was {snap['cutoffs']['CUTOFF_PREMIUM']:.4f}]")

delta_std  = cutoff_std  - snap["cutoffs"]["CUTOFF_STANDARD"]
delta_high = cutoff_high - snap["cutoffs"]["CUTOFF_HIGH"]
print(f"\n  Delta Standard: {delta_std:+.4f}  Delta High: {delta_high:+.4f}")

# ---------------------------------------------------------------------------
# Step 5 — Update Pine Script
# ---------------------------------------------------------------------------
pine_path = ROOT / "deploy_pine" / "pace_algo_v1.pine"
pine = pine_path.read_text(encoding="utf-8")

old_std  = snap["cutoffs"]["CUTOFF_STANDARD"]
old_high = snap["cutoffs"]["CUTOFF_HIGH"]
old_prem = snap["cutoffs"]["CUTOFF_PREMIUM"]

# Replace the exact cutoff values in the Pine file
pine_new = pine

replacements = [
    (f"var float CUTOFF_STANDARD = {old_std:.4f}", f"var float CUTOFF_STANDARD = {cutoff_std:.4f}"),
    (f"var float CUTOFF_HIGH     = {old_high:.4f}", f"var float CUTOFF_HIGH     = {cutoff_high:.4f}"),
    (f"var float CUTOFF_PREMIUM  = {old_prem:.4f}", f"var float CUTOFF_PREMIUM  = {cutoff_prem:.4f}"),
]

for old_str, new_str in replacements:
    if old_str not in pine_new:
        print(f"  WARNING: could not find '{old_str}' in Pine file — skipping")
    else:
        pine_new = pine_new.replace(old_str, new_str, 1)
        print(f"  Patched: {old_str} -> {new_str}")

# Sanity check
if f"CUTOFF_STANDARD = {old_std:.4f}" in pine_new:
    sys.exit("ERROR: old CUTOFF_STANDARD still present after patch")

pine_path.write_text(pine_new, encoding="utf-8")
print(f"\n  Written: {pine_path}")

# ---------------------------------------------------------------------------
# Step 6 — Save recalibration record
# ---------------------------------------------------------------------------
recal_dir = ROOT / "results" / "recalibration"
recal_dir.mkdir(parents=True, exist_ok=True)
recal_path = recal_dir / f"cutoffs_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
recal = {
    "date":          datetime.now(timezone.utc).isoformat(),
    "symbol":        SYMBOL,
    "tf":            TF,
    "n_bars":        len(probas),
    "start":         start.isoformat(),
    "end":           end.isoformat(),
    "proba_mean":    float(probas.mean()),
    "proba_std":     float(probas.std()),
    "proba_min":     float(probas.min()),
    "proba_max":     float(probas.max()),
    "old_cutoffs":   snap["cutoffs"],
    "new_cutoffs": {
        "CUTOFF_STANDARD": cutoff_std,
        "CUTOFF_HIGH":     cutoff_high,
        "CUTOFF_PREMIUM":  cutoff_prem,
    },
}
json.dump(recal, open(recal_path, "w", encoding="utf-8"), indent=2)
print(f"  Saved recalibration record: {recal_path}")

# ---------------------------------------------------------------------------
# Step 7 — Git commit + push
# ---------------------------------------------------------------------------
print("\nCommitting...")
try:
    subprocess.run(["git", "-C", str(ROOT), "add",
                    "deploy_pine/pace_algo_v1.pine",
                    "results/recalibration/"], check=True)
    msg = (f"recalibrate cutoffs from {MONTHS}m live {SYMBOL} {TF} distribution "
           f"(std={cutoff_std:.4f} high={cutoff_high:.4f} prem={cutoff_prem:.4f})")
    subprocess.run(["git", "-C", str(ROOT), "commit", "-m", msg], check=True)
    subprocess.run(["git", "-C", str(ROOT), "push", "origin", "main"], check=True)
    print("  Pushed to GitHub.")
except subprocess.CalledProcessError as e:
    print(f"  Git step failed: {e} — Pine file updated locally, push manually.")

print("\n=== DONE ===")
print(f"New CUTOFF_STANDARD = {cutoff_std:.4f}  ({(1-0.90)*100:.0f}% of bars will signal)")
print(f"New CUTOFF_HIGH     = {cutoff_high:.4f}  ({(1-0.97)*100:.0f}% of bars will signal)")
print(f"New CUTOFF_PREMIUM  = {cutoff_prem:.4f}  ({(1-0.99)*100:.0f}% of bars will signal)")
print("\nNext: reload pace_algo_v1.pine in TradingView Pine Editor.")
