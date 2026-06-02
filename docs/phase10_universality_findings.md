# Phase 10 — Universality Battery (2026-06-02): Final Findings

**Question (Nico):** Can the FX approach be made good on ALL assets, long AND short?
**Answer after the most exhaustive fair test to date: NO. The tool-vs-edge reframe
(product_rethink_2026-06-01) is confirmed. FX module = the edge; other classes = tool-only.**

## What was tested (all walk-forward, net, multi-seed)

| Test | Design | Result |
|---|---|---|
| 10a FX shorts under full stack | Shorts were rejected pre-META (phase3); re-test every pair short under META+sizing | **NEGATIVE.** Short-PF per pair 0.87–1.00; every addition dilutes the lock (1.574); ALL5 collapses 2026 (1.39 vs 1.666). USDCHF-only short CONFIRMED final. |
| 10b Universe expansion | +8 symbols (Dow, Russell, FTSE, CAC, EuroStoxx, Nikkei, HangSeng, DXY) — index class 2→9 symbols | Data clean (flat ≤0.9%). Used by 10d/10c. |
| 10c Class-owned features | Engineered (not just selected): index gap/OR/prev-day/dow; metal DXY+fix; crypto weekend/funding. BASE vs BASE+CLASS, identical harness | **NEGATIVE everywhere** (after causal fix): index −0.095, metal −0.224, crypto −0.001. |
| 10d TF×R sweep, home-session gates | indices+metals, 15m/30m/1h × R 1.0–3.0 × 3 cost levels, per-symbol home session (RTH/Xetra/TSE/London-NY) | **0/72 configs pass the bar** (≥1.3 net, all years pos). Best index 1.13 (2025 neg). Metal 15m R=3: only all-years-pos candidate, thin (1.02/1.08/1.22 @0.05ATR). |
| 10e Regime routing (crypto's fix) on indices/metals | trend-follow in TREND, mean-rev in RANGE, home-session gated, raw R | **NEGATIVE.** Combined PF ~0.95 both classes, all years <1. |

## Two research-hygiene findings (as important as the results)

1. **Phase 9 root-caused.** The discarded PF 5.2 (and 10c's initial crypto PF 6.2) is a
   DATA artifact: Dukascopy XRP/LTC/ADA 5m parquets contain 5–12% flat bars and 4–8%
   gaps → ATR≈0 stretches make barrier outcomes trivially predictable.
   **RULE: Dukascopy altcoin (non-BTC/ETH) intraday data is UNUSABLE for research.**
   Clean BTC+ETH reproduce the known thin result (PF 1.095).
2. **Opening-range lookahead trap.** `groupby(day).transform("max")` over the OR window
   lets bars INSIDE the first hour see the hour's full range — inflated index/metal
   "lifts" of +0.67/+0.50 that flipped to −0.10/−0.22 after the causal cummax/cummin fix.
   Any session-window aggregate feature must be running (cum*) not whole-window.

## Where this leaves the product (recommendation)

- **FX module (LOCKED, fx_module_LOCK.md): the one real edge.** Long 5 pairs +
  USDCHF short, net PF 1.51 @0.5pip ECN, all years positive. Long AND short — as good
  as the data allows.
- **Indices / metals / crypto: tool-only.** No class clears the AI-overlay bar under
  any tested structure (agnostic gate, per-class model, session search, home-session
  TF×R sweep, regime routing, class-owned features). Metal 15m R=3 and crypto
  regime-routed (~1.07–1.11) are thin pulses — below shippable, candidates for a
  clearly-labeled "experimental" tier at best, NOT for the premium promise.
- **Next step: roadmap Phase 0 — Pine export of the FX module** (kernel lock snapshot →
  4 cascades @50t + feature engine + NY/state gate + R exec → bit-exact, ops<5000).
