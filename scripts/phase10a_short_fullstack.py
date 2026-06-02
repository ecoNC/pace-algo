"""
Phase 10a: re-test the FX SHORT universe under the FULL phase-4 stack.

Motivation: per-pair shorts (all but USDCHF) were rejected in phase3_short_robustness
BEFORE meta-labeling + proba-sizing existed (phase4 lifted longs 1.28->1.60). Open
question: does META rescue shorts the primary ranker alone could not carry?

Configs (short universe added to the locked 5-pair long universe):
  none | USDCHF (locked baseline) | GBPUSD | USDJPY | USDCAD | NZDUSD | ALL5

Per config x {NOMETA, META, META_SIZED}: net PF / WR / trades-day / per-year PF,
plus the PF of the SHORT trades alone inside the selection (is the addition pulling
its weight, or is pooled selection just ignoring it?).

Walk-forward rolling quarters x seeds, net @0.5pip ECN (the lock's reference spread).

Output: results/model_validation/phase10a_short_fullstack_<UTC>/shorts.json
Run:    python scripts/phase10a_short_fullstack.py
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

from phase3_density import build_pool, FEATURES_9, netR, stats, VAL_WEEKS, FOLD_STARTS, PAIRS
from phase3_selection_compare import calib_thr
from phase3_short_features import feature_cols
from phase4_ensemble_sizing import tier_size, pf_wr_sized
from model_validation_suite import train_lgbm, predict

SPREAD, TOPN, GEN_MULT, NEG = 0.5, 10, 3.0, -1e9
SEEDS = [42, 7]
CONFIGS = {  # name -> set of short symbols
    "none": set(),
    "USDCHF": {"USDCHF"},                       # locked baseline
    "GBPUSD": {"GBPUSD"}, "USDJPY": {"USDJPY"},
    "USDCAD": {"USDCAD"}, "NZDUSD": {"NZDUSD"},
    "ALL5": set(PAIRS),
}
VARIANTS = ["NOMETA", "META", "META_SIZED"]


def build_cands(df, pL, pS, gate, shorts):
    """Pooled candidate frame: longs on all pairs + shorts on `shorts`. Keeps dir tag."""
    gi = np.where(gate)[0]
    sym = df["symbol"].values[gi]
    ts = df.index[gi]
    frames = [pd.DataFrame({"ts": ts, "proba": pL[gi], "gR": df["_grossR_long"].values[gi],
                            "cost": df["_cost"].values[gi], "row": gi, "dir": "L"})]
    if shorts:
        keep = np.isin(sym, list(shorts))
        frames.append(pd.DataFrame({"ts": ts[keep], "proba": pS[gi][keep],
                                    "gR": df["_grossR_short"].values[gi][keep],
                                    "cost": df["_cost"].values[gi][keep], "row": gi[keep], "dir": "S"}))
    cand = pd.concat(frames)
    cand = cand.sort_values("proba", ascending=False).drop_duplicates("row")
    cand["day"] = cand["ts"].dt.normalize()
    return cand


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase10a_short_fullstack_{stamp}"
    OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    feats_full = feature_cols(pool)
    days = max(1, (pool.index[-1] - FOLD_STARTS[0]).days)
    X = lambda d, f=FEATURES_9: d[f].values.astype(np.float32)
    print(f"pool={len(pool):,}  full_features={len(feats_full)}")

    acc = {c: {v: {"R": [], "S": [], "pf": [], "yr": {}, "shortR": []} for v in VARIANTS} for c in CONFIGS}

    def record(cfg, var, sel, sized):
        r = netR(sel["gR"].values, sel["cost"].values, SPREAD)
        sz = tier_size(sel["proba"].values) if sized else np.ones(len(sel))
        a = acc[cfg][var]
        a["R"].append(r); a["S"].append(sz)
        st = pf_wr_sized(r, sz); a["pf"].append(st["pf"] if st else None)
        a["shortR"].append(r[(sel["dir"] == "S").values])
        yrs = sel["ts"].dt.year.values
        for y in (2024, 2025, 2026):
            mk = yrs == y
            a["yr"].setdefault(y, {"R": [], "S": []})
            a["yr"][y]["R"].append(r[mk]); a["yr"][y]["S"].append(sz[mk])

    def sel_from(va_c, te_c):
        thr = calib_thr(va_c["proba"].values, max(1, va_c["day"].nunique()), TOPN)
        return te_c[te_c["proba"].values >= thr]

    nfolds = 0
    for sd in SEEDS:
        for ts0 in FOLD_STARTS:
            te_s, te_e = ts0, ts0 + pd.DateOffset(months=3); vs = ts0 - pd.Timedelta(weeks=VAL_WEEKS)
            tr = pool[pool.index < vs]; va = pool[(pool.index >= vs) & (pool.index < te_s)]
            te = pool[(pool.index >= te_s) & (pool.index < te_e)]
            if len(tr) < 5000 or len(va) < 500 or len(te) < 300: continue
            gv = va["_in_ny"].values & va["_tradeable"].values
            gt = te["_in_ny"].values & te["_tradeable"].values
            if gv.sum() < 100 or gt.sum() < 100: continue
            mL = train_lgbm(X(tr), tr["_lab_long"].values, X(va), va["_lab_long"].values, 100, None, sd)
            mS = train_lgbm(X(tr), tr["_lab_short"].values, X(va), va["_lab_short"].values, 100, None, sd)
            pvL, ptL = predict(mL, "lgbm", X(va)), predict(mL, "lgbm", X(te))
            pvS, ptS = predict(mS, "lgbm", X(va)), predict(mS, "lgbm", X(te))
            nfolds += 1

            # META models (per fold, shared across configs — candidate gen is universe-wide)
            ndays = max(1, va.index[gv].normalize().nunique())
            genL = calib_thr(pvL[gv], ndays, TOPN * GEN_MULT); genS = calib_thr(pvS[gv], ndays, TOPN * GEN_MULT)
            trva = pool[pool.index < te_s]; gtrva = trva["_in_ny"].values & trva["_tradeable"].values
            candL = gtrva & (mL.predict(X(trva)) >= genL); candS = gtrva & (mS.predict(X(trva)) >= genS)
            have_meta = candL.sum() > 200 and candS.sum() > 200
            if have_meta:
                metaL = train_lgbm(X(trva[candL], feats_full), trva["_lab_long"].values[candL],
                                   X(trva[candL], feats_full), trva["_lab_long"].values[candL], 100, None, sd)
                metaS = train_lgbm(X(trva[candS], feats_full), trva["_lab_short"].values[candS],
                                   X(trva[candS], feats_full), trva["_lab_short"].values[candS], 100, None, sd)

                def marr(df, primP, gen, meta):
                    cand = (df["_in_ny"].values & df["_tradeable"].values) & (primP >= gen)
                    out = np.full(len(df), NEG)
                    if cand.sum():
                        out[cand] = meta.predict(X(df[cand], feats_full))
                    return out
                mvL, mtL = marr(va, pvL, genL, metaL), marr(te, ptL, genL, metaL)
                mvS, mtS = marr(va, pvS, genS, metaS), marr(te, ptS, genS, metaS)

            for cfg, shorts in CONFIGS.items():
                base_sel = sel_from(build_cands(va, pvL, pvS, gv, shorts),
                                    build_cands(te, ptL, ptS, gt, shorts))
                record(cfg, "NOMETA", base_sel, False)
                if have_meta:
                    meta_sel = sel_from(build_cands(va, mvL, mvS, gv, shorts),
                                        build_cands(te, mtL, mtS, gt, shorts))
                    record(cfg, "META", meta_sel, False)
                    record(cfg, "META_SIZED", meta_sel, True)

    def block(d):
        allR = np.concatenate(d["R"]) if d["R"] else np.array([])
        allS = np.concatenate(d["S"]) if d["S"] else np.array([])
        st = pf_wr_sized(allR, allS) or {"n": 0, "wr": None, "pf": None}
        pfl = [p for p in d["pf"] if p is not None]
        yr = {str(y): (pf_wr_sized(np.concatenate(v["R"]), np.concatenate(v["S"])) or {"pf": None})["pf"]
              for y, v in d["yr"].items()}
        sR = np.concatenate(d["shortR"]) if d["shortR"] else np.array([])
        sstat = stats(sR)
        return dict(trades_per_day=round(st["n"] / (len(SEEDS) * days), 2),
                    net_pf=round(float(np.mean(pfl)), 3) if pfl else None,
                    pf_std=round(float(np.std(pfl)), 3) if pfl else None,
                    wr=st["wr"], pf_by_year=yr,
                    short_trades_per_day=round(len(sR) / (len(SEEDS) * days), 2),
                    short_pf=(sstat or {}).get("pf"), short_wr=(sstat or {}).get("wr"))

    res = {c: {v: block(acc[c][v]) for v in VARIANTS} for c in CONFIGS}
    (OUT / "shorts.json").write_text(json.dumps(dict(
        spread=SPREAD, topN=TOPN, seeds=SEEDS, folds=nfolds, configs=list(CONFIGS),
        results=res), indent=2, default=str), encoding="utf-8")

    for v in VARIANTS:
        print(f"\n=== {v} @{SPREAD}pip top{TOPN} ===")
        print(f"{'shorts':8s} {'net_PF':>7s} {'std':>6s} {'WR':>6s} {'tr/day':>7s} {'sh/day':>7s} {'sh_PF':>6s}  {'PF 24/25/26'}")
        for c in CONFIGS:
            d = res[c][v]
            pfm = f"{d['net_pf']:.3f}" if d["net_pf"] is not None else "  n/a"
            yr = "/".join(str(d["pf_by_year"].get(str(y))) for y in (2024, 2025, 2026))
            print(f"{c:8s} {pfm:>7s} {str(d['pf_std']):>6s} {str(d['wr']):>6s} "
                  f"{d['trades_per_day']:>7.2f} {d['short_trades_per_day']:>7.2f} {str(d['short_pf']):>6s}  {yr}")
    print(f"\nfolds={nfolds}. Bar: config beats USDCHF-baseline net_PF with all years positive "
          f"AND short_pf itself > 1 (shorts pull weight, not just noise).")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
