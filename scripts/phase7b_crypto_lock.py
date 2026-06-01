"""
Phase 7b: CRYPTO module — same logic as the locked FX module, adapted for crypto.

Same architecture: long+short LGBM ranker (crypto-own top-9) + META re-rank + proba
sizing + vol-regime gate + POOLED top-N + R=1.5. Crypto differences:
  - 24/7 -> NO session gate (FX's NY gate has no crypto analogue); vol-gate only.
  - Cost is the key unknown -> swept as ATR fraction (0.02 = tight maker / 0.05 / 0.10 =
    retail taker fees+spread). Crypto 5m moves are small vs fixed fees, so cost matters most.
  - long+short on both BTC & ETH (no per-symbol short curation yet).

Walk-forward, per-fold + per-year robustness. Honest verdict vs the AI bar (PF>=1.3,
all years +). Same rigor as FX lock.

Output: results/model_validation/phase7b_crypto_<UTC>/crypto.json
Run:    python scripts/phase7b_crypto_lock.py
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

from phase6_perclass import build_class, SEEDS, VAL_WEEKS, FOLD_STARTS, calib
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from model_validation_suite import train_lgbm, predict

SYMBOLS = ["BTCUSD", "ETHUSD"]
TREES, TOPN, SEED, GEN_MULT, NEG, NFEAT = 50, 8, 42, 3.0, -1e9, 9
COSTS = [0.02, 0.05, 0.10]   # ATR fraction (R units)


def cands(df, ptL, ptS, gate):
    gi = np.where(gate)[0]; ts = df.index[gi]
    fr = [pd.DataFrame({"ts": ts, "proba": ptL[gi], "g": df["_grossR_long"].values[gi], "row": gi}),
          pd.DataFrame({"ts": ts, "proba": ptS[gi], "g": df["_grossR_short"].values[gi], "row": gi})]
    c = pd.concat(fr).sort_values("proba", ascending=False).drop_duplicates("row")
    c["day"] = c["ts"].dt.normalize(); c["year"] = c["ts"].dt.year
    return c


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase7b_crypto_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    pool, feats = build_class(SYMBOLS)
    if pool is None:
        print("no crypto data"); return
    X = lambda d, f: d[f].values.astype(np.float32)
    cut0 = FOLD_STARTS[0] - pd.Timedelta(weeks=VAL_WEEKS); tr0 = pool[pool.index < cut0]
    m0 = train_lgbm(X(tr0, feats), (tr0["_grossR_long"].values > 0).astype(int),
                    X(tr0, feats), (tr0["_grossR_long"].values > 0).astype(int), 100, None, 42)
    imp = pd.Series(m0.feature_importance(importance_type="gain"), index=feats).sort_values(ascending=False)
    top = list(imp.index[:NFEAT])
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    print(f"pool={len(pool):,}  crypto top-9: {top}")

    acc = {c: {"R": [], "S": [], "foldpf": [], "yr": {2024: {"r": [], "s": []}, 2025: {"r": [], "s": []}, 2026: {"r": [], "s": []}}} for c in COSTS}
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            gv = va["_tradeable"].values; gt = te["_tradeable"].values   # 24/7: vol gate only
            if gv.sum() < 100 or gt.sum() < 100: continue
            yl = lambda d: (d["_grossR_long"].values > 0).astype(int); ys = lambda d: (d["_grossR_short"].values > 0).astype(int)
            mL = train_lgbm(X(tr, top), yl(tr), X(va, top), yl(va), TREES, None, sd)
            mS = train_lgbm(X(tr, top), ys(tr), X(va, top), ys(va), TREES, None, sd)
            pvL, ptL = predict(mL, "lgbm", X(va, top)), predict(mL, "lgbm", X(te, top))
            pvS, ptS = predict(mS, "lgbm", X(va, top)), predict(mS, "lgbm", X(te, top))
            gd = max(1, va.index[gv].normalize().nunique())
            genL = calib(pvL[gv], gd, TOPN * GEN_MULT); genS = calib(pvS[gv], gd, TOPN * GEN_MULT)
            trva = pool[pool.index < te_s]; gtrva = trva["_tradeable"].values
            cL = gtrva & (mL.predict(X(trva, top)) >= genL); cS = gtrva & (mS.predict(X(trva, top)) >= genS)
            if cL.sum() <= 200 or cS.sum() <= 200: continue
            meL = train_lgbm(X(trva[cL], feats), yl(trva[cL]), X(trva[cL], feats), yl(trva[cL]), TREES, None, sd)
            meS = train_lgbm(X(trva[cS], feats), ys(trva[cS]), X(trva[cS], feats), ys(trva[cS]), TREES, None, sd)
            def marr(d, pp, gen, me):
                c = d["_tradeable"].values & (pp >= gen)
                out = np.full(len(d), NEG)
                if c.sum(): out[c] = me.predict(X(d[c], feats))
                return out
            cv = cands(va, marr(va, pvL, genL, meL), marr(va, pvS, genS, meS), gv)
            ct = cands(te, marr(te, ptL, genL, meL), marr(te, ptS, genS, meS), gt)
            thr = calib(cv["proba"].values, max(1, cv["day"].nunique()), TOPN)
            sel = ct[ct["proba"].values >= thr]
            sz = tier_size(sel["proba"].values); yrs = sel["year"].values
            for c in COSTS:
                r = sel["g"].values - c
                acc[c]["R"].append(r); acc[c]["S"].append(sz)
                st = pf_wr_sized(r, sz)
                if st: acc[c]["foldpf"].append(st["pf"])
                for y in (2024, 2025, 2026):
                    mk = yrs == y
                    acc[c]["yr"][y]["r"].append(sel["g"].values[mk] - c); acc[c]["yr"][y]["s"].append(sz[mk])

    spec = {"module": "CRYPTO", "symbols": SYMBOLS, "features": top, "trees": TREES,
            "gate": "vol_tradeable only (24/7, no session)", "selection": f"POOLED top{TOPN}/day + meta + sizing",
            "robustness": {}}
    print(f"\n{'costATR':7s} {'net_PF':>7s} {'WR':>6s} {'tr/day':>7s} {'folds>1':>8s} {'minfold':>8s} {'medfold':>8s}  {'PF 24/25/26':>20s} {'BAR'}")
    for c in COSTS:
        allR = np.concatenate(acc[c]["R"]); allS = np.concatenate(acc[c]["S"])
        st = pf_wr_sized(allR, allS); fpf = np.array(acc[c]["foldpf"])
        yr = {str(y): (pf_wr_sized(np.concatenate(v["r"]), np.concatenate(v["s"])) or {"pf": None})["pf"] for y, v in acc[c]["yr"].items()}
        allpos = all(v and v > 1.0 for v in yr.values())
        prof = dict(net_pf=st["pf"], wr=st["wr"], trades_per_day=round(st["n"]/(len(SEEDS)*days), 2),
                    n_folds=len(fpf), pct_folds_pos=round(float((fpf > 1).mean()), 2),
                    min_fold_pf=round(float(fpf.min()), 2), median_fold_pf=round(float(np.median(fpf)), 2),
                    pf_by_year=yr, bar_pass=(st["pf"] >= 1.3 and allpos))
        spec["robustness"][f"{c}ATR"] = prof
        yrs = "/".join(str(yr[k]) for k in ("2024", "2025", "2026"))
        print(f"{c:<7} {st['pf']:>7} {st['wr']:>6} {prof['trades_per_day']:>7.2f} {prof['pct_folds_pos']:>8} {prof['min_fold_pf']:>8} {prof['median_fold_pf']:>8}  {yrs:>20s} {prof['bar_pass']}")
    (OUT / "crypto.json").write_text(json.dumps(spec, indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
