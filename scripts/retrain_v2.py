"""
Local retrain on 2022-2026 data (data/processed_v2/).

Steps:
  1. Generate triple-barrier labels from raw OHLCV
  2. Build extended feature files (_extended.parquet)
  3. Walk-forward split with updated date boundaries
  4. Train 3 seeds, 100 trees, NO early_stopping (v1b_100_noes params)
  5. VAL quantile cutoffs (q90/q97/q99) — no cluster detection
  6. Behavioral eval per seed + hold-out per pair
  7. Save best model to artifacts/models/

Run: py -3 scripts/retrain_v2.py
"""
from __future__ import annotations

import gc
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import lightgbm as lgb

from core.config import (
    FX_TRAIN_SYMBOLS, FX_HOLDOUT_SYMBOLS, HTF_CONTEXT_TIMEFRAMES,
)
from core.labeling import compute_triple_barrier_labels
from core.train.dataset import walk_forward_split, binary_label_for_long, NON_FEATURE_COLS
from core.features import (
    compute_features, attach_macro, attach_htf_context,
    compute_smc_features, compute_session_features, compute_htf_interactions,
)
from core.features.engineer import atr as atr_fn
from core.analysis.product_metrics import signals_per_day

# ── Config ─────────────────────────────────────────────────────────────────────
DATA_V2   = Path(__file__).parent.parent / "data" / "processed_v2"
DATA_EXT  = DATA_V2 / "extended"         # feature-engineered files
LABEL_DIR = DATA_V2 / "labels"           # triple-barrier labels
ARTIFACTS = Path(__file__).parent.parent / "artifacts" / "models"

DATA_EXT.mkdir(parents=True, exist_ok=True)
LABEL_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(parents=True, exist_ok=True)

TF          = "5m"
R_VALUE     = 1.5
WIN_R       = R_VALUE
SEEDS       = [42, 1, 7]

# Updated split dates for 2022-2026 data
TRAIN_END = datetime(2025, 1, 1, tzinfo=timezone.utc)
VAL_END   = datetime(2025, 7, 1, tzinfo=timezone.utc)
# Test: 2025-07-01 to 2026-05-29 (~11 months)

NY_SESSION_HOUR_START = 13
NY_SESSION_HOUR_END   = 22

PROFILES = {
    "Aggressive":   {"require_htf": False, "require_ny": False},
    "Balanced":     {"require_htf": True,  "require_ny": False},
    "Conservative": {"require_htf": True,  "require_ny": True},
}

# Fixed params — v1b_100_noes (no early_stopping)
BASE_PARAMS = {
    "objective": "binary", "metric": "binary_logloss",
    "num_leaves": 7, "max_depth": 3, "min_data_in_leaf": 200,
    "learning_rate": 0.05, "num_iterations": 100,
    "lambda_l2": 1.0, "feature_fraction": 0.8, "bagging_fraction": 0.8,
    "bagging_freq": 5, "is_unbalance": True,
    "verbose": -1, "n_jobs": -1,
}

RUN_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_raw(symbol: str, tf: str) -> pd.DataFrame | None:
    p = DATA_V2 / f"{symbol}_{tf}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def ensure_labels(symbol: str) -> pd.DataFrame | None:
    out = LABEL_DIR / f"labels_{symbol}_{TF}_R{R_VALUE}.parquet"
    if out.exists():
        return pd.read_parquet(out)
    ohlcv = load_raw(symbol, TF)
    if ohlcv is None or ohlcv.empty:
        return None
    print(f"  labeling {symbol} {TF}...", end="", flush=True)
    labels = compute_triple_barrier_labels(ohlcv, tp_R=R_VALUE, sl_atr_mult=1.0, time_barrier_bars=24)
    labels.to_parquet(out)
    win_rate = (labels["label"] == 1).mean()
    print(f" {len(labels):,} bars  WR={win_rate:.2%}")
    return labels


