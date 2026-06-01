"""
WR-Gap Analysis — isolate methodology vs real edge in the live-vs-validated gap.

For each holdout pair on the Dukascopy TEST period (>= 2025-07-01), at each
cutoff tier (q90/q97/q99), compute WR/PF two ways on the SAME signals:

  Method A (overlapping)      — every signal bar's triple-barrier label counted
                                independently. THIS is what retrain_v2.py's
                                metrics_for_mask did -> the validated PF 1.93 etc.
  Method B (non-overlapping)  — one position at a time: enter on signal when flat,
                                skip signals until the trade resolves (via
                                hit_bar_offset). Mirrors the Pine tradeable sim.

A vs B on identical data isolates the OVERLAP effect.
Sanity check: Method A @ q99 should reproduce validated "Aggressive" numbers
(retrain_v2 used cutoff_premium=q99 for its "Aggressive" profile).

Run: python scripts/wr_gap_analysis.py
"""
from __future__ import annotations

import sys
import json
import warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import numpy as np
import pandas as pd
import lightgbm as lgb

from core.config import FX_HOLDOUT_SYMBOLS, HTF_CONTEXT_TIMEFRAMES
from core.labeling import compute_triple_barrier_labels
from core.features import (
    compute_features, attach_macro, attach_htf_context,
    compute_smc_features, compute_session_features, compute_htf_interactions,
)
from core.features.engineer import atr as atr_fn

# ── Config (mirror retrain_v2.py) ───────────────────────────────────────────────
DATA_V2  = REPO / "data" / "processed_v2"
ARTIFACTS = REPO / "artifacts" / "models"
MODEL_PATH = ARTIFACTS / "fx_v2_lgbm_seed7_100trees_2026-05-31.txt"
SUMMARY    = ARTIFACTS / "retrain_v2_summary_2026-05-31.json"
TF       = "5m"
R_VALUE  = 1.5
WIN_R    = R_VALUE
VAL_END  = datetime(2025, 7, 1, tzinfo=timezone.utc)   # test window start

summary = json.loads(SUMMARY.read_text())
FEATURE_COLS = summary["feature_cols"]
CUTOFFS = {
    "q90 (Pine Aggressive)":   summary["cutoffs"]["standard"],
    "q97 (Pine Balanced)":     summary["cutoffs"]["high"],
    "q99 (Pine Conserv./val.Agg)": summary["cutoffs"]["premium"],
}


def load_raw(symbol, tf):
    p = DATA_V2 / f"{symbol}_{tf}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def build_extended(symbol):
    """Replicate retrain_v2.ensure_extended (features + label + hit_bar_offset)."""
    ohlcv = load_raw(symbol, TF)
    if ohlcv is None or ohlcv.empty:
        return None
    labels = compute_triple_barrier_labels(ohlcv, tp_R=R_VALUE, sl_atr_mult=1.0, time_barrier_bars=24)

    base = compute_features(ohlcv)
    htf_data = {}
    for htf in HTF_CONTEXT_TIMEFRAMES:
        d = load_raw(symbol, htf)
        htf_data[htf] = compute_features(d) if (d is not None and not d.empty) else pd.DataFrame()
    base = attach_htf_context(base, htf_data.get("1h", pd.DataFrame()), htf_data.get("4h", pd.DataFrame()))

    macro_path = DATA_V2 / "macro_daily.parquet"
    macro = pd.read_parquet(macro_path) if macro_path.exists() else pd.DataFrame()
    base = attach_macro(base, macro)

    atr14 = atr_fn(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14).values
    ema_align = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
    smc = compute_smc_features(ohlcv, atr14, ema_align)
    sess = compute_session_features(ohlcv, atr14)
    inter = compute_htf_interactions(base)
    ext = pd.concat([base, smc, sess, inter], axis=1)

    cols = ["label"] + (["hit_bar_offset"] if "hit_bar_offset" in labels.columns else [])
    ext = ext.join(labels[cols], how="inner")
    if "hit_bar_offset" not in ext.columns:
        ext["hit_bar_offset"] = 24
    return ext


