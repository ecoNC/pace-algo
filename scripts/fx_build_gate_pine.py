"""Block-2 Step 1: minimal Pine to bit-exact-verify the FX-module tradeable GATE.

The gate defines the FX trade population (PF 1.51 was measured on exactly these bars), so it
is pinned FIRST in isolation (Nico-locked sequence, fx_module_LOCK.md). tradeable reduces to:
    tradeable = (atr_pctile >= 0.33) AND (atr_pctile < 0.97) AND not warmup
where atr_pctile = atr14.rolling(100,min_periods=100).rank(pct=True) == _pf_pctrank100(_atr14)
(already proven bit-exact). Reuses HELPERS_HEADER so _atr14 / _adx14 / _pf_pctrank100 are
byte-identical to the production feature engine. Plots tradeable + atr_pctile + adx for
back-to-back comparison vs Python core.state.classify_market_state on the same TV bars.

Run: py -3 scripts/fx_build_gate_pine.py  -> deploy_pine/fx_gate_validate.pine
"""
from __future__ import annotations
import sys
from pathlib import Path
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))
from core.export.pine_features import HELPERS_HEADER
from core.state.market_state import DEFAULT_PARAMS as MS

VQ, VS = MS["vol_quiet"], MS["vol_shock"]   # 0.33 / 0.97 — single source of truth

pine = f"""//@version=6
// FX-module GATE validation (Block-2 step 1) — AUTO-GENERATED, DO NOT EDIT.
// Bit-exact target: core.state.market_state.classify_market_state['tradeable'].
indicator("FX Gate Validate", overlay=false)

{HELPERS_HEADER.rstrip()}

// === FX-module tradeable gate (classify_market_state) ===
// vol veto: QUIET (pctile < {VQ}) or SHOCK (pctile >= {VS}) => not tradeable; warmup => not tradeable.
_ms_atr_pctile = _pf_pctrank100(_atr14)
_ms_warm       = na(_adx14) or na(_atr14) or na(_ms_atr_pctile)
_ms_tradeable  = (not _ms_warm) and _ms_atr_pctile >= {VQ} and _ms_atr_pctile < {VS} ? 1.0 : 0.0

plot(_ms_tradeable,  "tradeable",  display=display.data_window)
plot(_ms_atr_pctile, "atr_pctile", display=display.data_window)
plot(_adx14,         "adx14",      display=display.data_window)
plot(_atr14,         "atr14",      display=display.data_window)
"""

out = REPO / "deploy_pine" / "fx_gate_validate.pine"
out.write_text(pine, encoding="utf-8")
print(f"written {out}  ({len(pine):,} chars, {pine.count(chr(10))} lines)  vol_quiet={VQ} vol_shock={VS}")
