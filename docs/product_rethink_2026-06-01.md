# PaceAlgo — Fundamental Product Rethink (2026-06-01)

Triggered by the cross-asset generalization result (`phase5`, commit `e4eba66`): the
ML-edge approach does **not** deliver a universal, multi-asset, user-configurable product.
This doc reframes the product around what the data actually supports.

---

## 1. Why the current approach cannot meet the end goal (evidence)

End goal (HANDOFF §1.1): one indicator, **any asset, any timeframe**, good results,
**user-set RR / ADR risk**, reproducible backtest.

What 2 phases of rigorous testing showed:
- The edge is **SELECTION within a gated population**, and it is **thin**.
- It is **FX-majors specific** — absent on EURUSD/AUDUSD, and cross-asset H1 fails
  (FX 1.11, crypto 1.05, metals 0.95, indices 0.88; mean 1.00, 0/4 classes ≥1.3).
- It is **session-specific** — FX drops 1.27→1.11 once the NY gate is removed. The NY
  gate, not the model, carried most of the FX edge.
- It is **fixed-R** — the labels/edge depend on TP1.5/SL1.0; user-set RR breaks it
  (TP/SL sweep already showed R=1.5 is the only good point).
- It is **cost-bound** — viable only at ECN spreads.

**Conclusion:** a single trained ML model that is "good on everything with user-set risk"
is not a thing the data supports. Forcing it produces either a narrow FX product OR a
break-even universal one. The premise needs to change, not the tuning.

---

## 2. The reframe — separate the TOOL from the EDGE

Two different things were conflated:

- **A universal TOOL** (works on any chart, user-configurable, transparent backtest) —
  this is achievable by construction, and it is what the $39–49/mo TradingView market
  actually buys.
- **A universal EDGE** (net-profitable everywhere) — this does **not** exist via our
  approach, and probably not via any single model. Edge is local (FX+session+ECN).

**New product definition:**
> PaceAlgo = an **adaptive, self-calibrating signal + risk-management framework** that
> works on any asset/timeframe by construction, with **user-configurable risk (RR, ADR/
> ATR stops, session filter)** and a **reproducible backtest panel** — plus an **optional
> ML "Confidence" overlay** that is active only on markets where we have a validated model
> (FX majors first). The AI is a *premium quality layer*, not the signal generator.

This is exactly the design-doc §8 stance ("deterministic core, ML as optional precision
filter") — which we correctly refuted as a *standalone net-edge generator*, but which is
the *right* role for ML in a **configurable tool**: it ranks/skims, the user owns risk.

---

## 3. Proposed V1 architecture (adaptive, universal-by-construction)

All self-normalizing (ATR/percentile based) so it adapts to each asset's scale + vol:

```
1. CONTEXT (per chart, no pre-training)
   - Volatility regime: ATR percentile (QUIET = no-trade — validated cost-loser)
   - Trend regime: EMA alignment + ADX
   - ADAPTIVE activity window: detect the asset's high-activity hours from ITS OWN
     volume/volatility profile (auto = NY for FX, RTH for indices, ~24/7 for crypto)
     -> replaces the hardcoded in_ny gate; universal by construction.

2. SIGNAL (user-selectable modes, not promised-edge)
   - Pullback-continuation / breakout-reclaim / range-fade (design §3), each a
     confirmed-bar, non-repaint trigger.

3. RISK (user-configurable — first-class inputs)
   - RR ratio, SL method (ATR mult / ADR fraction / structure), time-barrier,
     session filter on/off, one-position rule.

4. BACKTEST PANEL (per current chart/TF)
   - PF / WR / MDD / trades-per-day for the user's settings, non-repaint, reproducible.

5. [PREMIUM] ML CONFIDENCE OVERLAY (only on supported markets)
   - On FX majors: the validated long/short ranker + meta outputs a 0–100 confidence;
     "Premium" badge on high-confidence setups. Off / generic heuristic elsewhere until a
     class is validated (ANN-009 router fills classes in over time).
```

Universal by construction (1–4 compute live, any symbol). The *edge* claim is scoped to
where ML is validated (5). Everything else is an honest, high-quality configurable tool.

---

## 4. Keep / change

**Keep (all reusable):** the net/walk-forward/multi-year/no-lookahead methodology;
the volatility-regime + adaptive-session insight; R-based execution skeleton; bit-exact
Pine discipline; the FX long/short+meta+sizing model (becomes the FX Confidence overlay);
all the refutation knowledge (don't re-try dead levers).

**Change:** stop promising a universal *edge*. Make risk user-configurable (was locked
R=1.5). Replace hardcoded NY gate with adaptive activity-window detection. Demote ML to
overlay. Revisit §1.4 launch criteria — "PF ≥1.7 on ≥5 assets/3 classes" assumed a
universal edge that doesn't exist; criteria should be split into (a) tool quality/UX bar
and (b) per-class ML-overlay validation bar.

---

## 5. Honest positioning

- **Don't** market "AI that wins on every asset." Market "adaptive multi-factor signal
  engine + transparent, configurable backtest, with AI confidence scoring on supported
  markets (FX live; more rolling out)."
- The AI/ML is the **premium differentiator where earned**, not a blanket claim.
- This is defensible, shippable, and matches both the data and the TV-indicator market.

---

## 6. Open decisions (for Nico)

1. Accept the tool-vs-edge reframe as the product direction? (vs. ship narrow FX-only.)
2. Is "user-configurable risk + adaptive universal tool + FX-AI-overlay" the V1 scope?
3. Revise §1.4 launch criteria to the split (tool bar + per-class ML bar)?
4. Build order: (a) adaptive deterministic core in Pine first, then bolt on FX overlay; or
   (b) finish/lock the FX ML model first as the flagship overlay, then build the tool around it.
