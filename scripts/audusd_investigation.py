"""
AUDUSD Investigation — why is AUDUSD model-agnostically weak (PF<1 @ q97)?

Decides honestly which pairs are "supported" rather than forcing universality.
Four analyses on the validated healthy 100-tree LGBM (seed 7), same data/splits:

  1. PATTERN        — label base rate + per-tier (q90/q97/q99) WR/PF/n for all 4
                      holdout pairs, AUDUSD vs the rest.
  2. OVER-CONFIDENCE— AUDUSD signal bars binned by predicted proba -> actual win
                      rate per bin (is the model over-confident specifically here?).
  3. COVARIATE SHIFT— standardized mean diff of every feature, AUDUSD vs train pool
                      (is AUDUSD out-of-distribution?). Top shifted features listed.
  4. DECISIVE TEST  — retrain WITH AUDUSD added to the train pool, re-eval AUDUSD
                      test period. PF recovery => "just OOS"; no recovery =>
                      "intrinsically hard / needs own model".

Output: results/model_validation/audusd_<UTC>/ {audusd.json}
Run: python scripts/audusd_investigation.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import numpy as np
import pandas as pd

from model_validation_suite import (
    build_extended, train_lgbm, predict, wr_pf_overlapping,
    FX_TRAIN_SYMBOLS, FX_HOLDOUT_SYMBOLS, TRAIN_END, VAL_END,
)
from core.train.dataset import walk_forward_split, binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEED = 7
TIERS = ("q90", "q97", "q99")


def build_pool(symbols):
    frames = []
    for s in symbols:
        d = build_extended(s); d = d.copy(); d["symbol"] = s
        frames.append(d.astype({c: "float32" for c in d.select_dtypes("float64").columns}))
    return pd.concat(frames).sort_index()


def fit_model(train_symbols):
    pool = build_pool(train_symbols)
    feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"]
    pc = pool.dropna(subset=feat + ["label"])
    tr, va, te = walk_forward_split(pc, TRAIN_END, VAL_END)
    Xtr = tr[feat].values.astype(np.float32); ytr = binary_label_for_long(tr["label"]).values
    Xva = va[feat].values.astype(np.float32); yva = binary_label_for_long(va["label"]).values
    model = train_lgbm(Xtr, ytr, Xva, yva, 100, None, SEED)
    cuts = {t: float(np.quantile(model.predict(Xva), q))
            for t, q in zip(TIERS, (0.90, 0.97, 0.99))}
    return model, feat, cuts, tr


def holdout_df(sym, feat):
    h = build_extended(sym).dropna(subset=feat + ["label"])
    return h[h.index >= VAL_END]


def per_tier(model, h, feat, cuts):
    proba = predict(model, "lgbm", h[feat].values.astype(np.float32))
    lab = h["label"].values.astype(int)
    base = float((lab == 1).mean())
    out = {"label_base_rate": round(base, 4), "n_bars": int(len(h))}
    for t in TIERS:
        m = proba >= cuts[t]
        r = wr_pf_overlapping(lab[m]); r["signals"] = int(m.sum())
        out[t] = r
    return out, proba, lab


def confidence_bins(proba, lab, edges=(0.40, 0.50, 0.535, 0.554, 0.577, 0.62, 1.01)):
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (proba >= lo) & (proba < hi)
        if not m.any():
            continue
        l = lab[m]; w = int((l == 1).sum()); ls = int((l == -1).sum())
        rows.append(dict(bin=f"[{lo:.3f},{hi:.3f})", n=int(m.sum()),
                         mean_pred=round(float(proba[m].mean()), 4),
                         actual_win=round(w / (w + ls), 4) if (w + ls) else None))
    return rows


def covariate_shift(train_df, aud_df, feat, top=15):
    diffs = []
    for c in feat:
        mu_t, sd_t = train_df[c].mean(), train_df[c].std()
        if sd_t and np.isfinite(sd_t) and sd_t > 0:
            smd = (aud_df[c].mean() - mu_t) / sd_t
            if np.isfinite(smd):
                diffs.append((c, round(float(smd), 3), round(float(mu_t), 4), round(float(aud_df[c].mean()), 4)))
    diffs.sort(key=lambda x: -abs(x[1]))
    return [dict(feature=f, std_mean_diff=s, train_mean=tm, audusd_mean=am) for f, s, tm, am in diffs[:top]]


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"audusd_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Baseline model: trained on FX_TRAIN_SYMBOLS (AUDUSD OOS) ===")
    model, feat, cuts, train_df = fit_model(FX_TRAIN_SYMBOLS)
    print(f"train pool={FX_TRAIN_SYMBOLS}  cuts={ {k: round(v,4) for k,v in cuts.items()} }\n")

    # 1. PATTERN — all holdout pairs
    pattern = {}; aud_proba = aud_lab = None; aud_df = None
    for s in FX_HOLDOUT_SYMBOLS:
        h = holdout_df(s, feat)
        res, proba, lab = per_tier(model, h, feat, cuts)
        pattern[s] = res
        if s == "AUDUSD":
            aud_proba, aud_lab, aud_df = proba, lab, h
        print(f"  {s:7s} base={res['label_base_rate']:.3f}  "
              + "  ".join(f"{t}:PF{res[t]['pf']:.2f}/WR{res[t]['wr']:.2f}/n{res[t]['signals']}" for t in TIERS))

    # 2. OVER-CONFIDENCE on AUDUSD
    conf = confidence_bins(aud_proba, aud_lab)
    print("\n=== AUDUSD confidence bins (mean_pred vs actual_win) ===")
    for r in conf:
        print(f"  {r['bin']}  n={r['n']:5d}  pred={r['mean_pred']:.3f}  actual_win={r['actual_win']}")

    # 3. COVARIATE SHIFT
    shift = covariate_shift(train_df, aud_df, feat)
    print("\n=== Top covariate shifts AUDUSD vs train pool (std mean diff) ===")
    for r in shift[:8]:
        print(f"  {r['feature']:28s} smd={r['std_mean_diff']:+.2f}  train={r['train_mean']}  aud={r['audusd_mean']}")

    # 4. DECISIVE TEST — retrain WITH AUDUSD in pool
    print("\n=== Decisive test: retrain WITH AUDUSD in train pool ===")
    model2, feat2, cuts2, _ = fit_model(list(FX_TRAIN_SYMBOLS) + ["AUDUSD"])
    h2 = holdout_df("AUDUSD", feat2)
    res2, _, _ = per_tier(model2, h2, feat2, cuts2)
    print(f"  AUDUSD WITH-in-pool  " + "  ".join(f"{t}:PF{res2[t]['pf']:.2f}/WR{res2[t]['wr']:.2f}/n{res2[t]['signals']}" for t in TIERS))
    print(f"  AUDUSD baseline(OOS) " + "  ".join(f"{t}:PF{pattern['AUDUSD'][t]['pf']:.2f}/WR{pattern['AUDUSD'][t]['wr']:.2f}/n{pattern['AUDUSD'][t]['signals']}" for t in TIERS))

    payload = dict(seed=SEED, cuts=cuts, pattern=pattern,
                   audusd_confidence_bins=conf, covariate_shift=shift,
                   decisive_test=dict(with_in_pool=res2, baseline_oos=pattern["AUDUSD"]))
    (out_dir / "audusd.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
