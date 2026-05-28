# Timeframe Comparisons — Phase C (NB14) + Phase C.5 (NB14b/c)

**Status:** ✅ Phase C ABGESCHLOSSEN — V1=5m gelocked ([ANN-011](../docs/decisions/ANN-011-v1-timeframe-and-profile-setup.md))
**Status:** ✅ NB14b ABGESCHLOSSEN — Probability-Cutoff-Tier-Konzept widerlegt, Option A gelocked ([ANN-012](../docs/decisions/ANN-012-v1-tier-architecture-premium-core-plus-filters.md))
**Status:** 🟡 NB14c NEXT — Secondary-Filter Validation für die finalen Sigs/Tag-Zahlen pro Profil
**Decision-Framework:** [/docs/_phase_decision_template.md](../docs/_phase_decision_template.md)
**Architektur-Lock:** [ANN-009 Multi-Model Router](../docs/decisions/ANN-009-multi-model-router-architecture.md) — NB14 fokussiert auf **FX-Modell** (V1-Scope), Crypto/Indices/Commodity separat
**Quality-Anchor:** [ANN-010](../docs/decisions/ANN-010-quality-anchor.md) — Premium PF ~2.0 ist Vergleichspunkt
**V1-Tier-Mechanik (FINAL):** Premium Core + Secondary Filters per ANN-012 — Profile differenzieren via HTF-Confirm + NY-Session-Filter, NICHT via Probability-Cutoffs

---

## Strategische Verfeinerung nach NB13

NB13 hat bereits TF-Vergleich auf FX gezeigt (5m best, 1h schwächste):

| TF | FX Mean Premium PF (NB13) |
|---|---:|
| 5m | **2.49** |
| 15m | 1.60 |
| 30m | 1.48 |
| 1h | 1.18 |

Aber NB13 war **out-of-distribution test** (FX-trained inferenz pro Symbol). NB14 muss tiefer gehen:
- **Per-TF Stability über Jahre** (CV)
- **Per-TF Max Drawdown** (Risiko-Profil)
- **Per-TF Trade-Frequency und Premium-Tier-Density** (UX-relevanz)
- **Per-TF SHAP** (welche Features dominieren auf welchem TF)
- **Per-TF Hold-Out Test** auf nie trainierten FX-Symbolen
- **4h-Test** (optional) — ob langfristige Edge existiert

---

## 1. Hypothese

### H1: "5m ist der Sweet Spot für FX-V1"

NB13 zeigt 5m hat höchsten Premium-PF (2.49). H1 prüft ob das stabil über Jahre und Hold-Outs ist.

**Schwelle für H1 = TRUE:**
- 5m Mean Premium-PF auf Hold-Out-Symbolen ≥ 2.0
- 5m Stability-CV über Jahre ≤ 0.20
- 5m Max Drawdown < 18%
- 5m Trades/Tag pro Symbol ≥ 3 (Premium)

### H2: "15m ist robuste Alternative für niedrigere-Frequenz-Trader"

15m hat NB13 PF 1.60 (mean). Wenn 15m Stability deutlich besser ist als 5m und PF noch über 1.5 hält, ist 15m ein V1-Profil "Conservative" wert.

**Schwelle für H2 = TRUE:**
- 15m Mean Premium-PF ≥ 1.5
- 15m Stability-CV ≤ 0.15
- 15m Trades/Tag pro Symbol ≥ 1 (Premium)

### H3: "30m und 1h sind nicht V1-tauglich"

NB13 zeigt 30m PF 1.48 und 1h PF 1.18 — beide unter dem Quality-Anchor von 2.0. Aber: vielleicht ist 1h dafür extrem stabil mit niedrigem Drawdown.

**Schwelle für H3 = TRUE:** 30m + 1h erfüllen Quality-Anchor strict NICHT (PF < 1.5 OOS) → für V1 ausgeschlossen, für V1.5+ Swing-Profile vielleicht wieder einbringen.

