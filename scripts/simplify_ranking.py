"""
Phase 1: simplify the ML RANKER + enforce monotonic, stable ranking.

Reframe (validated): edge = probabilistic RANKING within a bad population, not
signal/no-signal. So the ML kernel must be a *good, stable, monotonic ranker* —
not a complex high-PF-in-backtest model. This compares feature-set sizes on:
  (a) Ranking monotonicity  — decile(proba) vs actual long-win-rate (Spearman; +1 = perfect rank)
  (b) Net PF @ q97          — on the gated universe (NY + tradeable state), net@1.0pip
  (c) Stability             — net-PF std across seeds*folds

Thesis: fewer features -> more monotonic, more stable ranking, less overfit.
Universe gate (Phase-2 preview): in_ny & state tradeable (not QUIET/SHOCK).
Model long-perspective (q97 = top long opportunities). Tier-1, 5m, clean (FVG-fixed).

Output: results/model_validation/simplify_<UTC>/simplify.json
Run: python scripts/simplify_ranking.py
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
from scipy.stats import spearmanr

from setup_makeorbreak import barrier_R, pip_size   # net barrier sim (long), TB/TP/SL/spread
from model_validation_suite import build_extended, train_lgbm, predict
from core.state.market_state import classify_market_state
from core.train.dataset import binary_label_for_long, NON_FEATURE_COLS

PAIRS = ["GBPUSD", "USDJPY", "USDCAD"]
SEEDS = [42, 7]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
SPREAD_PIP = 1.0
SIZES = [9, 18, 73]   # radical -> moderate -> full


def build_pool():
    frames = []
    for p in PAIRS:
        ext = build_extended(p).copy()
        ext = ext.astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        st = classify_market_state(pd.read_parquet(REPO / "data" / "processed_v2" / f"{p}_5m.parquet"))
        raw = pd.read_parquet(REPO / "data" / "processed_v2" / f"{p}_5m.parquet")
        from core.features.engineer import atr as atr_fn
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        lr = barrier_R(raw["open"].values, raw["high"].values, raw["low"].values, raw["close"].values, a, "long")
        lr = lr - (SPREAD_PIP * pip_size(p)) / np.where(a > 0, a, np.nan)
        ext["_in_ny"] = st["in_ny"].reindex(ext.index).values
        ext["_tradeable"] = st["tradeable"].reindex(ext.index).values
        ext["_longR_net"] = pd.Series(lr, index=raw.index).reindex(ext.index).values
        ext["symbol"] = p
        frames.append(ext)
    pool = pd.concat(frames).sort_index()
    feat = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol" and not c.startswith("_")]
    pool = pool.dropna(subset=feat + ["label"])
    return pool, feat


def monotonicity(proba, win):
    """Spearman between proba-decile and actual win-rate; + top-bottom decile win spread."""
    if len(proba) < 100:
        return None, None
    dec = pd.qcut(proba, 10, labels=False, duplicates="drop")
    wr = pd.Series(win).groupby(dec).mean()
    rho = spearmanr(wr.index.values, wr.values).statistic if len(wr) >= 5 else np.nan
    spread = float(wr.iloc[-1] - wr.iloc[0]) if len(wr) >= 2 else np.nan
    return (round(float(rho), 3) if np.isfinite(rho) else None), round(spread, 3)


def pf(rs):
    rs = rs[np.isfinite(rs)]
    if len(rs) < 10: return None
    gw = rs[rs > 0].sum(); gl = -rs[rs <= 0].sum()
    return float(gw / gl) if gl > 0 else 999.0


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"simplify_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool, feat = build_pool()
    print(f"pool={len(pool):,}  features={len(feat)}")

    # global gain-importance (train < first val window) to define top-N subsets
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS)
    tr0 = pool[pool.index < cut0]
    m0 = train_lgbm(tr0[feat].values.astype(np.float32), binary_label_for_long(tr0["label"]).values,
                    tr0[feat].values.astype(np.float32), binary_label_for_long(tr0["label"]).values, 100, None, 42)
    imp = pd.Series(m0.feature_importance(importance_type="gain"), index=feat).sort_values(ascending=False)
    subsets = {n: list(imp.index[:n]) for n in SIZES}
    print("top-9 features:", subsets[9])

    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    results = {}
    for n, fcols in subsets.items():
        net_pfs, rhos, spreads, ntr = [], [], [], 0
        gated_proba_all, gated_win_all = [], []
        for sd in SEEDS:
            for ts in FOLD_STARTS:
                te_s, te_e = ts, ts + pd.DateOffset(months=3); vs = ts - pd.Timedelta(weeks=VAL_WEEKS)
                tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
                te = pool[(pool.index >= te_s) & (pool.index < te_e)]
                if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
                mdl = train_lgbm(tr[fcols].values.astype(np.float32), binary_label_for_long(tr["label"]).values,
                                 va[fcols].values.astype(np.float32), binary_label_for_long(va["label"]).values, 100, None, sd)
                gate_v = va["_in_ny"].values & va["_tradeable"].values
                gate_t = te["_in_ny"].values & te["_tradeable"].values
                if gate_v.sum() < 100 or gate_t.sum() < 100: continue
                pv = predict(mdl, "lgbm", va[fcols].values.astype(np.float32))
                pt = predict(mdl, "lgbm", te[fcols].values.astype(np.float32))
                cut = float(np.quantile(pv[gate_v], 0.97))
                sigmask = (pt >= cut) & gate_t
                rs = te["_longR_net"].values[sigmask]
                p = pf(rs[np.isfinite(rs)])
                if p is not None:
                    net_pfs.append(p); ntr += int(np.isfinite(rs).sum())
                # monotonicity on gated test
                gp = pt[gate_t]; gw = (te["label"].values[gate_t] == 1).astype(int)
                gated_proba_all.append(gp); gated_win_all.append(gw)
        rho, spread = monotonicity(np.concatenate(gated_proba_all), np.concatenate(gated_win_all))
        d = dict(n_features=n, net_pf_mean=round(float(np.mean(net_pfs)), 3),
                 net_pf_std=round(float(np.std(net_pfs)), 3), folds=len(net_pfs),
                 rank_spearman=rho, decile_winrate_spread=spread,
                 trades_per_day=round(ntr / (len(SEEDS) * days), 2))
        results[f"n{n}"] = d
        print(f"  n={n:2d}: net_PF {d['net_pf_mean']:.2f} (std {d['net_pf_std']:.2f}, {d['folds']} folds)  "
              f"rank_spearman {d['rank_spearman']}  decile_spread {d['decile_winrate_spread']}  ~{d['trades_per_day']}/day")

    (OUT / "simplify.json").write_text(json.dumps(dict(subsets={k: v for k, v in subsets.items()},
        results=results), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
