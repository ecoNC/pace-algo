"""
30m V1-candidate confirmation — full rigor (capstone).

Confirms (or refutes) that 30m / Tier-1 is NET-profitable and TIME-stable, with
the FULL production feature set, under walk-forward + multi-seed. Closes the gap
between the promising single-split tfnet result and a locked fact.

  - 30m OHLCV (resampled from 5m), full feature pipeline (compute_features +
    HTF-context 1h/4h + smc + session + htf_interactions) + cross-asset lean-4
  - labels: triple-barrier R1.5/sl1.0/tb24 (24x30m = 12h horizon)
  - 10 quarterly walk-forward folds x seeds {42,1,7}, q97
  - NET sim: next-30m-bar-open entry + spread {0.3, 1.0} pip
  - per-pair net persistence + Tier-1 pooled

Output: results/model_validation/confirm30m_<UTC>/confirm30m.json
Run: python scripts/confirm_30m.py
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
                           compute_smc_features, compute_session_features, compute_htf_interactions,
                           build_usd_strength, compute_cross_asset_features, CROSS_ASSET_FEATURES)
from core.features.engineer import atr as atr_fn
from core.labeling import compute_triple_barrier_labels
from core.config import HTF_CONTEXT_TIMEFRAMES
from model_validation_suite import train_lgbm, predict, DATA_V2
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

OUT_BASE = REPO / "results" / "model_validation"
SEEDS = [42, 1, 7]
PAIRS = ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF", "AUDUSD"]
TIER1 = ["GBPUSD", "USDJPY", "USDCAD"]
SPREADS = [0.3, 1.0]
TB = 24
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")


def pip_size(s): return 0.01 if s.endswith("JPY") else 0.0001


def resample_30m(df):
    return df.resample("30min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def build_30m(sym):
    o30 = resample_30m(pd.read_parquet(DATA_V2 / f"{sym}_5m.parquet"))
    base = compute_features(o30)
    htf = {}
    for h in HTF_CONTEXT_TIMEFRAMES:
        d = pd.read_parquet(DATA_V2 / f"{sym}_{h}.parquet")
        htf[h] = compute_features(d)
    base = attach_htf_context(base, htf.get("1h", pd.DataFrame()), htf.get("4h", pd.DataFrame()))
    base = attach_macro(base, pd.DataFrame())
    atr14 = atr_fn(o30["high"], o30["low"], o30["close"], 14).values
    ema_align = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
    ext = pd.concat([base, compute_smc_features(o30, atr14, ema_align),
                     compute_session_features(o30, atr14), compute_htf_interactions(base)], axis=1)
    lab = compute_triple_barrier_labels(o30, tp_R=1.5, sl_atr_mult=1.0, time_barrier_bars=TB)
    ext = ext.join(lab[["label"]], how="inner")
    ext["symbol"] = sym
    ext["_open"] = o30["open"]; ext["_high"] = o30["high"]; ext["_low"] = o30["low"]
    ext["_close"] = o30["close"]; ext["_atr"] = atr14
    return ext, o30["close"]


def sim_net(sub, spread_price):
    o = sub["_open"].values; h = sub["_high"].values; l = sub["_low"].values
    c = sub["_close"].values; atr = sub["_atr"].values; sig = sub["_sig"].values
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
        if r is None:
            r = (c[end - 1] - entry) / risk
        rs.append(r - spread_price / risk)
    return rs


def pf_wr(rs):
    if not rs: return None
    w = sum(1 for r in rs if r > 0); gw = sum(r for r in rs if r > 0); gl = -sum(r for r in rs if r <= 0)
    return dict(n=len(rs), wr=round(w/len(rs), 3), pf=round(gw/gl, 3) if gl > 0 else 999.0, total_R=round(sum(rs), 1))


def persist(fold_pfs):
    pfs = [p for p in fold_pfs if p is not None and np.isfinite(p)]
    if len(pfs) < 5: return None
    gt1 = sum(1 for x in pfs if x > 1.0)
    return dict(n=len(pfs), pf_gt1=gt1, pf_mean=round(float(np.mean(pfs)), 3),
                pf_min=round(float(np.min(pfs)), 3), pf_std=round(float(np.std(pfs)), 3))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT_BASE / f"confirm30m_{stamp}"; out_dir.mkdir(parents=True, exist_ok=True)
    print("Building 30m full features...")
    exts, closes = {}, {}
    for s in PAIRS:
        e, c = build_30m(s); exts[s] = e; closes[s] = c
    # cross-asset lean-4 at 30m
    usd_ret, R = build_usd_strength(closes)
    for s in PAIRS:
        ca = compute_cross_asset_features(s, usd_ret, R)[CROSS_ASSET_FEATURES].reindex(exts[s].index)
        exts[s] = exts[s].join(ca)
    pool = pd.concat(exts.values()).sort_index()
    feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and not c.startswith("_")]
    pool = pool.dropna(subset=feat + ["label"])
    print(f"30m pool={len(pool):,}  features={len(feat)}\n")

    # per (pair, spread) -> list of fold-level net PF (across seeds); Tier-1 pooled likewise
    pp = {p: {sp: [] for sp in SPREADS} for p in PAIRS}
    t1 = {sp: [] for sp in SPREADS}; t1_gross = []

    for sd in SEEDS:
        for ts in FOLD_STARTS:
            test_start, test_end = ts, ts + pd.DateOffset(months=3)
            val_start = test_start - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < val_start]; va = pool[(pool.index >= val_start) & (pool.index < test_start)]
            te = pool[(pool.index >= test_start) & (pool.index < test_end)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300:
                continue
            m = train_lgbm(tr[feat].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                           va[feat].values.astype(np.float32), binary_label_for_long(va["label"]).values, 100, None, sd)
            q97 = float(np.quantile(predict(m, "lgbm", va[feat].values.astype(np.float32)), 0.97))
            te = te.copy(); te["_sig"] = predict(m, "lgbm", te[feat].values.astype(np.float32)) >= q97
            t1_rs = {sp: [] for sp in SPREADS}; t1_rs_gross = []
            for p in PAIRS:
                sub = te[te["symbol"] == p]
                if len(sub) < 50: continue
                for sp in SPREADS:
                    rs = sim_net(sub, sp * pip_size(p))
                    r = pf_wr(rs)
                    if r and r["n"] >= 10:
                        pp[p][sp].append(r["pf"])
                        if p in TIER1: t1_rs[sp] += rs
                if p in TIER1:
                    t1_rs_gross += sim_net(sub, 0.0)
            for sp in SPREADS:
                rr = pf_wr(t1_rs[sp])
                if rr and rr["n"] >= 10: t1[sp].append(rr["pf"])
            gg = pf_wr(t1_rs_gross)
            if gg and gg["n"] >= 10: t1_gross.append(gg["pf"])

    print("=== PER-PAIR NET persistence (folds x seeds, PF>1) ===")
    pp_out = {}
    for p in PAIRS:
        d10 = persist(pp[p][1.0]); d03 = persist(pp[p][0.3])
        pp_out[p] = {"net_1.0pip": d10, "net_0.3pip": d03}
        if d10 and d03:
            print(f"  {p:7s} @0.3pip PF{d03['pf_mean']:.2f} ({d03['pf_gt1']}/{d03['n']})  "
                  f"| @1.0pip PF{d10['pf_mean']:.2f} ({d10['pf_gt1']}/{d10['n']}) min {d10['pf_min']:.2f}")

    print("\n=== TIER-1 pooled persistence ===")
    out_t1 = {"gross": persist(t1_gross), "net_0.3pip": persist(t1[0.3]), "net_1.0pip": persist(t1[1.0])}
    for k, d in out_t1.items():
        if d:
            print(f"  {k:11s} PF mean {d['pf_mean']:.2f}  PF>1 {d['pf_gt1']}/{d['n']}  min {d['pf_min']:.2f}  std {d['pf_std']:.2f}")

    payload = dict(seeds=SEEDS, n_features=len(feat), per_pair=pp_out, tier1_pooled=out_t1)
    (out_dir / "confirm30m.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
