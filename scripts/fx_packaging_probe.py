"""Packaging Model-B ops probe (risk-first, no UX build): does 'PaceAlgo FX + slim regime
dashboard + module-own backtest' fit the Pine ops budget?

Conservative proxy: pace_algo_fx.pine (full FX module) + pace_algo_v1.pine lines 205..end
(the trade-sim + MTF + 3 panels = the display/backtest portion), EXCLUDING v1's rule-core
signal engine (lines 145-204). estimate_pine_ops only counts operators (no valid code needed),
so the concat is a fair upper bound: it uses v1's FULL panels (heavier than a slimmed set) and
double-counts the regime calc that FX already carries -> if THIS fits, slim Model B fits.
"""
import sys
sys.path.insert(0, '.')
from pathlib import Path
from core.export import pine_codegen as p

fx = Path('deploy_pine/pace_algo_fx.pine').read_text(encoding='utf-8', errors='replace')
v1 = Path('deploy_pine/pace_algo_v1.pine').read_text(encoding='utf-8', errors='replace').splitlines()
v1_display = "\n".join(v1[204:])   # lines 205..end (1-indexed) = trade-sim + panels, no signal engine

def show(name, src):
    r = p.estimate_pine_ops(src)
    print(f"=== {name} ===")
    for k in ['ops_estimate', 'ops_pct_of_budget', 'request_security_calls', 'n_lines', 'passed_budget_check', 'warnings']:
        print(f"  {k}: {r[k]}")
    return r

show("FX module (standalone)", fx)
show("v1 display+backtest portion (lines 205..end)", v1_display)
show("Model B proxy: FX + v1 display/backtest (conservative upper bound)", fx + "\n" + v1_display)
