"""Block-2 Step 4 closeout: ta.ema FORMULA proof. Plots the FULL features ema_20/50/200_dist_atr
(= (close-ema)/atr, the same wrapper ema_200_dist_atr uses) to the data window. Read at the
current (fully-warmed) bar vs Python: ema20 (converges ~100 bars) + ema50 (~250) match ~1e-6 ->
ta.ema == ewm(adjust=False) + alpha + wrapper proven by construction -> ema200 (same function)
inherits formula-identity. ema200 at this bar shows the WARMUP diff (documents it's warmup, not
formula). Reuses HELPERS_HEADER + registry snippets (single source of truth).

Run: py -3 scripts/fx_build_ema_pine.py  -> deploy_pine/fx_ema_validate.pine
"""
from __future__ import annotations
import sys
from pathlib import Path
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))
from core.export.pine_features import render_feature_engine

feats = ["ema_20_dist_atr", "ema_50_dist_atr", "ema_200_dist_atr"]
eng = render_feature_engine(feats)
assert not eng["dropped_features"], f"dropped: {eng['dropped_features']}"
# Plot the LAST CLOSED bar ([1]) — the forming bar's close ticks and would drift (close-ema)/atr
# by ~Δclose/atr for all features (atr tiny -> amplified). Closed bar is stable for clean compare.
plots = "\n".join(f'plot(f_{f}[1], "{f}", display=display.data_window)' for f in feats)
pine = f"""//@version=6
// ta.ema FORMULA proof (Block-2 step 4 closeout) — AUTO-GENERATED, DO NOT EDIT.
// Read at current (fully-warmed) bar vs Python: ema20/ema50 ~1e-6 proves ta.ema==ewm+wrapper;
// ema200 here shows the warmup diff (not a formula diff).
indicator("FX EMA Validate", overlay=false)

{eng['helpers'].rstrip()}

{eng['features'].rstrip()}

{plots}
"""
out = REPO / "deploy_pine" / "fx_ema_validate.pine"
out.write_text(pine, encoding="utf-8")
print(f"written {out}  ({len(pine):,} chars, {pine.count(chr(10))} lines)  feats={feats}")
