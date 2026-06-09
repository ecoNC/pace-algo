# Gate #2 (Non-Repaint) — Intra-Bar Interim Check, GBPUSD 5m, 2026-06-09

**Method:** replay-free two-capture live-forward (replay_start confirmed dead for 5m forward-step).
Capture #1 recorded 41 signals on closed bars at 06:50 UTC while the 05:00–09:00 UTC 4h HTF bar
was still forming. This interim re-pull is the "30-min early signal": confirm no INTRA-bar repaint
as new 5m bars print within the same still-forming 4h bar.

## Result — PASS (no intra-bar repaint)

- Capture #1 anchor: forming 5m bar open 06:50 UTC (unix 1780987800), sig_count 41.
- Interim re-pull: forming 5m bar open **07:20 UTC** (unix 1780989600), sig_count **41**.
- 6 new 5m bars formed (06:55, 07:00, 07:05, 07:10, 07:15, 07:20), **all inside the same 4h bar** (05:00–09:00 UTC).
- **Byte-diff of all 41 signal labels (time|dir|size|pooled|bss|ema_dist) vs Capture #1: 0 differences — BYTE-IDENTICAL.**

→ As the 5m bars evolve within the still-forming 4h HTF bar, the historical printed signals do
not move/appear/vanish. The `[1] + lookahead_on` idiom reads the last CLOSED HTF bar; intra-bar
stability confirmed.

## Still outstanding — the GOLD proof
Re-capture after the **09:00 UTC** 4h boundary crossing (the moment the forming 4h bar actually
closes and the next forms). Byte-identity of the same 41 closed-bar signals there = full non-repaint
proof. Until then Gate #2 is intra-bar-confirmed but not boundary-confirmed.

Baseline: `gate2_capture1_GBPUSD_2026-06-09.json` (the 41-signal SET).