def ensure_extended(symbol: str) -> pd.DataFrame | None:
    out = DATA_EXT / f"{symbol}_{TF}_extended.parquet"
    if out.exists():
        df = pd.read_parquet(out)
        if "label" in df.columns:
            return df

    ohlcv = load_raw(symbol, TF)
    if ohlcv is None or ohlcv.empty:
        return None
    labels = ensure_labels(symbol)
    if labels is None:
        return None

    print(f"  features {symbol}...", end="", flush=True)
    base = compute_features(ohlcv)

    htf_data: dict[str, pd.DataFrame] = {}
    for htf in HTF_CONTEXT_TIMEFRAMES:
        d = load_raw(symbol, htf)
        htf_data[htf] = compute_features(d) if (d is not None and not d.empty) else pd.DataFrame()

    base = attach_htf_context(base, htf_data.get("1h", pd.DataFrame()), htf_data.get("4h", pd.DataFrame()))

    macro_path = DATA_V2 / "macro_daily.parquet"
    macro = pd.read_parquet(macro_path) if macro_path.exists() else pd.DataFrame()
    base = attach_macro(base, macro)

    atr14     = atr_fn(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14).values
    ema_align = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
    smc  = compute_smc_features(ohlcv, atr14, ema_align)
    sess = compute_session_features(ohlcv, atr14)
    inter = compute_htf_interactions(base)
    ext = pd.concat([base, smc, sess, inter], axis=1)

    cols_to_join = ["label"]
    if "hit_bar_offset" in labels.columns:
        cols_to_join.append("hit_bar_offset")
    ext = ext.join(labels[cols_to_join], how="inner")
    if "hit_bar_offset" not in ext.columns:
        ext["hit_bar_offset"] = 24
    ext["symbol"] = symbol
    ext.to_parquet(out, compression="zstd")
    print(f" {len(ext):,} rows saved")
    return ext


def train_seed(X_tr, y_tr, seed: int) -> lgb.Booster:
    params = dict(BASE_PARAMS, seed=seed)
    td = lgb.Dataset(X_tr, label=y_tr)
    model = lgb.train(params, td, callbacks=[lgb.log_evaluation(period=0)])
    assert model.num_trees() == 100, f"Expected 100 trees, got {model.num_trees()}"
    return model


def metrics_for_mask(labels_triple, mask, n_bars: int, n_symbols: int, durations=None) -> dict:
    n_sig = int(mask.sum())
    if n_sig == 0:
        return dict(n_trades=0, wins=0, losses=0, pf=0.0, wr=0.0,
                    sigs_per_day_per_symbol=0.0, mdd=0.0)
    labs = labels_triple[mask]
    wins   = int((labs == 1).sum())
    losses = int((labs == -1).sum())
    pf  = (wins * WIN_R) / losses if losses > 0 else (float("inf") if wins > 0 else 0.0)
    wr  = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    pnl = np.where(labs == 1, WIN_R, np.where(labs == -1, -1.0, 0.0))
    equity = np.cumsum(pnl)
    mdd = float((np.maximum.accumulate(equity) - equity).max())
    spd = signals_per_day(n_sig, n_bars, TF, n_symbols)
    return dict(n_trades=n_sig, wins=wins, losses=losses, pf=pf, wr=wr,
                sigs_per_day_per_symbol=spd, mdd=mdd)


def profile_mask(df, proba, cutoff: float, profile_name: str) -> np.ndarray:
    cfg = PROFILES[profile_name]
    mask = proba >= cutoff
    if cfg["require_htf"] and "htf_ltf_agree_bull" in df.columns:
        mask = mask & (df["htf_ltf_agree_bull"].values == 1)
    if cfg["require_ny"]:
        h = df.index.hour.values
        mask = mask & ((h >= NY_SESSION_HOUR_START) & (h < NY_SESSION_HOUR_END))
    return mask


# ── 1. Labels + Features ───────────────────────────────────────────────────────

ALL_SYMBOLS = FX_TRAIN_SYMBOLS + FX_HOLDOUT_SYMBOLS
print(f"\n=== Step 1: Labels + Features ({len(ALL_SYMBOLS)} symbols) ===")