### H4: "Multi-TF-Modelle (5m+15m gepoolt) generalisieren besser als TF-spezifische"

Hypothese: Ein Modell trainiert auf gepooltem 5m+15m+30m+1h Datensatz lernt TF-invariante Patterns und ist robuster.

**Test:** Pooled-Modell PF vs Single-TF-Modell PF auf jedem TF einzeln gemessen.

**Schwelle für H4 = TRUE:** Pooled-Modell Premium PF ≥ Single-TF-Modell PF auf mindestens 3 von 4 TFs.

### H5: "Premium-Tier-Density-Reduction lohnt sich auf höheren TFs"

NB13: 5m 4323 Premium-Trades insgesamt, 1h nur ~110. Vielleicht bringt Tier-Cutoff-Anpassung (z.B. top 3% statt top 1% auf 1h) wieder Power.

**Test:** Top-3%-Cutoff auf 1h getestet, vergleich Premium-PF.

**Schwelle für H5 = TRUE:** Top-3% auf 1h liefert PF ≥ 1.5 mit ≥ 30 Trades/Jahr.

---

## 2. Experiment (Setup für NB14)

| Element | Wert |
|---|---|
| Trainings-Pool | FX-Train: EURUSD, USDJPY |
| Hold-Out-Symbole | GBPUSD, AUDUSD, USDCHF (nie trainiert) |
| Modell | LightGBM (V1-Sieger, 30 trees × depth 3) |
| TFs | 5m, 15m, 30m, 1h (+ optional 4h Test in Section 9) |
| Hyperparams | NB12-Stand (RANDOM_SEED=42, identische Hyperparams pro TF) |
| Features | 27 Features (NB11-Winner-Config) |
| Walk-Forward | TRAIN_END 2024-01-01, VAL_END 2024-07-01 (identisch wie NB13) |
| Quality-Anchor | ANN-010 — Premium PF ≥ 1.5 strict, ≥ 2.0 anchor reference |

**NB14 Sections (Plan):**

| Section | Inhalt |
|---|---|
| 0 | Config + Experiment Registry (TF_VARIANTS-Liste) |
| 1 | Data Loading + Inventory Check |
| 2 | Feature Engineering (re-use NB13) |
| 3 | Per-TF Walk-Forward Split + Class-Balance Report |
| 4 | Per-TF Training (LGBM) — 4 Modelle (5m, 15m, 30m, 1h) |
| 5 | **Detailed Metrics pro TF:** PF, WR, ExpR, MDD, Stability-CV, Yearly Breakdown, Premium Trades/Day |
| 6 | **Hold-Out-Test pro TF** (GBPUSD/AUDUSD/USDCHF) |
| 7 | **Per-TF SHAP** (mean abs SHAP, Top-Features-Vergleich) |
| 8 | **Pooled vs Single-TF Test** (H4) |
| 9 | **Cutoff-Variation auf 1h** (H5) |
| 10 | **Optional: 4h Sanity-Check** |
| 11 | **Auto-Decision-Engine** scort H1/H2/H3/H4/H5 mit PHASE_C_THRESHOLDS |
| 12 | Result Persistence (`/results/nb14/`) |
| 13 | Final Verdict + V1-TF-Empfehlung |
| 14 | Auto-Push to GitHub |

---

## 3. Resultat (NB14 Run 1, 2026-05-27, commit `81f2316`)

**Datenquelle:** `results/nb14/summaries/nb14_full_snapshot_2026-05-27.json`
**Run-ID:** `nb14_2026-05-27T16-15-44Z_81f2316`

### A. Per-TF Premium Metrics (in-sample TEST)

