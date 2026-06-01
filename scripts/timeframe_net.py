"""
Higher-timeframe NET viability — corrects the (invalid) 5m lock.

The 5m lock (ANN-011) and the higher-TF rejection were decided with the
DEGENERATE stump model -> invalid. Re-test 5m/15m/30m/1h with the healthy
LGBM-100, NET of spread (0.3 ECN, 1.0 retail), next-bar-open entry.
Hypothesis: larger ATR at higher TF -> spread is a smaller fraction of the
1-ATR risk -> the edge survives costs.

Comparable feature set across TFs: compute_features + compute_session_features
(TF-agnostic). Labels: triple-barrier R1.5/sl1.0/tb24 per TF.

Output: results/model_validation/tfnet_<UTC>/tfnet.json
Run: python scripts/timeframe_net.py
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

from model_validation_suite import train_lgbm, predict, DATA_V2
from core.features import compute_features, compute_session_features
from core.features.engineer import atr as atr_fn
from core.labeling import compute_triple_barrier_labels
from core.train.dataset import walk_forward_split, binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEED = 7
PAIRS = ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF", "AUDUSD"]
TIER1 = ["GBPUSD", "USDJPY", "USDCAD"]
TFS = ["5m", "15m", "30m", "1h"]
SPREADS = [0.0, 0.3, 1.0]   # pips (all-in)
TB = 24
TRAIN_END = pd.Timestamp("2025-01-01", tz="UTC")
VAL_END = pd.Timestamp("2025-07-01", tz="UTC")


def pip_size(s): return 0.01 if s.endswith("JPY") else 0.0001


def load_tf(sym, tf):
    if tf == "5m":
        return pd.read_parquet(DATA_V2 / f"{sym}_5m.parquet")
    if tf == "1h":
        return pd.read_parquet(DATA_V2 / f"{sym}_1h.parquet")
    rule = {"15m": "15min", "30m": "30min"}[tf]
    base = pd.read_parquet(DATA_V2 / f"{sym}_5m.parquet")
    o = base.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return o.dropna()


def build(sym, tf):
    ohlcv = load_tf(sym, tf)
    if len(ohlcv) < 5000:
        return None
    feat = compute_features(ohlcv)
    atr14 = atr_fn(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14).values
    sess = compute_session_features(ohlcv, atr14)
    lab = compute_triple_barrier_labels(ohlcv, tp_R=1.5, sl_atr_mult=1.0, time_barrier_bars=TB)
    ext = pd.concat([feat, sess], axis=1).join(lab[["label"]], how="inner")
    ext["symbol"] = sym
    ext["_open"] = ohlcv["open"]; ext["_high"] = ohlcv["high"]; ext["_low"] = ohlcv["low"]
    ext["_close"] = ohlcv["close"]; ext["_atr"] = atr14
    return ext


def sim(sub, spread_price):
    """Net trades on a single pair's test slice. Entry=next-bar-open, SL-first, 24-bar TB."""
    o = sub["_open"].values; h = sub["_high"].values; l = sub["_low"].values
    c = sub["_close"].values; atr = sub["_atr"].values; sigmask = sub["_sig"].values
    rs = []
    n = len(c)
    for i in range(n - 1):
        if not sigmask[i]:
            continue
        risk = atr[i]
        if not np.isfinite(risk) or risk <= 0:
            continue
        entry = o[i + 1]; tp = entry + 1.5 * risk; sl = entry - 1.0 * risk
        end = min(n, i + 1 + TB); r = None
        for k in range(i + 1, end):
            if l[k] <= sl: r = -1.0; break
            if h[k] >= tp: r = 1.5; break
        if r is None:
            r = (c[end - 1] - entry) / risk
        rs.append(r - spread_price / risk)
    return rs


def pf_wr(rs):
    if not rs: return None
    w = sum(1 for r in rs if r > 0); gw = sum(r for r in rs if r > 0); gl = -sum(r for r in rs if r <= 0)
    return dict(n=len(rs), wr=round(w/len(rs), 3), pf=round(gw/gl, 3) if gl > 0 else 999.0, total_R=round(sum(rs), 1))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"tfnet_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    print(f"{'TF':4s} {'spread':>7s} {'Tier1_PF':>9s} {'WR':>5s} {'totR':>8s} {'n':>6s}")
    for tf in TFS:
        exts = {s: build(s, tf) for s in PAIRS}
        exts = {s: e for s, e in exts.items() if e is not None}
        pool = pd.concat(exts.values()).sort_index()
        feat_cols = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and not c.startswith("_")]
        pool = pool.dropna(subset=feat_cols + ["label"])
        tr, va, te = walk_forward_split(pool, TRAIN_END, VAL_END)
        if len(tr) < 3000 or len(va) < 300 or len(te) < 300:
            print(f"{tf}: insufficient rows"); continue
        m = train_lgbm(tr[feat_cols].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                       va[feat_cols].values.astype(np.float32), binary_label_for_long(va["label"]).values, 100, None, SEED)
        q97 = float(np.quantile(predict(m, "lgbm", va[feat_cols].values.astype(np.float32)), 0.97))
        te = te.copy(); te["_sig"] = predict(m, "lgbm", te[feat_cols].values.astype(np.float32)) >= q97

        tf_res = {"per_pair": {}, "tier1": {}}
        for sp in SPREADS:
            t1_rs = []
            for s in exts:
                sub = te[te["symbol"] == s]
                if len(sub) < 50: continue
                rs = sim(sub, sp * pip_size(s))
                if s in TIER1: t1_rs += rs
                if sp == 0.3:
                    tf_res["per_pair"][s] = pf_wr(rs)
            tf_res["tier1"][f"{sp}pip"] = pf_wr(t1_rs)
            v = tf_res["tier1"][f"{sp}pip"]
            if v:
                print(f"{tf:4s} {sp:>6.1f}p {v['pf']:>9.2f} {v['wr']:>5.2f} {v['total_R']:>8.1f} {v['n']:>6d}")
        results[tf] = tf_res
        print()

    (out_dir / "tfnet.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Done -> {out_dir}")


if __name__ == "__main__":
    main()
