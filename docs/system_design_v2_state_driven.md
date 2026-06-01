# PaceAlgo V2 — State-Driven Trading System (Design)

**Status:** Design proposal · 2026-06-01
**Shift:** from "an ML model decides trades" → **deterministic, state-driven system** (Swift-Algo-style),
ML demoted to an *optional confluence filter* (see §8).

This design is **grounded in the empirical findings** of the ML phase, not a blank-slate SMC fantasy.
What the data proved, and what we therefore keep:

| Empirical finding (this project) | Consequence for V2 |
|---|---|
| NY session gate flips 5m net PF 0.86 → 1.17 (the single biggest lever) | **Session state is core; NY is the default trading window** |
| Low-vol bars are net cost-losers (1-ATR risk ≈ spread on quiet 5m) | **Volatility regime is a hard gate; Quiet = no-trade** |
| Edge concentrated in GBPUSD/USDJPY/USDCAD; EURUSD has none | **Scope = Tier-1; pair set is part of the spec** |
| Edge real but THIN; model complexity ≠ more robustness | **PF comes from removing bad conditions, not model IQ** |
| R-based triple-barrier (TP 1.5 / SL 1.0 ATR, 24-bar) is sound | **Keep as execution skeleton** |
| Non-repaint discipline (closed bars, lookahead_off, [1] shift, confirmed pivots) | **Mandatory, carried over verbatim** |

---

## 1. Architecture

All layers operate on **CLOSED bars only**. Strictly feed-forward — no layer reads the future.

```
                ┌─────────────────────────────────────────────┐
                │   DATA  (closed OHLCV, LTF + confirmed HTF)   │
                └───────────────────────┬─────────────────────┘
                                        │
        ┌───────────────────────────────▼───────────────────────────────┐
        │  1. MARKET STATE ENGINE   (deterministic, ≤6 discrete states)  │
        │     trend regime  ×  volatility regime  →  STATE                │
        │     + session context (Asia / London / NY)                      │
        └───────────────────────────────┬───────────────────────────────┘
                                        │  state, session
        ┌───────────────────────────────▼───────────────────────────────┐
        │  2. SETUP ENGINE   (per-state structural setups, price-action)  │
        │     trend→pullback/breakout · range→mean-revert · expansion→BO  │
        └───────────────────────────────┬───────────────────────────────┘
                                        │  candidate setup (dir, level)
        ┌───────────────────────────────▼───────────────────────────────┐
        │  3. FILTER LAYER   (HARD gates — quality > quantity)            │
        │     session gate · volatility gate · trend alignment · struct.  │
        │     [optional] ML confluence score ≥ threshold                  │
        └───────────────────────────────┬───────────────────────────────┘
                                        │  confirmed signal
        ┌───────────────────────────────▼───────────────────────────────┐
        │  4. EXECUTION LOGIC   (R-based, one position, non-repaint)      │
        │     entry next-bar-open · SL=1·ATR · TP=1.5·ATR · time-barrier  │
        └─────────────────────────────────────────────────────────────────┘
                                        │
                            BUY / SELL  +  tier (Std/High/Premium)
```

---

## 2. Market State Engine

Two orthogonal deterministic axes → a small discrete state set. Every input is a closed-bar value.

**Axis A — Trend regime** (from HTF EMA alignment + ADX, all on confirmed bars):
- `TREND_UP`   : EMA20>EMA50>EMA200 (on LTF) AND HTF(1h) EMA-aligned up AND ADX ≥ 20
- `TREND_DOWN` : mirror
- `RANGE`      : ADX < 18 (no directional conviction)

**Axis B — Volatility regime** (from ATR percentile over 100 bars):
- `EXPANSION` : atr_pct_rank ≥ 0.70  (and rising) — breakout conditions
- `NORMAL`    : 0.33 ≤ atr_pct_rank < 0.70
- `QUIET`     : atr_pct_rank < 0.33 — **NO-TRADE** (cost-losing zone, proven)

