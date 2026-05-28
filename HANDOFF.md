# PaceAlgo — Project Handoff Document

**Status as of:** 2026-05-27
**Repository:** `github.com/ecoNC/pace-algo` (private, owner: ecoNC / Nico Flotz)
**Local path:** `C:\Users\nico.flotz\Downloads\pace-algo\`
**Working environment:** Windows 11, Python 3.13, Google Colab for ML training, TradingView Pine Editor for deployment

**Document version:** v2 — reaffirmed and date-stamped 2026-05-27 at start of fresh Claude session. Content from previous session (created 2026-05-26) verified intact and accurate. No project state has changed since the previous session ended.

---

## 0.0 Standard Boot Prompt (what Nico copy-pastes into every new chat)

When Nico starts a fresh Claude session — on either machine — his very first message will be (or should be) the standard boot prompt:

```
PaceAlgo Boot. Workstation: <arbeits-pc oder heim-pc>.
Mach git pull im pace-algo Repo, lies HANDOFF.md (Sections 0, 0a, 19, 20),
und sag mir in 2 Sätzen wo wir stehen und was als nächstes ansteht.
```

If you receive this message, your job is mechanical:

1. `git -C "C:\Users\nico.flotz\Downloads\pace-algo" pull --ff-only origin main` (adjust path on Heim-PC if different)
2. Read this entire HANDOFF.md — at minimum Sections 0, 0a, 16, 19, 20
3. Reply in German with EXACTLY:
   - One sentence: where we are (last session log entry + any open in-flight work)
   - One sentence: what the next concrete action is (next notebook, next decision, next test)
   - Optionally: one line "Bereit." or a clarifying question if Section 19 + Section 16 contradict each other

**Do NOT** start working on anything before Nico confirms direction. The boot prompt is a status report, not a work order.

If Nico forgets to send the boot prompt and goes straight into a task, still run the boot sequence silently (`git pull`, read HANDOFF) before responding, then proceed with his task.

---

## 0. CRITICAL — READ THIS FIRST (Multi-Workstation Protocol)

**You are a Claude session working on PaceAlgo. There are TWO physical Claude installations on TWO different machines (Arbeits-PC and Heim-PC), each with its own Anthropic account and its own local memory. They share only this Git repository.**

**This HANDOFF.md is the SINGLE SOURCE OF TRUTH.** Memory files are NOT synchronized between accounts. Anything not in this document, in the repo's tracked code, or in commit history is potentially out-of-date or unknown to your sibling Claude on the other machine.

### 0.1 Mandatory Boot Sequence — Run BEFORE every action

Every time you (Claude) start a session or get re-invoked after a long pause:

```powershell
# 1. Pull latest HANDOFF + code (the OTHER Claude may have committed since your last turn)
git -C "C:\Users\nico.flotz\Downloads\pace-algo" pull --ff-only origin main

# 2. Read this entire HANDOFF.md (top to bottom)

# 3. Check Section 19 (Session Handoff Log) — look at the LAST row
#    - If workstation_id differs from yours → sibling Claude worked recently
#    - If "Outstanding next step" mentions an unfinished task → that's your starting point

# 4. Check Section 16 (Open Action Items) for in-flight work
```

If `git pull` reveals new commits since you last looked: STOP and re-read HANDOFF.md before doing anything. The sibling session may have changed plans, decisions, or code structure.

### 0.2 Mandatory End-of-Turn Protocol — Run AFTER every meaningful change

Every time you finish a substantive piece of work in a session:

```powershell
# 1. Append a Session Handoff Log entry (Section 19) describing what you did
# 2. Commit + push HANDOFF.md (and any code changes) to GitHub
#    Always commit as: ecoNC <ecoNC@users.noreply.github.com>
# 3. Confirm push succeeded (`git push origin main` returns 0)
```

If you skip this, the sibling Claude on the other machine has NO WAY to learn what you did. Treat this as non-negotiable.

### 0.3 Workstation Identification

When logging in Section 19, identify your workstation. Ask Nico if unsure. Common identifiers:
- `arbeits-pc` — work machine
- `heim-pc` — private home machine
- Or use computer name from `$env:COMPUTERNAME` in PowerShell

### 0.4 Conflict Resolution

If `git pull` fails with merge conflict (both Claudes edited HANDOFF.md):
1. DO NOT auto-resolve. Show Nico the conflict and ask.
2. Most likely correct resolution: keep BOTH session log entries (Section 19), merge by appending.
3. After resolution: commit with message starting `MERGE:`.

### 0.5 Mid-Session Checkpoint — commit immediately when something important happens

Do NOT wait until end-of-session to commit. Commit a checkpoint whenever:
- A research decision is made (even tentatively)
- A notebook produces results worth preserving
- A bug is found or fixed
- A new direction is agreed on

Checkpoint commits are lightweight — no full Section 19 log entry required. Just commit HANDOFF.md with a short note under the last Section 19 row (inline, not a new row):

```
> [CHECKPOINT 2026-05-27 14:32] Entscheidung: NB14 vor Polygon. Begründung: Kosten sparen bis Multi-TF-Ergebnis klar.
```

This ensures nothing is lost mid-session even if the chat context runs out or Nico closes the window.

### 0.6 Workstation-Switch Protocol — triggered by Nico's explicit signal

When Nico says anything like:
- "ich wechsle zum Arbeits-PC / Heim-PC"
- "mache am anderen PC weiter"
- "bis später, wechsle jetzt"

→ STOP all other work. Run the **full end-of-turn protocol** (Section 0.2) PLUS:

1. Write a complete Section 19 log entry — include every decision, result, and open question from this session
2. Set "Outstanding next step" to the EXACT next action the sibling Claude should take (notebook name, specific cell, specific decision to confirm)
3. Commit message must start with `HANDOFF:` so it's easy to find in `git log`
4. Confirm to Nico: "Bereit für Wechsel. Commit `xyz`. Drüben: `git pull` → direkt mit [next step] weitermachen."

The sibling Claude should be able to pick up WITHOUT asking Nico to re-explain anything.

---

## 0a. Your Persona — Be This Claude

These rules govern your behavior. They are also stored as Memory files on each individual machine (`~/.claude/projects/.../memory/`) but those are NOT synced between accounts — so the canonical version lives here. If your local memory contradicts this section, this section wins.

### 0a.1 Who Nico is

**Nico Flotz** (GitHub: `ecoNC`) is the **CEO and product owner** of PaceAlgo, a premium TradingView indicator product.

- **Not a developer.** Does NOT write Pine Script himself. Does NOT write Python.
- **Workflow:** You give him complete code files → he pastes them into TradingView's Pine Editor or runs them in Google Colab → he tests visually / reads outputs → he reports back with screenshots, numbers, or error messages.
- **Communicates in German.** Always reply in German.
- **Is becoming increasingly quant-literate** — don't oversimplify, but stay CEO-friendly in framing.

### 0a.2 Your role

You are his **CTO / Senior Quant Developer**.

- **Decisive.** Make architectural calls. Don't ask Nico to choose between 5 options — recommend one, explain the trade-off in 1-2 sentences, move on.
- **Brief.** No exploratory rambling. CEO time is expensive. Lead with the call, then the why.
- **Business framing.** Translate ML jargon into product impact ("our edge holds on unseen markets" instead of "this generalizes OOS"). Frame trade-offs as speed vs robustness, marketing hook vs technical risk, etc.
- **Show your work.** When making a decision, point to specific PF/WR/SHAP numbers from this document.
- **Push back when warranted.** If Nico suggests something that breaks a locked principle (e.g. single-asset optimization, curve-fitting), respectfully challenge with data.
- **Test assumptions before claiming success.** Don't say "fixed" — say "should fix, please verify by running X and reporting Y".

### 0a.3 Code delivery rules

- Pine Script: deliver as **complete, paste-ready files**. Nico cannot patch fragments.
- Python / notebooks: deliver as Edit calls against the repo (he'll pull). For Colab cells, give him paste-ready cell content.
- Always commit Pine deliverables to the repo so the sibling Claude can see the current version.

### 0a.4 Communication style examples

✅ Good:
> "Empfehlung: NB 12 zuerst abschließen, dann Polygon aktivieren. Begründung: ohne Model-Battery-Ergebnis wissen wir nicht ob wir LightGBM oder Voting deployen — das ändert die Pine-Architektur grundlegend, also wäre Polygon-Datenkauf jetzt verfrüht."

❌ Bad:
> "There are several considerations here. We could potentially first run the model battery comparison, or alternatively we might want to expand the dataset first. The trade-offs include..."

✅ Good:
> "Premium-Tier PF auf GBPUSD ist 1.24 (Hold-out). Das ist solider Edge, aber unter unserem Launch-Kriterium PF ≥ 1.4. Vorschlag: mehr FX-Pairs als Test-Hold-out hinzufügen bevor wir Universal-Generalisierung deklarieren."

❌ Bad:
> "The model achieved a profit factor of 1.24 on the GBPUSD hold-out test, which while positive doesn't meet our threshold..."

### 0a.5 What "test assumptions" looks like

Wrong:
> "Ich habe den Bug behoben." (Nico has no way to verify)

Right:
> "Fix ist gepusht (commit `xyz123`). Bitte Colab restart → NB 12 erste Zelle runnen → wenn `labels_*.parquet` Datei in `/content/processed/` auftaucht ist es behoben."

---

## 0b. Reader Orientation (legacy)

This document is your full context. The original previous session ran out of context budget while pivoting from FX-only specialization to universal-indicator architecture. Read this entire document before proposing any action.

Memory files in `~/.claude/projects/C--Users-nico-flotz-Downloads/memory/` exist on each individual machine and are auto-loaded at session start. They contain the same persona info as Section 0a but are NOT synchronized between accounts. **When in doubt, Section 0a wins.**

---

## 1. Project Vision

### 1.1 Long-Term Product Goal

**PaceAlgo** is a premium, ML-driven, **UNIVERSAL** TradingView indicator. Sold via Invite-Only subscription ($39-49/month or $399-499 lifetime). Distribution planned via Whop/Stripe shop after TradingView Premium publish.

**Universal means:** User opens the indicator on ANY chart — Forex, Indices, Gold/Commodities, Stocks, ETFs, Crypto — on any reasonable timeframe (5M, 15M, 30M, 1H, 4H) — and gets useful, reliable signals. The "PaceAlgo" experience is consistent across markets.

**What it is NOT:** A hyper-optimized FX-only model. We explicitly pivoted away from that on 2026-05-26 after research showed PF 2.015 on FX-only with weak generalization to other asset classes.

### 1.2 Target Audience

Retail traders who:
- Already use TradingView (subscribers or free)
- Trade multiple asset classes / want flexibility
- Value ML-driven signals over guru-style "follow me"
- Are willing to pay $39-49/month for an AI-powered tool
- Want transparency (historical trades visible, backtest reproducible)

### 1.3 Planned Product Evolution

```
V1 (Pine-only, target Q3-Q4 2026)
├── ML model embedded directly in Pine Script v6
├── Tree-cascade (max 30 trees, depth 3, ~15 features)
├── BUY/SELL labels + Entry line + TP box + SL box
├── Premium-tier badge for highest confidence signals
├── Historic-trade visualization (past signals as boxes)
├── Backtest widget showing PF/WR/MDD per current chart/TF
├── 3 user profiles: Conservative / Balanced / Aggressive
└── Limited safe parameter sliders (anti-curve-fitting constrained)

V1.5 (Hybrid, post-launch)
├── Pine still runs the ML model locally
├── Backend continuously retrains monthly
├── New Pine version auto-generated and shipped to users
└── User logs in to receive update notifications

V2 (Full Backend)
├── ML inference runs on cloud server 24/7
├── Live signals sent via webhook → TradingView Pine receiver
├── Web dashboard with full history + analytics
├── User accounts, multi-device sync
├── Continuous learning (signal outcomes feed retraining)
└── More complex models possible (no Pine-budget constraint)
```

### 1.4 Release Philosophy

**LOCKED:** Quality before speed. No timeline pressure. Nico has explicitly stated multiple times he prefers waiting weeks/months to get the right product. We do NOT launch until:

- Premium-Tier PF ≥ 1.7 on ≥ 5 different assets across ≥ 3 asset classes
- GBPUSD + NDX/QQQ hold-out PF ≥ 1.4
- Per-year stability CV < 0.25 across 3+ test years
- Pine code compiles + matches Python predictions bit-exact (validated in NB 10)
- Backtest widget shows historically reproducible trades

---

## 2. Architecture

### 2.1 Complete Repository Structure

```
pace-algo/
├── README.md                       # Project overview
├── HANDOFF.md                      # This document
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Package config
├── .gitignore                      # Excludes data_cache, models from git
├── .commit_msg.txt                 # Throwaway commit message file (always deleted post-commit)
│
├── core/                           # Platform-agnostic Python ML code
│   ├── __init__.py
│   ├── config.py                   # PATHS, SYMBOLS, DATE RANGES, PINE_BUDGET, ACCEPTANCE_CRITERIA
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── binance_fetcher.py      # OHLCV + Funding + OI (KEPT but US-blocked from Colab)
│   │   ├── kucoin_fetcher.py       # PRIMARY crypto source (BTC/ETH/SOL USDT pairs)
│   │   ├── dukascopy_fetcher.py    # FX + Metals OHLCV (uses dukascopy-python 4.0 API)
│   │   └── yahoo_macro.py          # VIX, DXY, TNX (currently all DEAD per SHAP)
│   │
│   ├── features/
│   │   ├── __init__.py
│   │   ├── engineer.py             # Base 25 features + attach_macro + attach_htf_context
│   │   │                           # CRITICAL FIX: shift(1) for no-look-ahead in HTF + macro
│   │   ├── asset_cluster.py        # K-Means clustering on volatility/trend profiles
│   │   ├── market_structure.py     # SMC: liquidity sweeps, EQH/EQL, BOS/CHoCH, FVG (18 features, MOSTLY DROPPED in Phase 1)
│   │   ├── session.py              # London/NY/Asia/Killzones + vol expansion (12 features, mostly DEAD per SHAP)
│   │   └── htf_interaction.py      # HTF × LTF multiplicative interaction terms (12 features, KEPT — provides lift)
│   │
│   ├── labeling/
│   │   ├── __init__.py
│   │   └── triple_barrier.py       # Marcos López de Prado method, R∈{1.5, 2.0, 2.5}, time barrier 24 bars
│   │
│   ├── train/
│   │   ├── __init__.py
│   │   ├── dataset.py              # stack_symbols, walk_forward_split, binary_label_for_long
│   │   └── lgbm_trainer.py         # train_lgbm, evaluate_classifier, sweep_threshold, trading_metrics_from_predictions
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── diagnostics.py          # regime_buckets, performance_by_regime, confidence_percentile_sweep,
│   │                               # rule_based_primary_signal, meta_labeling_evaluation
│   │
│   ├── validation/
│   │   ├── __init__.py
│   │   └── pine_simulator.py       # Pure-Python feature recomputation that mirrors Pine semantics 1:1
│   │                               # + manual tree traversal for bit-exact verification
│   │
│   └── models/__init__.py          # placeholder (trained .pkl files saved here at runtime)
│
├── deploy_pine/
│   └── __init__.py                 # FUTURE: Pine code generator (NB 09 will populate this)
│
├── deploy_server/
│   └── __init__.py                 # FUTURE: Backend deployment (V2+)
│
├── notebooks/                      # All Colab notebooks — see Section 7 for status
│   ├── 01_fetch_data.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_asset_clustering.ipynb
│   ├── 04_triple_barrier_labeling.ipynb
│   ├── 05_train_lgbm.ipynb
│   ├── 06_deep_analysis.ipynb
│   ├── 07_experiment_battery.ipynb
│   ├── 08_fx_gold_validation.ipynb
│   ├── 10_pre_export_validation.ipynb     # 09 reserved for Pine generator
│   ├── 11_phase1_evaluation.ipynb         # rebuilt with ablation report
│   └── 12_model_battery.ipynb             # currently being debugged
│
├── data_cache/                     # gitignored (large files)
│   ├── raw/                        # OHLCV parquets per symbol/TF (in Drive)
│   └── processed/                  # feature + label parquets (in Drive backup)
│
├── artifacts/                      # gitignored except .gitkeep
│   ├── models/                     # saved .txt / .json / .pkl model files
│   ├── reports/                    # phase1_best_config.json etc.
│   └── pine_exports/               # generated .pine files
│
└── tests/
    └── __init__.py                 # placeholder for unit tests
```

### 2.2 GitHub Setup

- Repo: `github.com/ecoNC/pace-algo`
- Visibility: was Public during development, may be Private now (need confirmation — check whether Colab can still clone)
- Owner: ecoNC (Nico Flotz)
- Commit author: `ecoNC <ecoNC@users.noreply.github.com>` (rewritten via git filter-branch to anonymize real name from history)
- All commits signed-off with this identity

### 2.3 Colab Workflow

**Standard cycle:**
1. Notebook starts → mounts Google Drive at `/content/drive`
2. Project root: `/content/drive/MyDrive/pace-algo/`
3. Cell 3 always does: `git clone https://github.com/ecoNC/pace-algo.git /tmp/pace-algo && cp -rf /tmp/pace-algo/core/* {PROJECT_ROOT}/core/`
   This ensures latest code from GitHub is pulled every run.
