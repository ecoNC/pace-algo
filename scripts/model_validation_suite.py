"""
Scientific Model Validation Suite — PaceAlgo FX core.

Controlled, reproducible audit answering: is the historical degeneracy an
early_stopping artifact, and which model config is ROBUSTLY STABLE (not just
highest PF)? Same data / features / splits / holdouts for every variant.

Matrix (x seeds 42/1/7):
  lgbm_es10_30   LGBM 30 trees + early_stopping(10)   <- reproduces the degenerate stump
  lgbm_noes_30   LGBM 30 trees, no early_stopping
  lgbm_noes_100  LGBM 100 trees, no early_stopping    <- production config (sanity anchor)
  lgbm_noes_300  LGBM 300 trees, no early_stopping
  xgb_100        XGBoost 100 trees (depth 3) baseline

Per variant x seed:
  1. Structural audit : num_trees, effective_trees (>0 gain), leaf-value spread
  2. Probability diag  : unique probs, 20-bin histogram, VAL q90/q97/q99 + separation,
                         calibration ECE + reliability table (test)
  3. Robustness        : per holdout pair WR/PF at each tier (overlapping label-eval),
                         regime stability (test split into 3 time slices)
  4. Seed drift        : aggregated across seeds (cutoff std, proba-mean std, PF/WR CV)

Output: results/model_validation/<UTC>/ {audit.json, REPORT.md}
Run: python scripts/model_validation_suite.py
"""
from __future__ import annotations

import sys, json, gc, warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import numpy as np
import pandas as pd
import lightgbm as lgb
try:
    import xgboost as xgb
    HAS_XGB = True
except Exception:
    HAS_XGB = False

from core.config import FX_TRAIN_SYMBOLS, FX_HOLDOUT_SYMBOLS, HTF_CONTEXT_TIMEFRAMES
from core.labeling import compute_triple_barrier_labels
from core.features import (
    compute_features, attach_macro, attach_htf_context,
    compute_smc_features, compute_session_features, compute_htf_interactions,
)
from core.features.engineer import atr as atr_fn
from core.train.dataset import walk_forward_split, binary_label_for_long, NON_FEATURE_COLS

# ── Config (mirror retrain_v2.py) ───────────────────────────────────────────────
DATA_V2  = REPO / "data" / "processed_v2"
DATA_EXT = DATA_V2 / "extended"
OUT_BASE = REPO / "results" / "model_validation"
TF, R_VALUE, WIN_R = "5m", 1.5, 1.5
SEEDS = [42, 1, 7]
TRAIN_END = datetime(2025, 1, 1, tzinfo=timezone.utc)
VAL_END   = datetime(2025, 7, 1, tzinfo=timezone.utc)

LGBM_BASE = dict(objective="binary", metric="binary_logloss",
                 num_leaves=7, max_depth=3, min_data_in_leaf=200,
                 learning_rate=0.05, lambda_l2=1.0, feature_fraction=0.8,
                 bagging_fraction=0.8, bagging_freq=5, is_unbalance=True,
                 verbose=-1, n_jobs=-1)

VARIANTS = [
    dict(name="lgbm_es10_30",  algo="lgbm", trees=30,  es=10),
    dict(name="lgbm_noes_30",  algo="lgbm", trees=30,  es=None),
    dict(name="lgbm_noes_100", algo="lgbm", trees=100, es=None),
    dict(name="lgbm_noes_300", algo="lgbm", trees=300, es=None),
    dict(name="xgb_100",       algo="xgb",  trees=100, es=None),
]

DATA_EXT.mkdir(parents=True, exist_ok=True)


