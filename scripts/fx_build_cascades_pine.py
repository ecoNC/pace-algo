"""Block-2 Step 2: assemble the 4 FX cascades into one validation Pine + LOCAL cascade-math
bit-exact + dropped-feature report. Plots pL/pS (primary L/S, 9-feat) + pmL/pmS (meta L/S,
73-feat) for the per-bar plausibility check vs Python (Step-2 stop anchor). NOT the selection
chain (step 3).

NOTE: the boosters were trained on numpy arrays WITHOUT feature_name, so booster.feature_name()
is generic — the real index->name map is FEATURES_9 (primary) and feature_cols(pool) (meta),
reconstructed here exactly as in fx_production_train.py.

Run: py -3 scripts/fx_build_cascades_pine.py  -> deploy_pine/fx_cascades_validate.pine
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import numpy as np
import lightgbm as lgb
from phase3_density import build_pool, FEATURES_9
from phase3_short_features import feature_cols
from core.export.pine_codegen import (lgbm_to_pine_cascade, cascade_signature_args, _pine_arg,
                                       bit_exact_check)
from core.export.pine_features import render_feature_engine

MODELS = REPO / "artifacts" / "models"
snap = json.loads((MODELS / "fx_ship_snapshot.json").read_text())
DEFAULT_FN = "f_pace_algo_v1_probability"
RENAME = {"mL": "f_pL", "mS": "f_pS", "meL": "f_pmL", "meS": "f_pmS"}
PROB = {"mL": "pL", "mS": "pS", "meL": "pmL", "meS": "pmS"}

def load(tag):
    s = (MODELS / snap["models"][tag]).read_text(encoding="utf-8").replace("\r\n", "\n")
    return lgb.Booster(model_str=s)

def main():
    pool = build_pool()
    feats_full = feature_cols(pool)
    print(f"pool={len(pool):,}  FEATURES_9={len(FEATURES_9)}  feats_full={len(feats_full)}")
    namemap = {"mL": FEATURES_9, "mS": FEATURES_9, "meL": feats_full, "meS": feats_full}
    casc = {t: load(t) for t in RENAME}

    # local cascade-math bit-exact (given features) on a holdout sample
    rng = np.random.RandomState(7)
    print("\n-- LOCAL cascade-math bit-exact (booster.predict vs Pine mirror) --")
    for t in RENAME:
        names = namemap[t]
        X = pool[names].values.astype(np.float32)
        samp = X[rng.choice(len(X), size=min(5000, len(X)), replace=False)]
        chk = bit_exact_check(casc[t], names, samp, atol=1e-5)
        print(f"  {t}: trees={casc[t].num_trees()}  max_abs_diff={chk['max_abs_diff']:.2e}  passed={chk['passed']}")

    # generate 4 renamed cascades + collect referenced features (union, stable order)
    blocks, calls, seen = [], [], []
    for t in RENAME:
        b, names = casc[t], namemap[t]
        blocks.append(lgbm_to_pine_cascade(b, names).replace(DEFAULT_FN, RENAME[t]))
        sig = cascade_signature_args(b, names)
        for n in sig:
            if n not in seen:
                seen.append(n)
        calls.append((t, RENAME[t], ", ".join(_pine_arg(n) for n in sig)))

    eng = render_feature_engine(seen)
    print(f"\nreferenced features (union across 4 cascades): {len(seen)}")
    print("DROPPED (no Pine impl -> 0.0, would break meta):", eng["dropped_features"] or "none")

    call_lines = [f"{PROB[t]} = {fn}({args})" for t, fn, args in calls]
    plot_lines = [f'plot({PROB[t]}, "{PROB[t]}", display=display.data_window)' for t, _, _ in calls]
    pine = f"""//@version=6
// FX 4-Cascade validation (Block-2 step 2) — AUTO-GENERATED, DO NOT EDIT.
// pL/pS = primary long/short (9-feat); pmL/pmS = meta long/short (73-feat).
// Per-bar plausibility vs Python booster.predict. NOT the selection chain (step 3).
indicator("FX Cascades Validate", overlay=false, max_lines_count=20)

{eng['helpers'].rstrip()}

{eng['htf'].rstrip()}

{eng['features'].rstrip()}

{chr(10).join(b.rstrip() for b in blocks)}

{chr(10).join(call_lines)}
{chr(10).join(plot_lines)}
"""
    out = REPO / "deploy_pine" / "fx_cascades_validate.pine"
    out.write_text(pine, encoding="utf-8")
    print(f"\nwritten {out}  ({len(pine):,} chars, {pine.count(chr(10))} lines)")

if __name__ == "__main__":
    main()
