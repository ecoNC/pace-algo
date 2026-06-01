"""
Phase 5: does the edge GENERALIZE across asset classes? (universal-goal probe)

The whole point of the product (HANDOFF §1.1) is "works on ANY asset". This session's
V1 is FX-majors-only with a NY-session gate + FX session features. Here we test the
core blueprint with an ASSET-AGNOSTIC setup:

  features : 7 agnostic (drop in_ny / is_fx_market_open from the locked 9)
  gate     : volatility-regime only (state in TREND/RANGE, NOT QUIET/SHOCK). NO session.
  signal   : long + short rankers, POOLED top-N/day per asset, R=1.5 barrier.
  cost     : asset-agnostic, as a fraction of ATR (0 / 0.05 / 0.10 R).

Per-asset walk-forward. Aggregated per asset class vs acceptance H1 (config.py):
mean PF >= 1.4, min class PF >= 1.3. FX is included WITH the agnostic (no-session) gate
to quantify how much the NY gate was carrying FX.

Output: results/model_validation/phase5_crossasset_<UTC>/crossasset.json
Run:    python scripts/phase5_crossasset.py
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

from setup_makeorbreak import barrier_R
from model_validation_suite import build_extended, train_lgbm, predict
from core.state.market_state import classify_market_state
from core.features.engineer import atr as atr_fn

FEATURES_7 = ["hour_cos", "hour_sin", "rvol_20", "ema_20_dist_atr", "atr_pct",
              "htf_4h_rsi_14", "htf_4h_atr_percentile_100"]
CLASSES = {
    "fx":     ["GBPUSD", "USDJPY", "USDCAD", "NZDUSD", "USDCHF"],
    "crypto": ["BTCUSD", "ETHUSD"],
    "metal":  ["XAUUSD", "XAGUSD"],
    "index":  ["SPX500", "NAS100"],
}
SEEDS = [42, 7]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
COSTS_ATR = [0.0, 0.05, 0.10]   # cost as fraction of ATR (R units)
TOPN = 10


def build_asset(sym):
    """Per-asset pool: agnostic features + vol-gate flag + long/short gross R + cost-per-ATR=1."""
    ext = build_extended(sym)
    if ext is None or ext.empty:
        return None
    ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
    raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{sym}_5m.parquet")
    st = classify_market_state(raw)
    a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
    idx = raw.index
    gL = barrier_R(raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values, a, "long")
    gS = barrier_R(raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values, a, "short")
    ext["_tradeable"] = st["tradeable"].reindex(ext.index).values   # vol regime, NO session
    ext["_grossR_long"] = pd.Series(gL, index=idx).reindex(ext.index).values
    ext["_grossR_short"] = pd.Series(gS, index=idx).reindex(ext.index).values
    miss = [f for f in FEATURES_7 if f not in ext.columns]
    if miss:
        return None
    ext = ext.dropna(subset=FEATURES_7 + ["_grossR_long", "_grossR_short"])
    return ext


def stats_cost(grossR, cost):
    r = grossR - cost
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return None
    w = int((r > 0).sum()); gw = r[r > 0].sum(); gl = -r[r <= 0].sum()
    return dict(n=int(len(r)), wr=round(w / len(r), 3), pf=round(float(gw / gl), 3) if gl > 0 else 999.0)


def calib(proba_gated, gdays, per_day):
    n = len(proba_gated)
    if n == 0 or gdays == 0:
        return np.inf
    q = 1.0 - per_day * gdays / n
    return float(np.quantile(proba_gated, min(max(q, 0.0), 0.9995)))


def cands(df, ptL, ptS, gate):
    gi = np.where(gate)[0]
    ts = df.index[gi]
    fr = [pd.DataFrame({"ts": ts, "proba": ptL[gi], "gL": df["_grossR_long"].values[gi],
                        "gS": np.nan, "row": gi, "dir": "L"}),
          pd.DataFrame({"ts": ts, "proba": ptS[gi], "gL": np.nan,
                        "gS": df["_grossR_short"].values[gi], "row": gi, "dir": "S"})]
    c = pd.concat(fr).sort_values("proba", ascending=False).drop_duplicates("row")
    c["gross"] = np.where(c["dir"].values == "L", c["gL"].values, c["gS"].values)
    c["day"] = c["ts"].dt.normalize()
    return c


def eval_asset(sym):
    pool = build_asset(sym)
    if pool is None or len(pool) < 20000:
        return None
    X = lambda d: d[FEATURES_7].values.astype(np.float32)
    grossR = {c: [] for c in COSTS_ATR}  # realized gross R of selected trades (cost applied later)
    sel_gross = []
    days_total = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            gv = va["_tradeable"].values; gt = te["_tradeable"].values
            if gv.sum() < 100 or gt.sum() < 100: continue
            mL = train_lgbm(X(tr), (tr["_grossR_long"].values > 0).astype(int), X(va), (va["_grossR_long"].values > 0).astype(int), 100, None, sd)
            mS = train_lgbm(X(tr), (tr["_grossR_short"].values > 0).astype(int), X(va), (va["_grossR_short"].values > 0).astype(int), 100, None, sd)
            cv = cands(va, predict(mL, "lgbm", X(va)), predict(mS, "lgbm", X(va)), gv)
            ct = cands(te, predict(mL, "lgbm", X(te)), predict(mS, "lgbm", X(te)), gt)
            thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
            sel = ct[ct["proba"].values >= thr]
            sel_gross.append(sel["gross"].values)
    allg = np.concatenate(sel_gross) if sel_gross else np.array([])
    out = {"trades_per_day": round(len(allg[np.isfinite(allg)]) / (len(SEEDS) * days_total), 2)}
    for cost in COSTS_ATR:
        st = stats_cost(allg, cost)
        out[f"cost{cost}"] = st
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase5_crossasset_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    per_symbol = {}
    for cls, syms in CLASSES.items():
        for s in syms:
            print(f"[{cls:6s}] {s} ...", end="", flush=True)
            try:
                r = eval_asset(s)
            except Exception as e:
                r = None; print(f" ERR {type(e).__name__}: {e}", end="")
            per_symbol[s] = {"class": cls, "result": r}
            if r:
                c5 = r.get("cost0.05") or {}
                print(f"  PF@5%ATR {c5.get('pf')}  WR {c5.get('wr')}  {r['trades_per_day']}/day")
            else:
                print("  (no data / skipped)")

    # aggregate per class at 5% ATR cost
    agg = {}
    for cls in CLASSES:
        pfs = [per_symbol[s]["result"]["cost0.05"]["pf"] for s in CLASSES[cls]
               if per_symbol[s]["result"] and per_symbol[s]["result"].get("cost0.05")]
        agg[cls] = round(float(np.mean(pfs)), 3) if pfs else None
    classes_ok = [c for c, v in agg.items() if v is not None and v >= 1.3]
    verdict = dict(mean_pf=round(float(np.mean([v for v in agg.values() if v is not None])), 3) if any(agg.values()) else None,
                   classes_pf_ge_1_3=classes_ok, n_classes_ok=len(classes_ok),
                   h1_pass=(len(classes_ok) >= 3))

    (OUT / "crossasset.json").write_text(json.dumps(dict(features=FEATURES_7, costs_atr=COSTS_ATR,
        per_symbol=per_symbol, class_pf_at_5pct=agg, verdict=verdict), indent=2, default=str), encoding="utf-8")

    print(f"\n=== per-symbol (gross / 5%ATR / 10%ATR cost) ===")
    print(f"{'sym':8s} {'class':7s} {'PF_gross':>8s} {'PF_5%':>6s} {'PF_10%':>7s} {'WR_5%':>6s} {'tr/day':>7s}")
    for s, d in per_symbol.items():
        r = d["result"]
        if not r:
            print(f"{s:8s} {d['class']:7s}   (skipped)"); continue
        g = r.get("cost0.0") or {}; c5 = r.get("cost0.05") or {}; c10 = r.get("cost0.1") or {}
        print(f"{s:8s} {d['class']:7s} {str(g.get('pf')):>8s} {str(c5.get('pf')):>6s} {str(c10.get('pf')):>7s} {str(c5.get('wr')):>6s} {r['trades_per_day']:>7.2f}")
    print(f"\nclass PF @5%ATR: {agg}")
    print(f"H1 verdict: mean_pf={verdict['mean_pf']}  classes>=1.3: {classes_ok}  PASS={verdict['h1_pass']}")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