| TF | PF | WR | ExpR | MDD | Stability CV | Trades/Tag/Symbol | n_trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| **5m** | **2.00** | **57.2%** | +0.424 | **2.9%** | **0.145** | **3.53** | 3,354 |
| 15m | 1.23 | 45.1% | +0.140 | 34.3% | 0.070 | 1.00 | 954 |
| 30m | 1.04 | 40.9% | +0.020 | 134% | 0.051 | 1.57 | 1,495 |
| 1h | 0.98 | 39.5% | -0.011 | 150% | 0.108 | 4.65 | 4,414 |

→ Nur 5m erreicht produktwürdige PF. 30m/1h haben Kapital-Wipeouts in der Equity-Kurve (MDD > 100%).

### B. Per-TF Hold-Out (GBPUSD/AUDUSD/USDCHF gemittelt)

| TF | Hold-Out Premium PF | Mean WR | Min PF | Max PF |
|---|---:|---:|---:|---:|
| **5m** | **2.39** | **60.9%** | 2.12 (USDCHF) | 2.57 (GBPUSD) |
| 15m | 1.83 | — | 1.67 | — |
| 30m | 1.28 | — | 1.17 | — |
| 1h | 0.90 | — | 0.84 | — |

**5m Hold-Out per Symbol:**

| Symbol | PF | WR | n_trades |
|---|---:|---:|---:|
| GBPUSD | **2.57** | **63.2%** | 1,951 |
| AUDUSD | **2.47** | **62.2%** | 1,182 |
| USDCHF | **2.12** | 58.6% | 1,778 |

→ 5m Hold-Out outperformt in-sample (WR 60.9% vs 57.2%, PF 2.39 vs 2.00). **Generalisierung ist real**, kein Overfit-Verdacht.

### C. Per-TF SHAP-Top-5

| TF | Top-1 | Top-2 | Top-3 | Top-4 | Top-5 |
|---|---|---|---|---|---|
| 5m | hour_sin (0.0053) | ema_20_dist_atr (0.0037) | hour_cos (0.0012) | rvol_20 (0.0009) | dist_to_swing_low_atr (0.0) |
| 15m | hour_sin (0.0062) | ema_20_dist_atr (0.0017) | htf_ltf_agree_bull (0.0008) | atr_percentile_100 (0.0008) | rvol_20 (0.0006) |
| 30m | hour_sin (0.0031) | htf_ltf_agree_bull (0.0010) | rvol_20 (0.0010) | dist_to_swing_low_atr (0.0008) | realized_vol_20 (0.0005) |
| 1h | **adx_14** (0.0042) | atr_pct (0.0022) | realized_vol_20 (0.0013) | ltf_rsi_minus_htf_rsi (0.0011) | atr_percentile_100 (0.0008) |

→ **Edge-Paradigma-Wechsel zwischen 30m und 1h:** `hour_sin` (Time-of-Day Edge) ist auf 5m/15m/30m Top-1, verschwindet auf 1h komplett. Auf 1h dominiert `adx_14` (Trendstärke). Andere Marktstruktur, anderes Modell-Paradigma nötig.

### D. Pooled vs Single-TF (H4)

| TF | Single-TF PF | Pooled-Modell PF auf gleichem TF | Lift | Pooled n |
|---|---:|---:|---:|---:|
| 5m | 2.00 | 2.08 | +0.08 | 3,161 |
| 15m | 1.23 | 1.42 | +0.19 | 1,327 |
| 30m | 1.04 | 1.24 | +0.20 | 1,036 |
| 1h | 0.98 | 1.13 | +0.15 | 439 |

→ Pooled-Modell ist auf 4/4 TFs besser. Lift +0.08 bis +0.20 PF. **H4 wäre PASS** (lift ≥ 0 auf ≥ 3 TFs), aber Pooled-PF auf 30m/1h liegt immer noch unter Quality-Anchor — Pooling rettet die schwachen TFs nicht zur Deploy-Qualität.

### E. Produkt-Metriken (5m Premium-Tier)

