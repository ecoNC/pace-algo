"""Bit-exact + cascade-size check for all 4 FX ship cascades (ANN-026 step 3' de-risk)."""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import numpy as np, lightgbm as lgb
from phase3_density import build_pool, FEATURES_9
from phase3_short_features import feature_cols
from core.export.pine_codegen import lgbm_to_pine_cascade, bit_exact_check

MODELS = REPO / "artifacts" / "models"
snap = json.loads((MODELS / "fx_ship_snapshot.json").read_text())
pool = build_pool(); feats_full = feature_cols(pool)
te = pool[pool.index >= snap["cutoff"]]
rs = np.random.RandomState(7)
def samp(cols):
    X = te[cols].values.astype(np.float32)
    return X[rs.choice(len(X), size=min(5000,len(X)), replace=False)]

for tag, feats in [("mL",FEATURES_9),("mS",FEATURES_9),("meL",feats_full),("meS",feats_full)]:
    b = lgb.Booster(model_file=str(MODELS / snap["models"][tag]))
    pine = lgbm_to_pine_cascade(b, feats)
    chk = bit_exact_check(b, feats, samp(feats), atol=1e-5)
    print(f"{tag:4s} feats={len(feats):2d} trees={b.num_trees():3d}  pine={len(pine):6,d} chars  "
          f"bitexact={chk['passed']}  maxdiff={chk['max_abs_diff']:.2e}")