missing = []
for sym in ALL_SYMBOLS:
    ext = ensure_extended(sym)
    if ext is None:
        missing.append(sym)

if missing:
    raise SystemExit(f"Feature-Engineering failed for: {missing}")

# ── 2. Build Training Pool ─────────────────────────────────────────────────────

print(f"\n=== Step 2: Build Pool (train: {FX_TRAIN_SYMBOLS}) ===")

frames = []
for sym in FX_TRAIN_SYMBOLS:
    d = pd.read_parquet(DATA_EXT / f"{sym}_{TF}_extended.parquet")
    d["symbol"] = sym
    frames.append(d.astype({c: "float32" for c in d.select_dtypes("float64").columns}))
pool = pd.concat(frames, axis=0).sort_index()
del frames; gc.collect()

probe = pool.head(1)
FEATURE_COLS = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
print(f"Features: {len(FEATURE_COLS)}")

pool_c = pool.dropna(subset=FEATURE_COLS + ["label"])
train_df, val_df, test_df = walk_forward_split(pool_c, TRAIN_END, VAL_END)
print(f"Train: {len(train_df):,}  Val: {len(val_df):,}  Test: {len(test_df):,}")

X_train = train_df[FEATURE_COLS].values.astype(np.float32)
y_train = binary_label_for_long(train_df["label"]).values
X_val   = val_df[FEATURE_COLS].values.astype(np.float32)
y_val   = binary_label_for_long(val_df["label"]).values
del pool, pool_c; gc.collect()

# ── 3. Train 3 Seeds ───────────────────────────────────────────────────────────

print(f"\n=== Step 3: Train (seeds={SEEDS}, 100 trees, no early_stopping) ===")

per_seed: dict = {}
for seed in SEEDS:
    print(f"  seed={seed}...", end="", flush=True)
    model = train_seed(X_train, y_train, seed)
    pv = model.predict(X_val)
    pt = model.predict(test_df[FEATURE_COLS].values.astype(np.float32))

    # VAL quantile cutoffs (q90/q97/q99) — no cluster detection
    cutoff_standard = float(np.quantile(pv, 0.90))
    cutoff_high     = float(np.quantile(pv, 0.97))
    cutoff_premium  = float(np.quantile(pv, 0.99))
    unique_probs    = len(np.unique(np.round(pv, 4)))

    per_seed[seed] = dict(
        model=model, proba_val=pv, proba_test=pt,
        cutoff_standard=cutoff_standard,
        cutoff_high=cutoff_high,
        cutoff_premium=cutoff_premium,
    )
    print(f"  trees={model.num_trees()}  unique_probs={unique_probs}"
          f"  q90={cutoff_standard:.4f}  q97={cutoff_high:.4f}  q99={cutoff_premium:.4f}")

# ── 4. In-Sample Eval (Test set = held-out from pool) ─────────────────────────

print(f"\n=== Step 4: In-Sample Eval (test split, {len(test_df):,} bars) ===")

test_labels = test_df["label"].values
in_sample_rows = []
for seed in SEEDS:
    data = per_seed[seed]
    cutoff = data["cutoff_premium"]
    for profile_name in PROFILES:
        mask = profile_mask(test_df, data["proba_test"], cutoff, profile_name)
        m = metrics_for_mask(test_labels, mask, len(test_df), len(FX_TRAIN_SYMBOLS))
        m["seed"] = seed; m["profile"] = profile_name; m["cutoff_used"] = cutoff
        in_sample_rows.append(m)

in_sample_df = pd.DataFrame(in_sample_rows)
print(in_sample_df[["seed", "profile", "n_trades", "pf", "wr", "mdd"]].to_string(index=False))

# ── 5. Hold-Out Eval (per symbol, unseen pairs) ────────────────────────────────

print(f"\n=== Step 5: Hold-Out Eval ({FX_HOLDOUT_SYMBOLS}) ===")