| Metrik | Wert | Threshold | Pass |
|---|---:|---:|---|
| Signals/Day/Symbol | 3.53 | [1.0 – 8.0] | ✓ |
| Premium Density | 1.22% | ≤ 1.5% | ✓ |
| Trade Duration (mean bars) | 6.2 | [3 – 24] | ✓ |
| Chart Cleanliness (max overlapping) | 13 | ≤ 2 | ✗ |
| Session Dependency (NY share) | **66.6%** | ≤ 65% | ✗ |

→ 5m erreicht `product_grade_C` (3/5). Verbesserungspunkte sind klar identifiziert: NY-Konzentration + Chart-Überlappung. R-13 Research-Item.

### F. Session-Verteilung (5m Premium)

| Session | Share | Notes |
|---|---:|---|
| **NY (13–22 UTC)** | **66.6%** | überproportional konzentriert |
| Asia | 5.0% | minimal |
| London | 0.3% | nahezu null |
| LDN/NY Killzone | 0.03% | nahezu null |

→ Premium-Signal-Engine ist faktisch ein **NY-Session-Detector**. Großer Hinweis für Marketing + Product-Positioning.

### G. Yearly Stability (5m Premium)

| Year | PF |
|---|---:|
| 2024 | 1.79 |
| 2025 | 2.04 |
| 2026 | **2.52** |

→ Edge wird mit der Zeit besser, nicht schlechter. CV 0.145 unter 0.20-Schwelle.

### H. Quality-Anchor-Status (ANN-010)

| TF | Severity | strict pass | soft pass |
|---|---|---:|---:|
| 5m | **SOFT_ONLY** ✓ | 7/7 | 1/2 (matches FX-anchor ✓, WR-target ✗) |
| 15m | BLOCKED | 5/7 | 0/2 |
| 30m | BLOCKED | 3/7 | 0/2 |
| 1h | BLOCKED | 3/7 | 0/2 |

→ Nur 5m ist deploy-fähig (mit Marketing-Transparenz wegen WR < 60% Soft-Target).

---

## 4. Decision (gelockt in ANN-011)

```
H1 (5m Sweet Spot)
  → ⚠️ TECHNISCH PASS (alle Schwellen erfüllt), aber product_grade_C statt A/B
  → KONSEQUENZ: 5m wird V1-Default-TF, Marketing muss session-Konzentration kommunizieren

H2 (15m als Conservative-Profil)
  → ❌ FAIL (PF 1.23 < 1.5, MDD 34%, in-sample-Schwäche)
  → KONSEQUENZ: Conservative-Profil wird KEIN TF-Switch, sondern Tier-Cutoff auf 5m

H3 (30m/1h ausschließen)
  → ✅ PASS (beide PF < 1.5 in-sample, MDD > 100%)
  → KONSEQUENZ: 30m/1h nicht in V1; auch nicht in V1.5 ohne Re-Research

H4 (Pooled > Single-TF)
  → ✅ TECHNISCH PASS (Lift +0.08 bis +0.20 auf allen 4 TFs)
  → KONSEQUENZ: Pooled-Approach wird in V1.5/V2 erwogen, NICHT in V1 (Single-Modell-Simplicity)

H5 (1h Top-3%-Cutoff)
  → ❌ FAIL (PF blieb 0.98, weit unter 1.5)
  → KONSEQUENZ: 1h ist mit keinem Cutoff-Trick rettbar
```

**FINAL V1-DECISION:**
- **Default-TF:** 5m
- **Supported TFs in V1:** nur 5m
- **User-Profile-Mapping:** verschiedene Tier-Cutoffs auf 5m (NICHT verschiedene TFs)
- **Aggressive** → Standard-Tier (Top 10%)
- **Balanced** → High-Tier (Top 3%)
- **Conservative** → Premium-Tier (Top 1%)

→ Vollständige Konsequenzen in [ANN-011](../docs/decisions/ANN-011-v1-timeframe-and-profile-setup.md).

---

## 5. Konsequenz (umgesetzt in diesem Commit-Batch)

