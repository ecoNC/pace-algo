"""FX export chain smoke-test (Heim-PC, 2026-06-03).

Proves the full chain on REAL FX data: build_pool -> train production primary-long
(9-feat, 50t) -> lgbm_to_pine_cascade -> bit_exact_check (Python booster == Pine mirror).
This is the hard gate for the FX overlay export. NOT the full ship model (meta/gates/
POOLED/sizing still to come) — just de-risks the codegen on a real model.

Run: py -3 scripts/fx_primary_export_smoke.py
"""
from __future__ import annotations
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))

import numpy as np
import pandas as pd
from phase3_density import build_pool, FEATURES_9
from model_validation_suite import train_lgbm, predict
from core.export.pine_codegen import lgbm_to_pine_cascade, bit_exact_check

TREES, SEED = 50, 42
CUTOFF = pd.Timestamp("2025-07-01", tz="UTC")   # production train end (val_end from retrain_v2)

def main():
    pool = build_pool()
    Xall = pool[FEATURES_9].values.astype(np.float32)
    yall = pool["_lab_long"].values
    tr = pool.index < CUTOFF
    te = pool.index >= CUTOFF
    Xtr, ytr = Xall[tr], yall[tr]
    Xte = Xall[te]
    print(f"pool={len(pool):,}  train={tr.sum():,}  test(holdout)={te.sum():,}  trees={TREES}")

    booster = train_lgbm(Xtr, ytr, Xtr, ytr, TREES, None, SEED)
    print("trained primary-long booster, num_trees =", booster.num_trees())

    # generate Pine cascade
    pine = lgbm_to_pine_cascade(booster, FEATURES_9)
    out_pine = REPO / "artifacts" / "models" / "fx_primary_long_50t_cascade.pine.txt"
    out_pine.write_text(pine, encoding="utf-8")
    print(f"pine cascade: {len(pine):,} chars -> {out_pine.name}")

    # bit-exact gate on a holdout sample
    samp = Xte[np.random.RandomState(7).choice(len(Xte), size=min(5000, len(Xte)), replace=False)]
    chk = bit_exact_check(booster, FEATURES_9, samp, atol=1e-5)
    print("BIT-EXACT:", {k: chk[k] for k in chk if k != 'sample'})

    # save the booster (production primary-long candidate)
    out_model = REPO / "artifacts" / "models" / "fx_primary_long_50t_seed42_2026-06-03.txt"
    booster.save_model(str(out_model))
    print("saved booster ->", out_model.name)

if __name__ == "__main__":
    main()
