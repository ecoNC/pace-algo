# ANN-011: V1 Timeframe Lock + Profile Setup + User-Settings Whitelist

**Status:** Active (V1-TF-Lock + Settings-Whitelist gültig — **Profile-Mechanik durch [ANN-012](ANN-012-v1-tier-architecture-premium-core-plus-filters.md) superseded**)
**Datum:** 2026-05-27
**Locked-By:** Nico-Decision nach NB14-Multi-TF-Deep-Dive
**Related:** [[ANN-006]] (Robustheits-Mantra) [[ANN-009]] (Multi-Model-Router) [[ANN-010]] (Quality-Anchor) [[ANN-012]] (V1-Tier-Architektur — Premium + Filters)
**Supersedes:** Profile-Annahmen in ANN-005 (V1-Scope) — User-Profile sind jetzt Tier-basiert, nicht TF-basiert
**Superseded BY ANN-012 für:** Profile-Map-Mechanik §0b (Probability-Cutoffs → Filter-Stack). V1-TF-Lock auf 5m + User-Settings-Whitelist §0c bleiben gültig.

---

## 1. Hypothese

Vor NB14 wurde angenommen, dass User-Profile (Conservative / Balanced / Aggressive) durch unterschiedliche Timeframes umgesetzt werden — Aggressive auf 5m, Conservative auf 1h, etc. NB14 sollte bestimmen welche TFs in V1 unterstützt werden und wie die Profile darauf abbilden.

Diese Annahme ist nach NB14 **revidiert**: Profile werden in V1 NICHT durch verschiedene TFs, sondern durch verschiedene **Confidence-Tier-Cutoffs auf demselben TF (5m)** umgesetzt.

## 2. Experiment

**NB14 (`notebooks/14_multi_tf_deep_dive.ipynb`)** — produktorientierte Evaluation für FX-Modell auf 5m / 15m / 30m / 1h:

- Train: EURUSD + USDJPY (Walk-Forward 2020-01 → 2024-01, VAL bis 2024-07)
- Hold-Out: GBPUSD + AUDUSD + USDCHF (nie trainiert)
- 27 Features (NB11-Winner-Config), LightGBM 30 trees × depth 3
- Quant-Metriken + Produkt-Metriken + Quality-Anchor pro TF
- Pooled vs Single-TF (H4) + 1h Top-3%-Cutoff (H5)

**Vollständige Daten:** `results/nb14/summaries/nb14_full_snapshot_2026-05-27.json` (Run-ID `nb14_2026-05-27T16-15-44Z_81f2316`)

## 3. Resultat

### Per-TF Summary (Premium-Tier OOS)

| TF | PF | WR | n_trades | MDD | CV | Hold-Out PF | Hold-Out WR | sigs/day | Anchor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **5m** | **2.00** | **57.2%** | **3,354** | **2.9%** | **0.145** | **2.39** | **60.9%** | **3.5** | **SOFT_ONLY ✓** |
| 15m | 1.23 | 45.1% | 954 | 34.3% | 0.070 | 1.83 | — | 1.0 | BLOCKED |
| 30m | 1.04 | 40.9% | 1,495 | 134% | 0.051 | 1.28 | — | 1.6 | BLOCKED |
| 1h | 0.98 | 39.5% | 4,414 | 150% | 0.108 | 0.90 | — | 4.6 | BLOCKED |

### 5m Hold-Out Detail (Premium-Tier, nie trainierte Symbole)

| Symbol | PF | WR | n_trades |
|---|---:|---:|---:|
| GBPUSD | 2.57 | **63.2%** | 1,951 |
| AUDUSD | 2.47 | **62.2%** | 1,182 |
| USDCHF | 2.12 | 58.6% | 1,778 |
| **Mean** | **2.39** | **60.9%** | 4,911 |

→ **Hold-Out outperformt in-sample** (WR 60.9% vs 57.2%, PF 2.39 vs 2.00). Kein Overfit-Verdacht.