- ✅ `docs/decisions/ANN-011-v1-timeframe-and-profile-setup.md` — V1 TF-Lock + Profile + User-Settings-Whitelist
- ✅ `docs/roadmap.md` — Phase C ABGESCHLOSSEN, Phase D (NB15 Pine-Generator) ACTIVE
- ✅ `docs/model_registry.md` — FX-Modell-Slot mit `tf: '5m'` und Quality-Anchor-Status gelocked
- ✅ `docs/pine_router_design.md` — Single-TF-V1-Logic dokumentiert (Pine zeigt Warning auf nicht-5m-Charts)
- ✅ `docs/decisions/README.md` — ANN-011 in Index aufgenommen
- ✅ `HANDOFF.md` Section 16 + 16a + 19 aktualisiert

### Offene Research-Items (separat, NICHT V1-blockend)

| ID | Item | Priorität |
|---|---|---|
| R-12 | 15m-Anomalie: In-Sample 1.23 vs Hold-Out 1.83 (verdient eigene Untersuchung) | mittel — V1.5-Kandidat |
| R-13 | NY-Session-Konzentration: 66.6% — Feature-Bug oder echter Markt-Effekt? | hoch — Marketing-relevant |
| R-14 | Tier-Cutoff-Konvergenz: Standard- und High-Tier kollabieren auf 5m | hoch — UX-blockend |
| R-15 | WR-Boost-Suche: 57% → 60%+ ohne PF-Verlust? Optuna-Tuning | niedrig — V1.5 |

---

## Phase C Thresholds — sollen in `core/config.py` aufgenommen werden

Vorschlag für `PHASE_C_THRESHOLDS` constant:

```python
PHASE_C_THRESHOLDS = {
    # H1 — 5m als V1-Default
    "h1_min_premium_pf_holdout":   2.0,   # auf Hold-Out-Symbolen
    "h1_max_stability_cv":         0.20,
    "h1_max_drawdown":             0.18,
    "h1_min_trades_per_day":       3.0,

    # H2 — 15m als Conservative
    "h2_min_premium_pf":           1.5,
    "h2_max_stability_cv":         0.15,
    "h2_min_trades_per_day":       1.0,

    # H3 — Exclude 30m/1h
    "h3_exclude_threshold_pf":     1.5,   # unter diesem PF strict ausschließen

    # H4 — Pooled beats Single-TF
    "h4_min_pooled_lift":          0.0,   # mindestens nicht schlechter
    "h4_required_tf_count":        3,     # mindestens 3 von 4 TFs

    # H5 — Cutoff-Variation
    "h5_relaxed_cutoff_premium":   0.97,  # top 3% statt top 1%
    "h5_min_trades_per_year":      30,
}
```

---

## Output-Pfade (für NB14-Code)

```
/results/nb14/
├── metrics/
│   ├── per_tf_premium_metrics_{date}.csv
│   ├── per_tf_holdout_{date}.csv
│   └── per_tf_yearly_stability_{date}.csv
├── shap/
│   ├── shap_per_tf_{date}.csv
│   └── shap_top_features_diff_{date}.csv
├── summaries/
│   ├── tf_comparison_summary_{date}.csv
│   ├── pooled_vs_single_tf_{date}.csv
│   ├── cutoff_variation_1h_{date}.csv
│   └── nb14_full_snapshot_{date}.json
└── config_snapshots/
    └── {EXPERIMENT_ID}_config.json
```

---

## Bekannte Limitierungen

1. **NB14 testet NUR FX-Modell.** Multi-Asset-TF-Vergleich kommt erst wenn Crypto/Indices-Modelle gebaut sind (V2-Phase).
2. **4h ist optional** und nur als Sanity-Check — Daten-Volumen wird knapp (geschätzt ~10k bars/symbol vs 470k auf 5m).
3. **Pooled-Modell-Test (H4) erhöht Compute-Budget** — wenn nicht in Single-Run möglich, in NB14b auslagern.