def metrics_overlapping(labels):
    """Method A: count every signal bar's label."""
    wins = int((labels == 1).sum())
    losses = int((labels == -1).sum())
    neut = int((labels == 0).sum())
    n = wins + losses
    pf = (wins * WIN_R) / losses if losses > 0 else (float("inf") if wins > 0 else 0.0)
    wr = wins / n if n > 0 else 0.0
    return dict(n=wins + losses + neut, wins=wins, losses=losses, neut=neut, wr=wr, pf=pf)


def metrics_nonoverlapping(mask, labels, hit):
    """Method B: greedy one-position-at-a-time using hit_bar_offset for resolution."""
    sig_pos = np.where(mask)[0]
    taken = []
    next_free = -1
    for p in sig_pos:
        if p > next_free:
            taken.append(int(labels[p]))
            next_free = p + int(hit[p])   # trade resolves hit bars later
    taken = np.array(taken, dtype=int)
    wins = int((taken == 1).sum())
    losses = int((taken == -1).sum())
    neut = int((taken == 0).sum())
    n = wins + losses
    pf = (wins * WIN_R) / losses if losses > 0 else (float("inf") if wins > 0 else 0.0)
    wr = wins / n if n > 0 else 0.0
    return dict(n=len(taken), wins=wins, losses=losses, neut=neut, wr=wr, pf=pf)


def main():
    # Load via model_str with LF-normalized newlines — git may have checked the
    # file out with CRLF, which breaks LightGBM's tree_sizes byte-offset parser.
    model_str = MODEL_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    model = lgb.Booster(model_str=model_str)
    print(f"Model: {MODEL_PATH.name}  trees={model.num_trees()}  n_features={len(FEATURE_COLS)}")
    print(f"Holdout symbols: {FX_HOLDOUT_SYMBOLS}   test window >= {VAL_END.date()}\n")

    # accumulate pooled label arrays per cutoff per method
    rows = []
    pooled = {c: {"A": [], "B": []} for c in CUTOFFS}

    for sym in FX_HOLDOUT_SYMBOLS:
        ext = build_extended(sym)
        if ext is None:
            print(f"  {sym}: no data — skip"); continue
        ext = ext[ext.index >= VAL_END]
        ext = ext.dropna(subset=FEATURE_COLS + ["label"])
        if len(ext) == 0:
            print(f"  {sym}: no test rows — skip"); continue
        X = ext[FEATURE_COLS].values.astype(np.float32)
        proba = model.predict(X)
        labels = ext["label"].values.astype(int)
        hit = ext["hit_bar_offset"].values.astype(int)

        for cname, cval in CUTOFFS.items():
            mask = proba >= cval
            A = metrics_overlapping(labels[mask])
            B = metrics_nonoverlapping(mask, labels, hit)
            rows.append(dict(symbol=sym, cutoff=cname,
                             A_n=A["wins"]+A["losses"], A_wr=A["wr"], A_pf=A["pf"],
                             B_n=B["wins"]+B["losses"], B_wr=B["wr"], B_pf=B["pf"],
                             B_neut=B["neut"]))
            pooled[cname]["A"].append(labels[mask])
            # store taken trades for B pooling: re-derive
            pooled[cname]["B"].append((mask, labels, hit))

    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", lambda v: f"{v:.2f}")
    print("=== PER-SYMBOL: Method A (overlapping=validated) vs B (non-overlapping=tradeable) ===")
    print(df.to_string(index=False))

    print("\n=== POOLED across holdout pairs ===")
    for cname in CUTOFFS:
        a_labels = np.concatenate(pooled[cname]["A"]) if pooled[cname]["A"] else np.array([])
        A = metrics_overlapping(a_labels)
        # pooled B: sum taken trades across symbols
        bw = bl = bn = 0
        for (mask, labels, hit) in pooled[cname]["B"]:
            B = metrics_nonoverlapping(mask, labels, hit)
            bw += B["wins"]; bl += B["losses"]; bn += B["neut"]
        b_pf = (bw * WIN_R) / bl if bl > 0 else 0.0
        b_wr = bw / (bw + bl) if (bw + bl) > 0 else 0.0
        print(f"\n{cname}:")
        print(f"  A overlapping : n={A['wins']+A['losses']:5d}  WR={A['wr']:.1%}  PF={A['pf']:.2f}")
        print(f"  B tradeable   : n={bw+bl:5d}  WR={b_wr:.1%}  PF={b_pf:.2f}   (+{bn} time-exits excluded)")


if __name__ == "__main__":
    main()
