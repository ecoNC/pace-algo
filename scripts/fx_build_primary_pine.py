"""Assemble a minimal, compilable 9-feat primary-long validation Pine (ANN-026 step 3', block 1).

Goal: prove the generated feature-engine + tree-cascade COMPILE in TV 3.2.0, and expose pL + the
9 feature values as plots for whole-chain bit-exact comparison vs Python mL.predict.
NOT the full ship overlay — the smallest testable building block of the 4-cascade build.

Run: py -3 scripts/fx_build_primary_pine.py  -> deploy_pine/fx_primary_validate.pine
"""
from __future__ import annotations
import sys, json
from pathlib import Path
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import lightgbm as lgb
from phase3_density import FEATURES_9
from core.export.pine_codegen import lgbm_to_pine_cascade
from core.export.pine_features import render_feature_engine

MODELS = REPO / "artifacts" / "models"
snap = json.loads((MODELS / "fx_ship_snapshot.json").read_text())
# Load via model_str with LF-normalized newlines — git may check the .txt out with
# CRLF, which breaks LightGBM's tree_sizes byte-offset parser (see wr_gap_analysis.py).
_mL_str = (MODELS / snap["models"]["mL"]).read_text(encoding="utf-8").replace("\r\n", "\n")
mL = lgb.Booster(model_str=_mL_str)

eng = render_feature_engine(FEATURES_9)
cascade = lgbm_to_pine_cascade(mL, FEATURES_9)   # defines f_pace_algo_v1_probability(...)
arglist = eng["feature_arg_list"]

# plots of the 9 features (for bit-exact read-back vs Python)
fnames = ["f_hour_cos","f_hour_sin","f_rvol_20","f_ema_20_dist_atr","f_atr_pct",
          "f_htf_4h_rsi_14","f_is_fx_market_open","f_in_ny","f_htf_4h_atr_percentile_100"]
feat_plots = "\n".join(f'plot({fn}, "{fn[2:]}", display=display.data_window)' for fn in fnames)

pine = f"""//@version=6
// FX Primary-Long validation build (ANN-026 step 3' block 1) — AUTO-GENERATED, DO NOT EDIT.
// Proves: feature engine + primary-long cascade compile in TV; pL + 9 feats exposed for bit-exact.
indicator("FX Primary Validate", overlay=false, max_lines_count=20)

{eng['helpers'].rstrip()}

{eng['htf'].rstrip()}

{eng['features'].rstrip()}

{cascade.rstrip()}

pL = f_pace_algo_v1_probability({arglist})
plot(pL, "pL_primary_long", color=color.teal)
{feat_plots}
"""

out = REPO / "deploy_pine" / "fx_primary_validate.pine"
out.write_text(pine, encoding="utf-8")
print(f"written {out}  ({len(pine):,} chars, {pine.count(chr(10))} lines)")
print("cascade fn: f_pace_algo_v1_probability  | features:", len(FEATURES_9))
