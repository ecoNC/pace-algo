"""
PaceAlgo FX Core — Balanced Mode system build + validation (product phase).

Hard, reproducible structure (NOT research):
  - Scope: Tier-1 only (GBPUSD, USDJPY, USDCAD)
  - Hard TRADE GATE (pre-filter, applied to test signals, not a feature):
      NY session  : in_ny == 1
      vol regime  : atr_percentile_100 >= 0.33  (exclude low-vol third)
      trend (opt) : adx_14 >= 18                 (no chop)
  - Signal: model proba >= q97 (computed on GATED val distribution)
  - Target: ~6-10 trades/day (Balanced)
Model: LGBM-100 (fixed), trained on Tier-1, clean data (FVG-fixed).
Evaluated NET (next-bar-open + spread 0.3/1.0 pip), walk-forward x 3 seeds.

Goal: show the gate makes a high-frequency TF NET-viable by removing
cost-losing marginal trades — PF from fewer bad conditions, not model tuning.

Output: results/model_validation/balanced_<UTC>/balanced.json
Run: python scripts/system_balanced.py
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

from core.features import (compute_features, attach_macro, attach_htf_context,
                           compute_smc_features, compute_session_features, compute_htf_interactions)
from core.features.engineer import atr as atr_fn
from core.labeling import compute_triple_barrier_labels
from core.config import HTF_CONTEXT_TIMEFRAMES
from model_validation_suite import train_lgbm, predict, DATA_V2
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEEDS = [42, 1, 7]
CORE = ["GBPUSD", "USDJPY", "USDCAD"]
TFS = ["5m", "15m"]
SPREADS = [0.3, 1.0]
TB = 24
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
BARS_PER_DAY = {"5m": 288, "15m": 96, "30m": 48}


def pip_size(s): return 0.01 if s.endswith("JPY") else 0.0001


def load_tf(sym, tf):
    if tf in ("5m", "1h"):
        return pd.read_parquet(DATA_V2 / f"{sym}_{tf}.parquet")
    rule = {"15m": "15min", "30m": "30min"}[tf]
    b = pd.read_parquet(DATA_V2 / f"{sym}_5m.parquet")
    return b.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def build(sym, tf):
    o = load_tf(sym, tf)
    base = compute_features(o)
    htf = {h: compute_features(pd.read_parquet(DATA_V2 / f"{sym}_{h}.parquet")) for h in HTF_CONTEXT_TIMEFRAMES}
    base = attach_htf_context(base, htf.get("1h", pd.DataFrame()), htf.get("4h", pd.DataFrame()))
    base = attach_macro(base, pd.DataFrame())
    atr14 = atr_fn(o["high"], o["low"], o["close"], 14).values
    ema = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
    ext = pd.concat([base, compute_smc_features(o, atr14, ema),
                     compute_session_features(o, atr14), compute_htf_interactions(base)], axis=1)
    lab = compute_triple_barrier_labels(o, tp_R=1.5, sl_atr_mult=1.0, time_barrier_bars=TB)
    ext = ext.join(lab[["label"]], how="inner"); ext["symbol"] = sym
    ext["_o"] = o["open"]; ext["_h"] = o["high"]; ext["_l"] = o["low"]; ext["_c"] = o["close"]; ext["_atr"] = atr14
    return ext


def gate_mask(df, gate):
    m = np.ones(len(df), bool)
    if "NY" in gate:
        m &= df["in_ny"].values == 1
    if "vol" in gate and "atr_percentile_100" in df.columns:
        m &= df["atr_percentile_100"].values >= 0.33
    if "trend" in gate and "adx_14" in df.columns:
        m &= df["adx_14"].values >= 18.0
    return m


def sim(sub, sig, spread_price):
    o = sub["_o"].values; h = sub["_h"].values; l = sub["_l"].values; c = sub["_c"].values; atr = sub["_atr"].values
    n = len(c); rs = []
    for i in range(n - 1):
        if not sig[i]:
            continue
        risk = atr[i]
        if not np.isfinite(risk) or risk <= 0:
            continue
        entry = o[i + 1]; tp = entry + 1.5 * risk; sl = entry - 1.0 * risk
        end = min(n, i + 1 + TB); r = None
        for k in range(i + 1, end):
            if l[k] <= sl: r = -1.0; break
            if h[k] >= tp: r = 1.5; break
        if r is None: r = (c[end - 1] - entry) / risk
        rs.append(r - spread_price / risk)
    return rs


def pf_wr(rs):
    if not rs: return None
    w = sum(1 for r in rs if r > 0); gw = sum(r for r in rs if r > 0); gl = -sum(r for r in rs if r <= 0)
    return dict(n=len(rs), wr=round(w/len(rs), 3), pf=round(gw/gl, 3) if gl > 0 else 999.0)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"balanced_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    GATES = ["none", "NY", "NY+vol", "NY+vol+trend"]
    results = {}

    for tf in TFS:
        pool = pd.concat([build(s, tf) for s in CORE]).sort_index()
        feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and not c.startswith("_")]
        pool = pool.dropna(subset=feat + ["label"])
        print(f"\n### TF={tf}  pool={len(pool):,}  feat={len(feat)}")
        # per gate: collect fold-level net PF (@1.0) + trades/day, across seeds
        gate_acc = {g: {"pf10": [], "pf03": [], "wr10": [], "tpd": []} for g in GATES}
        for sd in SEEDS:
            for ts in FOLD_STARTS:
                te_s, te_e = ts, ts + pd.DateOffset(months=3); vs = ts - pd.Timedelta(weeks=VAL_WEEKS)
                tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
                te = pool[(pool.index >= te_s) & (pool.index < te_e)]
                if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
                m = train_lgbm(tr[feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                               va[feat].values.astype(np.float32), binary_label_for_long(va["label"]).values, 100, None, sd)
                pv = predict(m, "lgbm", va[feat].values.astype(np.float32))
                pt = predict(m, "lgbm", te[feat].values.astype(np.float32))
                days = max(1, (te_e - te_s).days)
                for g in GATES:
                    gv = gate_mask(va, g); gt = gate_mask(te, g)
                    if gv.sum() < 100 or gt.sum() < 50: continue
                    cut = float(np.quantile(pv[gv], 0.97))     # q97 of GATED val distribution
                    sig = (pt >= cut) & gt
                    # net per pair pooled
                    rs10, rs03, ntr = [], [], 0
                    for p in CORE:
                        pm = te["symbol"].values == p
                        sub = te[pm]; s_sub = sig[pm]
                        rs10 += sim(sub, s_sub, 1.0 * pip_size(p))
                        rs03 += sim(sub, s_sub, 0.3 * pip_size(p))
                        ntr += int(s_sub.sum())
                    r10, r03 = pf_wr(rs10), pf_wr(rs03)
                    if r10 and r10["n"] >= 10:
                        gate_acc[g]["pf10"].append(r10["pf"]); gate_acc[g]["wr10"].append(r10["wr"])
                        gate_acc[g]["pf03"].append(r03["pf"]); gate_acc[g]["tpd"].append(ntr / days)
        tf_out = {}
        print(f"  {'gate':14s} {'net@1.0 PF':>11s} {'folds>1':>8s} {'net@0.3 PF':>11s} {'WR':>5s} {'trades/day':>11s}")
        for g in GATES:
            pf10 = [x for x in gate_acc[g]["pf10"] if np.isfinite(x)]
            if len(pf10) < 5: continue
            d = dict(net10_pf=round(float(np.mean(pf10)), 3), folds_gt1=sum(1 for x in pf10 if x > 1),
                     n_folds=len(pf10), net03_pf=round(float(np.mean(gate_acc[g]["pf03"])), 3),
                     wr=round(float(np.mean(gate_acc[g]["wr10"])), 3),
                     trades_per_day=round(float(np.mean(gate_acc[g]["tpd"])), 1))
            tf_out[g] = d
            print(f"  {g:14s} {d['net10_pf']:>11.2f} {str(d['folds_gt1'])+'/'+str(d['n_folds']):>8s} "
                  f"{d['net03_pf']:>11.2f} {d['wr']:>5.2f} {d['trades_per_day']:>11.1f}")
        results[tf] = tf_out

    (out_dir / "balanced.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