### Yearly Stability (5m Premium)

| Year | PF |
|---|---:|
| 2024 | 1.79 |
| 2025 | 2.04 |
| 2026 | **2.52** |

→ Edge ist über Jahre stabil und wird besser, nicht schlechter. CV = 0.145.

### Per-TF SHAP-Top-1

| TF | Top-1 Feature |
|---|---|
| 5m | `hour_sin` |
| 15m | `hour_sin` |
| 30m | `hour_sin` |
| 1h | `adx_14` ← Edge-Paradigma wechselt |

→ Auf 1h verschwindet die Time-of-Day-Edge komplett. Fundamental anderes Marktverhalten.

### Pooled vs Single-TF (H4)

| TF | Single-TF PF | Pooled PF | Lift |
|---|---:|---:|---:|
| 5m | 2.00 | 2.08 | +0.08 |
| 15m | 1.23 | 1.42 | +0.19 |
| 30m | 1.04 | 1.24 | +0.20 |
| 1h | 0.98 | 1.13 | +0.15 |

→ Pooled-Modell ist auf jedem TF besser. Lift ist real, rettet aber keinen TF zur deploy-Qualität.

### Session-Konzentration (5m Premium)

| Session | Anteil |
|---|---:|
| NY (13–22 UTC) | **66.6%** |
| Asia | 5.0% |
| London | 0.3% |
| LDN/NY Killzone | 0.03% |

→ Premium-Edge ist stark NY-konzentriert (verletzt 65%-Soft-Schwelle). Marketing-relevanter Befund.

### Produkt-Verdicts

Alle 4 TFs erreichen nur `product_grade_C`. 5m scheitert an:
- `chart_clean` ✗ — max_overlapping=13 (Threshold ≤ 2)
- `session_balanced` ✗ — NY-Share 66.6% (Threshold ≤ 65%)

Aber: `signals_per_day_in_range` ✓, `premium_density_ok` ✓, `trade_duration_in_range` ✓.

## 4. Decision

### 4.1 V1-Timeframe-Lock

**Supported TFs in V1:** `['5m']` (nur)
**Default-TF:** `5m`
**Sperrgrund 15m/30m/1h:** Quality-Anchor BLOCKED (per-Jahr-PF unter 1.2, MDD > 100% bei 30m/1h).

15m wird als Forschungs-Item separat aufgenommen (siehe Section 5) — In-Sample-Schwäche bei Hold-Out-Stärke verdient Untersuchung, aber nicht in V1.

### 4.2 User-Profile-Mapping (REVIDIERT)

User-Profile werden NICHT durch verschiedene TFs umgesetzt, sondern durch verschiedene **Tier-Cutoffs auf 5m**:

| Profil | Tier-Cutoff | erwartete Sigs/Tag/Symbol | erwarteter PF | erwartete WR |
|---|---|---:|---:|---:|
| Aggressive | Standard (≥ Top 10%) | ~35 | 1.13 | 43% |
| Balanced | High (≥ Top 3%) | ~10 | 1.13 | 43% |
| Conservative | Premium (≥ Top 1%) | ~3.5 | **2.00** | **57%** |

**Hinweis:** NB14-Daten zeigen Standard/High kollabieren auf das gleiche Cutoff weil VAL-Verteilung am oberen Ende konzentriert ist. Vor V1-Release muss VAL-Cutoff-Stratifikation überprüft werden — alternativ kompletter NB14b-Run mit angepassten Tier-Percentilen. Tracking-Item **R-14** (V1-blockend).

### 4.3 User-Settings-Whitelist (Anti-Curve-Fitting-Lock)

User-Settings dürfen Verhalten personalisieren, **dürfen aber NICHT echtes Curve-Fitting ermöglichen**.

**ERLAUBT** in V1-Pine-Inputs:

