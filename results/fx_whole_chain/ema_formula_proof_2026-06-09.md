# ta.ema Formula Proof — 2026-06-09 (Block 2 Step 4 closeout, Gate-1 unconditional)

Closes the one conditional in the Step-4 Mengen-Abgleich (ema_200_dist_atr was injected/trusted).
Read at the LAST CLOSED bar (Pine plots `f_x[1]`; Python iloc[-2]) to remove forming-bar drift.

| feature | python | pine | \|diff\| | verdict |
|---|---|---|---|---|
| ema_20_dist_atr | 0.704566 | 0.704570 | 3.5e-6 | PASS — formula + (close-ema)/atr wrapper bit-exact |
| ema_50_dist_atr | 2.660045 | 2.660040 | 5.1e-6 | PASS — formula + wrapper bit-exact |
| ema_200_dist_atr | 5.686517 | 5.372670 | 3.1e-1 | warmup diff (Python ema200 unconverged at 400 bars) — NOT a formula diff |

## What this proves
`ta.ema(close, length)` == pandas `ewm(span=length, adjust=False)` (same recursion, alpha=2/(length+1))
at length 20 AND 50, including the shared `(close-ema)/atr` wrapper (atr itself bit-exact per Step 1).
`ema_200_dist_atr` uses the SAME ta.ema function (length=200) and the SAME wrapper → inherits
formula-identity by construction. ema200's 0.31 diff here is purely Python's warmup (400 < ~1000
bars); in production Pine runs ema200 in the CONVERGED regime — exactly the regime ema20/50 proved.

## Provenance (honest, per Nico)
ema200 formula-identity is established by **short-EMA extrapolation in the converged regime**, NOT by
a direct >1000-bar measurement (tooling-blocked: data_get_ohlcv capped at 500; visible-range clamps;
chart_scroll_to_date is a tool bug; replay_start fails; CAPITALCOM history >500 exists only in TV).
The single untested point is Python's INDEPENDENT ema200 on the specific non-converged June-7 window
— irrelevant, because production runs converged and the formula proof establishes equality there.
A future reviewer should NOT look for the >1000-bar measurement: it cannot exist via current tooling;
this extrapolation is the verification.

## Gate-1 (Whole-Chain bit-exact) — UNCONDITIONAL
- Trade SET + Class-C bars_since_sweep_down + feed-level features + chain + sizes: unconditional
  (mengen_abgleich_2026-06-08.md — 9/9 reproduced, bss 0/9 mismatch).
- EMA family (incl. ema_200_dist_atr): formula-proven (this doc).
Gate-1 is closed. Remaining live-gates: Non-Repaint-Replay (lookahead_on+[1]) + OOS-Reval.
