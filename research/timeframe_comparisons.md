# Timeframe Comparisons — Phase C (NB14)

**Status:** 🟡 NEXT — Plan + Hypothesen für NB14, verfeinert nach NB13-Verdict (Crypto-Pivot)
**Decision-Framework:** [/docs/_phase_decision_template.md](../docs/_phase_decision_template.md)
**Architektur-Lock:** [ANN-009 Multi-Model Router](../docs/decisions/ANN-009-multi-model-router-architecture.md) — NB14 fokussiert auf **FX-Modell** (V1-Scope), Crypto/Indices/Commodity separat
**Quality-Anchor:** [ANN-010](../docs/decisions/ANN-010-quality-anchor.md) — Premium PF ~2.0 ist Vergleichspunkt

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

## 3. Resultat (wird nach NB14-Run gefüllt)

⏳ TBD nach Colab-Run.

Wird folgende Sections enthalten:

**A. Per-TF Premium Metrics (in-sample TEST):**

| TF | PF | WR | ExpR | MDD | Stability CV | Trades/Tag/Symbol |
|---|---:|---:|---:|---:|---:|---:|
| 5m | ? | ? | ? | ? | ? | ? |
| 15m | ? | ? | ? | ? | ? | ? |
| ... | ... | ... | ... | ... | ... | ... |

**B. Per-TF Hold-Out (GBPUSD/AUDUSD/USDCHF gemittelt):**

| TF | Hold-Out Premium PF | Hold-Out WR | Trades-Drop vs in-sample |
|---|---:|---:|---:|
| 5m | ? | ? | ? |
| ... | ... | ... | ... |

**C. Per-TF SHAP-Top-5:**

| TF | Top-1 | Top-2 | Top-3 | Top-4 | Top-5 |
|---|---|---|---|---|---|
| 5m | hour_sin | ema_20_dist_atr | dist_to_swing_low | ... | ... |
| ... | ... | ... | ... | ... | ... |

**D. Pooled vs Single-TF (H4):**

| TF | Single-TF PF | Pooled-Modell PF auf gleichem TF | Lift |
|---|---:|---:|---:|
| 5m | ? | ? | ? |
| ... | ... | ... | ... |

---

## 4. Decision (wird nach NB14-Run gefüllt)

⏳ TBD nach Colab-Run.

Decision-Matrix-Skelett:

```
H1 (5m Sweet Spot)
├── PASS → 5m bleibt V1-Default-TF, Profile "Balanced"
└── FAIL → höhere TFs neu evaluieren

H2 (15m als Conservative-Profil)
├── PASS → 15m wird V1-Profile "Conservative"
└── FAIL → User-Profile-Konzept wird ohne 15m gebaut

H3 (30m/1h ausschließen)
├── PASS → 30m+1h nicht in V1, vielleicht V1.5
└── FAIL → mindestens einer der beiden bleibt drin

H4 (Pooled > Single-TF)
├── PASS → V1-Pine embeds POOLED-Modell, Inferenz auf jeglichem TF
└── FAIL → V1-Pine embeds Single-TF-Modell (5m), nur für 5m-Charts

H5 (Cutoff-Variation auf 1h)
├── PASS → Per-TF-Cutoffs werden in V1 unterstützt
└── FAIL → Single-Cutoff (top 1% VAL) bleibt für alle TFs
```

---

## 5. Konsequenz (vorbereitet, finalisiert nach NB14)

Wird folgende Files updaten:

- `docs/decisions/ANN-011-XX.md` (neu) — finale V1-TF-Wahl als ADR
- `docs/roadmap.md` — Phase D (NB15) startet mit klarem TF-Mandat
- `docs/model_registry.md` — V1 FX-Modell TF-Setup gelocked
- `docs/pine_router_design.md` — TF-Handling in Pine-Code (single oder multi-TF Modell)
- `research/shap_analysis.md` — Per-TF SHAP-Sektion mit Daten

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