# ── Data ─────────────────────────────────────────────────────────────────────
def load_raw(symbol, tf):
    p = DATA_V2 / f"{symbol}_{tf}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def build_extended(symbol):
    out = DATA_EXT / f"{symbol}_{TF}_extended.parquet"
    if out.exists():
        return pd.read_parquet(out)
    ohlcv = load_raw(symbol, TF)
    if ohlcv is None or ohlcv.empty:
        return None
    labels = compute_triple_barrier_labels(ohlcv, tp_R=R_VALUE, sl_atr_mult=1.0, time_barrier_bars=24)
    base = compute_features(ohlcv)
    htf = {}
    for h in HTF_CONTEXT_TIMEFRAMES:
        d = load_raw(symbol, h)
        htf[h] = compute_features(d) if (d is not None and not d.empty) else pd.DataFrame()
    base = attach_htf_context(base, htf.get("1h", pd.DataFrame()), htf.get("4h", pd.DataFrame()))
    macro_p = DATA_V2 / "macro_daily.parquet"
    base = attach_macro(base, pd.read_parquet(macro_p) if macro_p.exists() else pd.DataFrame())
    atr14 = atr_fn(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14).values
    ema_align = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
    ext = pd.concat([base, compute_smc_features(ohlcv, atr14, ema_align),
                     compute_session_features(ohlcv, atr14), compute_htf_interactions(base)], axis=1)
    cols = ["label"] + (["hit_bar_offset"] if "hit_bar_offset" in labels.columns else [])
    ext = ext.join(labels[cols], how="inner")
    if "hit_bar_offset" not in ext.columns:
        ext["hit_bar_offset"] = 24
    ext.to_parquet(out, compression="zstd")
    return ext


# ── Training ───────────────────────────────────────────────────────────────────
def train_lgbm(Xtr, ytr, Xval, yval, trees, es, seed):
    params = dict(LGBM_BASE, num_iterations=trees, seed=seed)
    cbs = [lgb.log_evaluation(period=0)]
    valid = None
    if es:
        valid = [lgb.Dataset(Xval, label=yval)]
        cbs.append(lgb.early_stopping(es, verbose=False))
    return lgb.train(params, lgb.Dataset(Xtr, label=ytr), valid_sets=valid, callbacks=cbs)


def train_xgb(Xtr, ytr, trees, seed):
    pos = max(1, int((ytr == 0).sum())); neg = max(1, int((ytr == 1).sum()))
    clf = xgb.XGBClassifier(n_estimators=trees, max_depth=3, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
                            scale_pos_weight=pos / neg, random_state=seed,
                            n_jobs=-1, eval_metric="logloss", verbosity=0)
    clf.fit(Xtr, ytr)
    return clf


def predict(model, algo, X):
    if algo == "lgbm":
        return model.predict(X)
    return model.predict_proba(X)[:, 1]


# ── Audits ───────────────────────────────────────────────────────────────────
def audit_structural(model, algo):
    if algo == "lgbm":
        n_trees = model.num_trees()
        df = model.trees_to_dataframe()
        gain_ok = df[df["split_gain"].notna() & (df["split_gain"] > 0)]
        eff = gain_ok["tree_index"].nunique()
        leaves = df[df["value"].notna() & df["left_child"].isna()]["value"].values \
            if "left_child" in df.columns else df[df["split_gain"].isna()]["value"].values
    else:
        booster = model.get_booster()
        df = booster.trees_to_dataframe()
        n_trees = df["Tree"].nunique()
        eff = df[df["Feature"] != "Leaf"]["Tree"].nunique()
        leaves = df[df["Feature"] == "Leaf"]["Gain"].values
    leaves = np.asarray(leaves, dtype=float)
    return dict(num_trees=int(n_trees), effective_trees=int(eff),
                n_leaf_values=int(len(leaves)),
                leaf_min=float(np.min(leaves)) if len(leaves) else None,
                leaf_max=float(np.max(leaves)) if len(leaves) else None,
                leaf_std=float(np.std(leaves)) if len(leaves) else None,
                leaf_range=float(np.ptp(leaves)) if len(leaves) else None)


def ece_reliability(proba, y, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(proba, edges) - 1, 0, bins - 1)
    e = 0.0; rel = []
    for b in range(bins):
        m = idx == b
        if not m.any():
            continue
        conf = float(proba[m].mean()); acc = float(y[m].mean()); n = int(m.sum())
        e += abs(conf - acc) * n / len(proba)
        rel.append(dict(bin=b, n=n, mean_pred=round(conf, 4), frac_pos=round(acc, 4)))
    return float(e), rel