| Setting | Typ | Beispiel-Optionen |
|---|---|---|
| Profile-Switch | Dropdown 3-Stufen | Aggressive / Balanced / Conservative |
| Signal-Density-Tweak | Discrete +/- 1 step | Reduce / Default / Boost (ändert Tier-Cutoff in fest-validierten Schritten) |
| Session-Filter | Multi-Check | Asia / London / NY (User kann Sessions ausblenden) |
| HTF-Confirmation-Required | Boolean | wenn ON, nur Signale wenn 1h-Trend übereinstimmt |
| Alert-Frequency-Cap | Discrete | Max 5/10/20 alerts/day |
| Risk-per-Trade-Display | Discrete | Pip- vs %-Anzeige (rein UI, keine Modell-Auswirkung) |

**VERBOTEN** in V1-Pine-Inputs:

| Verboten | Begründung |
|---|---|
| freie ML-Probability-Thresholds | Bricht VAL-derived Tier-System, ermöglicht Curve-Fit auf TEST-Daten |
| rohe Probability-Cutoffs | Selber Effekt wie oben |
| unbounded ATR-Inputs | Ändert Backtest-Statistik unkontrolliert |
| unbounded TP-/SL-R-Multiplier | Ändert Triple-Barrier-Equivalenz → Backtest ungültig |
| Feature-Toggles (z.B. "RSI an/aus") | Modell darf nicht zur Laufzeit verändert werden |
| beliebige Optimierungsparameter | Definitionsgemäß Curve-Fit |

**Locked Rule:** Jede neue User-Setting-Idee MUSS gegen diese Whitelist geprüft werden, BEVOR sie in Pine-Code landet.

### 4.4 Marketing-Sprache

Folgende Aussagen sind durch NB14-Daten gedeckt:

- ✓ "AI Trading Indicator für FX Major Pairs auf 5-Minuten-Charts"
- ✓ "Profit Factor 2.0 OOS"
- ✓ "Win Rate 57% in-sample, 61% auf Hold-Out-Symbolen"
- ✓ "Backtest über 6 Jahre, validiert auf 3 nie trainierten Pairs"
- ✓ "Maximum Drawdown unter 3%"

Folgende Aussagen sind **VERBOTEN** (nicht datengestützt):

- ✗ "85%+ Win Rate" (echter Wert: 57–63%)
- ✗ "Universal Multi-Timeframe Indicator" (V1 ist 5m-only)
- ✗ "Funktioniert auf jedem Asset" (V1 ist FX-Major-only)
- ✗ "Garantierte Profitabilität" (ist eh nirgendwo erlaubt)

### 4.5 V1-Priority-Order (gelockt)

Bei V1-Trade-offs zwischen folgenden Aspekten gilt **diese Priorität (absteigend)**:

1. **Robustheit** (Stability CV, Hold-Out-Performance)
2. **Niedrige MDD** (Risiko-Profil über User-Vertrauen)
3. **Non-Repainting** (keine Look-Ahead-Leakage, Pine-bit-exact)
4. **Cleanes UX** (Chart-Übersicht, Alert-Frequenz)
5. **Pine-Simplicity** (Maintenance + Pine-Budget)
6. **Stabile OOS-Performance** (Yearly-CV < 0.20)
7. **Win Rate** — NACHRANGIG. PF 2.0 bei 57% WR > PF 1.5 bei 70% WR.

## 5. Konsequenz

### 5.1 Code-Änderungen

- `core/config.py` — `PRIMARY_TIMEFRAMES = ['5m']` für V1-Production-Runs (oder eigene `V1_TIMEFRAMES = ['5m']` Konstante)
- `core/router/model_selector.py` — `MODEL_SLOTS[AssetClass.FX]` bekommt `tf: '5m'` field
- `core/eval/tf_pipeline.py` — bleibt unverändert, V2 ist Multi-TF-fähig wenn V2-Asset-Klassen-Modelle dranne sind

### 5.2 Doku-Updates (in diesem Commit-Batch)

