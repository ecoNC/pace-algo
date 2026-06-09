"""Gate #3 — OOS-Revalidation of the SHIPPED 50t FX model, ANN-026 evidence.

ANN-026 gate bar: net PF >= 1.3 on the >=2025-07 holdout, **all years positive, cross-symbol
Holdout** (NOT aggregate-only). The 2026-06-03 ship-train report banked only the aggregate
net PF by spread (2.04/1.85/1.46) -- this script adds the per-YEAR and per-SYMBOL breakdown
that the lock explicitly requires, and that the COVERAGE_MATRIX needs to decide which FX symbols
ship as "edge-validated (live)" vs tool-only/WAIT.

Reuses the EXACT chain path proven bit-identical (3179==3179) by fx_verify_chain_logic.py,
the committed ship boosters (NOT a retrain), the fixed snapshot thresholds, and the canonical
ANN-023 exit accounting (netR + pf_wr_sized + tier_size). Nothing reinvented.

Run: py -3 scripts/fx_oos_reval.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import numpy as np
import pandas as pd
import lightgbm as lgb
from phase3_density import build_pool, FEATURES_9, netR
from phase3_short_features import feature_cols
from phase3_v1_config import build_cands
from phase4_ensemble_sizing import tier_size, pf_wr_sized

MODELS = REPO / "artifacts" / "models"
snap = json.loads((MODELS / "fx_ship_snapshot.json").read_text())
GL, GS, THR, Q1, Q2 = (snap["gen_long"], snap["gen_short"], snap["pooled_thr"],
                       snap["size_q1"], snap["size_q2"])
CUTOFF = pd.Timestamp(snap["cutoff"])
NEG = -1e9
GATE_BAR = 1.3          # ANN-026 lock net-PF bar
GATE_SPREAD = 0.5       # ECN; walk-forward 1.51 reference is @0.5pip

def load(t):
    return lgb.Booster(model_str=(MODELS / snap["models"][t]).read_text(encoding="utf-8").replace("\r\n", "\n"))

def pf_at(gR, cost, sz, spread):
    r = netR(np.asarray(gR), np.asarray(cost), spread)
    return pf_wr_sized(r, sz)

def main():
    pool = build_pool(); ff = feature_cols(pool)
    X9 = lambda d: d[FEATURES_9].values.astype(np.float32)
    X73 = lambda d: d[ff].values.astype(np.float32)
    mL, mS, meL, meS = load("mL"), load("mS"), load("meL"), load("meS")

    te = pool[pool.index >= CUTOFF]
    gate = te["_in_ny"].values & te["_tradeable"].values
    ptL, ptS = mL.predict(X9(te)), mS.predict(X9(te))
    pmL_all, pmS_all = meL.predict(X73(te)), meS.predict(X73(te))

    # EXACT proven chain (fx_verify_chain_logic.py path): gen-gate before meta, POOLED long+USDCHF-short
    marr = lambda pp, gen, me: np.where(gate & (pp >= gen), me, NEG)
    ct = build_cands(te, marr(ptL, GL, pmL_all), marr(ptS, GS, pmS_all), gate, "long_short_usdchf")
    sel = ct[ct["proba"].values >= THR].copy()
    sz = tier_size(sel["proba"].values)
    sym = te["symbol"].values[sel["row"].values]
    sel["symbol"] = sym
    print(f"holdout >= {CUTOFF.date()}:  rows={len(te):,}  selected n={len(sel)}  (expect ~3179)")

    # ---- OVERALL (sanity vs 2026-06-03 ship-train: 0.3->2.04 / 0.5->1.85 / 1.0->1.46) ----
    print("\n=== OVERALL net PF by spread ===")
    for s in (0.3, 0.5, 1.0):
        st = pf_at(sel["gR"].values, sel["cost"].values, sz, s)
        print(f"  spread {s}pip:  net_PF={st['pf']:.3f}  WR={st['wr']:.3f}  n={st['n']}")

    out = {"cutoff": str(CUTOFF.date()), "gate_spread_pip": GATE_SPREAD, "gate_bar_pf": GATE_BAR,
           "n_total": int(len(sel)), "by_year": {}, "by_symbol": {}}

    # ---- PER-YEAR @0.5pip (ANN-026: all years positive) ----
    print(f"\n=== PER-YEAR net PF @ {GATE_SPREAD}pip (ANN-026: all years > {GATE_BAR}) ===")
    years_pass = []
    for y, g in sel.groupby("year"):
        szy = tier_size(g["proba"].values)
        st = pf_at(g["gR"].values, g["cost"].values, szy, GATE_SPREAD)
        if st is None:
            print(f"  {y}:  n<10 ({len(g)}) -> skipped"); out["by_year"][str(y)] = {"n": int(len(g)), "pf": None}
            continue
        ok = st["pf"] >= GATE_BAR
        years_pass.append(ok)
        print(f"  {y}:  net_PF={st['pf']:.3f}  WR={st['wr']:.3f}  n={st['n']}  {'PASS' if ok else 'FAIL'}")
        out["by_year"][str(y)] = {"n": st["n"], "pf": st["pf"], "wr": st["wr"], "pass": ok}

    # ---- PER-SYMBOL @0.5pip (feeds COVERAGE_MATRIX: edge-validated vs tool-only) ----
    print(f"\n=== PER-SYMBOL net PF @ {GATE_SPREAD}pip (decides coverage: >= {GATE_BAR} = edge-validated) ===")
    for symname, g in sel.groupby("symbol"):
        szs = tier_size(g["proba"].values)
        st = pf_at(g["gR"].values, g["cost"].values, szs, GATE_SPREAD)
        if st is None:
            print(f"  {symname}:  n<10 ({len(g)}) -> tool-only (insufficient OOS trades)")
            out["by_symbol"][symname] = {"n": int(len(g)), "pf": None, "coverage": "tool-only"}
            continue
        cov = "edge-validated" if st["pf"] >= GATE_BAR else "tool-only/WAIT"
        print(f"  {symname}:  net_PF={st['pf']:.3f}  WR={st['wr']:.3f}  n={st['n']}  -> {cov}")
        out["by_symbol"][symname] = {"n": st["n"], "pf": st["pf"], "wr": st["wr"], "coverage": cov}

    all_years_ok = len(years_pass) > 0 and all(years_pass)
    edge_syms = [s for s, v in out["by_symbol"].items() if v.get("coverage") == "edge-validated"]
    out["all_years_pass"] = bool(all_years_ok)
    out["edge_validated_symbols"] = edge_syms
    print("\n=== ANN-026 GATE-3 VERDICT ===")
    print(f"  all years >= {GATE_BAR}: {all_years_ok}")
    print(f"  edge-validated symbols ({len(edge_syms)}): {edge_syms}")
    print(f"  tool-only symbols: {[s for s in out['by_symbol'] if s not in edge_syms]}")
    print("  -> The per-symbol verdict IS the honest coverage; do not green-wash weak symbols.")

    outp = REPO / "results" / "model_validation" / "fx_oos_reval_breakdown_2026-06-09.json"
    outp.write_text(json.dumps(out, indent=2))
    print(f"\nwritten: {outp.relative_to(REPO)}")

if __name__ == "__main__":
    main()