def diagnostics(proba_val, proba_test, y_test):
    q90, q97, q99 = (float(np.quantile(proba_val, q)) for q in (0.90, 0.97, 0.99))
    counts, _ = np.histogram(proba_test, bins=20, range=(0.0, 1.0))
    e, rel = ece_reliability(proba_test, y_test)
    return dict(
        unique_probs=int(len(np.unique(np.round(proba_test, 4)))),
        proba_min=float(proba_test.min()), proba_max=float(proba_test.max()),
        proba_mean=float(proba_test.mean()), proba_std=float(proba_test.std()),
        q90=q90, q97=q97, q99=q99,
        sep_q90_q99=round(q99 - q90, 4), sep_q97_q99=round(q99 - q97, 4),
        hist20=counts.tolist(), ece=round(e, 4), reliability=rel,
    )


def wr_pf_overlapping(labels):
    w = int((labels == 1).sum()); l = int((labels == -1).sum())
    pf = (w * WIN_R) / l if l > 0 else (float("inf") if w > 0 else 0.0)
    wr = w / (w + l) if (w + l) > 0 else 0.0
    return dict(n=w + l, wr=round(wr, 4), pf=round(pf, 3))


def regime_stability(proba_test, test_labels, idx_dt, cutoff):
    """Split test into 3 contiguous time slices; PF at given cutoff per slice."""
    n = len(proba_test); thirds = [slice(0, n // 3), slice(n // 3, 2 * n // 3), slice(2 * n // 3, n)]
    pfs = []
    for s in thirds:
        m = proba_test[s] >= cutoff
        pfs.append(wr_pf_overlapping(test_labels[s][m])["pf"])
    finite = [p for p in pfs if np.isfinite(p)]
    cv = float(np.std(finite) / np.mean(finite)) if finite and np.mean(finite) > 0 else None
    return dict(pf_by_third=[round(p, 3) for p in pfs], pf_cv=round(cv, 3) if cv is not None else None)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build pool (train symbols) + holdouts
    missing = [s for s in (FX_TRAIN_SYMBOLS + FX_HOLDOUT_SYMBOLS) if load_raw(s, TF) is None]
    if missing:
        raise SystemExit(f"Missing raw 5m data for: {missing} — run scripts/fetch_v2_data.py first")

    frames = []
    for s in FX_TRAIN_SYMBOLS:
        d = build_extended(s); d["symbol"] = s
        frames.append(d.astype({c: "float32" for c in d.select_dtypes("float64").columns}))
    pool = pd.concat(frames).sort_index()
    FEATURE_COLS = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
    pool_c = pool.dropna(subset=FEATURE_COLS + ["label"])
    train_df, val_df, test_df = walk_forward_split(pool_c, TRAIN_END, VAL_END)
    del frames, pool, pool_c; gc.collect()

    Xtr = train_df[FEATURE_COLS].values.astype(np.float32); ytr = binary_label_for_long(train_df["label"]).values
    Xval = val_df[FEATURE_COLS].values.astype(np.float32);   yval = binary_label_for_long(val_df["label"]).values
    Xte = test_df[FEATURE_COLS].values.astype(np.float32)
    yte = binary_label_for_long(test_df["label"]).values
    test_labels = test_df["label"].values.astype(int)

    holdouts = {}
    for s in FX_HOLDOUT_SYMBOLS:
        h = build_extended(s)
        h = h.dropna(subset=FEATURE_COLS + ["label"])
        h = h[h.index >= VAL_END]
        holdouts[s] = h

    print(f"Features={len(FEATURE_COLS)}  Train={len(train_df):,} Val={len(val_df):,} Test={len(test_df):,}")
    print(f"Holdouts: {[(s, len(h)) for s, h in holdouts.items()]}\n")

    results = []
    for v in VARIANTS:
        if v["algo"] == "xgb" and not HAS_XGB:
            print(f"  {v['name']}: xgboost not installed — skip"); continue
        for seed in SEEDS:
            if v["algo"] == "lgbm":
                model = train_lgbm(Xtr, ytr, Xval, yval, v["trees"], v["es"], seed)
            else:
                model = train_xgb(Xtr, ytr, v["trees"], seed)
            pv = predict(model, v["algo"], Xval)
            pt = predict(model, v["algo"], Xte)

            audit = audit_structural(model, v["algo"])
            diag = diagnostics(pv, pt, yte)

            # robustness per holdout pair at this model's own VAL cutoffs
            tiers = {"q90": diag["q90"], "q97": diag["q97"], "q99": diag["q99"]}
            ho = {}
            for s, h in holdouts.items():
                ph = predict(model, v["algo"], h[FEATURE_COLS].values.astype(np.float32))
                hl = h["label"].values.astype(int)
                ho[s] = {t: wr_pf_overlapping(hl[ph >= c]) for t, c in tiers.items()}
            regime = regime_stability(pt, test_labels, test_df.index, tiers["q97"])

            row = dict(variant=v["name"], seed=seed, **audit, **{f"diag_{k}": diag[k] for k in
                       ("unique_probs", "proba_min", "proba_max", "proba_mean", "proba_std",
                        "q90", "q97", "q99", "sep_q90_q99", "ece")},
                       hist20=diag["hist20"], reliability=diag["reliability"],
                       holdout=ho, regime=regime)
            results.append(row)
            print(f"  {v['name']:14s} seed={seed}  trees={audit['num_trees']:3d} eff={audit['effective_trees']:3d} "
                  f"uniq={diag['unique_probs']:5d}  q90/97/99={diag['q90']:.3f}/{diag['q97']:.3f}/{diag['q99']:.3f} "
                  f"ECE={diag['ece']:.3f}")

    (out_dir / "audit.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_report(out_dir, results)
    print(f"\nDone -> {out_dir}")


def write_report(out_dir, results):
    df = pd.DataFrame(results)
    lines = ["# Model Validation Report", "",
             f"Generated: {out_dir.name}", "",
             "## 1. Structural audit + probability diagnostics (mean over seeds)", ""]
    g = df.groupby("variant")
    lines.append("| variant | num_trees | eff_trees | uniq_probs | leaf_range | q90 | q97 | q99 | sep90-99 | ECE |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for name, sub in g:
        lines.append("| {} | {:.0f} | {:.0f} | {:.0f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |".format(
            name, sub["num_trees"].mean(), sub["effective_trees"].mean(), sub["diag_unique_probs"].mean(),
            sub["leaf_range"].mean(), sub["diag_q90"].mean(), sub["diag_q97"].mean(), sub["diag_q99"].mean(),
            sub["diag_sep_q90_q99"].mean(), sub["diag_ece"].mean()))

    lines += ["", "## 2. Seed drift (std across seeds)", "",
              "| variant | q90_std | q97_std | q99_std | proba_mean_std | uniq_probs_std |",
              "|---|---|---|---|---|---|"]
    for name, sub in g:
        lines.append("| {} | {:.5f} | {:.5f} | {:.5f} | {:.5f} | {:.1f} |".format(
            name, sub["diag_q90"].std(), sub["diag_q97"].std(), sub["diag_q99"].std(),
            sub["diag_proba_mean"].std(), sub["diag_unique_probs"].std()))

    lines += ["", "## 3. Holdout robustness — PF @ q97 (mean / std over seeds)", "",
              "| variant | " + " | ".join(FX_HOLDOUT_SYMBOLS) + " | regime_pf_cv |",
              "|---|" + "|".join(["---"] * (len(FX_HOLDOUT_SYMBOLS) + 1)) + "|"]
    for name, sub in g:
        cells = []
        for s in FX_HOLDOUT_SYMBOLS:
            pfs = [r["holdout"][s]["q97"]["pf"] for _, r in sub.iterrows() if np.isfinite(r["holdout"][s]["q97"]["pf"])]
            cells.append(f"{np.mean(pfs):.2f}/{np.std(pfs):.2f}" if pfs else "n/a")
        cvs = [r["regime"]["pf_cv"] for _, r in sub.iterrows() if r["regime"]["pf_cv"] is not None]
        cells.append(f"{np.mean(cvs):.2f}" if cvs else "n/a")
        lines.append("| {} | {} |".format(name, " | ".join(cells)))

    lines += ["", "## Interpretation hooks", "",
              "- Degenerate stump signature: effective_trees≈1, uniq_probs tiny (<30), leaf_range tiny, huge seed drift.",
              "- Healthy ensemble: effective_trees≈num_trees, uniq_probs in thousands, smooth hist, low seed drift, low ECE.",
              "- 'Survives stably' = holdout PF mean>1 across ALL pairs with low std + low regime_pf_cv.", ""]
    (out_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