- `docs/roadmap.md` — Phase C ABGESCHLOSSEN, Phase D ACTIVE
- `docs/model_registry.md` — FX-Modell-Slot mit `tf: '5m'` gelocked, Quality-Anchor-Status `soft_only`
- `docs/pine_router_design.md` — Single-TF-V1 dokumentieren (kein TF-Switch im Pine-Code)
- `docs/decisions/README.md` — ANN-011 Index-Eintrag
- `research/timeframe_comparisons.md` — Sections 3/4/5 mit NB14-Daten gefüllt

### 5.3 Pine-Code-Implikation

V1-Pine bleibt **single-model, single-TF (5m)**:

```pine
//@version=6
indicator("PaceAlgo", overlay=true)

// === V1 RESTRICTION: 5m only ===
if timeframe.in_seconds() != 300
    label.new(bar_index, high, "PaceAlgo V1 supports 5-minute charts only.\nSwitch to 5m timeframe.")
    // … (no signals shown)
else
    // … (full router + FX-model logic)
```

→ User auf 15m/30m/1h sehen eine klare UI-Warnung, kein silent-fail mit zufälligen Signalen.

### 5.4 Forschungs-Items (separat, NICHT V1-blockend)

| ID | Item | Priorität |
|---|---|---|
| R-12 | **15m-Anomalie:** In-Sample-PF 1.23 vs Hold-Out-PF 1.83 — verdient eigene Untersuchung (Sampling-Bias? Asset-Mix? Trainings-Period?) | mittel — V1.5-Kandidat |
| R-13 | **NY-Session-Konzentration:** 66.6% der Premium-Signale in NY-Session. Feature-Bug oder echter Markt-Effekt? Session-Decomposition-Test | hoch — Marketing-relevant |
| R-14 | **Tier-Cutoff-Konvergenz:** Standard- und High-Tier kollabieren auf identische Cutoffs auf 5m. VAL-Verteilung-Analyse + Re-Stratifikation vor V1-Release | hoch — V1 UX-blockend |
| R-15 | **WR-Boost-Suche:** kann WR von 57% auf 60%+ ohne PF-Verlust? Optuna-Tuning der Hyperparams im Pine-Budget | niedrig — V1.5 |

### 5.5 Open Technical Risks (in HANDOFF Section 16a ergänzt)

- **R-11 — Quality-Anchor SOFT_ONLY:** WR 57% < 60%-Soft-Target. Marketing muss ehrlich "57% in-sample / 61% Hold-Out" kommunizieren statt "85%+ WR"-Claim.
- **R-14 — Tier-Cutoff-Konvergenz:** Standard- und High-Tier identisch auf 5m. Profile "Aggressive" und "Balanced" hätten identische Signal-Mengen, womit das Profile-Konzept löchrig wird. Mitigation: VAL-Quantile schon vor Pine-Generation re-stratifizieren oder Cutoffs außerhalb der natürlichen Verteilung manuell ableiten. **V1-blockend.**

### 5.6 Lessons

1. **Quality-Anchor war richtig gewählt.** Ohne strikte Schwellen hätten wir 15m als "Conservative"-Profil gelauncht (PF 1.23 wirkt akzeptabel auf den ersten Blick). Hold-Out 1.83 hätte das in der Realität gerettet — aber Yearly-PF-Min bricht und MDD 34% wäre ein User-Vertrauen-Killer.

2. **Pooled-Lift ist real aber nicht ausreichend.** +0.08 bis +0.20 PF zeigt: Pooled-Training ist eine valide Optimierung für später. Aber für V1 reicht Single-TF-5m.

3. **Profile ≠ TF.** Das war eine Architektur-Annahme die durch Daten falsifiziert wurde. NB14 hat sie gerettet bevor sie in V1-Pine-Code landete.

4. **NY-Session-Effekt war unsichtbar.** Ohne Produkt-Metriken (session_dependency-Score) wäre die 66.6%-Konzentration im "PF 2.0" verschwunden. Das war exakt warum Produkt-Metriken neben Quant-Metriken evaluiert werden müssen.
