"""
Phase 11: CRYPTO MODULE v2 — clean Binance perp data + crypto-NATIVE features.

Why v1 was invalid as a final answer (module_registry):
  - Dukascopy altcoin data unusable (flat bars/gaps), BTC+ETH only -> thin universe
  - zero crypto-native information: no real volume, no funding, no taker flow

This test: 8 liquid USDT-perps, real volume, funding rates.
  Arms: BASE (generic feature stack) vs BASE+NATIVE (funding_rate/funding_z/
        hours_to_funding/taker_buy_z/vol_z/dow/weekend).
  TFs: 1h (HTF 4h) and 4h (HTF 1d resampled). 5m skipped on purpose: round-trip fee
       ~0.08% vs 5m ATR ~0.05-0.1% of price = fee >= 1R -> structurally dead.
  Cost model: HONEST per-trade fee in R = fee_roundtrip * close / atr (per bar!),
       scenarios 0.05% (maker-ish) and 0.10% (taker+slippage).
  Harness: pooled long+short across coins, vol-tradeable gate, POOLED top-N/day,
       proba sizing, walk-forward rolling quarters x seeds, per-year robustness.
  Bar (module_registry): net PF >= 1.3, all years positive, >=80% folds positive.

Output: results/model_validation/phase11_crypto_v2_<UTC>/crypto_v2.json
Run:    python scripts/phase11_crypto_v2.py
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

from core.features import (compute_features, attach_htf_context, compute_smc_features,
                           compute_session_features, compute_htf_interactions)
from core.features.engineer import atr as atr_fn
from core.train.dataset import NON_FEATURE_COLS
from core.state.market_state import classify_market_state
from model_validation_suite import train_lgbm, predict
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from phase7c_crypto_htf import barrier, calib

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT"]
TFS = ["1h", "4h"]
TP_R, TB = 1.5, 24
FEES = [0.0005, 0.0010]          # round-trip fee+slippage as price fraction
SEEDS = [42, 7]
VAL_WEEKS = 26
FOLD_STARTS = pd.date_range("2024-01-01", "2026-04-01", freq="QS", tz="UTC")
TOPN, NFEAT = 8, 9
DATA = REPO / "data" / "binance"
EXTDIR = REPO / "data" / "binance" / "extended"


def load(sym, tf):
    p = DATA / f"{sym}_{tf}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def native_feats(raw, sym):
    """Crypto-native features. All causal (funding shifted to known-in-advance rate)."""
    out = pd.DataFrame(index=raw.index)
    f = pd.read_parquet(DATA / f"{sym}_funding.parquet")["funding_rate"]
    # the rate settled at T applies to the period BEFORE T; the NEXT period's rate is
    # predicted/known during the period -> conservative: use last settled rate only.
    f_ff = f.reindex(raw.index.union(f.index)).sort_index().ffill().reindex(raw.index)
    out["nat_funding"] = f_ff.values
    roll = f.rolling(90)  # ~30 days of 8h settlements
    fz = ((f - roll.mean()) / roll.std()).reindex(raw.index.union(f.index)).sort_index().ffill().reindex(raw.index)
    out["nat_funding_z"] = fz.values
    hour = raw.index.hour.values
    out["nat_hrs_to_funding"] = (8 - (hour % 8)) % 8
    dow = raw.index.dayofweek.values
    out["nat_is_weekend"] = (dow >= 5).astype(float)
    out["nat_dow_sin"] = np.sin(2 * np.pi * dow / 7); out["nat_dow_cos"] = np.cos(2 * np.pi * dow / 7)
    if "taker_buy_ratio" in raw.columns:
        tb = raw["taker_buy_ratio"].astype(float)
        out["nat_taker_buy"] = tb.values
        out["nat_taker_buy_z"] = ((tb - tb.rolling(96).mean()) / tb.rolling(96).std()).values
    v = raw["volume"].astype(float)
    out["nat_vol_z"] = ((v - v.rolling(96).mean()) / v.rolling(96).std()).values
    return out


def build_ext(sym, tf):
    cache = EXTDIR / f"{sym}_{tf}_v2_extended.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    raw = load(sym, tf)
    if raw is None: return None
    if tf == "1h":
        htf_a, htf_b = load(sym, "4h"), load(sym, "4h")
    else:  # 4h primary -> daily HTF (resampled)
        d = raw.resample("1D").agg({"open": "first", "high": "max", "low": "min",
                                    "close": "last", "volume": "sum"}).dropna(subset=["close"])
        htf_a, htf_b = d, d
    base = compute_features(raw)
    base = attach_htf_context(base, compute_features(htf_a), compute_features(htf_b))
    atr14 = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
    ema_align = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
    ext = pd.concat([base, compute_smc_features(raw, atr14, ema_align),
                     compute_session_features(raw, atr14), compute_htf_interactions(base),
                     native_feats(raw, sym)], axis=1)
    EXTDIR.mkdir(parents=True, exist_ok=True)
    ext.to_parquet(cache, compression="zstd")
    return ext


def build_pool(tf):
    frames, used = [], []
    for sym in SYMBOLS:
        ext = build_ext(sym, tf)
        if ext is None: continue
        ext = ext.copy().astype({c: "float32" for c in ext.select_dtypes("float64").columns})
        raw = load(sym, tf)
        st = classify_market_state(raw)
        a = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
        for col, vals in [("_atr", a), ("_o", raw["open"].values), ("_h", raw["high"].values),
                          ("_l", raw["low"].values), ("_c", raw["close"].values)]:
            ext[col] = pd.Series(vals, index=raw.index).reindex(ext.index).values
        ext["_tradeable"] = st["tradeable"].reindex(ext.index).values
        sub = ext
        gL = barrier(sub["_o"].values, sub["_h"].values, sub["_l"].values, sub["_c"].values,
                     sub["_atr"].values, "long", TP_R, 1.0, TB)
        gS = barrier(sub["_o"].values, sub["_h"].values, sub["_l"].values, sub["_c"].values,
                     sub["_atr"].values, "short", TP_R, 1.0, TB)
        ext["_gL"] = gL; ext["_gS"] = gS
        ext["_fee_R"] = ext["_c"].values / np.where(a > 0, a, np.nan)   # x fee_frac = cost in R
        ext["symbol"] = sym
        frames.append(ext); used.append(sym)
    pool = pd.concat(frames).sort_index()
    feats_all = [c for c in pool.columns if c not in NON_FEATURE_COLS and c != "symbol"
                 and c != "label" and not c.startswith("_")]
    base_feats = [c for c in feats_all if not c.startswith("nat_")]
    pool = pool.dropna(subset=base_feats + ["_gL", "_gS", "_fee_R"])
    return pool, base_feats, feats_all, used


def cands(df, ptL, ptS, gate):
    gi = np.where(gate)[0]; ts = df.index[gi]
    fr = [pd.DataFrame({"ts": ts, "proba": ptL[gi], "g": df["_gL"].values[gi],
                        "feeR": df["_fee_R"].values[gi], "row": gi}),
          pd.DataFrame({"ts": ts, "proba": ptS[gi], "g": df["_gS"].values[gi],
                        "feeR": df["_fee_R"].values[gi], "row": gi})]
    c = pd.concat(fr).sort_values("proba", ascending=False).drop_duplicates("row")
    c["day"] = c["ts"].dt.normalize(); c["year"] = c["ts"].dt.year
    return c


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase11_crypto_v2_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for tf in TFS:
        pool, base_feats, feats_all, used = build_pool(tf)
        days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
        X = lambda d, f: d[f].values.astype(np.float32)
        print(f"\n[{tf}] pool={len(pool):,} coins={len(used)} base_feats={len(base_feats)} "
              f"native={len(feats_all)-len(base_feats)}")
        for arm, fpool in [("BASE", base_feats), ("BASE+NATIVE", feats_all)]:
            cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS)
            tr0 = pool[pool.index < cut0].dropna(subset=fpool)
            m0 = train_lgbm(X(tr0, fpool), (tr0["_gL"].values > 0).astype(int),
                            X(tr0, fpool), (tr0["_gL"].values > 0).astype(int), 100, None, 42)
            imp = pd.Series(m0.feature_importance(importance_type="gain"), index=fpool).sort_values(ascending=False)
            top = list(imp.index[:NFEAT])
            acc = {f: {"R": [], "S": [], "fold": [], "yr": {y: {"r": [], "s": []} for y in (2024, 2025, 2026)}} for f in FEES}
            p = pool.dropna(subset=top)
            for sd in SEEDS:
                for ts0 in FOLD_STARTS:
                    te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
                    tr = p[p.index < vs]; va = p[(p.index >= vs) & (p.index < te_s)]
                    te = p[(p.index >= te_s) & (p.index < te_e)]
                    if len(tr) < 3000 or len(va) < 300 or len(te) < 200: continue
                    gv = va["_tradeable"].values; gt = te["_tradeable"].values
                    if gv.sum() < 80 or gt.sum() < 80: continue
                    yl = lambda d: (d["_gL"].values > 0).astype(int); ys = lambda d: (d["_gS"].values > 0).astype(int)
                    mL = train_lgbm(X(tr, top), yl(tr), X(va, top), yl(va), 100, None, sd)
                    mS = train_lgbm(X(tr, top), ys(tr), X(va, top), ys(va), 100, None, sd)
                    cv = cands(va, predict(mL, "lgbm", X(va, top)), predict(mS, "lgbm", X(va, top)), gv)
                    ct = cands(te, predict(mL, "lgbm", X(te, top)), predict(mS, "lgbm", X(te, top)), gt)
                    thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
                    sel = ct[ct["proba"].values >= thr]; sz = tier_size(sel["proba"].values)
                    yrs = sel["year"].values
                    for f in FEES:
                        r = sel["g"].values - f * sel["feeR"].values
                        acc[f]["R"].append(r); acc[f]["S"].append(sz)
                        st = pf_wr_sized(r, sz)
                        if st: acc[f]["fold"].append(st["pf"])
                        for y in (2024, 2025, 2026):
                            mk = yrs == y
                            acc[f]["yr"][y]["r"].append(r[mk]); acc[f]["yr"][y]["s"].append(sz[mk])
            rr = {}
            for f in FEES:
                allR = np.concatenate(acc[f]["R"]) if acc[f]["R"] else np.array([])
                allS = np.concatenate(acc[f]["S"]) if acc[f]["S"] else np.array([])
                st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
                fpf = np.array(acc[f]["fold"])
                yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"]
                      for y, v in acc[f]["yr"].items()}
                allpos = all(v and v > 1.0 for v in yr.values())
                foldspos = round(float((fpf > 1).mean()), 2) if len(fpf) else None
                rr[f"fee{f}"] = dict(net_pf=st["pf"], wr=st["wr"],
                                     trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                                     pct_folds_pos=foldspos, pf_by_year=yr,
                                     bar_pass=bool(st["pf"] and st["pf"] >= 1.3 and allpos
                                                   and foldspos and foldspos >= 0.8))
            res[f"{tf}_{arm}"] = dict(symbols=used, top_features=top,
                                      n_native_in_top=sum(1 for t in top if t.startswith("nat_")), costs=rr)
            for f in FEES:
                d = rr[f"fee{f}"]; yr = "/".join(str(d["pf_by_year"][k]) for k in ("2024", "2025", "2026"))
                print(f"  {arm:12s} fee={f}: PF {d['net_pf']}  WR {d['wr']}  {d['trades_per_day']}/day  "
                      f"folds+ {d['pct_folds_pos']}  yrs {yr}  native-in-top9 {res[f'{tf}_{arm}']['n_native_in_top']}  BAR={d['bar_pass']}")
    (OUT / "crypto_v2.json").write_text(json.dumps(dict(
        symbols=SYMBOLS, tfs=TFS, tp_r=TP_R, fees=FEES, topN=TOPN, seeds=SEEDS,
        results=res), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