**Resulting actionable STATES (≤6):**
| State | Condition | Tradeable? |
|---|---|---|
| `S1_TREND_PULLBACK` | TREND_UP/DOWN × (NORMAL∨EXPANSION) | ✅ pullback continuation |
| `S2_BREAKOUT`       | (TREND or RANGE) × EXPANSION | ✅ breakout |
| `S3_RANGE_REVERT`   | RANGE × NORMAL | ✅ mean-reversion |
| `S4_QUIET`          | any × QUIET | ❌ no-trade |
| `S5_NEWS_SHOCK`     | atr_pct_rank ≥ 0.97 (extreme) | ❌ stand aside (risk) |

Session context (Asia/London/NY) is computed in parallel and consumed by the Filter Layer (§3),
not folded into the state enum (keeps states market-structural, session orthogonal).

---

## 3. Setup Engine (per state, structural — no probability-only triggers)

Each tradeable state has 1–2 **price-action setups** with an exact, closed-bar trigger:

- **S1_TREND_PULLBACK** → *Pullback continuation*: in an up-trend, price pulls back to a reference
  (EMA20 / prior confirmed swing-low / bull-FVG mid) and prints a **confirmed reversal bar**
  (close back above the level). Long. (Mirror for down-trend.)
- **S2_BREAKOUT** → *Liquidity-sweep breakout*: price sweeps a confirmed swing high/low (takes liquidity)
  then **closes back through** the level in the breakout direction within N bars. Trade the reclaim.
- **S3_RANGE_REVERT** → *Range-edge fade*: in a confirmed range, price reaches the upper/lower band
  (e.g. BB or range high/low) with a sweep + rejection close → fade back toward mid.

All triggers are **confirmed-bar events** (sweep = pivot confirmed with rightbars; reclaim = bar close
beyond level). No intrabar / repainting triggers.

---

## 4. Filter Layer (HARD gates — the proven PF lever)

A candidate setup must pass ALL active gates to become a signal:

1. **Session gate** — `in_ny` (13–22 UTC). *(Empirically the #1 net-PF driver.)* Balanced default = NY-only.
2. **Volatility gate** — state ≠ QUIET and ≠ NEWS_SHOCK (atr_pct_rank ∈ [0.33, 0.97)).
3. **Trend-alignment gate** — setup direction must agree with HTF(1h/4h) bias (no counter-trend in trend states).
4. **Structure confirmation** — require the setup's structural event (sweep/reclaim/rejection) on a closed bar.
5. **[Optional] ML confluence score** ≥ threshold (§8) — final quality skim.

> Design intent: gates *subtract* bad trades. Each gate must justify itself by **net-PF lift under
> walk-forward**, exactly as we validated the NY gate (0.86→1.17). No gate ships without that proof.

---

## 5. Execution Logic (R-based, deterministic, non-repaint)

- **Entry:** next-bar-open after the confirmed trigger (validated as realistic + net-neutral vs close-entry).
- **Stop:** entry − 1.0 × ATR(14) (long); **Target:** entry + 1.5 × ATR(14). (R = 1.5.)
- **Time barrier:** close at market after 24 bars if neither hit (matches labeling; bounds exposure).
- **One position per symbol** (no pyramiding). New signal only when flat.
- **Tiers** (display + optional sizing): Standard / High / Premium = increasing confluence
  (e.g. # of gates passed, or ML score band). Same trade mechanics; tier is a confidence label.

---

## 6. Reaching 8–10 trades/day (Balanced) — by construction, not by loosening

Density = **#pairs × #setups × session-hours**, throttled by a quality threshold — never by trading QUIET.

- 3 Tier-1 pairs × ~3 tradeable states × NY window (~9h on 5m) → ample candidates.
- Empirically (validated): **5m + Tier-1 + NY gate ≈ 7 trades/day** at q97-equivalent selectivity.
- To dial to **8–10/day**: (a) include the **London→NY overlap** hour in the session gate, and/or
  (b) add **NZDUSD/USDCHF as Conditional pairs** (NY-gated), and/or (c) slightly relax the structure-
  confirmation strictness — each change **must hold net-PF under walk-forward** before it's accepted.
- **Modes** = different gate/threshold presets on the *same* engine:
  - **Aggressive** ≈ 12–18/day (NY, all tradeable states, looser confluence)
  - **Balanced** ≈ 8–10/day (NY, exclude RANGE_REVERT in chop, medium confluence)  ← product default
  - **Conservative** ≈ 2–4/day (NY+vol, EXPANSION/strong-trend only, high confluence)

Modes change *selection*, not the engine — fully reproducible.

---

## 7. No-Repaint & Backtesting guarantees (the non-negotiables)

| Requirement | How it's guaranteed |
|---|---|
| All features on bar-close / confirmed | State/Setup/Filter read only `close[t]` and earlier; no `[0]` intrabar logic |
| No HTF lookahead | `request.security(..., barmerge.lookahead_off)` + `[1]` shift → only the *last closed* HTF bar |
| Confirmed structure only | `ta.pivothigh/low(L, R)` resolves at bar[R]; sweeps/levels forward-filled, never future |
| No forward-repaint signals | Signal evaluated at bar close; entry at next bar open; a printed signal never moves |
| Python ↔ Pine parity | Deterministic rules → bit-exact achievable (same discipline as `pine_codegen` bit-exact tests) |
| Reproducible backtest | Fixed rules + fixed data + walk-forward splits → identical results across runs |
| Realistic costs | Backtest is **net** (spread + next-bar-open) by default — gross numbers are banned from decisions |

Validation protocol carried over: **walk-forward (rolling quarters) × multi-seed-equivalent robustness,
net of spread, per-pair persistence** — every rule/gate proven this way before locking.

---

## 8. Does ML still have a role? — Honest recommendation

**Verdict: V1 ships ML-FREE in the decision path. ML returns later as an OPTIONAL confluence filter, never the decider.**

Why:
- Our own evidence: the ML edge was *real but thin*, and **structure + regime + session filtering delivered
  the larger, more robust gains**. Model complexity (XGB, deeper trees, more features) did **not** add net
  robustness. The biggest single win (NY gate, +0.31 net PF) was pure structure.
- A deterministic engine maximizes exactly what you asked for: reproducibility, non-repaint guarantee,
  backtestability, and *intuitive trading logic instead of black-box*.

**Where ML adds the most value (V1.5+), if at all:** as a **meta-labeling / confluence score** —
the deterministic engine proposes a candidate setup; the LGBM (trained on the same closed-bar features)
outputs P(this setup wins) and acts as a **final quality gate** ("take only setups with score ≥ X").
This is the textbook role for ML here: *rank/skim* deterministic setups, not generate them. It stays
non-repainting (deterministic function of closed-bar features) and interpretable (it only ever *removes*
trades). It must clear the same net-PF walk-forward bar as any other gate, or it doesn't ship.

So: **deterministic core now; ML as optional precision filter once the core is proven.**

---

## 9. Implementation path (Python research ↔ Pine, phased)

1. **`core/state/` — Market State Engine** (Python): deterministic state classifier from closed-bar OHLCV +
   confirmed HTF. Unit-tested, no lookahead.
2. **`core/setups/` — Setup Engine**: per-state structural triggers, each returning (dir, entry-level, confirmed-bar).
3. **`core/filters/` — Filter Layer**: composable gates, each with a net-PF walk-forward justification.
4. **Backtester** (net, next-bar-open, walk-forward) — reuse `scripts/system_balanced.py` machinery.
5. **Pine port** with bit-exact parity tests vs Python (reuse the `pine_codegen` bit-exact discipline).
6. ML confluence filter — only after 1–5 are net-validated.

## 10. What we keep from the ML era (don't throw away the gold)

- The **net/cost-aware, walk-forward, per-pair, multi-seed validation methodology** (it caught every artifact).
- The **NY-session + volatility-regime + Tier-1 findings** (they ARE the state/gate definitions above).
- The **non-repaint feature implementations** (HTF [1]-shift, confirmed pivots, FVG 0-fill).
- The **R-based execution skeleton** (1.5/1.0 ATR, 24-bar barrier).
- The **LGBM model** as the future optional confluence scorer (not discarded — repurposed).
