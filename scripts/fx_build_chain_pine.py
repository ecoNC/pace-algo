"""Block-2 Step 3: assemble the full FX selection chain into one validation Pine.

Encodes the chain 1:1 from fx_production_train.py (marr + build_cands + selection) — the
THREE operator-order traps (Nico-locked):
  (a) gen-gate BEFORE meta:  scoreL = (gate AND pL >= gen_long) ? pmL : NEG   (meta only ranks gen-passers)
  (b) POOLED dedupe per bar takes the HIGHER meta-proba (sort-desc + drop_duplicates => long+short
      collision resolves to the higher proba; tie -> long, stable sort with long frame first):
        pooled = max(scoreL, scoreS);  dir = scoreL >= scoreS ? long : short
  (c) Sizing tiers on the META-proba (_pooled), not primary:
        size = pooled < size_q1 ? 0.5 : pooled < size_q2 ? 1.0 : 1.5
Gate = in_ny AND tradeable (tradeable = classify_market_state vol-veto, Step-1 _ms_tradeable).
Short path USDCHF-only (build_cands cfg 'long_short_usdchf'). All thresholds FIX from snapshot.

Plots: signal (0/1), direction (+1/-1/0), pooled_proba, size — for the Step-3 plausibility check.

Run: py -3 scripts/fx_build_chain_pine.py  -> deploy_pine/fx_chain_validate.pine
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import lightgbm as lgb
from phase3_density import build_pool, FEATURES_9
from phase3_short_features import feature_cols
from core.export.pine_codegen import lgbm_to_pine_cascade, cascade_signature_args, _pine_arg
from core.export.pine_features import render_feature_engine
from core.state.market_state import DEFAULT_PARAMS as MS

MODELS = REPO / "artifacts" / "models"
snap = json.loads((MODELS / "fx_ship_snapshot.json").read_text())
GL, GS = snap["gen_long"], snap["gen_short"]
THR, Q1, Q2 = snap["pooled_thr"], snap["size_q1"], snap["size_q2"]
VQ, VS = MS["vol_quiet"], MS["vol_shock"]
DEFAULT_FN = "f_pace_algo_v1_probability"
RENAME = {"mL": "f_pL", "mS": "f_pS", "meL": "f_pmL", "meS": "f_pmS"}
PROB = {"mL": "pL", "mS": "pS", "meL": "pmL", "meS": "pmS"}

def load(t):
    return lgb.Booster(model_str=(MODELS / snap["models"][t]).read_text(encoding="utf-8").replace("\r\n", "\n"))

def main():
    pool = build_pool(); feats_full = feature_cols(pool)
    namemap = {"mL": FEATURES_9, "mS": FEATURES_9, "meL": feats_full, "meS": feats_full}
    casc = {t: load(t) for t in RENAME}
    blocks, calls, seen = [], [], []
    for t in RENAME:
        b, names = casc[t], namemap[t]
        blocks.append(lgbm_to_pine_cascade(b, names).replace(DEFAULT_FN, RENAME[t]))
        for n in cascade_signature_args(b, names):
            if n not in seen: seen.append(n)
        calls.append((t, RENAME[t], ", ".join(_pine_arg(n) for n in cascade_signature_args(b, names))))
    eng = render_feature_engine(seen)
    assert not eng["dropped_features"], f"dropped: {eng['dropped_features']}"

    call_lines = [f"{PROB[t]} = {fn}({args})" for t, fn, args in calls]
    chain = f"""// === FX-module tradeable gate (classify_market_state, Step-1 verified) ===
_ms_atr_pctile = _pf_pctrank100(_atr14)
_ms_warm       = na(_adx14) or na(_atr14) or na(_ms_atr_pctile)
_ms_tradeable  = (not _ms_warm) and _ms_atr_pctile >= {VQ} and _ms_atr_pctile < {VS}

// === Selection chain (1:1 fx_production_train.py; thresholds FIX from fx_ship_snapshot.json) ===
_gate      = (f_in_ny > 0.5) and _ms_tradeable
_is_usdchf = str.contains(syminfo.tickerid, "USDCHF")
_NEG       = -1e9
// (a) gen-gate BEFORE meta: meta-proba only ranks gen-passers, else NEG
_scoreL = (_gate and pL >= {GL}) ? pmL : _NEG
_scoreS = (_is_usdchf and _gate and pS >= {GS}) ? pmS : _NEG
// (b) POOLED dedupe per bar -> higher meta-proba wins (tie -> long)
_pooled  = math.max(_scoreL, _scoreS)
_sig_dir = _scoreL >= _scoreS ? 1 : -1
_signal  = _pooled >= {THR}
// (c) sizing tiers on the META-proba (_pooled)
_size    = _pooled < {Q1} ? 0.5 : (_pooled < {Q2} ? 1.0 : 1.5)

plot(_signal ? 1.0 : 0.0,            "signal",       display=display.data_window)
plot(_signal ? _sig_dir : 0,         "direction",    display=display.data_window)
plot(_pooled,                        "pooled_proba", display=display.data_window)
plot(_signal ? _size : 0.0,          "size",         display=display.data_window)

// === Step-4 MENGEN instrumentation: running count + per-signal label (time|dir|size) ===
// Label text encodes the bar timestamp so data_get_pine_labels yields the full signal SET.
var int _sig_count = 0
if _signal
    _sig_count += 1
    label.new(bar_index, high, str.tostring(time) + "|" + str.tostring(_sig_dir) + "|" + str.tostring(_size),
              color=color.new(color.blue, 100), textcolor=color.blue, size=size.tiny, style=label.style_none)
plot(_sig_count, "sig_count", display=display.data_window)
"""
    pine = f"""//@version=6
// FX selection-chain validation (Block-2 step 3) — AUTO-GENERATED, DO NOT EDIT.
// Full chain: gate -> gen -> meta-rank -> POOLED(dedupe) -> signal>=pooled_thr -> sizing.
indicator("FX Chain Validate", overlay=false, max_lines_count=20, max_labels_count=500)

{eng['helpers'].rstrip()}

{eng['htf'].rstrip()}

{eng['features'].rstrip()}

{chr(10).join(b.rstrip() for b in blocks)}

{chr(10).join(call_lines)}

{chain}"""
    out = REPO / "deploy_pine" / "fx_chain_validate.pine"
    out.write_text(pine, encoding="utf-8")
    print(f"thresholds: gen_long={GL:.5f} gen_short={GS:.5f} pooled_thr={THR:.5f} size_q1={Q1:.5f} size_q2={Q2:.5f}")
    print(f"written {out}  ({len(pine):,} chars, {pine.count(chr(10))} lines)")

if __name__ == "__main__":
    main()