holdout_rows = []
for sym in FX_HOLDOUT_SYMBOLS:
    ho_ext = pd.read_parquet(DATA_EXT / f"{sym}_{TF}_extended.parquet")
    ho_ext = ho_ext.astype({c: "float32" for c in ho_ext.select_dtypes("float64").columns})
    ho_clean = ho_ext.dropna(subset=FEATURE_COLS + ["label"])
    # Hold-out window: same as test split (after VAL_END)
    ho = ho_clean[ho_clean.index >= VAL_END]
    if len(ho) == 0:
        print(f"  {sym}: no data after VAL_END — skipping")
        continue
    for seed in SEEDS:
        data = per_seed[seed]
        X_ho = ho[FEATURE_COLS].values.astype(np.float32)
        proba_ho = data["model"].predict(X_ho)
        cutoff = data["cutoff_premium"]
        for profile_name in PROFILES:
            mask = profile_mask(ho, proba_ho, cutoff, profile_name)
            m = metrics_for_mask(ho["label"].values, mask, len(ho), 1)
            m["symbol"] = sym; m["seed"] = seed; m["profile"] = profile_name
            holdout_rows.append(m)

holdout_df = pd.DataFrame(holdout_rows)
# Summary per symbol x profile (mean over seeds)
agg = holdout_df.groupby(["symbol", "profile"])[["n_trades", "pf", "wr"]].mean().round(2)
print(agg.to_string())

# ── 6. Best Seed Selection ─────────────────────────────────────────────────────

print(f"\n=== Step 6: Best Seed Selection ===")

seed_scores = []
for seed in SEEDS:
    sub = holdout_df[(holdout_df["seed"] == seed) & (holdout_df["profile"] == "Aggressive")]
    if sub.empty:
        continue
    wins = sub["wins"].sum(); losses = sub["losses"].sum()
    pf = (wins * WIN_R) / losses if losses > 0 else 0.0
    seed_scores.append(dict(seed=seed, aggressive_holdout_pf=round(pf, 3),
                            aggressive_total_trades=int(sub["n_trades"].sum()),
                            cutoff_premium=per_seed[seed]["cutoff_premium"]))

seed_scores.sort(key=lambda x: x["aggressive_holdout_pf"], reverse=True)
best = seed_scores[0]
BEST_SEED    = best["seed"]
BEST_CUTOFF  = best["cutoff_premium"]

print(f"Seed ranking: {seed_scores}")
print(f"BEST_SEED={BEST_SEED}  BEST_CUTOFF_PREMIUM={BEST_CUTOFF:.4f}")

# ── 7. Save Best Model ─────────────────────────────────────────────────────────

model_name = f"fx_v2_lgbm_seed{BEST_SEED}_100trees_{RUN_DATE}.txt"
model_path = ARTIFACTS / model_name
per_seed[BEST_SEED]["model"].save_model(str(model_path))
print(f"\nModel saved: {model_path}")

# ── 8. Output Summary JSON ─────────────────────────────────────────────────────

summary = {
    "run_date": RUN_DATE,
    "model_name": model_name,
    "train_end":  TRAIN_END.isoformat(),
    "val_end":    VAL_END.isoformat(),
    "best_seed":  BEST_SEED,
    "cutoffs": {
        "standard": per_seed[BEST_SEED]["cutoff_standard"],
        "high":     per_seed[BEST_SEED]["cutoff_high"],
        "premium":  per_seed[BEST_SEED]["cutoff_premium"],
    },
    "feature_cols": FEATURE_COLS,
    "n_features": len(FEATURE_COLS),
    "train_rows": int(len(train_df)),
    "val_rows":   int(len(val_df)),
    "test_rows":  int(len(test_df)),
    "seed_scores": seed_scores,
    "holdout_summary": agg.reset_index().to_dict("records"),
}

summary_path = ARTIFACTS / f"retrain_v2_summary_{RUN_DATE}.json"
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(f"Summary: {summary_path}")

print(f"""
=== DONE ===
Model: {model_name}
Best seed: {BEST_SEED}
Cutoffs:   standard={summary['cutoffs']['standard']:.4f}  high={summary['cutoffs']['high']:.4f}  premium={summary['cutoffs']['premium']:.4f}
""")