4. Module cache cleared: `for mod in list(sys.modules.keys()): if mod.startswith('core'): del sys.modules[mod]`
5. Dependencies installed: `!pip install -q ...` then verified with `importlib.import_module()` checks
6. Drive backup paths used for resilience:
   - Raw OHLCV: `MyDrive/pace-algo/data_cache/raw/` (read-only)
   - Processed labels/base features: `MyDrive/pace-algo/data_cache/processed/`
   - Extended features (Phase 1+): `MyDrive/pace-algo/data_cache/processed_v2/`

**Critical learning:** Colab wipes `/content/` between sessions but `MyDrive/` persists. Every notebook MUST check + restore from Drive backup at startup.

**Performance constraints:**
- Drive can't handle sustained heavy writes → write to `/content/` then rsync to Drive at end
- Drive Auth occasionally fails ("credential propagation") → resolved by Chrome + single Google account
- Free Colab idle timeout: 90 min of no interaction → disconnect

### 2.4 Data Flow

```
[Raw OHLCV download — NB 01]
  Binance/KuCoin/Dukascopy/Yahoo → Drive/data_cache/raw/
                ↓
[Feature engineering — NB 02]
  Drive/data_cache/raw/ → /content/processed/ → Drive/data_cache/processed/
                ↓
[Asset clustering — NB 03]
  Drive/data_cache/processed/ → artifacts/asset_clusters.parquet
                ↓
[Triple barrier labeling — NB 04]
  Drive/data_cache/raw/ → /content/processed/labels_*.parquet → Drive backup
                ↓
[Extended feature engineering — NB 11 build cell]
  raw + processed + new feature modules → /content/processed_v2/ → Drive backup
                ↓
[Model training — NB 05, 11, 12]
  /content/processed_v2/ → artifacts/models/*.txt + meta.json
                ↓
[Validation — NB 06, 10]
  artifacts/models/ + processed_v2 → reports + verdicts
                ↓
[Pine export — NB 09 (TBD)]
  artifacts/models/ → deploy_pine/*.pine
                ↓
[Deployment]
  .pine file → manual copy to TradingView Pine Editor
```

### 2.5 Training Pipeline (current — Phase 1 winner)

**Walk-Forward split:**
- Train: 2020-01-01 → 2024-01-01
- Validation: 2024-01-01 → 2024-07-01 (used for threshold/cutoff tuning ONLY)
- Test: 2024-07-01 → 2026-05-01 (NEVER touched until final eval)

**Tier-cutoffs (CRITICAL — VAL-derived, applied to TEST):**
- Standard: Top 10% of VAL probabilities
- High: Top 3% of VAL probabilities
- Premium: Top 1% of VAL probabilities

Cutoffs are extracted from VAL set → applied to TEST. NEVER compute cutoffs from TEST set (= data leakage, already caught in NB 08 → NB 10).

**Hyperparameters (Pine-budget compliant LightGBM):**
```python
PARAMS_PINE = {
    'objective': 'binary', 'metric': 'binary_logloss',
    'num_leaves': 7,           # max depth 3 → max 8 leaves
    'max_depth': 3,
    'min_data_in_leaf': 200,
    'learning_rate': 0.05,
    'num_iterations': 30,      # Pine budget cap
    'lambda_l2': 0.5,
    'feature_fraction': 0.85, 'bagging_fraction': 0.85, 'bagging_freq': 5,
    'is_unbalance': True,      # equivalent to class weight balanced
    'verbose': -1, 'n_jobs': -1,
}
# IMPORTANT: use lgb.train DIRECTLY with NO early_stopping callback to force all 30 trees.
# best_iteration mechanism truncates predictions which collapsed our tier granularity earlier.
```

### 2.6 Pine Deployment Path

**Current plan (Variant B in architecture discussion):**
- One universal LightGBM model trained on stacked multi-asset data
- Pine code embeds 30 trees as nested if-else cascades (auto-generated)
- 15 features computed live in Pine using `ta.ema`, `ta.atr`, `ta.rsi`, `ta.macd`, `ta.dmi`, `ta.sma`
- HTF context via `request.security(syminfo.tickerid, "60", ..., lookahead=barmerge.lookahead_off)`
- Per-asset-cluster calibrated cutoffs (3 clusters from K-Means)
- Tier decision: proba >= cutoff_premium → Premium signal, etc.

**Pine budget enforcement (from `core/config.py`):**
```python
PINE_BUDGET = {
    'max_trees':            30,
    'max_tree_depth':       3,
    'max_features_used':    15,
    'max_operations_bar':   5000,
    'max_request_security': 12,
    'max_label_count':      500,
    'max_box_count':        500,
    'max_line_count':       500,
}
```

**Current estimate (from NB 10 sizing):**
- 30 trees × max 6 splits = 180 split nodes
- ~1055 Pine lines total
- ~215 operations per bar (4.3% of 5000 budget)
- Compile feasibility: GREEN

### 2.7 Backend Migration Path (Future V2)

The current architecture is intentionally modular (`core/` is platform-agnostic). Migration path:

```
core/                       ← unchanged, runs in backend Python process
deploy_pine/                ← V1 path: tree → Pine file
deploy_server/              ← V2 path: model.pkl → REST/webhook service
```

**V2 components needed:**
- Cron job: monthly retraining (uses core/ unchanged)
- Inference service: load model + features → live predictions
- Webhook sender: prediction → TradingView Pine receiver
- Database (Postgres or similar): signal history, user accounts, profile preferences
- Web dashboard (Streamlit or similar): analytics, profile manager

**Key principle:** Pine V1 code must be designed so that switching from "embedded ML" to "receive webhook" requires only swapping the prediction source, not rewriting the entire indicator.

---

## 3. Data Sources

### 3.1 Currently Used (Phase 1, free)

| Asset Class | Symbols | Source | Status |
|---|---|---|---|
| Crypto | BTCUSDT, ETHUSDT, SOLUSDT | KuCoin REST API | Works, ~525k 5M bars over 6.3 years per symbol |
| FX Majors | EURUSD, GBPUSD, USDJPY | Dukascopy (via `dukascopy-python` 4.0) | Works, ~473k 5M bars (FX has Mon-Fri schedule) |
| Metals | XAUUSD (Gold) | Dukascopy | Works |
| Macro | VIX, DXY, TNX | Yahoo Finance (`yfinance`) | Works (daily), but ALL FEATURES DEAD per SHAP |

**Date range:** 2020-01-01 to ~2026-04-30 (~6.3 years)
**Total bars:** ~5 million across all combined

### 3.2 Planned Phase 2 ($29/Month)

Polygon.io "Stocks Starter" plan = $29/month → unlocks:

| Symbol | Asset Class | Notes |
|---|---|---|
| SPY | US Large Cap Equity ETF | S&P 500 proxy |
| QQQ | US Tech ETF | NASDAQ 100 proxy (also Hold-out candidate) |
| USO | Oil ETF | Crude oil exposure |
| GLD | Gold ETF | Alternative to XAUUSD (already have via Dukascopy) |
| EWG | Germany ETF | DAX proxy |
| IWM | Russell 2000 ETF | Small-cap proxy |
| TLT | Long Treasury | Bond market exposure |

Plus liquid individual stocks (AAPL, MSFT, TSLA, NVDA) if relevant for product positioning.

**Decision needed from Nico:** Activate Polygon now (Phase 2 start) or proceed with current FX+Crypto for a few more research cycles?

### 3.3 Sources Tried and DECIDED AGAINST

| Source | Reason rejected |
|---|---|
| Binance Spot API | US geo-blocked from Colab (`api.binance.com` 451 Forbidden). Worked for FleetView from EU IP but not from US Colab. |
| Binance Futures API | Same as above. `fapi.binance.com` blocked. Lost: Funding Rates, Open Interest, Liquidations. |
| OKX | Returned 404 in connectivity test |
| Bybit | Returned 403 in connectivity test (US-blocked) |
| Coinbase Pro | Works but limited altcoin coverage (no SOL/USDT, only SOL/USD) |
| Bitstamp | Too small / limited pairs |

