# Gate #2 (Non-Repaint) — GOLD boundary-crossing proof, GBPUSD 5m, 2026-06-09

**PASS.** After the 05:00-09:00 UTC 4h HTF bar actually CLOSED (capture at 09:05 UTC, feed bar
unix 1780995900, new 4h bar forming), all 41 closed-bar signals are BYTE-IDENTICAL to Capture #1
(taken at 06:50 UTC while that 4h bar was still forming). 0 differences across time|dir|size|pooled|
bars_since_sweep_down|ema_200_dist_atr.

Chain of evidence:
- Capture #1 (06:50 UTC, 4h forming): 41 signals -> gate2_capture1_GBPUSD_2026-06-09.json
- Intra-bar interim (07:20 + 07:25 UTC, same 4h bar): 0 diffs -> gate2_interim_intrabar_2026-06-09.md
- GOLD boundary crossing (09:05 UTC, 4h bar CLOSED): 0 diffs (this file)

=> The barmerge.lookahead_on + expr[1] idiom reads the LAST CLOSED HTF bar and does NOT repaint
when the forming HTF bar resolves. The flag carried the lookahead risk; the [1] shift neutralises it.
Empirically proven by forward-stepping across a real 4h boundary (replay_start was dead for 5m).

GATE #2 CLOSED. All three live-gates green: #1 whole-chain bit-exact, #2 non-repaint (this),
#3 OOS-reval (per-year + per-symbol, all 5 >=1.3). FX-Majors -> COVERAGE_MATRIX "Edge-Validated (live)".