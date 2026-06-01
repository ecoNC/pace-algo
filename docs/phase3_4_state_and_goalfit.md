# PaceAlgo — Phase 3+4 State & Goal-Fit Review (2026-06-01, Heim-PC)

Snapshot of where the research stands after Phase 3 (density) + Phase 4 (quality),
plus an honest assessment against the **end goal** (universal multi-asset, multi-TF
indicator with user-set RR/ADR risk + backtesting).

Commits: `9c3a386` (phase3), `5a3270c` (phase4 levers), `615464d` (phase4 treecount).

---

## 1. What we validated (FX majors, 5m, walk-forward, net of spread)

**Locked architecture (this session):**
`9-feature LGBM ranker (SELECTOR) + state/session gate (NY + tradeable vol) + simple R=1.5 execution`,
with long + short rankers, POOLED per-pair proba threshold for ~N/day, optional meta-labeling
re-rank and proba-tiered sizing.

**Best deployable V1 config:**
- long (5 pairs) + **USDCHF-short only** + META re-rank, all models **50 trees**, POOLED top10, ECN 0.5pip.
- Result: **net PF 1.30 (1.52 with sizing), WR 0.51, ~9 trades/day, all years positive (2026 1.40–1.66), Pine 88%.**

**Key empirical findings:**
- Edge is **SELECTION, not structure** — deterministic setups fail net; ML ranking within a gated
  bad population is the edge. Fewer features rank better (9 > 18 > 73).
- Density to 8–10/day comes from **more candidates (short side, more pairs)**, NOT cutoff loosening
  (refuted) — the edge lives only in the top ~3% per direction.
- **Short is thin/concentrated**: only USDCHF-short robust; GBPUSD-short loses; 2026 short negative.
- **META-labeling** lifts WR+PF without variance cost; **proba-sizing** lifts PF at higher variance.
  At equal Pine budget, 4×50-tree models (primary+meta) beat 2×100-tree (no meta).
- Refuted: trend-align gate, dynamic exits (breakeven/trail), seed ensemble, uniqueness weighting,
  short-specific features, TP/SL level sweep (R=1.5 optimal).
- **Cost-bound**: viable only at ECN spreads (0.3–0.5pip); retail 1.0pip not all-years-positive.

---

## 2. Goal-fit assessment — HONEST

**End goal (HANDOFF §1.1):** universal indicator — ANY asset (FX, indices, gold, stocks, ETFs,
crypto), ANY reasonable TF (5M–4H), consistent useful signals, user-set RR/ADR risk + reproducible
backtest. Explicitly **"NOT a hyper-optimized FX-only model."**

**What we actually built:** a hyper-optimized FX-majors, 5m, NY-session, ECN-spread, fixed-R=1.5
model — with a hardcoded pair rule (USDCHF-short-only). **This is close to the exact thing §1.1 says
the product is NOT.**

### Concrete mismatches

| End-goal requirement | Current state | Gap |
|---|---|---|
| Any asset (≥3 classes) | 5 FX majors only | Edge shown absent on EURUSD/AUDUSD; never tested on indices/crypto/stocks |
| Any timeframe (5M–4H) | 5m only; 30m marginal | NY-session gate + barriers are intraday-5m specific |
| Asset-agnostic logic | `is_fx_market_open`, `in_ny`, USDCHF-short hardcoded | FX-specific; won't transfer to 24/7 crypto or equity hours |
| User-set RR / ADR risk | R=1.5 hard-locked (labels depend on it) | Free RR breaks the validated edge; ADR-risk not built |
| Launch §1.4: PF ≥1.7 on ≥5 assets, ≥3 classes; NDX/QQQ ≥1.4 | FX PF ~1.3–1.5, 1 class, no equity data | Not launch-eligible by project's own criteria |
| V1 spec: ~15 features, ≤30 trees | 9-feat primary + 73-feat meta, 50 trees | Over the documented complexity budget |

### Is the work wasted? No.
The **methodology** (net/walk-forward/per-pair/multi-year, no-lookahead, bit-exact, the
selection-not-structure insight, meta/sizing/pooled mechanics, the honest refutations) is the durable
asset and transfers to any asset class. But the **specific locked config is an FX module**, not the
universal product.

### The core tension
The data says the edge is **thin and regime/asset-specific**. A single model "good on everything" is
likely unrealistic — consistent with the project's own ANN-009 (per-asset-class model router) and
ANN-016 (industrialize FX, launch only at ≥2 classes over the SAME blueprint). So "universal" almost
certainly means **per-asset-class models behind one consistent UI**, not one model on all markets.
And **user-configurable RR** conflicts with a fixed-R ML edge — needs a product decision: is the
product the ML edge (fixed R) or a configurable signal tool (user owns risk, PF not promised)?

---

## 3. Recommended forks (decision needed before kernel-lock)

- **A. Ship FX as the first module (honest framing).** Kernel-lock the FX V1, label it "FX majors"
  with other classes "Coming Soon" (the ANN-009 router). Backtest widget shows fixed-R results.
  Fastest to a real, defensible product; matches the empirical reality.
- **B. Pursue universal properly.** Fetch indices/crypto/metals/equity data; test whether the
  blueprint generalizes or needs per-class models + an asset-agnostic gate (replace `in_ny`/
  `is_fx_market_open` with a generic liquidity/session abstraction); validate against §1.4. Large
  effort; earlier evidence says generalization off FX is weak.
- **C. Reframe as configurable signal tool.** ML gives direction + confidence; user sets RR/ADR in
  an execution overlay. Backtest reflects the user's settings (so we can't promise the validated PF).
  Closest to the literal "user sets RR" ask, but decouples the product from the validated edge.

**My recommendation:** **A now, B as the real roadmap.** Ship the validated FX module honestly (it is
genuinely good *for FX-majors/ECN/5m*), and treat "universal" as a per-asset-class industrialization
program (B) — each class validated to §1.4 before it ships. Resolve the RR/ADR question explicitly:
keep R fixed for the *promised* edge, expose RR/ADR only as a "what-if" backtest overlay clearly
marked as user-risk (not the validated config). Do **not** market "works on every asset/TF" until B
delivers per-class validation.