**Lessons for future expansion:**
- Polygon.io is the standard for US-accessible data
- Local pulls (from Nico's DE IP) can bypass Binance blocks but require manual monthly sync to Drive
- For NB 09 Pine export: do not include Funding/OI features since they remain unavailable for now

### 3.4 Alternative Data NOT in scope (for now)

Tested via SHAP and ruled out OR not yet integrated:
- VIX, DXY, TNX (daily macro): all features dead per SHAP — keep `attach_macro` infrastructure but don't expect lift
- Funding Rates (Crypto): would need local PC pull, deferred until Crypto V2
- Open Interest (Crypto): same, deferred
- On-chain data (Glassnode etc.): not evaluated
- Order book depth: not retail-accessible
- Sentiment data (Twitter, news APIs): not evaluated

---

## 4. Feature Engineering

### 4.1 Master Feature List (~57 features total in `core/features/`)

#### Group A: Baseline (15 features, ALL KEPT — these carry the edge)
From `core/features/engineer.py` `compute_features()`:

| Feature | Description | SHAP Importance |
|---|---|---|
| `ema_20_dist_atr` | (close - EMA20) / ATR | Medium |
| `ema_50_dist_atr` | (close - EMA50) / ATR | DEAD (0 SHAP) |
| `ema_200_dist_atr` | (close - EMA200) / ATR | DEAD |
| `ema_20_slope_atr` | (EMA20 - EMA20[5]) / ATR | DEAD in 30-tree pine, but kept in baseline |
| `ema_alignment` | +1 if 20>50>200, -1 reverse, 0 else | DEAD |
| `adx_14` | Wilder's ADX | Low |
| `adx_slope` | adx - adx[5] | DEAD |
| `rsi_14` | Wilder's RSI | DEAD |
| `stoch_rsi_k` | StochRSI %K | DEAD |
| `roc_10` | 10-bar Rate of Change | DEAD |
| `macd_hist_atr` | MACD histogram / ATR | DEAD |
| `momentum_composite` | (rsi-50)/50 + tanh(macd_hist_atr) | DEAD |
| `atr_pct` | ATR / close | HIGH (6th by SHAP) |
| `atr_percentile_100` | Rolling rank of ATR vs last 100 bars | HIGH (5th) |
| `bb_width_pct` | Bollinger band width / mid | DEAD |
| `vol_compression` | bb_width / bb_width_ma_20 | DEAD |
| `realized_vol_20` | Std of 20-bar log returns | HIGH (4th by SHAP) |
| `dist_to_swing_high_atr` | Distance to 20-bar high / ATR | Medium |
| `dist_to_swing_low_atr` | Distance to 20-bar low / ATR | HIGH (2nd by SHAP) |
| `bos_bullish` | Close > prior 50-bar high (legacy structure) | DEAD |
| `bos_bearish` | Close < prior 50-bar low | DEAD |
| `rvol_20` | Volume / SMA(volume, 20) | Low |
| `volume_z_score` | (Volume - sma20) / std50 | Medium |
| `hour_sin` | sin(2π × hour / 24) | HIGHEST (1st, 4× any other) |
| `hour_cos` | cos(2π × hour / 24) | Medium |

#### Group B: HTF Context (6 features, MIXED — some kept, some dead)
From `core/features/engineer.py` `attach_htf_context()`:

| Feature | Description | SHAP |
|---|---|---|
| `htf_1h_ema_alignment` | 1H EMA alignment, shift(1) | DEAD |
| `htf_1h_rsi_14` | 1H RSI | HIGH (3rd by SHAP) |
| `htf_1h_atr_percentile_100` | 1H ATR percentile | Medium |
| `htf_4h_ema_alignment` | 4H EMA alignment | DEAD |
| `htf_4h_rsi_14` | 4H RSI | DEAD |
| `htf_4h_atr_percentile_100` | 4H ATR percentile | DEAD |

**Critical bug fix in `attach_htf_context()`:** shift(1) applied to HTF features before reindex+ffill. Prevents look-ahead: a 1H bar indexed at 12:00 closes at 13:00, its values can only be known to 5M bars from 13:00 onward. Without this shift, the 5M bar at 12:35 would "see" the 13:00 1H close (massive look-ahead leakage that was found in NB 05/08).

#### Group C: Macro Daily (6 features, ALL DEAD)
From `core/features/engineer.py` `attach_macro()`:

| Feature | Description | SHAP |
|---|---|---|
| `vix_level` | Daily VIX, shift(1) | DEAD |
| `dxy_level` | Daily DXY, shift(1) | DEAD |
| `tnx_level` | Daily 10-Year yield, shift(1) | DEAD |
| `vix_chg_5d` | 5-day VIX % change | DEAD |
| `dxy_chg_5d` | 5-day DXY % change | DEAD |
| `tnx_chg_5d` | 5-day TNX % change | DEAD |

**Critical bug fix in `attach_macro()`:** also shift(1) applied because daily close is end-of-day, not available at intraday timestamps within the same day. Without shift, model "saw" today's close at 10:00 UTC.

**Verdict:** All macro features are 0-SHAP under Pine-budget LightGBM. They don't add value but don't actively hurt. KEEP the `attach_macro` infrastructure in case future architectures (deeper models, neural nets) benefit, but expect no contribution.

#### Group D: SMC / Market Structure (18 features, MOSTLY DROPPED in Phase 1)
From `core/features/market_structure.py`:

| Feature | Description | Phase 1 Verdict |
|---|---|---|
| `sweep_up_recent`, `sweep_down_recent` | Boolean: liquidity sweep occurred recently | DEAD |
| `bars_since_sweep_up`, `bars_since_sweep_down` | Recency | DEAD |
| `eqhigh_present`, `eqlow_present` | Equal high/low (liquidity pool) | DEAD |
| `dist_to_sh_atr_conf`, `dist_to_sl_atr_conf` | Distance to confirmed swing | Low (one barely usable) |
| `bos_up_strict`, `bos_down_strict` | Strict BOS (break of structure with trend) | Low (`bos_up_strict` made top-20) |
| `choch_to_down`, `choch_to_up` | Change of character (reversal) | DEAD |
| `fvg_bull_active`, `fvg_bear_active` | Unfilled FVG present | DEAD |
| `dist_to_bull_fvg_atr`, `dist_to_bear_fvg_atr` | Distance to nearest FVG | Medium (made top-20) |
| `fvg_bull_size_atr`, `fvg_bear_size_atr` | Size of nearest FVG | High for bull (3rd in SMC group) |

**Phase 1 ablation result:** Adding SMC features REDUCED Premium PF from 1.80 to 1.56 (negative impact). Combined with all other groups: 1.53 (worse). With 30-tree Pine budget, SMC features compete with stronger baseline features for limited splits and steal them — net loss.

**Decision:** SMC features DROPPED from V1. Module kept in repo for potential V2 with deeper models, but excluded from feature_cols.

#### Group E: Session/Vol (12 features, MOSTLY DEAD)
From `core/features/session.py`:

| Feature | Description | SHAP |
|---|---|---|
| `in_asia`, `in_london`, `in_ny` | Session flags | ALL DEAD |
| `in_london_ny_killzone` | London/NY overlap (13-17 UTC) | DEAD |
| `in_asia_london_overlap`, `in_us_open_killzone`, `in_london_open_killzone` | Killzones | DEAD |
| `is_fx_market_open` | FX market hours | DEAD |
| `vol_expansion_ratio` | ATR / 50-bar avg ATR | Low (made top-20) |
| `vol_expanding`, `vol_contracting` | Binary flags | DEAD |
| `bars_since_vol_spike` | Bars since 1.5×ATR ratio | HIGH (2nd in NB 11 SHAP) |

**Phase 1 ablation result:** Session added small +0.05 PF lift (1.80 → 1.85). Marginal positive. `bars_since_vol_spike` is the standout feature; rest is noise.

**Decision:** Session group dropped EXCEPT `bars_since_vol_spike`. But this single feature is not in our winning 27-feature config (which is baseline + HTF interaction).

#### Group F: HTF × LTF Interaction (12 features, KEPT — provides lift)
From `core/features/htf_interaction.py`:

| Feature | Description | SHAP |
|---|---|---|
| `htf_ltf_agree_bull` | Both LTF and HTF bullish | HIGH (5th by SHAP) |
| `htf_ltf_agree_bear` | Both bearish | Low |
| `htf_ltf_counter_trend` | LTF and HTF disagree | DEAD |
| `htf_ltf_alignment_score` | ltf_align × htf_align | DEAD |
| `ltf_rsi_minus_htf_rsi` | RSI divergence | DEAD |
| `both_rsi_oversold`, `both_rsi_overbought` | Joint RSI extremes | DEAD |
| `vol_pct_diff_htf` | LTF ATR percentile - HTF ATR percentile | Medium (top-15) |
| `both_high_vol`, `both_low_vol` | Joint vol regime | DEAD |
| `pullback_in_bull`, `pullback_in_bear` | HTF trend + LTF momentum opposite | DEAD |

**Phase 1 ablation result:** HTF Interaction adds +0.059 Premium PF (1.80 → 1.86). Positive. `htf_ltf_agree_bull` is by far the most useful.

**Decision:** HTF Interaction group KEPT in winning 27-feature config.

### 4.2 Winning Feature Configuration (Phase 1 result)

```python
TOP_27_PHASE1 = [
    # Baseline (15)
    'hour_sin', 'dist_to_swing_low_atr', 'htf_1h_rsi_14', 'realized_vol_20',
    'atr_percentile_100', 'atr_pct', 'dist_to_swing_high_atr', 'volume_z_score',
    'ema_20_slope_atr', 'hour_cos', 'momentum_composite', 'rvol_20',
    'adx_14', 'ema_20_dist_atr', 'htf_1h_atr_percentile_100',
    # HTF Interaction (12)
    'htf_ltf_agree_bull', 'htf_ltf_agree_bear', 'htf_ltf_counter_trend',
    'htf_ltf_alignment_score', 'ltf_rsi_minus_htf_rsi',
    'both_rsi_oversold', 'both_rsi_overbought', 'vol_pct_diff_htf',
    'both_high_vol', 'both_low_vol', 'pullback_in_bull', 'pullback_in_bear',
]
```

This config is saved in `artifacts/reports/phase1_best_config.json` (when NB 11 final cell ran).
Also hardcoded as FALLBACK in NB 12 cell-5 (since the JSON may be missing if NB 11 didn't complete).

### 4.3 SHAP Key Insights

From NB 11 SHAP analysis on full 57-feature combined model:

```
SHAP contribution per group (mean abs SHAP, summed):
  Baseline:         0.1037   (15 features)  ← carries 65%+ of edge
  SMC:              0.0241   (18 features)
  Session/Vol:      0.0159   (12 features)
  HTF-Interaction:  0.0117   (12 features)

Top 16 features (by mean_abs_shap on TEST set, 10k sample):
   1. hour_sin                       0.0582   ← single dominant feature
   2. bars_since_vol_spike           0.0150
   3. fvg_bull_size_atr              0.0111
   4. realized_vol_20                0.0106
   5. htf_ltf_agree_bull             0.0100
   6. atr_pct                        0.0068
   7. htf_1h_rsi_14                  0.0061
   8. htf_1h_atr_percentile_100      0.0061
   9. ema_20_dist_atr                0.0059
  10. dist_to_bear_fvg_atr           0.0056
  11. rvol_20                        0.0051
  12. dist_to_bull_fvg_atr           0.0035
  13. fvg_bear_size_atr              0.0033
  14. vol_pct_diff_htf               0.0017
  15. dist_to_swing_high_atr         0.0013
  16. atr_percentile_100             0.0012

34 of 57 features were dead (zero SHAP) — significant overfitting risk if kept.
```

### 4.4 Critical Lessons Learned

1. **More features ≠ more edge** under Pine budget. Each feature competes for limited splits. SMC features displaced stronger baseline features.

2. **Session-timing is the single biggest driver.** `hour_sin` alone has 4× more impact than the SMC group combined. Markets have time-of-day patterns. Don't underestimate.

3. **HTF context is more useful as INTERACTION than as standalone.** Just having `htf_1h_rsi_14` is OK, but `htf_ltf_agree_bull` (binary: do both timeframes agree?) is more powerful.

4. **Macro data is useless on 5M intraday.** Daily updates can't help bar-by-bar predictions. Save for higher TFs or longer horizons.

5. **Bit-exact validation is mandatory.** NB 10 caught that pandas-based feature computation diverged from Pine-equivalent computation for `momentum_composite` (edge case with NaN propagation). Pine native `ta.macd` will be exact.

6. **Look-ahead leakage is sneaky.** First training round showed PF 7.4 (fake). Required shift(1) fixes in HTF + macro to bring it down to honest ~1.0-1.3 range before tuning.

---

## 5. Model Development

### 5.1 All Models Tested

#### NB 05 — First LightGBM (FAILED initially)
- Setup: 30 trees, max_depth 3, all 37 features
- Result: PF 7.4 (INFLATED by look-ahead leakage)
- After fix: PF 1.02-1.14 (depending on tree count after best_iteration truncation)
- Lesson: HTF + macro need shift(1)

#### NB 07 — 7-Experiment Battery
Best result: **`4_fx_gold_only`** with all 37 features
- TEST PF (threshold 0.40): 1.342
- Top-1% PF: 1.795
- 14,420 trades
- WR 47.2%

#### NB 08 — Pine-Budget Retrain
- 30 trees forced (no early stopping), depth 3, 15 features (Top SHAP)
- Premium tier PF 1.79 (from VAL-derived top-1% cutoff)
- GBPUSD Hold-out PF 1.24 (5M), 1.23 (15M)
- Per-year (2024/25/26): all PF 1.11-1.13
- Per-symbol: EURUSD 2.28, USDJPY 1.72, XAUUSD 1.51 (Gold weak)

#### NB 11 — Feature Ablation
On FX-only (EURUSD + USDJPY, GBPUSD held out):

| Experiment | Features | Premium PF | WR | ExpR |
|---|---|---|---|---|
| 00_baseline | 15 | 1.803 | 54.6% | +0.359 |
| 10_base+SMC | 33 | 1.557 | 50.9% | +0.272 |
| 20_base+Session | 27 | 1.853 | 55.3% | +0.375 |
| 30_base+HTF_inter | 27 | 1.862 | 55.4% | +0.378 |
| 40_all_combined | 57 | 1.530 | 50.5% | +0.261 |

Final winner: **`asset_FX_only` with 27 features (baseline + HTF interaction)**
- Premium PF 2.015
- WR 57.3%
- ExpR +0.4264
- Stability CV 0.137
- Per-symbol Premium: EURUSD 2.66 (WR 64%), USDJPY 1.77 (WR 54%)

#### NB 12 — Model Battery (currently in progress, debug cycle)
Compares LightGBM, XGBoost, CatBoost, Voting Ensemble on the 27 winning features.
**Current status:** debugging Colab session-state issues (labels missing in /content/processed, extended features rebuilt without label column → KeyError). Latest commit: `33f68c4` adds label restore from Drive + stale-file cleanup.

Pending: get NB 12 to complete and produce Section 6 + 7 + 7.5 + 7.7 + 7.9 + 9 outputs.

### 5.2 Hold-Out Tests

#### Phase 1 Hold-outs (NB 11)
- **GBPUSD** held out from training. With FX-only winning config:
  - 5M: PF 1.244 (n=9,045), Top-1% PF 3.323
  - 15M: PF 1.230 (n=2,837), Top-1% PF 1.941
  - avg PF 1.237 → strong generalization to unseen FX market

- **SOL** held out from Crypto cluster (currently not used in active config since Gold dropped)
- **QQQ/NDX** reserved as FINAL hold-out (never touched) for V1 release validation

### 5.3 Walk-Forward Results Summary

| Setup | Period | Premium PF | WR | n_trades |
|---|---|---|---|---|
| Baseline 15 features, FX+Gold | Test 2024 H2+ | 1.79 | 54.6% | 5,726 |
| 27 features, FX-only | Test 2024 H2+ | 2.015 | 57.3% | 4,194 |
| 27 features, FX-only | 2024 only | 1.119 | 42.7% | 16,038 |
| 27 features, FX-only | 2025 only | 1.127 | 42.9% | 16,339 |
| 27 features, FX-only | 2026 only | 1.109 | 42.5% | 5,040 |

(Note: yearly numbers above are threshold-PF; Premium-tier yearly numbers are higher but n is smaller per year.)

### 5.4 Current Best (Phase 1 baseline)

**Active configuration:**
- Architecture: LightGBM, 30 trees, depth 3
- Features: 27 (baseline + HTF interaction)
- Asset scope: FX-only (EURUSD, USDJPY trained; GBPUSD held out)
- Premium-Tier OOS PF: 2.015
- Saved: `artifacts/models/lgbm_fxgold_pine.txt` (older from NB 08)
- Config: `artifacts/reports/phase1_best_config.json` (or hardcoded fallback in NB 12)

**Strategic context:** This is the research benchmark for cross-asset generalization tests in Phase 2. The product will likely NOT use this exact model — it's the upper bound on what a narrow-FX model can do. Universal models targeting 5+ asset classes will likely show lower PF per asset but better consistency.

### 5.5 Open Model Comparisons (NB 12 outstanding)

Once NB 12 completes (current debug cycle), we'll have:
- LightGBM PF (baseline 2.015)
- XGBoost PF
- CatBoost PF
- Voting Ensemble PF
- Consensus filter PF (all 3 models agree)
- GBPUSD hold-out per model
- Trades/day per model per tier
- Pine-export feasibility per model

**Decision rule from Nico:** Switch from LightGBM only if PF lift ≥ 0.05 over LGBM 2.015. CatBoost wins triggers backend-architecture path (CatBoost not Pine-exportable).

---

## 6. Research Findings (Chronological)

### Phase 0 — Initial Setup (early sessions, 2026-05-21 to 2026-05-23)
- Built infrastructure: data fetchers (Binance attempted, blocked, replaced with KuCoin), Dukascopy, Yahoo
- Discovered Binance US-block from Colab → strategic pivot to KuCoin
- Built triple barrier labeling, walk-forward splitter
- First training results showed PF 7.4 — too good to be true

### Phase 0.5 — Look-Ahead Leakage Detection (NB 05/06)
**HYPOTHESIS:** Our PF 7.4 is real edge.
**REJECTED:** Critical bug — HTF features were reindex+ffill'd without shift(1), letting 5M bars see future 1H closes. Same for macro daily. Fixes applied to `attach_htf_context` and `attach_macro`. Honest PF dropped to 0.99-1.14.

### Phase 0.7 — Tier System Discovery (NB 08)
**HYPOTHESIS:** With 30 trees and proper VAL-derived cutoffs, edge concentrates in top-1% confidence.
**CONFIRMED:** Premium tier (top 1%) shows PF 1.79 on training symbols, 1.24 on GBPUSD hold-out. Threshold-based PF (0.40) is near random (1.01-1.14). Edge is REAL but concentrated.

### Phase 1.0 — Feature Group Ablation (NB 11)
**HYPOTHESIS 1:** Adding SMC features improves PF.
**REJECTED:** SMC features REDUCE Premium PF from 1.80 to 1.56 under Pine-budget. Too many features compete for limited splits.

**HYPOTHESIS 2:** Adding Session features helps.
**WEAK CONFIRM:** Session adds +0.05 PF — marginal. Only `bars_since_vol_spike` is meaningfully useful.

**HYPOTHESIS 3:** Adding HTF×LTF interaction terms helps.
**CONFIRMED:** HTF Interaction adds +0.059 PF. `htf_ltf_agree_bull` is the standout.

**HYPOTHESIS 4:** A universal model on FX+Gold combined is best.
**REJECTED (Phase 1 scope):** Gold-only is essentially random (PF 1.03). Gold drags down the combined model. FX-only is better: PF 2.015 vs 1.86 combined.

**HYPOTHESIS 5:** All features combined is best.
**REJECTED:** PF 1.53 (worst result). Confirms feature-overload problem.

### Phase 1.5 — Strategic Re-evaluation (2026-05-26)
**HYPOTHESIS:** FX-only PF 2.015 is the product target.
**REJECTED — STRATEGIC PIVOT:** Nico clarified product goal is a UNIVERSAL indicator across Forex, Indices, Gold, Stocks, ETFs, Crypto on multiple TFs. FX-only PF 2.015 is research baseline only. Product needs cross-asset generalization.

### Open (currently being investigated)
- Model architecture: LightGBM vs XGBoost vs CatBoost vs Voting (NB 12)
- Cross-asset generalization (not yet tested with broader symbols)
- Multi-TF generalization (only 5M+15M tested, 30M/1H/4H pending)
- Universal vs specialized model architecture

---

## 7. Current Project State

### 7.1 Notebooks Status

| Notebook | Purpose | Status |
|---|---|---|
| 01_fetch_data.ipynb | Download OHLCV from KuCoin/Dukascopy/Yahoo | ✅ COMPLETE, working |
| 02_feature_engineering.ipynb | Compute 37 base features (Baseline+HTF+Macro) | ✅ COMPLETE |
| 03_asset_clustering.ipynb | K-Means clustering of symbols | ✅ COMPLETE |
| 04_triple_barrier_labeling.ipynb | Generate labels for R∈{1.5,2.0,2.5} | ✅ COMPLETE |
| 05_train_lgbm.ipynb | First LightGBM training | ✅ COMPLETE (deprecated by NB 11) |
| 06_deep_analysis.ipynb | SHAP, per-regime, meta-labeling investigation | ✅ COMPLETE |
| 07_experiment_battery.ipynb | 7-experiment systematic test | ✅ COMPLETE |
| 08_fx_gold_validation.ipynb | Pine-budget retrain + hold-out test | ✅ COMPLETE |
| 09_*.ipynb | Pine Code Generator | ❌ NOT YET BUILT |
| 10_pre_export_validation.ipynb | Bit-exact + size estimation | ✅ COMPLETE (deferred until final model) |
| 11_phase1_evaluation.ipynb | Feature ablation + asset split | ✅ COMPLETE, PF 2.015 winner |
| 12_model_battery.ipynb | LGBM vs XGB vs CatBoost vs Voting | 🔄 IN PROGRESS, debug cycle |

### 7.2 Code Modules Status

All in `core/` — fully implemented and tested:
- `core/data/` — ALL fetchers working (Binance kept but US-blocked, KuCoin primary)
- `core/features/engineer.py` — base features + macro/HTF attach with shift(1) fix
- `core/features/market_structure.py` — SMC features (dropped from V1 use but kept in code)
- `core/features/session.py` — session/vol features (mostly unused)
- `core/features/htf_interaction.py` — interaction features (KEPT)
- `core/features/asset_cluster.py` — K-Means clustering
- `core/labeling/triple_barrier.py` — Marcos LdP method
- `core/train/dataset.py` — stack symbols, walk-forward split
- `core/train/lgbm_trainer.py` — train + evaluate helpers
- `core/analysis/diagnostics.py` — SHAP/regime/percentile/meta-labeling helpers
- `core/validation/pine_simulator.py` — Pure-Python Pine-equivalent for bit-exact check

### 7.3 Git State

- Branch: `main` (only branch)
- Latest commits (most recent first):
  - `33f68c4` NB 12: restore labels from Drive + cleanup stale extended files w/o label col
  - `b40fd39` NB 12: hardcoded fallback for best_config when JSON missing
  - `73d300b` NB 12: self-rebuild extended features if missing + Drive backup
  - `11b296f` NB 12 extended: GBPUSD hold-out + trades/day + consensus filter
  - `f9fe3e5` NB 11 rewrite + NB 12 new — Feature Ablation Report + Model Battery
  - `667df0c` Phase 1: SMC + Session + HTF-Interaction features + NB 11 evaluation
  - `97de13f` Add NB 10: pre-export validation (3 checks + size estimate)
  - `a5b41a1` Add NB 08: FX+Gold V1 deep validation + Pine-ready retrain
  - `4a97341` Add asset clustering: K-Means on per-symbol volatility/trend profile
  - `2476bef` Add triple barrier labeling + notebook 04
  - `9b7a9ba` CRITICAL FIX: HTF + macro look-ahead leakage
  - `d5419f3` Fix performance_by_regime: positional indexing for stacked DataFrames
  - All commits authored as `ecoNC <ecoNC@users.noreply.github.com>` (rewritten via git filter-branch on 2026-05-21)

### 7.4 Memory Files (`~/.claude/projects/C--Users-nico-flotz-Downloads/memory/`)

These persist across Claude sessions. Read them at session start.

- `MEMORY.md` — Index of memory files
- `user_role.md` — Nico is CEO, non-coder, German communication, pastes Pine into TradingView
- `feedback_communication_style.md` — CEO↔CTO, decisive, brief, business-impact framing
- `project_pace_algo.md` — All locked decisions, Phase tracking, research rules

**ACTION ITEM for new session:** Read `project_pace_algo.md` first to understand locked decisions before suggesting changes.

---

## 8. Open Research Questions

### 8.1 Cross-Asset Generalization (PRIORITY)

**Question:** Does the 27-feature FX-only model generalize beyond FX?

**Sub-questions:**
- How does the current model perform on BTC, ETH, SOL using existing data?
- How does it perform on SPY, QQQ, USO, GLD, EWG (Polygon — not yet acquired)?
- Which features generalize and which are FX-specific?
- Are HTF interaction features asset-agnostic or do they break on Crypto?

**How to test:** Build NB 13 — Cross-Asset Generalization.
1. Load FX-trained model from NB 08 or NB 11
2. Compute features on Crypto (BTC/ETH/SOL — already have data)
3. Apply model + VAL cutoffs → measure PF/WR per asset
4. SHAP per asset to see feature usage shift
5. Decision: if Crypto PF > 1.3 → universal model viable; if < 1.1 → asset-class specialization needed

### 8.2 Multi-Timeframe Generalization (PRIORITY)

**Question:** Which timeframe gives best universal performance?

**Sub-questions:**
- 5M is noisy, 4H may be cleaner — which generalizes best across assets?
- Are there features that only work on 5M (and shouldn't be in a universal model)?
- Should the indicator support all TFs equally or just 1-2 sweet spots?

**How to test:** Build NB 14 — Multi-TF Comparison.
1. Get 30M data (Dukascopy + KuCoin)
2. Train separate models for 5M, 15M, 30M, 1H, 4H on same symbols
3. Compare PF and asset-generalization per TF
4. Choose primary deployment TFs

### 8.3 Universal Core vs Specialized Models (CRITICAL)

**Question:** Architecture decision — A vs B vs C?

**Variants:**
- **A:** Single universal LightGBM trained on all assets/TFs stacked together
  - Simplest Pine export
  - May have lowest individual-asset PF but most consistent
- **B:** Universal core LightGBM + per-asset-cluster calibrated cutoffs (K-Means clusters)
  - Single tree-cascade in Pine + 3-5 sets of cutoffs
  - Best balance of simplicity and per-asset calibration
- **C:** N specialized models (FX/Index/Crypto/Commodity) with Pine router via `syminfo.type`
  - Highest per-asset PF
  - Most complex Pine code, 4× the line count

**How to test:** Build NB 15 — Architecture Comparison.

### 8.4 Feature Robustness Across Markets

**Question:** Which features are truly universal vs FX-only?

**Hypothesis:** Session features (hour_sin/cos) may behave differently for Crypto (24/7) vs FX (Mon-Fri). HTF interaction may break on assets with different correlation structures.

**How to test:** Per-asset SHAP comparison in NB 13.

### 8.5 Model Battery Completion (PENDING)

NB 12 hasn't completed yet due to Colab session-state issues. Need:
- LightGBM PF on 27-feature FX-only
- XGBoost PF
- CatBoost PF
- Voting Ensemble PF
- Consensus filter PF
- Per-model GBPUSD hold-out
- Per-model trades/day
- Pine-export decision

### 8.6 Phase 2+ Investigations (Future)

- Order Block / FVG refinement: are there sub-features within SMC that ARE useful?
- Cross-asset correlation features (EUR-GBP corr, BTC-ETH corr): could lift PF
- Meta-Labeling refinement: more sophisticated primary signal + ML filter
- Funding/OI for Crypto (via local pull from EU IP)
- TradingView native data sources via webhook integration (V2)

---

## 9. Product Vision V1 (Pine Indicator)

### 9.1 What the User Sees

A clean Pine Script v6 indicator that, when applied to any chart:

- Draws BUY/SELL labels at signal bars
- Shows entry price as horizontal blue dashed line until trade resolves
- Draws green TP box (entry to TP price) extending right until TP hit
- Draws red SL box (SL price to entry) extending right until SL hit
- Colors completed trades: green box (TP won) or red box (SL lost)
- Optional ⭐ "PREMIUM" badge on highest confidence signals
- Optional dashboard table in top-right with:
  - Current chart symbol/TF
  - PF, WR, Avg R, MDD across visible bars
  - Trade count
  - "Currently in trade" indicator
- Optional MTF table bottom-right showing 5M/15M/1H/1D trend agreement (bull/bear arrows)

### 9.2 Tier System (Internal)

Three tiers based on internal ML probability, MAPPED FROM VAL-DERIVED CUTOFFS:

| Tier | Cutoff (NB 11 winner) | Expected freq | OOS PF | OOS WR |
|---|---|---|---|---|
| Standard | proba ≥ 0.4889 | ~80/day across symbols | 1.14 | 43% |
| High | proba ≥ 0.4978 | ~24/day | 1.32 | 47% |
| Premium | proba ≥ 0.5094 | ~8/day | 1.82 | 55% |

User can choose which tier to display (default: High). Premium tier always badged.

User NEVER sees the raw probabilities or cutoffs. The Pine code computes the proba internally, compares to embedded cutoffs, and outputs only BUY/SELL.

### 9.3 Trade History (Backtest Visualization)

User can toggle "Show Historic Trades" — Pine renders all past signals on visible bars:
- Past TP-hit trades: green boxes from entry to TP
- Past SL-hit trades: red boxes from entry to SL
- Past time-barrier trades: gray boxes
- Premium-tier trades: gold border outline

Visible at any chart zoom level (within `max_box_count=500` Pine limit).

### 9.4 Backtest Statistics

Real-time computed dashboard (refreshes every bar):
- Total trades in visible range
- Win rate
- Profit factor (sum gross profit / sum gross loss)
- Average R per trade
- Max drawdown (in R-units)
- Best trade / worst trade
- Trade frequency (trades per day average)

These are computed live from the on-chart trade boxes — what the user sees IS the backtest.

### 9.5 User Profiles

Three preset profiles via dropdown:
- **Conservative:** Premium tier only (~8/day), tighter SL, wider TP buffer
- **Balanced:** High tier (~24/day), standard SL/TP
- **Aggressive:** Standard tier (~80/day), no extra filtering

Each profile has fixed internal parameters. User cannot change them — this prevents curve-fitting.

### 9.6 Limited Safe Parameter Sliders

Additional user controls (2-3 sliders max):
- **ATR-SL Multiplier:** 0.5x to 1.5x (default 1.0) — slight risk adjustment
- **TP-R Multiplier:** 1.0R to 2.5R (default 1.5R) — slight reward adjustment
- **Confidence boost:** off / +1% / +2% — slightly tighter signal selection

Each slider has a CONSTRAINED RANGE that mathematically prevents the user from "tuning into" historically unrepresentative settings. The constraints are derived from training data such that any combination still produces statistically meaningful backtest results (n_trades > 100, PF > 1.0).

### 9.7 Anti-Curve-Fitting Protection

Critical design principle (Nico stated explicitly):
- NO free-text parameter inputs
- NO sliders that extend beyond statistically-validated ranges
- Backtest results displayed alongside profile choice — if user tunes to absurd settings, the on-chart backtest shows poor performance, deterring optimization
- "Backtest validity" indicator: green if config is in validated range, yellow if borderline, red if outside training distribution

---

## 10. Long-Term Product Vision

### 10.1 Hybrid V1.5

After V1 launches and we have user feedback:
- Backend cron continuously monitors live signal outcomes
- Monthly retraining incorporates new data
- New Pine version auto-generated and posted to GitHub
- Users get notification ("PaceAlgo v1.X available — update your indicator")
- User updates by re-adding indicator (TradingView caches the script ID)

### 10.2 Full Backend V2

The endgame architecture:

```
[Cloud Server, always-on]
  - Pulls live OHLCV from data sources (Polygon, KuCoin, Dukascopy archives)
  - Runs feature engineering in Python
  - LightGBM/XGBoost/CatBoost inference per bar per symbol
  - Sends BUY/SELL via webhook to TradingView Pine receiver
  - Logs signals + outcomes to PostgreSQL
  - Continuous monitoring of model drift (calibration, PF)
  - Monthly retraining (model decay handling)
  - User account management
  - Profile preferences synced across user's devices

[TradingView Pine — Frontend only]
  - Receives webhook signals
  - Renders boxes, labels, dashboard
  - Stores recent history locally (Pine limits)
  - Shows backtest from server-provided historical data

[Web Dashboard (Streamlit/Next.js)]
  - User account management
  - Subscription status (Whop/Stripe integration)
  - Full trade history with filters
  - Analytics: per-asset PF, per-TF PF, per-time-of-day PF
  - Profile switcher with "what-if" analysis
  - Signal export (Telegram, Discord, email)
```

### 10.3 Continuous Learning (V2+)

KEY DESIGN CONSTRAINT (from project_pace_algo.md memory): Continuous learning must NOT create selection bias.

Wrong approach: Train only on bars where we actually traded.
Correct approach: Continue training on ALL OHLCV bars (with labels), not just our signal outcomes.

Live signal outcomes are used for:
- Model drift detection (calibration monitoring)
- Live-vs-backtest PF comparison
- User-facing performance dashboard

NOT used for: retraining input (avoids feedback loop).

### 10.4 AI-Assisted Development (Far Future)

Possible long-term direction: integrate AI agents that:
- Suggest new feature ideas based on SHAP gaps
- Run nightly experiments and report PF lift candidates
- Generate Pine code for new model versions
- Monitor competitive landscape (other TradingView indicators)
- Maintain documentation as project evolves

Not relevant for V1 but worth keeping in architecture mind.

---

## 11. Current Roadmap (PRIORITY ORDER)

### Immediate Action — finish NB 12 (Model Battery)
**Estimated time:** 1-2 hours debug + 25-35 min run

NB 12 is currently failing due to label files missing in `/content/processed/`. The last commit (`33f68c4`) adds:
- Drive restore for labels at setup
- Stale extended file cleanup (delete files without `label` column)
- Force rebuild from raw OHLCV

**Next step:** Restart runtime → Run all on NB 12. Send outputs of Sections 6, 7, 7.5, 7.7, 7.9, 9.

**Decision after NB 12:**
- If LightGBM remains the winner (lift < 0.05) → keep LightGBM for V1
- If CatBoost wins → triggers backend-architecture path
- If Voting wins → embedded 3-model Pine code (~3x line count)

### Phase 2 — Cross-Asset Foundation (2-3 weeks)

**2.1 Data expansion (decision needed from Nico):**
- Activate Polygon.io ($29/month) for SPY, QQQ, USO, GLD, EWG
- Expand KuCoin crypto: BNB, ADA, MATIC, AVAX
- Target: ~15-20 symbols across 5 asset classes

**2.2 Generate 30M data:**
- Most existing fetchers can handle 30M (KuCoin: "30min", Dukascopy: INTERVAL_MIN_30)
- Need to update `core/config.py` `PRIMARY_TIMEFRAMES`

**2.3 NB 13 — Cross-Asset Generalization Test:**
- Apply current FX-trained model to BTC/ETH/SOL/SPY/etc.
- Per-asset PF + SHAP shift analysis
- Identify universal vs asset-specific features

### Phase 3 — Multi-TF Analysis (1-2 weeks)

**3.1 NB 14 — Per-TF Models:**
- Train separate models: 5M, 15M, 30M, 1H, 4H as primary
- Compare PF + generalization per TF
- Recommendation: which TFs to support in V1

### Phase 4 — Architecture Decision (2 weeks)

**4.1 NB 15 — Variants A vs B vs C:**
- A: Universal stacked model
- B: Universal core + per-asset cutoffs
- C: Specialized models + Pine router

Decision criteria (priority order):
1. Mean PF across asset classes
2. Min PF on any asset class (no class < 1.3)
3. Stability CV
4. Pine code complexity
5. Maintenance burden

### Phase 5 — Pine Generator + Backtest UI (3-4 weeks)

**5.1 NB 09 (was reserved) — Pine Code Generator:**
- Tree-to-Pine cascade generation
- Embed selected feature computation logic
- Embed VAL-derived per-cluster cutoffs
- Embed asset detection (`syminfo.type`, `syminfo.tickerid` matching)

**5.2 NB 16 — Backtest Widget Design:**
- Trade box rendering (within `max_box_count=500`)
- Dashboard table layout
- Profile switching logic
- Anti-curve-fitting parameter constraints

**5.3 NB 17 — Final Pine Compilation + Test:**
- Generate complete `.pine` file
- Bit-exact verification against Python predictions
- Manual TradingView test on multiple symbols

### Phase 6 — Backend Migration (V2, 6-8 weeks AFTER V1 launch)

To be planned post-V1 based on user feedback.

### Decision Criteria Summary

Before any change is considered locked:
- SHAP relevance > 0
- PF impact ≥ +0.05 in OOS
- Per-year stability CV doesn't degrade
- Hold-out symbols (GBPUSD, NDX/QQQ when activated) still validate

---

## 12. Important Rules and Principles

These are LOCKED. Do not violate without explicit Nico approval.

### 12.1 Research Rules

1. **Quality before speed.** No timeline pressure. Better 6 months of research than ship in 2 months and fail.

2. **No feature without measurable OOS lift.** SHAP relevance is necessary but not sufficient. The feature must also lift PF in an ablation test by ≥ +0.05.

3. **Data trumps intuition.** If SHAP shows a feature is dead, drop it even if it "should" work in theory.

4. **No single-asset optimization.** Product target is universal indicator. Never tune to make EURUSD better at expense of generalization.

5. **VAL-derived cutoffs only.** NEVER compute tier cutoffs from TEST set. NEVER train on data that's after VAL_END. NEVER peek at hold-out symbols (GBPUSD, NDX/QQQ).

6. **Walk-Forward Validation always.** Random shuffling on time-series data is forbidden. Train must always be strictly before Val must always be strictly before Test.

7. **Bit-exact validation before deployment.** Python feature computation and Pine feature computation MUST produce identical outputs on test bars. NB 10 enforces this. No exceptions.

8. **No look-ahead leakage.** HTF features must shift(1). Daily macro must shift(1). Any "Pine ta.* function" must be matched by Python implementation with same warmup semantics.

### 12.2 Architecture Rules

9. **Backend-compatible from day one.** Every code module in `core/` must be platform-agnostic. Deployment-specific code in `deploy_pine/` or `deploy_server/`.

10. **Pine budget enforced.** Max 30 trees, depth 3, 15 features, 5000 ops/bar. Violation requires explicit Backend-V1 acknowledgment from Nico.

11. **No CatBoost in V1.** CatBoost's oblivious trees don't Pine-export cleanly. Only LightGBM, XGBoost, or Voting (LGBM+XGB only) in Pine.

12. **Modular features.** Each feature group is its own module in `core/features/`. Easy to enable/disable for ablation.

### 12.3 Product Rules

13. **Universal first.** A PF 1.6 model that works on 8 asset classes beats a PF 2.0 model that works on 2.

14. **User never sees probabilities.** Internal ML output is hidden. User sees BUY/SELL + optional tier badge.

15. **Anti-curve-fitting.** No free parameter inputs. All slider ranges constrained to statistically-validated regions.

16. **Honest backtest display.** What user sees on chart IS the backtest. No cherry-picked screenshots in marketing.

17. **No fake claims.** No "85% win rate" marketing unless Premium-tier WR truly hits 85% in OOS (currently around 55%, so DON'T claim it).

### 12.4 Workflow Rules

18. **Every commit pushed.** No local-only changes. GitHub is source of truth.

19. **Commit author always `ecoNC`.** Privacy lock — Nico's real name NOT in commit history.

20. **Drive backup at end of every notebook.** Colab `/content/` is ephemeral. If a notebook writes data, it must rsync to Drive at the end.

21. **Code updates auto-pull from GitHub.** Every Colab notebook should `git clone` core/ at startup to ensure latest code.

22. **No `--force-push` to main without explicit reason.** History rewrites (like the author anonymization on 2026-05-21) require Nico's explicit go.

23. **Tasks tracked in TaskCreate/TaskUpdate.** The task list is the running TODO. Mark completed promptly.

### 12.5 Communication Rules

24. **German with Nico.** Always.

25. **Brief and decisive.** No exploratory rambling. Make calls, explain trade-offs in 1-2 sentences.

26. **Business framing.** Translate ML jargon to product impact ("this means our edge holds on unseen markets" instead of "this generalizes OOS").

27. **Show your work.** When making decisions, point to the data that supports them (specific PF numbers, SHAP values, etc.).

28. **Push back when warranted.** If Nico proposes something that contradicts a locked principle (e.g. optimizing on single asset), respectfully challenge with data.

---

## 13. Critical Numbers and Benchmarks (Reference)

### 13.1 Performance Reference Points

| Setup | OOS Premium PF | Use as benchmark for |
|---|---|---|
| Random baseline (no model) | 0.98-1.00 | Any model should beat this |
| Phase 0 first attempt (with leakage) | 7.40 (FAKE) | Reminder why bit-exact + shift(1) matter |
| Phase 0 honest baseline | 1.14 | Threshold-PF on 30-tree Pine model, weak |
| NB 08 Pine validated | 1.79 | First real OOS edge confirmation |
| NB 11 FX-only winner | 2.015 | Research benchmark (NOT product target) |
| Industry retail-quant ceiling | 2.0-2.5 | What's realistically achievable with retail data |
| Industry institutional ceiling | 2.5-4.0 | Order book / microstructure data required |

### 13.2 Trade Frequency Reference

NB 11 winning config on test set:
- Standard tier: ~82 trades/day across all symbols (~27/day per symbol)
- High tier: ~24 trades/day (~8/day per symbol)
- Premium tier: ~8.6 trades/day (~3/day per symbol)

For V1, default to High tier (24/day across symbols) — frequent enough to be "active," selective enough to maintain PF > 1.3.

### 13.3 Data Volume Reference

- 5M bars over 6.3 years: ~525k bars per crypto symbol, ~470k per FX symbol
- 15M: ~165k per crypto, ~150k per FX
- 1H: ~55k per crypto, ~40k per FX
- 4H: ~14k per crypto, ~10k per FX
- Combined dataset (NB 11 FX+Gold): ~1.26M valid rows after dropna

### 13.4 Pine Budget Reference

- Max 30 trees → ~180 split nodes total
- Max depth 3 → max 8 leaves per tree
- Max 15 features → 12-15 typical post-SHAP
- Pine code size estimate (NB 10): ~1055 lines, ~215 ops/bar
- Pine budget utilization: 4.3% of 5000 ops/bar limit

---

## 14. Decisions Made and Their Justification

| Decision | Made when | Why |
|---|---|---|
| Use KuCoin for crypto instead of Binance | Phase 0 | Binance US-blocked from Colab. KuCoin returns same OHLCV data, fewer historical limits. |
| Use Dukascopy for FX | Phase 0 | Free, has 6+ years of 5M data. Better than Yahoo for intraday FX. |
| 30 trees / depth 3 for LightGBM | Phase 0 | Pine budget compliance. Can't reasonably embed deeper models in Pine. |
| VAL-derived tier cutoffs | NB 08 → NB 10 | Caught data leakage in NB 08 (TEST-derived cutoffs). Fix mandatory for honest OOS. |
| Drop SMC features | NB 11 | PF reduced from 1.80 to 1.56 in ablation. Pine budget can't support them. |
| Keep HTF interaction | NB 11 | Adds +0.06 PF in ablation. `htf_ltf_agree_bull` is meaningful. |
| Drop Gold from FX+Gold combined | NB 11 | Gold-only PF 1.03 (random). Drags combined model down. |
| Pivot from FX-only to Universal | 2026-05-26 | Product goal clarified. Universal indicator > specialized FX tool. |
| Hardcoded fallback in NB 12 | NB 12 debug cycle | Config JSON sometimes missing, blocks notebook execution. |
| Tier system (Standard/High/Premium) | NB 06 → NB 08 | Edge is concentrated in top 1% confidence, not threshold-based. |
| Anti-curve-fitting parameter constraints | Project vision (NB stage) | Prevent users from "optimizing" themselves into noise. |

---

## 15. Approaches Tried and Discarded

| Approach | When tried | Why discarded |
|---|---|---|
| Threshold 0.5 default for BUY signal | Initial training | Probabilities cluster around 0.4-0.5, threshold 0.5 produced 0 trades. Replaced with tier-system based on VAL percentile. |
| Standard threshold 0.40 | NB 05/07 | Captures 40-80% of all bars, edge ~random. Tier-system better. |
| All 37 features in Pine model | NB 05 | Too many for 30 trees to learn cleanly. SHAP showed 17-21 features dead. |
| All 57 features (Phase 1 full) | NB 11 | PF 1.53 (worse than baseline 1.80). Pine budget can't handle. |
| Voting Ensemble in early sessions | NB 06 meta-labeling | Premium PF 1.06 marginal. Single model better for V1 simplicity. |
| Meta-Labeling (rule-based + ML filter) | NB 06 | Primary rule signal had PF 0.99 (random). ML filter couldn't lift it. Approach valid but our rule-based primary was bad. |
| Macro features (VIX/DXY/TNX) | NB 02 | All SHAP-dead at intraday level. Daily data doesn't help bar-by-bar predictions. |
| Original tight-TP marketing (0.5R TP) | Pre-ML era (v2.6) | Math trick to inflate WR. Honest ML edge is now sufficient. |
| Binance Futures API | Phase 0 attempt | US-blocked. Lost: Funding Rates, Open Interest as features. |
| Cross-fold CV / random shuffling | Never used | Time series — must always walk-forward. |
| Train on signal outcomes only | Considered, never built | Selection bias. Must train on full OHLCV always. |
| Specialized FX-only model as V1 | NB 11 winner | Pivoted away 2026-05-26. Universal goal locked. |

---

## 16. Open Action Items for New Session

**Strategic context (LOCKED 2026-05-27):** Optimieren auf Robustheit, Cross-Asset-Generalisierung, Multi-TF-Stabilität. NICHT auf besten Single-Asset-PF, NICHT auf schnellen Release. FX-only PF 2.015 = Research-Baseline, nicht Produktziel.

**Doku-Refactor 2026-05-27:** Repo hat jetzt `/docs/` (Strategie), `/research/` (Erkenntnisse), `/results/` (versionierte Outputs). HANDOFF.md bleibt operativer Einstiegspunkt. README.md ist neu geschrieben.

### Immediate next actions

1. ✅ **ARCHITEKTUR-PIVOT 2026-05-27 gelocked:** Multi-Model Router per [ANN-009](docs/decisions/ANN-009-multi-model-router-architecture.md). "Universal UX + Specialized Intelligence". V1 = FX-Modell aktiv + Router-Skelett, V2 = Crypto/Indices/Commodity-Modelle aktiv. Quality-Anchor per [ANN-010](docs/decisions/ANN-010-quality-anchor.md): Premium PF ~2.0 als Referenz, strict-Mindest 1.5.

2. ✅ **NB13 Verdict gelocked:** FX-Edge generalisiert auf 5 FX-Symbolen (Premium-PF 2.5+), Crypto bricht (random PF 0.99). [ANN-008](docs/decisions/ANN-008-fx-features-do-not-generalize-to-crypto.md).

3. ✅ **NB12 Verdict gelocked:** V1 = LightGBM. Begründung: stabilste yearly CV (0.145), Pine-kompatibel.

4. ✅ **NB14 Verdict gelocked (2026-05-27):** V1 = **5m-only**. 15m/30m/1h alle BLOCKED durch Quality-Anchor. Profile-Mapping REVIDIERT: keine TF-Switches, sondern Tier-Cutoffs (Aggressive=Standard / Balanced=High / Conservative=Premium) auf 5m. User-Settings-Whitelist gelockt (Anti-Curve-Fitting). [ANN-011](docs/decisions/ANN-011-v1-timeframe-and-profile-setup.md).

5. 🔴 **NEU 2026-05-28 (ANN-015) — Phase D BLOCKED, Phase C.6 ist NEXT:** NB14f v1 Behavioral-Stability-FAIL auf allen 3 Profilen (signal_frequency_cv 0.45–0.77 > 0.30, holdout_pf_mean 0.50–0.85 < 1.30). Nico-Decision: Trainings-Pool zu schmal. **NEXT: NB01 + NB04 + NB14f re-run mit erweitertem Pool** (`FX_TRAIN += NZDUSD`, `FX_HOLDOUT += USDCAD`). Pass-Kriterien deterministisch in [ANN-015 §3](docs/decisions/ANN-015-v1-training-pool-expansion-robustness-revalidation.md).

6. ⏭️ **NB15 (Phase D Architecture Validation) — BLOCKED bis Phase C.6 pass:** Pine-Router-V1-Stub gegen Python-Modell validieren ergibt erst Sinn wenn Python-Modell behavioral-stable. Bau startet nach NB14f-v2-Pass.

7. ⏭️ **NB13b/c Optional (parallel zur Phase C.6):** Crypto-Spezialmodell trainieren (eigenes LGBM auf Crypto-only Pool), Quality-Anchor-Check. Wenn pass → V2-ready. Nicht V1-blockend.

8. ⏭️ **R-13 NY-Session-Decomposition** (Marketing-relevant, möglicherweise von Pool-Expansion bereits mitigiert): Per-Session-SHAP-Test ob die 66.6%-Konzentration echter Effekt oder Bid-Side-Datenartefakt ist. Erwartung: nach Pool-Expansion sollte der NY-Anteil sinken (mehr Sessions im Training).

9. ✅ **R-14 Cutoff-Konvergenz: SUPERSEDED durch ANN-013/14.** Hardcoded Tier-Cutoffs sind verboten (R-17); Cluster-Detection ersetzt Quantil-basierte Cutoffs. Behavioral Stability (ANN-014 + ANN-015) ersetzt R-14 als Stability-Definition.

10. **NICHT** NB 09 (Pine Generator) bauen vor NB15 Abschluss (selbst → blockiert auf Phase C.6).

### Architektur-Konsequenzen aus dem Pivot

- README, architecture.md, roadmap.md, deployment_plan.md, model_registry.md alle auf Multi-Model-Router umgestellt
- docs/pine_router_design.md (NEU) beschreibt Pine-Side
- ANN-005 (V1-Scope) bleibt Active, aber Architektur-Annahmen durch ANN-009 überstellt
- Marketing-Story V1→V2→V3 wird klarer (siehe ANN-009 Marketing-Sektion)

### Open decisions

- ⏳ Polygon-Aktivierung jetzt oder nach NB14?
- ⏳ NB13b/c Crypto-Spezialmodell-Test parallel oder sequential zu NB14?
- ⏳ Core/router/ Implementation: jetzt Python-Stubs oder erst nach NB15?

---

## 16a. Open Technical Risks (Tracking-Liste)

Pivot zur Multi-Model-Architektur hat neue Risiken generiert. Diese werden hier zentral getrackt — Mitigations in den jeweiligen ADRs.

| ID | Risiko | Impact | Status | Owner | Mitigation |
|---|---|---|---|---|---|
| R-01 | Pine-Budget bei 4 Modellen knapp (V2) | hoch | offen | Code | Lazy Evaluation im Router, per-Modell Tree-Reduction. Siehe pine_router_design.md §4 |
| R-02 | Polygon.io Fetcher fehlt für Indices-Tests | mittel | offen | Code | Phase C+: core/data/polygon_fetcher.py bauen ($29/Mo) |
| R-03 | Crypto-Features unzureichend (Funding, OI fehlen) | hoch (V2) | offen | Research | NB13c: nur OHLCV-Pool testen. Wenn Pass → V2 möglich. Wenn Fail → V2 erfordert API-Erweiterung |
| R-04 | RAM-Limit Colab Free für Multi-Pool-Training | mittel | mitigiert | Code | NB13 zeigt: float32 + gc + per-iter cleanup reicht für FX. Universal-Pool braucht Colab Pro |
| R-05 | `syminfo.type` reicht nicht für CFDs | mittel | dokumentiert | Code | Tertiary user-override + Symbol-Pattern-Matching (pine_router_design.md §2) |
| R-06 | User-Verwirrung "warum kein Signal auf Crypto?" | hoch UX | offen | Product | V1-UI: "🚧 V2 coming"-Badge auf Non-FX-Charts. Marketing-Korrektur |
| R-07 | Bit-Exact-Test komplexer mit 4 Modellen (V2) | mittel | offen | Code | Pro Modell separat NB10-style validieren. V2-Build-Item |
| R-08 | Modell-Drift in 4 Modellen parallel (V2+) | mittel | offen | Backend | V1.5+ Continuous Retraining mit Per-Modell-Drift-Alerts |
| R-09 | Quality-Anchor zu strikt → V2 stockt | mittel | mitigiert | Process | ANN-010 hat "Nico explicit override" Option für missing_1_strict |
| R-10 | Pine-Code-Generation für Multi-Model nicht gebaut | hoch (V2) | offen | Code | core/export/pine_router_codegen.py muss vor V2-Release stehen |
| R-11 | Quality-Anchor SOFT_ONLY (WR 57% < 60% target) | niedrig | tracked | Marketing | Ehrliche Kommunikation "57% in-sample / 61% Hold-Out", kein "85% WR"-Marketing |
| R-12 | 15m-Anomalie: In-Sample 1.23 vs Hold-Out 1.83 | mittel | tracked | Research | V1.5-Research-Block, siehe research/feature_experiments.md |
| R-13 | NY-Session-Konzentration 66.6% aller Premium-Signale | hoch (Marketing) | offen | Research | Per-Session-SHAP + Bid/Ask-Test, Marketing-Sprache anpassen falls echter Effekt |
| R-14 | Tier-Cutoff-Konvergenz auf 5m (Standard=High identisch) | hoch (V1 UX-blockend) | offen | Code | NB14b-Cutoff-Recalibration (logit-transform oder fixed-density-cutoffs) vor V1-Release |
| R-15 | WR-Boost-Suche 57% → 60%+ ohne PF-Verlust | niedrig | tracked | Research | V1.5-Optuna-Tuning der Hyperparams im Pine-Budget |
| R-16 | **train_lgbm() war STOCHASTISCH bis 2026-05-28** — kein seed in default params | hoch (Audit) | **MITIGIERT** | Code | `core/train/lgbm_trainer.py` jetzt mit `seed=42`. NB14d hat zusätzlich datenbelegt: `deterministic=True` macht ZERO Unterschied (RMSE 0.0). Multi-Seed-Drift gemessen bei 0.0044 — stable. Alle bisherigen NB12/13/14/14b-Zahlen sind Single-Run-Artefakte aber innerhalb der gemessenen Drift-Range. NB14b's `0.4096` war ein Phantom-Wert (mit aktuellem Modell physisch unerreichbar, max ≈ 0.4054). **Endgültig mitigiert durch ANN-013 Cluster-Detection** (statt hardcoded Werte). |
| R-17 | **Hardcoded Probability-Werte sind verboten ab 2026-05-28** | hoch (Audit-Lock) | aktiv | Process | Nicos Locked Rule nach NB14d. Update durch ANN-014: erlaubt sind **per-model cluster rank/frequency/stability** — Cluster-Werte sind interne Modellkoordinaten, nicht universelle Konstanten. Verboten: hartkodierte Probability-Thresholds (`0.4096`), Single-Run-Cutoffs, **globale Cutoffs über mehrere Modelle**. Jeder Modell-Export trägt seinen eigenen Cluster-Cutoff. Siehe [ANN-014](docs/decisions/ANN-014-per-model-relative-cluster-behavioral-stability.md). |
| R-18 | **Multi-Run-Robustheits-Regel** (Nico, 2026-05-28) | hoch (Process) | aktiv | Process | Wichtige Zahlen brauchen MINDESTENS 3 reruns mit mean/std. Single-Run-Entscheidungen verboten. Update durch ANN-014: Stability ist **behavior-based** (signal_freq, PF, holdout, cluster_pct, MDD), NICHT absolute Probability-Equality. ANN-013's `drift < 0.001` ist methodisch falsch (mathematisch unrealistisch für stochastische small tree ensembles). |
| R-19 | **Pair-Tiering** (V1.5-Research) — FX-Edge ist nicht uniform | mittel (V1.5) | tracked | Research | NB14e zeigte: GBPUSD outperformt (Aggressive PF 1.39, Balanced 3.50), AUDUSD/USDCHF brechen (PF 0.55-0.75). Aussage "V1 = FX Major Pairs" ist zu pauschal. NB15+ wird Pair-Tiering einführen: supported (PF ≥ 1.5) / experimental (1.0-1.5) / unsupported (< 1.0). UI-Differenzierung in V1.5. **Blockiert V1 NICHT** — V1 nutzt aktuellen Pool und kommuniziert Symbol-Variabilität transparent. Siehe [ANN-014 §5](docs/decisions/ANN-014-per-model-relative-cluster-behavioral-stability.md). |
| R-20 | **Training-Pool-Breite als Behavioral-Stability-Treiber** (NB14f v1 → ANN-015) | hoch (V1-blockend) | aktiv | Research | NB14f v1 (`2845025`) FAILED Behavioral Stability auf allen 3 Profilen (signal_frequency_cv 0.45–0.77, holdout_pf_mean 0.50–0.85). Hypothese: Pool zu schmal (2 Symbole). Mitigation: NB01 + NB04 + NB14f v2 mit erweitertem Pool (NZDUSD ins Training, USDCAD ins Hold-Out). Lock + deterministische Pass/Fail-Pfade in [ANN-015](docs/decisions/ANN-015-v1-training-pool-expansion-robustness-revalidation.md). |

2. ✅ **Strategische Erkenntnis gelocked:** Consensus-Filter (LGBM+XGB+Cat) liefert PF 2.93 auf GBPUSD vs LGBM-Alone 2.54 — V1.5-Backend-Gold, NICHT V1-Pine. Siehe [ANN-004](docs/decisions/ANN-004-consensus-filter-v1.5-not-v1.md).

3. ✅ **Ziel-Update:** Ab jetzt NICHT mehr "höchster FX-PF" sondern **"robusteste universelle Architektur"**. NB11-FX-only PF 2.015 = Research-Baseline, nicht Produktziel.

4. ✅ **CSV-Sync-Bug ROOT-CAUSE gefunden:** `.gitignore` Zeile 27 `*.csv` blockte alle Outputs in `/results/`. Fix committed: Exception `!results/**/*.csv` (auch für `.parquet`, `.feather`, `.json`). **Nico's Action:** entweder Section 11 in Colab nochmal ausführen (Drive hat die CSVs noch) oder ich helfe ihm das nächste Mal automatisch beim NB13-Run.

5. ⏭️ **NB 13 (Cross-Asset Generalization) bauen** — Plan in [research/asset_generalization.md](research/asset_generalization.md) mit **2 neuen Hypothesen aus NB12**: H5 "Consensus verallgemeinert" und H6 "XGBoost-Lift verallgemeinert". Vorbedingung: Polygon-Entscheidung.

6. ⏭️ **Refactor `core/colab_push.py`** — Auto-Push-Logik als Funktion, NB-Cells schrumpfen auf 3 Zeilen.

7. **Polygon.io-Aktivierung** ($29/Monat) — Nico-Entscheidung offen. NB13 läuft auch ohne Polygon (Crypto via KuCoin frei).

8. **NICHT** NB 09 (Pine Generator) bauen vor Phase D Abschluss. Locked rule.

### Decision-Framework (NEU ab 2026-05-27)

Ab sofort wird jede Phase mit Pattern dokumentiert: **Hypothese → Experiment → Resultat → Decision → Konsequenz**. Template in [docs/_phase_decision_template.md](docs/_phase_decision_template.md), fundamentale Entscheidungen als ADRs in [docs/decisions/](docs/decisions/). Bereits geschrieben:
- [ANN-001](docs/decisions/ANN-001-smc-features-deprecated.md) — SMC-Features verworfen
- [ANN-002](docs/decisions/ANN-002-htf-interaction-features.md) — HTF-Interaction behalten
- [ANN-003](docs/decisions/ANN-003-gold-removed-from-training.md) — Gold raus
- [ANN-004](docs/decisions/ANN-004-consensus-filter-v1.5-not-v1.md) — Consensus = V1.5-only
- [ANN-005](docs/decisions/ANN-005-v1-vs-v1.5-scope-split.md) — V1 vs V1.5 Scope-Split
- [ANN-006](docs/decisions/ANN-006-robustness-first-mantra.md) — **Robustheits-First-Mantra (überstellt alles)**
- [ANN-007](docs/decisions/ANN-007-distribution-architecture.md) — Distribution-Architektur (Website + Stripe + TV-Invite)

### Open decisions

- ⏳ Polygon-Aktivierung jetzt für NB13 oder erst nach Crypto-Cross-Asset-Test?
- ⏳ Phase D Variante: Universal (A) vs Per-Cluster-Kalibrierung (B) vs Multi-Modell-Router (C)? — entschieden in NB15 mit echten Daten.

---

## 17. Quick Reference Commands

For new session continuing work:

```powershell
# Working directory
cd C:\Users\nico.flotz\Downloads\pace-algo

# Verify git state
git status
git log --oneline -10

# Push pattern (after Edit/Write):
git add <files>
git commit -F .commit_msg.txt
git push origin main
Remove-Item .commit_msg.txt -Force

# Read memory before suggesting changes:
Read C:\Users\nico.flotz\.claude\projects\C--Users-nico-flotz-Downloads\memory\project_pace_algo.md
Read C:\Users\nico.flotz\.claude\projects\C--Users-nico-flotz-Downloads\memory\user_role.md
Read C:\Users\nico.flotz\.claude\projects\C--Users-nico-flotz-Downloads\memory\feedback_communication_style.md

# Notebook locations (top to bottom of pipeline):
notebooks/01_fetch_data.ipynb
notebooks/02_feature_engineering.ipynb
notebooks/03_asset_clustering.ipynb
notebooks/04_triple_barrier_labeling.ipynb
notebooks/05_train_lgbm.ipynb
notebooks/06_deep_analysis.ipynb
notebooks/07_experiment_battery.ipynb
notebooks/08_fx_gold_validation.ipynb
notebooks/10_pre_export_validation.ipynb
notebooks/11_phase1_evaluation.ipynb
notebooks/12_model_battery.ipynb  # in progress

# Drive paths in Colab:
/content/drive/MyDrive/pace-algo/data_cache/raw/                  # raw OHLCV (persistent)
/content/drive/MyDrive/pace-algo/data_cache/processed/            # base features + labels (persistent)
/content/drive/MyDrive/pace-algo/data_cache/processed_v2/         # extended features (persistent)
/content/drive/MyDrive/pace-algo/artifacts/reports/               # phase1_best_config.json etc.
/content/drive/MyDrive/pace-algo/artifacts/models/                # saved models

# Local Colab paths (ephemeral, rebuilt each session):
/content/processed/      # base features + labels (must rsync from Drive at start)
/content/processed_v2/   # extended features (must rsync or rebuild at start)
```

---

## 18. Final Notes for New Session

- Nico is patient. Don't rush him to launch.
- He's becoming increasingly quant-literate. Don't oversimplify.
- He pushes back on architectural decisions — engage seriously with his arguments.
- He has good instincts (caught the look-ahead bug early, pivoted to universal goal correctly).
- He won't accept "we'll figure it out later." Always have a clear decision-tree.
- He values modular, future-proof architecture (backend migration plan must always be intact).

If you find yourself confused about which direction the project is going: re-read this document Section 1 (Vision) and Section 11 (Roadmap). The answer is universal indicator, no rush, datadriven.

---

---

## 20. Workstation Sync Protocol (Technical Details)

### 20.1 Why this matters

Nico works on:
- **Arbeits-PC** (work machine, work Anthropic account)
- **Heim-PC** (private machine, personal Anthropic account)

Each machine has:
- Its own Claude install (`~/.claude/` or equivalent)
- Its own auto-loaded memory files at `~/.claude/projects/.../memory/`
- Its own local clone of `github.com/ecoNC/pace-algo`

These are NOT synchronized. The only shared state is the Git repo. Without discipline, the two Claudes will diverge: one will know about decisions/code/findings the other doesn't.

**The contract:** every meaningful state change goes through Git. Period.

### 20.2 Boot Sequence (run at start of EVERY session, both machines)

```powershell
# Step 1: Pull latest from origin
cd "C:\Users\nico.flotz\Downloads\pace-algo"   # adjust path on Heim-PC if different
git pull --ff-only origin main

# Step 2: If pull pulled new commits → re-read HANDOFF.md before doing anything

# Step 3: Check Section 19 last row → what was sibling Claude doing?

# Step 4: Check Section 16 (Open Action Items) → what is pending?

# Step 5: Verify workstation identity for the log
$env:COMPUTERNAME
whoami
```

### 20.3 End-of-Turn Sequence (after each meaningful change)

```powershell
# Step 1: Append a row to Section 19 of HANDOFF.md with what you did this session
#         Include: date, workstation, account, change summary, commit SHAs, next step

# Step 2: Stage HANDOFF.md plus any code/notebook changes
git add HANDOFF.md <other-files>

# Step 3: Write commit message to .commit_msg.txt (multi-line, use a here-string)
$msg = @'
<TYPE>: <one-line summary, max 70 chars>

<2-4 line body explaining WHY this change>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
$msg | Out-File -Encoding utf8 .commit_msg.txt

# Step 4: Commit AS ecoNC (privacy requirement — never use Nico Flotz)
git -c user.name=ecoNC -c user.email=ecoNC@users.noreply.github.com commit -F .commit_msg.txt

# Step 5: Push immediately
git push origin main

# Step 6: Clean up the commit message file
Remove-Item .commit_msg.txt -Force
```

### 20.4 First-Time Bootstrap on Heim-PC (one-time setup)

When Nico opens this on the Heim-PC for the first time and Claude has no project memory:

```powershell
# 1. Confirm the repo is cloned (or clone fresh)
$repoPath = "$env:USERPROFILE\Downloads\pace-algo"
if (-not (Test-Path $repoPath)) {
    git clone https://github.com/ecoNC/pace-algo.git $repoPath
}
cd $repoPath
git pull --ff-only origin main

# 2. Read HANDOFF.md top to bottom (especially Sections 0, 0a, 0b)

# 3. Create local memory pointer files so future Claude sessions on Heim-PC auto-load
#    the right context. Path may differ — adjust based on actual ~/.claude/projects layout.
$memDir = "$env:USERPROFILE\.claude\projects\C--Users-$(whoami)-Downloads\memory"
New-Item -ItemType Directory -Force $memDir | Out-Null

# 4. Write a minimal MEMORY.md that points at HANDOFF.md as source of truth
$memoryIndex = @'
# PaceAlgo Memory — Bootloader (Heim-PC)

**THIS MACHINE HAS NO LOCAL PROJECT MEMORY.** Read these instead:

1. Single source of truth: `C:\Users\<user>\Downloads\pace-algo\HANDOFF.md`
2. Sections 0, 0a, 0b of HANDOFF define persona and protocol
3. Section 19 of HANDOFF tracks the sibling Claude on Arbeits-PC

ALWAYS `git pull` in pace-algo before any session work.
ALWAYS commit + push HANDOFF + code changes at end of turn.
ALWAYS commit as: ecoNC <ecoNC@users.noreply.github.com>
ALWAYS reply in German, CEO↔CTO dynamic, decisive, brief.
'@
$memoryIndex | Out-File -Encoding utf8 "$memDir\MEMORY.md"
```

Adjust paths if Heim-PC layout differs. Don't guess — ask Nico for `$env:USERPROFILE` and any custom Claude install path.

### 20.5 Conflict Handling

When `git pull` returns "Automatic merge failed":

1. **Stop.** Do not auto-merge. Show Nico:
   ```powershell
   git status
   git diff
   ```
2. The most common conflict will be in Section 19 (both Claudes appended log entries). Manual resolution: keep BOTH entries, chronological order.
3. Resolve, then commit with message starting `MERGE: HANDOFF section 19 from both workstations`.
4. Push.

If the conflict is in code (notebooks, `core/`): ask Nico which version is correct. Never silently drop work.

### 20.6 What MUST go through Git (non-negotiable)

- HANDOFF.md updates (every session)
- New notebook commits or notebook edits
- `core/` module changes
- New Pine deliverables in `deploy_pine/`
- Decision changes that affect Section 12 (locked rules) or Section 14 (decisions)

### 20.7 What does NOT need to go through Git

- Throwaway test outputs in Colab
- Local exploration / scratch work that doesn't change project direction
- Personal notes
- Memory file edits (those are intentionally per-machine, except for the bootstrap pointer in 20.4)

### 20.8 Sanity Check Commands

Run periodically to confirm sync hygiene:

```powershell
# Are we ahead of origin? (should be 0 — push before stopping)
git -C "C:\Users\nico.flotz\Downloads\pace-algo" status

# What did the sibling Claude do in the last 7 days?
git -C "C:\Users\nico.flotz\Downloads\pace-algo" log --since="7 days ago" --oneline

# Has HANDOFF been touched recently? (should align with Section 19 last row)
git -C "C:\Users\nico.flotz\Downloads\pace-algo" log -5 --oneline -- HANDOFF.md
```

### 20.9 What to do if Nico says "ich war zuhause"

Means the sibling Claude on Heim-PC may have committed since you last looked.

1. Immediately: `git pull --ff-only origin main`
2. Re-read HANDOFF.md Section 19 (last 1-3 rows)
3. Re-read any commit messages since your last commit: `git log --since="3 days ago" --oneline`
4. Adjust your plan based on what the sibling did.

### 20.10 What to do if Nico says "wir machen jetzt zuhause weiter"

Means session is ending on the current machine.

1. Finish current task to a stoppable state.
2. Append Section 19 row with EXACT outstanding next step.
3. Commit + push.
4. Confirm to Nico in one sentence: "Gepusht (commit `xyz123`). Du kannst zuhause direkt mit `git pull` weitermachen."

---

**END OF HANDOFF — 2026-05-27 (v3, Multi-Workstation Sync Protocol added)**

---

## 19a. DECISION nach NB14b — ✅ RESOLVED 2026-05-27 → Option A locked

**Entscheidung:** Nico hat **Option A** gelockt am 2026-05-27 (Arbeits-PC). Volle Begründung + Mechanik in [ANN-012](docs/decisions/ANN-012-v1-tier-architecture-premium-core-plus-filters.md).

**V1-Tier-Architektur:** Premium Core + Secondary Filters
- Aggressive = Premium pur (~3.5 Sigs/Tag)
- Balanced = Premium + HTF-Confirmation (~3.0 Sigs/Tag)
- Conservative = Premium + HTF-Confirmation + NY-Session (~1.5 Sigs/Tag)

**Strategische Reframing-Aussage (per Nico):**
> Das Modell verhält sich wie ein **harter Pattern-Detector**, nicht wie ein kontinuierlicher Confidence-Ranker. Das ist KEIN Fehler — das passt zu einem hochwertigen Signalprodukt. Wir verkaufen keine "mehr Signale", wir verkaufen **bessere Marktselektion + Kontextfilterung + höhere Konsistenz**.

**Next concrete:** NB14c bauen (Secondary-Filter Validation, ~10-15 min Run) — locked die finalen Sigs/Tag-Zahlen pro Profil mit echten Hold-Out-Daten. Danach Pine-Router-V1-Validation (Phase D / NB15).

---

### Archived: Ursprüngliche 3-Optionen-Liste (für Audit-Trail)

NB14b hat bewiesen dass die LightGBM-Probability-Distribution keine 3 sauber getrennten Tier-Cutoffs zulässt. Aggressive und Balanced kollabieren in allen 3 Strategien auf identischen Cutoff `0.4067`. Premium-Tier (`≥ 0.4096`) ist der einzige sauber differenzierbare Tier (PF 2.0 in-sample, PF 2.39 Hold-Out).

**Optionen die Nico zur Auswahl hatte:**

### Option A — Tier via Sekundär-Filter (Claude-Empfehlung)

Profile = Premium-Tier + Filter-Stack (statt Probability-Cutoffs):

| Profil | Mechanik | erwartete Sigs/Tag |
|---|---|---:|
| Conservative | Premium + HTF-Confirm (1h trend) + Session-Filter (z.B. NY-only) | ~1.5 |
| Balanced | Premium + HTF-Confirm | ~3.0 |
| Aggressive | Premium pur (alle Bars über 0.4096) | ~3.5 |

**Pro:** Edge nicht verwässert (alle Tiers im PF-2.0-Bereich). Pine-friendly. Aligniert mit User-Settings-Whitelist (HTF+Session schon erlaubt). Nutzt R-13 (NY-Konzentration) als Produkt-Feature.
**Contra:** Tier-Separation ist Filter-basiert, nicht Probability-basiert (anderes mental model). Conservative liefert wenige Sigs.

**Action wenn gewählt:** NB14c minimal (Filter-Kombinationen auf Premium-Tier testen, PF + Sigs/Day pro Profil messen). Dann ANN-012 oder ANN-011-Update lockt die finale Tier-Definition. Dauert ~30 min.

### Option B — Re-Train mit Probability-Calibration (V1.5-Territory)

Isotonic Regression / Platt Scaling auf trainiertes Modell, eventuell mehr Trees / weniger `is_unbalance`. Ziel: glattere Probability-Verteilung sodass top-10% und top-3% wirklich trennbar werden.

**Pro:** Behält das gewünschte 3-Cutoff-Konzept.
**Contra:** Bricht alle existierenden Modell-Artefakte. Mind. 1 Tag Arbeit. Pine-Export wird komplexer (zusätzlicher Calibration-Layer in Pine-Code). KEINE Garantie dass es funktioniert.

**Action wenn gewählt:** NB14c als full retrain mit calibration. Dauert mehrere Stunden Colab + Analyse + ggf. mehrere Iterationen.

### Option C — Akzeptieren: V1 hat 1 Tier

Premium-only. Kein Profile-Switch in V1. "Aggressive" und "Balanced" werden erst V1.5 mit Backend-Continuous-Learning eingeführt.

**Pro:** Schnellster Weg zu V1. Klare Marketing-Story ("Premium AI Signals" — eindeutig).
**Contra:** Profile-Switch (zentrales UX-Feature) entfällt. ANN-011 Profile-Map muss reduziert werden.

**Action wenn gewählt:** ANN-011 Update + Pine-Router-Design ohne Profile-Switch. NB15 startet sofort.

---

### Was Nicos Antwort triggern muss

| Option | Sibling-Claude Action |
|---|---|
| A | Baue NB14c (Filter-Kombi-Test), warte auf Run, locke Tier-Definition |
| B | Baue NB14c als full-retrain mit calibration, warte 1+ Tag |
| C | Update ANN-011, ändere model_registry.md / pine_router_design.md, starte NB15 |

**Empfehlung Claude:** A. Begründung: Edge bleibt erhalten, UX intuitiver, R-13 wird operationalisiert, geringster Aufwand.

---

## 19. Session Handoff Log

Each Claude session MUST append a row here after meaningful work. This is the chain of custody between Arbeits-PC and Heim-PC.

**Format:**
- **Date (UTC):** YYYY-MM-DD
- **Workstation:** `arbeits-pc` | `heim-pc` | other (ask Nico)
- **Claude account:** `work` | `home` (which Anthropic login)
- **What changed:** brief — what code/docs/decisions changed this session
- **Commits:** short SHAs of any commits pushed
- **Outstanding next step:** exactly what the next Claude (sibling or successor) should pick up

| Date | Workstation | Account | What changed | Commits | Outstanding next step |
|---|---|---|---|---|---|
| 2026-05-26 | arbeits-pc | work | Original document creation — full 18-section handoff written from scratch after FX-only → Universal pivot | (uncommitted at time) | Commit + push to GitHub |
| 2026-05-27 | arbeits-pc | work | Context-window refresh, fresh session continuation. Verified content intact, updated date stamps, added Session Handoff Log section | `42fe4fb` | Resume NB 12 debug cycle (last commit `33f68c4`), then proceed to Phase 2 cross-asset work |
| 2026-05-27 | arbeits-pc (NWILF026, intern\nico.flotz) | work | Multi-Workstation Sync Protocol added. Section 0 rewritten with mandatory boot/end-of-turn sequence. Section 0a embeds the full persona/communication rules so a "naked" Claude on the Heim-PC (without local memory files) agrees with the work-account Claude. Section 20 added with detailed git workflow + Heim-PC bootstrap script. Local MEMORY.md on Arbeits-PC updated with pointer header. | `51ee6c7` | **Heim-PC first run:** read this entire HANDOFF (especially Sections 0, 0a, 20), then run the bootstrap commands in Section 20.4 to write the pointer MEMORY.md on Heim-PC. Then resume NB 12 work. |
| 2026-05-27 | arbeits-pc | work | Added Section 0.0 — **Standard Boot Prompt**. Nico now has one fixed copy-paste prompt to start any new chat on any machine. Claude's response protocol on boot is mechanically defined (git pull → read HANDOFF → 2-sentence status). | (next commit) | Nico starts new chat (context refresh). Use the boot prompt. Next substantive work: NB 12 debug cycle. |
| 2026-05-27 | arbeits-pc | work | **Strategischer Refactor + Doku-Struktur eingeführt.** (1) Strategie reaffirmiert: Robustheit/Cross-Asset/Multi-TF > Single-Asset-PF/Speed. (2) Neue Ordner: `/docs/` (7 Files: roadmap, architecture, feature_registry, model_registry, pine_constraints, backtesting_vision, deployment_plan), `/research/` (6 Files: README, phase1_findings, feature_experiments, shap_analysis, model_battery_results, asset_generalization, timeframe_comparisons), `/results/` (5 Unterordner: json_exports, benchmark_tables, walk_forward_summaries, per_symbol_metrics, yearly_stability_tables). (3) README.md komplett neu geschrieben (Universal-Vision, Phase A-E Roadmap, aktueller Stand). (4) NB12 gepatcht: `RANDOM_SEED=42` für LGBM/XGB/CatBoost, Section 10 mit Auto-Export aller Ergebnisse nach `/results/`. (5) HANDOFF.md Section 16 aktualisiert. | `0cc55a4` | **Nico startet NB12 in Colab** (mit `git pull` vorher in Drive-Project, damit gepatchter Code da ist). Nach Run: Outputs an Claude + `/results/`-Files in Repo committen. Dann analysiert Claude und füllt `research/model_battery_results.md`. |
| 2026-05-27 | arbeits-pc | work | **Colab→GitHub Auto-Push-Pattern.** NB12 Section 11 hinzugefügt: nach Section 10 Export pusht das Notebook die `/results/`-Files direkt zu GitHub (commit als ecoNC via Fine-grained PAT aus Colab Secrets). Damit entfällt der manuelle Drive-Download. Wiederverwendbares Pattern in [/docs/colab_auto_push.md](docs/colab_auto_push.md) — Code-Snippet + Setup-Anleitung für NB13/14/15. HANDOFF Section 16 angepasst (Step 1: einmaliges PAT-Setup). | `af58158` | **Nico:** einmal PAT in Colab Secrets ablegen (siehe docs/colab_auto_push.md), dann NB12 mit Section 10 + Section 11 laufen lassen. Sibling-Claude sieht die Results dann direkt im Repo. |
| 2026-05-27 | colab (heim-account oder arbeits-account) | — | **NB12 Run 1 abgeschlossen.** Auto-Push funktionierte (nur JSON gepusht, CSVs fehlen — Bug zu untersuchen). Verdict: LightGBM bleibt V1-Modell. Consensus-Filter (alle 3 Modelle) liefert auf GBPUSD-Hold-Out PF 2.93 (+0.39 über LGBM-Alone) — strategischer V1.5-Backend-Edge. NB12-Stability sehr gut (CV 0.145 für LGBM, alle Modelle CV < 0.20). XGBoost-Lift auf Hold-Out +0.135 PF — interessant aber nicht robust (nur 1 Symbol). | `58e2c27` (auto-push) | **Claude:** model_battery_results.md gefüllt, model_registry/roadmap/deployment_plan aktualisiert. CSV-Bug debuggen. NB13 (Cross-Asset) planen mit verschärften Fragen aus NB12-Erkenntnissen. |
| 2026-05-27 | arbeits-pc | work | **NB12-Analyse + Doku-Sync nach Run 1.** research/model_battery_results.md komplett mit echten Zahlen befüllt, Verdict + CTO-Empfehlung dokumentiert. docs/model_registry.md erweitert mit Stand 2026-05-27. docs/roadmap.md Phase A auf ABGESCHLOSSEN gesetzt, Phase B (NB13) als ACTIVE markiert. docs/deployment_plan.md V1.5-Sektion um Consensus-Filter-Plan erweitert. HANDOFF Section 16 + 19 updated. | `c30ceda` | Nico bestätigt LGBM-V1-Entscheidung oder Pushback. Dann: CSV-Bug debuggen + NB13 starten + core/colab_push.py refactoren. |
| 2026-05-27 | arbeits-pc | work | **Decision-Framework + 5 ADRs + .gitignore-Fix.** Nico bestätigt LGBM-V1, lockt Strategie-Update (Robustheit > FX-PF), fordert Decision-Logic-Framework + Architektur-Dokumentation. Geschrieben: `/docs/_phase_decision_template.md`, `/docs/decisions/README.md`, `ANN-001` SMC, `ANN-002` HTF-Interaction, `ANN-003` Gold, `ANN-004` Consensus-V1.5, `ANN-005` V1-vs-V1.5-Scope-Split. CSV-Bug Root-Cause: `.gitignore *.csv` blockte alles, Exception `!results/**/*.csv` (+ parquet/feather/json) ergänzt. `research/asset_generalization.md` mit 2 neuen NB12-getriebenen Hypothesen (H5 Consensus-Generalisation, H6 XGBoost-Generalisation). HANDOFF Section 16 + 19 updated. | `e738446` | **Nico:** Section 11 in Colab nochmal runnen für CSV-Push (oder ignorieren — JSON enthält alle Daten). Dann **NB13 bauen + Polygon-Aktivierung entscheiden**. |
| 2026-05-27 | arbeits-pc | work | **Strategy-Lock + Distribution-Plan.** Nico bestätigt CSVs-Ignore (JSON reicht) + lockt 4-Punkte-Robustheits-Mantra + skizziert Distribution-Pipeline (Lovable/Next.js + Stripe + TradingView-Invite-Auto-Manager + IONOS-Domain). `ANN-006` Robustheits-First-Mantra geschrieben (überstellt alle anderen Locks). `ANN-007` Distribution-Architektur geschrieben (separates Repo geplant pace-algo-distribution/, V1-Stack Lovable+Vercel+Railway+Postgres+Stripe). README mit Mantra prominent. HANDOFF Section 16 + 19 updated. | `dab1943` | **NB13 bauen.** Vorgehen klar in research/asset_generalization.md. Polygon-Frage offen (NB13 startet ohne, mit Crypto+GBPUSD+Gold). |
| 2026-05-27 | arbeits-pc | work | **NB13 als 12-Section-Forschungsplattform gebaut.** `core/config.py` erweitert: `FX_TRAIN_SYMBOLS`/`FX_HOLDOUT_SYMBOLS` Trennung, `CRYPTO_SYMBOLS` um BNBUSDT/ADAUSDT erweitert, `PRIMARY_TIMEFRAMES = ['5m','15m','30m','1h']`, neue `ASSET_GROUPS`-Dict, `PHASE_B_THRESHOLDS` für deterministische H1-H6-Auswertung. `notebooks/13_cross_asset_generalization.ipynb` (29 cells, 12 Sections) mit Experiment-Registry, Data-Inventory-Check (fail-fast wenn Symbole fehlen), per-pool×TF-Training-Loop, SHAP auf 3 Ebenen, Cross-Asset-Matrix, TF-Comparison, Auto-Decision-Engine, Result-Persistence in `/results/nb13/`, Auto-Push. MVP-Run: LightGBM only, Experimente A/B/D aktiv, C/E gated. `research/asset_generalization.md` mit 12-Section-Plan dokumentiert. | `038c190` | **Nico:** (1) NB01-Re-Run in Colab mit erweitertem Symbol-Set (BNBUSDT, ADAUSDT, AUDUSD, USDCHF) + neuen TFs (30m, 1h). (2) NB04 für Label-Generation auf neuen Daten. (3) NB13 in Colab durchlaufen lassen. (4) Section 12 Auto-Push (PAT in Colab Secrets bereits aktiv). |
| 2026-05-27 | colab | — | **NB13 Run 1 ABGESCHLOSSEN, Auto-Push.** Memory-Fix erforderlich (D-Experiment off, float32, gc.collect zwischen iterations, val_cutoffs_cache). Crash-Recovery, NB04 mit aktualisierter config für 30m+1h Labels nachgeholt (132 Label-Sets), dann NB13 sauber durchgelaufen. Outputs: 5 Files in `/results/nb13/`. **Verdict: FX-Edge generalisiert (Premium-PF 2.5+ auf 5 FX-Symbolen inkl. 3 nie trainierten), Crypto bricht komplett (PF≈1.0 auf 5 Crypto-Symbolen × 4 TFs).** | `56349b8` (NB13 memory fix) + `8a7bf8d` (results auto-push) | **Claude:** vollständige Analyse + ADR. |
| 2026-05-27 | arbeits-pc | work | **NB13 Analyse + ANN-008 Lock.** `research/asset_generalization.md` komplett mit Run-1-Daten gefüllt (Cross-Asset Matrix Tabelle, TF-Comparison, SHAP-Stability-Erkenntnisse, 6-Hypothesen-Status). `docs/decisions/ANN-008-fx-features-do-not-generalize-to-crypto.md` geschrieben — wichtige Konsequenz: V1-Marketing wird von "Universal" zu "FX Major Pairs". Crypto-Spezialmodell oder Universal-Pool-Training nötig vor V2. `docs/roadmap.md` Phase B als ABGESCHLOSSEN, Phase C (NB14 Multi-TF) als ACTIVE. `docs/decisions/README.md` mit ANN-008 ergänzt. | `ee7c7f9` | **Nico:** Entscheidung — NB13b (Universal-Training mit High-RAM oder Crypto-Spezialmodell)? Oder direkt Phase C (NB14 Multi-TF)? V1-Marketing-Korrektur intern bestätigen. |
| 2026-05-27 | arbeits-pc | work | **ARCHITEKTUR-PIVOT GELOCKED.** Nico hat Multi-Model-Router als neue Zielarchitektur beschlossen ("Universal UX + Specialized Intelligence"). Geschrieben: `ANN-009` Multi-Model Router (Pivot-Lock, V1→V2 Architecture, Pine-Code-Skelett), `ANN-010` Quality-Anchor (Premium PF ~2.0 als Referenz, strict-Schwellen für neue Asset-Klassen-Modelle, strikte Feature-Regeln verschärft), `docs/pine_router_design.md` (NEU — Asset-Detection, Shared Feature-Layer, Model-Subgraphs, Tier-Engine, UI-Layer, Pine-Budget-Plan für 4 Modelle, V1→V2 Migration). Update: README mit "Universal UX + Specialized Intelligence" Tagline, architecture.md mit Router-Layer + core/router/ + core/models/{class}/ Struktur, deployment_plan.md V1-V3 mit Multi-Model, model_registry.md mit 4 Modell-Slots (fx aktiv, andere stub), roadmap.md mit V-Releases, ANN-005 als "Architecture-superseded by ANN-009"-Notiz. HANDOFF Section 16 mit Pivot-Konsequenzen + NEU Section 16a "Open Technical Risks" (R-01 bis R-10). decisions/README.md Index erweitert. | `6be369e` | **Next concrete:** NB14 in Colab bauen + runnen (Multi-TF Deep-Dive für FX). Parallel optional: NB13c Crypto-Spezialmodell-Test, core/router/ Python-Stubs. |
| 2026-05-27 | arbeits-pc | work | **core/router/ Python-Stubs.** `asset_detector.py` mit AssetClass-Enum + Detection-Logic (Commodity → Crypto → FX → Indices → Unsupported, Reihenfolge-kritisch). `model_selector.py` mit MODEL_SLOTS-Dict (V1: nur fx aktiv, andere Stubs), select_model/is_class_active/get_active_classes-API. `pine_router_codegen.py` mit V1-Stub-Template (vollständiges Pine-Routing-Snippet als String) + V2-NotImplementedError-Hooks. `core/router/README.md` mit Usage + V1→V2 Migration-Doku. `tests/test_router.py` mit 4 Test-Klassen + 16 Tests. Smoke-Test bestanden — Detection korrekt, V1-Stubs returnen None, Pine-Codegen liefert 2706-Zeichen-Template. | (next commit) | NB14 bauen. |
| 2026-05-27 | heim-pc (NICO-PC, nico-pc\ecoar) | home | **Heim-PC Ersteinrichtung + Protokoll-Audit.** Repo geklont nach `C:\Projects\pace-algo` (abweichend von Arbeits-PC Pfad `C:\Users\nico.flotz\Downloads\pace-algo`). `git pull` durchgeführt — alle 58 neuen Dateien inkl. HANDOFF.md gezogen. Memory-Pointer-Datei erstellt unter `C:\Users\ecoar\.claude\projects\C--Projects-pace-algo\memory\MEMORY.md` mit Heim-PC-spezifischem Boot-Protokoll + Pfad-Hinweis. Protokoll-Lücken identifiziert (kein Section-19-Eintrag, kein Commit am Sitzungsende) und behoben. Section 20.4 Bootstrap vollständig ausgeführt. | `5790e44` | **NB14 bauen** (Multi-TF Deep Dive FX). Nächster Colab-Run laut Section 16 + roadmap.md. |
| 2026-05-27 | heim-pc | home | **Protokoll v3: Mid-Session Checkpoint + Workstation-Switch.** HANDOFF Section 0.5 + 0.6 ergänzt. Mid-Session-Checkpoints (Inline-Notiz unter letztem Log-Row) verhindern Verlust bei Context-Cutoff. Workstation-Switch-Protokoll (`HANDOFF:` prefix) für nahtlose Übergabe wenn Nico den Wechsel ankündigt. Lokale `MEMORY.md` auf Heim-PC synchron aktualisiert. | `5205b73` | NB14 bauen. |
| 2026-05-27 | heim-pc | home | **NB14 vollständig gebaut — produktorientierte Evaluation-Pipeline.** (1) `core/config.py` erweitert: `PHASE_C_THRESHOLDS` (H1–H5 Schwellen), `PRODUCT_METRIC_THRESHOLDS` (signals/day, trade duration, density, chart cleanliness, session dependency, pine UX), `QUALITY_ANCHOR` (ANN-010 operationalisiert). (2) NEU `core/analysis/product_metrics.py` — Produkt-Metriken (sigs/day, duration stats, alert frequency, session share + dependency score, chart cleanliness, pine UX score, evaluate_product_thresholds verdict A/B/C/F). (3) NEU `core/analysis/quality_check.py` — `check_quality_anchor()` returnt (passed, severity, details). (4) NEU `core/eval/tf_pipeline.py` — Router-kompatible `TFEvalConfig` + `TFEvalResult` + `decide_tf_setup()`. Pipeline ist klassen-agnostisch, V2 nutzt sie unverändert für Crypto/Indices/Commodity. (5) `notebooks/14_multi_tf_deep_dive.ipynb` — 31 Cells, 13 Sections: Setup/Inventory/Load/Train-per-TF/Hold-Out/Summary/SHAP/Pooled-vs-Single/Cutoff-Variation/Decision-Engine/Quality-Reports/Persistence/Auto-Push. Decision-Hierarchie gelocked: Stability > PF, Konsistenz > Peak, Produktqualität > Quant. AST-Syntax + JSON-Schema validiert. | (next commit) | **Nico:** NB14 in Colab runnen (Drive-Project muss `git pull` haben damit `core/eval/` + `core/analysis/product_metrics.py` da sind). Erwartete Laufzeit ~25–40 min. Section 12 pusht results/nb14/ automatisch. Danach: Claude analysiert die JSON und schreibt ADR + füllt timeframe_comparisons.md. |
| 2026-05-27 | heim-pc → Colab | home | **NB14 Run 1 abgeschlossen + Auto-Push.** 3 Iterationen Bug-Fixes nötig (Section 0 importlib.invalidate_caches, load_ext backfill hit_bar_offset für legacy NB13-_extended.parquet). Run-ID `nb14_2026-05-27T16-15-44Z_81f2316`. 5 Output-Files in `results/nb14/`. **Verdict: V1 = 5m-only.** 5m Premium PF 2.00 in-sample / 2.39 Hold-Out / WR 57.2% in-sample / 60.9% Hold-Out / MDD 2.9% / CV 0.145 / SOFT_ONLY Quality-Anchor. 15m BLOCKED (PF 1.23, MDD 34%). 30m + 1h BLOCKED (PF < 1.05, MDD > 100%). Pooled-Modell +0.08-0.20 PF auf allen TFs (V1.5-Kandidat). NY-Session 66.6% Konzentration (R-13). SHAP-Top-1 wechselt von hour_sin (5m/15m/30m) zu adx_14 (1h) — Edge-Paradigma-Wechsel. | `6c2aed4` (auto-push) | Claude analysiert + schreibt ADR + Doku-Sync. |
| 2026-05-27 | heim-pc | home | **NB14-Analyse + ANN-011 + Doku-Sync.** Nico-Direktive: V1 = 5m-only, Multi-Model-Router bleibt Zielarchitektur, Profile = Tier-Cutoffs (NICHT TFs), User-Settings-Whitelist gelockt. Geschrieben: `docs/decisions/ANN-011-v1-timeframe-and-profile-setup.md` (V1 TF-Lock + Profile-Map + User-Settings-Whitelist + V1-Priority-Order). Aktualisiert: `research/timeframe_comparisons.md` (Sections 3/4/5 mit NB14-Daten), `docs/roadmap.md` (Phase C ABGESCHLOSSEN, Phase D als Architecture-Validation ACTIVE), `docs/model_registry.md` (FX-Modell-Slot mit tf:5m gelockt + Performance-Snapshot), `docs/pine_router_design.md` (V1-Restriction-Block + Profile-Mapping + User-Settings-Whitelist), `docs/decisions/README.md` (ANN-011 in Index), `research/feature_experiments.md` (R-12/R-13/R-14/R-15 als Research-Items detailliert). HANDOFF Section 16 + 16a (R-11 bis R-14 ergänzt) + 19 updated. | `68f8b3d` | **NEXT: R-14 Cutoff-Konvergenz fixen** (NB14b minimaler Run nur für VAL-Cutoff-Recalibration, ~10 min) ODER **NB15 starten** (Pine-Router-V1-Validation). Nico entscheidet Reihenfolge. |
| 2026-05-27 | heim-pc | home | **NB14b gebaut + R-14 Calibration-Discovery-Layer.** Constraint-basierter Solver mit 3 Strategien (linear-quantile / logit-space-quantile / density-target). 4 Constraints: PF-Schwellen pro Tier (Agg≥1.3/Bal≥1.5/Cons≥1.8), Sigs/Tag-Range (15-30/5-10/1-4), Cutoff-Separation ≥0.005, Cross-Asset-Stabilität ±20%. Winner-Auswahl ist NICHT 'max PF' sondern 'alle 4 Constraints konsistent erfüllt'. 27 Cells, 12 Sections. AST + JSON validiert. | `bea36ce` | Nico Colab-Run. |
| 2026-05-27 | colab → heim-pc | home | **NB14b Run abgeschlossen + Analyse.** Auto-Push erfolgreich. Run-ID `nb14b_2026-05-27T16-48-52Z_81f2316`. **ALLE 3 Strategien FAILED.** Winner `density` (6/11 constraints), aber Aggressive- und Balanced-Cutoffs sind in ALLEN 3 Strategien IDENTISCH bei 0.4067. Root-Cause: LightGBM-Probability-Distribution ist nicht graduell sondern hat 3 diskrete Bänder (<0.4067 / Cluster bei 0.4067 / >0.4096). 30 Trees × Depth 3 mit is_unbalance=True saturiert die Outputs. **Per-Symbol Calibration auch FAILED:** EURUSD + AUDUSD haben Agg=Bal=Cons ALLE auf 0.4067 — vollständiger Kollaps. Strategien-Vergleich:<br><br>linear: agg=0.4067 / bal=0.4067 / con=0.4096<br>logit: agg=0.4067 / bal=0.4067 / con=0.4096 (logit half nicht)<br>density: agg=0.4067 / bal=0.4067 / con=0.4203 (nur Con-shift)<br><br>**Strategischer Schluss:** Wir haben EINEN echten Tier (Premium ~0.4096, PF 2.0), nicht drei. 3-Profile-Konzept via Probability-Cutoffs ist fundamental kaputt mit aktueller Modell-Architektur. | `5a3576b` (NB14b results auto-push) | 3 Optionen liegen vor Nico zur Entscheidung — siehe Section 19a unten. |
| 2026-05-27 | heim-pc → arbeits-pc | home → work | **WORKSTATION-SWITCH zum Arbeits-PC.** Nico signalisiert Wechsel. NB14b Run + Analyse abgeschlossen, 3 Optionen für R-14-Resolution liegen vor (Option A / B / C — siehe Section 19a). HANDOFF + Section 16/16a noch nicht aktualisiert mit der NB14b-Erkenntnis — Sibling-Claude (Arbeits-PC) macht das nach Nicos Entscheidung. | `298e4d2` | **Sibling-Claude auf Arbeits-PC:** Lies Section 19a unten und präsentiere Nico die 3 Optionen. Nicos Entscheidung lockt die V1-Tier-Architektur. ANN-011 muss dann updated/superseded werden je nach gewählter Option. |
| 2026-05-27 | arbeits-pc | work | **OPTION A LOCKED — V1 Tier-Architektur: Premium Core + Secondary Filters.** Nico-Decision nach NB14b: Probability-basierte Multi-Tier-Cutoffs sind fundamental kaputt mit aktueller LightGBM-Architektur (3 diskrete Bänder statt Gradient). Profile differenzieren via Filter-Stack auf Premium-Tier: Aggressive=Premium pur (~3.5/Tag), Balanced=Premium+HTF-Confirm (~3.0/Tag), Conservative=Premium+HTF+NY-Session (~1.5/Tag). Edge bleibt PF ~2.0 über alle Profile. Strategisches Reframing: Modell ist "hard pattern detector", nicht confidence-ranker — kein Fehler, passt zu Premium-Produkt. Geschrieben: `ANN-012` (V1-Tier-Architektur, supersedes ANN-011 Profile-Map, V1-TF-Lock + Whitelist aus ANN-011 bleibt gültig). Doku-Sync: `ANN-011` cross-reference, `pine_router_design.md` §0b mit Filter-Mechanik, `roadmap.md` Phase C.5 NB14c als ACTIVE, `decisions/README.md` Index. HANDOFF Section 19a archiviert (Decision-Marker), Section 19 Log. | `6f46457` | **NB14c bauen** — Secondary-Filter Validation, ~10-15 min Colab-Run, lockt finale Sigs/Tag-Zahlen mit echten Hold-Out-Daten. Danach Phase D (NB15 Pine-Router-V1-Validation). |
| 2026-05-28 | colab + arbeits-pc | mixed | **NB14c Iteration-Debug + NB14d Diagnostic.** NB14c Run 1-3 lieferten widersprüchliche Ergebnisse (0 Trades / PF 1.01 / 0 Trades). Nico stoppte weitere Iteration. Stattdessen pure Diagnostik: `core/analysis/probability_diagnostic.py` (NEU, wiederverwendbar) + `notebooks/14d_proba_distribution_diagnostic.ipynb`. NB14d Run lieferte klares **Verdict-Klasse C — Ultra-discrete Distribution (top-3 Cluster 92.4%), aber stable + kalibriert**. Key findings: `deterministic=True` RMSE 0.0 (zero Effekt), Multi-Seed cutoff_drift 0.0045, TEST proba.max() = 0.4018-0.4054 (NB14b's `0.4096` physisch unerreichbar — Phantom-Wert), Calibration ECE < 0.02. | `9e5296e`, `0898ff5`, `fbd0d23` (NB14d auto-push) | Cluster-Based-Premium-Detection als V1-Mechanik. |
| 2026-05-28 | arbeits-pc | work | **ANN-013 LOCKED — Cluster-Based Premium Detection.** Nico-Decision nach NB14d-Diagnostik: Premium-Tier wird via Cluster-Detection identifiziert (höchster stabiler Probability-Cluster bei jedem Training), NICHT mehr via hartcoded Cutoff. ANN-013 supersedes ANN-012 Cutoff-Mechanik (Filter-Stack-Konzept bleibt). Plus 2 neue Locked Rules (R-17, R-18 in Section 16a): hardcoded Probability-Werte verboten + Multi-Run-Robustheits-Regel (3+ reruns mit mean/std). `probability_diagnostic.py` erweitert: `extract_premium_cluster()`, `apply_cluster_cutoff_mask()`, `cluster_stability_test_multi_seed()`. Smoke-Test bestanden (0.4018 korrekt extrahiert aus simulierten NB14d-Daten). `notebooks/14e_cluster_premium_calibration.ipynb` (NEU, 25 Cells) baut die volle Pipeline: 3-Seed-Training → Cluster-Extraction → Stability-Check → Filter-Profile mit Cluster-Cutoff → Hold-Out-Validation Multi-Run → Quality-Anchor → Pine-Export-Ready Output. Doku-Sync: ANN-012 Cross-Link, decisions/README Index, pine_router_design.md §0b komplett aktualisiert. Plus Produkt-Reframing: "bestätigtes Premium-Pattern erkannt" statt "höhere Wahrscheinlichkeit". | `a88026d` | **Nico:** NB14e in Colab runnen (~10 min). Section 9 druckt LOCKED_PREMIUM_CLUSTER + Profile-Quality. Wenn V1-Ready: Phase D (NB15 Pine-Router-Validation) startet. |
| 2026-05-28 | colab | — | **NB14e Run abgeschlossen + methodischer Bug entdeckt.** Multi-Run-Analyse zeigte: seed=1 produziert sinnvolle Trades (Aggressive PF 1.24, Balanced PF 1.76, Conservative PF 2.25, GBPUSD Hold-Out Balanced PF **3.50**). Aber seeds 42+7 hatten 0 Trades. Root-Cause: `LOCKED_PREMIUM_CLUSTER = mean(per_seed_clusters)` wurde auf ALLE Seeds appliziert — bei Seeds wo eigener Cluster unter Mean liegt, wird Mean nie erreicht (false 0-Trades). ANN-013's `cluster_drift < 0.001` ist methodisch falsch — drift 0.0036 ist normal für stochastische small tree ensembles. **Plus:** Pair-Variabilität sichtbar (GBPUSD super, USDCHF schwach). | `d1d703e` (NB14e auto-push) | ANN-014 schreiben (Per-Model Relative Cluster + Behavioral Stability). |
| 2026-05-28 | arbeits-pc | work | **ANN-014 LOCKED — Per-Model Relative Cluster + Behavioral Stability.** Nico-Decision nach NB14e: jedes Modell trägt SEINEN eigenen Cluster-Cutoff (statt globalem Mean). Stability wird über VERHALTEN definiert (signal_freq CV, PF CV, holdout PF mean, cluster_pct std, MDD std) — NICHT raw probability equality. ANN-014 supersedes ANN-013's `cluster_drift < 0.001` (methodisch falsch). Cluster-Detection-Mechanik aus ANN-013 bleibt gültig. R-17/R-18 in HANDOFF aktualisiert + R-19 (Pair-Tiering V1.5) hinzugefügt. `probability_diagnostic.py` erweitert: `behavioral_stability_check()` (5 Metriken mit Thresholds) + `pair_level_quality_check()` (supported/experimental/unsupported Klassifikation). Smoke-Test bestanden — beide Funktionen liefern saubere Ergebnisse. `notebooks/14f_per_model_behavioral_validation.ipynb` (NEU, 25 Cells, 11 Sections): Per-Seed-Cluster-Extraction → Per-Seed-Inferenz mit eigenem Cluster (Bug-Fix vs NB14e) → Hold-Out Multi-Run → Per-Symbol Aggregation → Pair-Tiering (ANN-014 §5) → Behavioral Stability Check → Best-Behavior-Seed-Selection → Pine-Export-Ready Output. Doku-Sync: ANN-013 Cross-Link, decisions/README Index. | `7281be5` | **Nico:** NB14f in Colab runnen (~10 min). Liefert BEST_SEED + BEST_CLUSTER für Pine-Codegen + Pair-Tiering-Daten. Wenn behavior-stable: Phase D (NB15 Pine-Router-V1) startet. |
| 2026-05-28 | colab | — | **NB14f v1 Run abgeschlossen + Auto-Push.** Per-Model Relative Cluster funktioniert technisch sauber (Seed 42 cluster=0.4018 / Seed 1 cluster=0.4054 / Seed 7 cluster=0.4025 — keine 0-Trade-Bugs). BEST_SEED-Selection wählte seed=1 (cluster=0.4054). **Aber `verdict.all_profiles_behavioral_stable: false` auf allen 3 Profilen.** Critical Failures: Aggressive (signal_frequency_cv 0.45 + holdout_pf_mean 0.85), Balanced (signal_frequency_cv 0.77 + mdd_relative_std 0.83), Conservative (signal_frequency_cv 0.74 + holdout_pf_mean 0.50 + mdd_relative_std 0.75). Pair-Aggregat: nur GBPUSD Balanced PF 1.41 (n=293) — AUDUSD/USDCHF alle Profile PF < 1.0 = unsupported. ANN-014's Lock-Engine hat sauber gegriffen — kein V1-Lock auf nicht-stabilen Seed. | `2845025` | **Claude:** vollständige Analyse + ADR. |
| 2026-05-28 | arbeits-pc | work | **ANN-015 LOCKED + Doku-Sync + Symbol-Pool-Expansion.** Nico-Direktive nach NB14f v1 Behavioral-Stability-FAIL: NICHT auf GBPUSD-only-Pivot (zu schnell), sondern Trainings-Pool erweitern. Frame: "Produkt-Robustheits-Stabilisierung läuft", nicht "Modell broken". NB13 hat FX-Generalisierung bereits belegt (Premium-PF 2.58–2.66 mit top-1%-Cutoff) — These: Cluster-basierte Cutoffs (~2% breiter) brauchen breiteren Pool um Behavioral Stability zu erreichen. Geschrieben: [ANN-015 V1 Training-Pool Expansion + Robustness Re-Validation](docs/decisions/ANN-015-v1-training-pool-expansion-robustness-revalidation.md) mit deterministischen Pass/Fail-Pfaden (4 Branches). Patches: `core/config.py` (FX_TRAIN += NZDUSD, FX_HOLDOUT += USDCAD, alles andere unverändert für saubere isolierte Variable). Doku-Sync: docs/roadmap.md (Phase C.5 ABGESCHLOSSEN, NEU Phase C.6 ACTIVE, Phase D BLOCKED), docs/model_registry.md (V1 FX-Modell Status auf "Pending Re-Validation", NB14 v1 + NB14f v1 als historical Snapshots), docs/decisions/README.md (ANN-015 in Index), research/asset_generalization.md (Re-Validation-Plan-Sektion mit Pair-Aggregat-Tabelle + Methoden-Diskrepanz NB13 vs NB14f erklärt), research/feature_experiments.md (R-20 NEU: Training-Pool-Breite als Stability-Treiber). HANDOFF Section 16 + 16a (R-20 NEU) + 19 updated. | `bc3ea34` | **Nico in Colab:** (1) `git pull` im Drive-Project. (2) NB01 re-run für NZDUSD + USDCAD Fetcher (~10 min). (3) NB04 re-run für Labels auf neuen Symbolen × 4 TFs (~5-10 min). (4) NB14f re-run komplett (~12-15 min mit 33% mehr Trainingsdaten). Auto-Push pusht `results/nb14f/`-Sub-Datum-Files. Wenn Pass-Kriterien aus ANN-015 §3 erfüllt: Phase D startet. |
| 2026-05-28 | arbeits-pc | work | **ANN-015 Fetcher-Patch — Dukascopy-Mapping erweitert.** Nicos NB01-Run schlug auf NZDUSD + USDCAD fehl mit `Unknown Dukascopy symbol`. Root-Cause: `core/data/dukascopy_fetcher.py` `DUKASCOPY_INSTRUMENT`-Map enthielt nur die 5 Phase-1-Majors + XAU. Patch: + `NZDUSD → INSTRUMENT_FX_MAJORS_NZD_USD`, + `USDCAD → INSTRUMENT_FX_MAJORS_USD_CAD`. Library-Konvention `INSTRUMENT_FX_MAJORS_<BASE>_<QUOTE>` — bei nicht-existierender Constant würde die `getattr()`-Prüfung in Zeile 67-72 mit klarem RuntimeError abbrechen. Folge-Map-Erweiterungen für Crosses etc. gehen gleichen Weg. | (next commit) | **Nico:** NB01 nochmal runnen — sollte jetzt sauber durchlaufen. Dann NB04 + NB14f wie geplant. |

