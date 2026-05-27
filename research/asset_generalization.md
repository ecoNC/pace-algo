# Asset Generalization — Phase B (NB13)

**Status:** 🟡 ACTIVE — NB13 als 12-Section-Forschungsplattform gebaut, wartet auf Colab-Run
**Decision-Framework:** Diese Datei nutzt das Pattern aus [/docs/_phase_decision_template.md](../docs/_phase_decision_template.md)
**Notebook:** [notebooks/13_cross_asset_generalization.ipynb](../notebooks/13_cross_asset_generalization.ipynb)

---

## NB13-Architektur (12 Sections)

Modulares Research-Framework, NICHT nur ein Experiment-Notebook:

| Section | Inhalt |
|---|---|
| **0** | Config + Experiment Registry — alles tracebar (EXPERIMENT_ID, GIT_COMMIT, RUN_DATE, Seeds) |
| **1** | Data Loading + Inventory Check — verifiziert welche Symbole × TFs verfügbar sind |
| **2** | Feature Engineering — extended features für alle Symbole × TFs (NB12-Pattern generalisiert) |
| **3** | Labeling Check — Class-Balance-Report pro Asset × TF |
| **4** | Walk-Forward Split Builder — identische Cutoffs über alle Asset-Gruppen |
| **5** | Model Training Loop (Pool × TF × Model) — `fx_train` und `universal` Pools |
| **6** | SHAP Analysis (Global / per Asset-Class / per TF / Consistency Score) |
| **7** | Cross-Asset Generalization Matrix — Pool × TF × Test-Asset → Premium-PF |
| **8** | Timeframe Comparison — welcher TF generalisiert am stabilsten? |
| **9** | Architecture Decision Engine — Auto-Scoring von H1/H5/H6 |
| **10** | Result Persistence (`/results/nb13/` mit Subordnern `metrics/`, `shap/`, `summaries/`, etc.) |
| **11** | Final Verdict — human-readable Conclusion + next steps |
| **12** | Auto-Push to GitHub (NB12-Pattern, `nb13`-tag) |

**Steuerung über Flags in Section 0:**
- `EXPERIMENTS_TO_RUN`: A/B/C/D/E pro Experiment togglebar
- `MODELS_TO_TRAIN`: Default `['LightGBM']` (schlanker MVP), erweiterbar auf XGB/CatBoost
- `TIMEFRAMES_USED`: Default `PRIMARY_TIMEFRAMES = ['5m', '15m', '30m', '1h']`
- `TRAIN_FRESH=True`, `LOAD_CACHE=False` — wissenschaftlich sauber per Nico-Lock

---

---

## Strategische Verschärfung nach NB12

NB12 hat **zwei** überraschende Signale geliefert die NB13 jetzt aufklären muss:

1. **XGBoost-Marginal-Lift auf Hold-Out (+0.135 PF):** Auf in-sample TEST sind LightGBM und XGBoost praktisch gleich, aber auf GBPUSD-Hold-Out ist XGBoost +0.135 PF besser. EIN Symbol = kein robustes Signal — wir wissen nicht, ob das systematisch ist oder GBPUSD-spezifisches Glück.

2. **Consensus-Filter-Lift auf Hold-Out (+0.39 PF):** Massiv, aber auch nur EIN Symbol. Wenn das auf Crypto/Indices/Gold hält → V1.5-Backend ist unverhandelbar. Wenn nicht → Consensus war Zufall, V1.5 macht nur Continuous Retraining (siehe [ANN-004](../docs/decisions/ANN-004-consensus-filter-v1.5-not-v1.md)).

**Beide Fragen müssen in NB13 quantitativ beantwortet werden, sonst überinterpretieren wir GBPUSD-Daten.**

---

## 1. Hypothese (für NB13)

### H1 (alt — bleibt): "FX-trainiertes Modell generalisiert eingeschränkt"

Mean-PF über alle Asset-Klassen wird messbar unter FX-only PF 2.0 liegen. Die "Universalitäts-Strafe" wird quantifizierbar.

**Schwelle für H1 = TRUE:** Mean Premium-PF über ≥4 Asset-Klassen liegt im Bereich 1.2–1.7.
**Schwelle für H1 = FALSE:** Mean Premium-PF über ≥4 Asset-Klassen liegt > 1.8.

### H2 (alt — bleibt): "Crypto bricht, FX-Cousins generalisieren"

Per-Asset-Rangfolge wird:
- Top: GBPUSD, USDCHF, EURJPY (FX-Familie) — PF > 1.5
- Mitte: SPY, QQQ (Indices) — PF 1.1–1.4
- Bottom: BTC, ETH (Crypto, andere Vola-Regimes) — PF < 1.1

### H3 (alt — bleibt): "Session-Features sind FX-spezifisch und brechen auf Crypto"

`hour_sin/cos` SHAP-Rang fällt auf Crypto deutlich ab (kein klares Session-Cycle bei 24/7-Markt).

### H4 (alt — bleibt): "Volatilitäts-Features generalisieren"

`realized_vol_20`, `atr_percentile_100` haben über alle Asset-Klassen ähnliche SHAP-Werte und tragen zur Edge bei.

### H5 🔥 (NEU nach NB12): "Consensus-Lift verallgemeinert sich"

Wenn der Consensus-Filter-Lift (LGBM+XGB+Cat alle drei) systemisch ist und nicht GBPUSD-spezifisches Ensemble-Glück, dann sollte er auf MINDESTENS 3 von 5 Asset-Klassen messbar Lift gegenüber LightGBM-Alone bringen.

**Schwelle für H5 = TRUE:** Consensus-Premium-Lift > +0.15 PF auf ≥3 von ≥5 getesteten Asset-Klassen.
**Schwelle für H5 = FALSE:** Consensus-Lift verschwindet auf 3+ Asset-Klassen (PF-Differenz <±0.05).

**Konsequenz wenn H5 = TRUE:** V1.5-Backend mit Consensus-API ist unverhandelbar, marketing-fähig.
**Konsequenz wenn H5 = FALSE:** Consensus war Zufall, V1.5 macht nur Continuous Retraining ([ANN-004](../docs/decisions/ANN-004-consensus-filter-v1.5-not-v1.md) muss revisited werden).

### H6 🔥 (NEU nach NB12): "XGBoost-Hold-Out-Lift verallgemeinert sich"

Wenn XGBoost auf GBPUSD systematisch besser als LightGBM ist (und nicht 1-Symbol-Glück), sollte es das auf MINDESTENS 4 von 5 Asset-Klassen tun.

**Schwelle für H6 = TRUE:** XGBoost-Premium-Lift > +0.05 PF auf ≥4 von ≥5 getesteten Asset-Klassen.
**Schwelle für H6 = FALSE:** XGBoost-Lift verschwindet oder kehrt sich um auf 2+ Klassen.

**Konsequenz wenn H6 = TRUE:** XGBoost wird zum V1-Modell statt LightGBM. ADR-Update + NB17 Pine-Generator XGBoost-spezifisch.
**Konsequenz wenn H6 = FALSE:** LightGBM bleibt V1, Verdict aus NB12 final.

---

## 2. Experiment (Setup für NB13)

| Element | Wert |
|---|---|
| Trainings-Daten | FX-only (EURUSD, USDJPY) — wie NB11/NB12 |
| Trainings-Pool | NICHT erweitert, Phase-A-Sieger-Modell weiterverwenden |
| Test-Daten (alle OOS, `>= VAL_END`) | Crypto: BTC, ETH, SOL · Indices: SPY, QQQ (Polygon nötig) · FX Hold-Out: GBPUSD · Gold: XAUUSD |
| Retraining | KEINS — pure Out-of-Distribution-Inferenz |
| Modelle inferenziert | LightGBM (V1-Sieger) + XGBoost + CatBoost (für Consensus-Test) |
| Tier-Cutoffs | TWO Varianten parallel: (a) FX-VAL-derived, (b) Per-Asset-VAL-derived |
| Evaluation | Per-Asset PF/WR/Trade-Count + Per-Asset Consensus vs LGBM-Alone |
| SHAP | Pro Asset (TreeExplainer) — Feature-Rang-Stabilität messen |

**Vorbedingung — kritisch:**
- Polygon.io-Aktivierung für SPY/QQQ ($29/Monat) — siehe HANDOFF Section 16 Item 5
- Alternativ: starte ohne Polygon, nur Crypto + GBPUSD + Gold + sekundäre FX-Cousins (USDCHF, EURJPY)

**Schwellen für Decision-Robustheit:**
- Min Trades pro Asset/Tier für valide Aussage: **200** (sonst "data insufficient", nicht "edge missing")
- Min Asset-Klassen für H5/H6-Verallgemeinerung: **3 von 5** bzw. **4 von 5** (oben definiert)

---

## 3. Resultat (wird nach NB13-Run gefüllt)

⏳ TBD nach Colab-Run.

Wird folgende Tabellen enthalten:

**A. Per-Asset PF (LightGBM-Alone, Premium-Tier, FX-VAL Cutoffs):**

| Asset | Klasse | PF | WR | Trades | H1/H2-Klassifikation |
|---|---|---:|---:|---:|---|
| GBPUSD | FX | 2.54 | 62.8% | 2366 | (Referenz aus NB12) |
| BTC | Crypto | ? | ? | ? | ? |
| ... | ... | ... | ... | ... | ... |

**B. Per-Asset Consensus vs LGBM-Alone (Premium-Tier):**

| Asset | LGBM PF | Consensus PF | Lift | H5-Klassifikation |
|---|---:|---:|---:|---|
| GBPUSD | 2.54 | 2.93 | +0.39 | (Referenz aus NB12) |
| BTC | ? | ? | ? | ? |
| ... | ... | ... | ... | ... |

**C. Per-Asset XGBoost vs LightGBM (Premium-Tier):**

| Asset | LGBM PF | XGB PF | Lift | H6-Klassifikation |
|---|---:|---:|---:|---|
| GBPUSD | 2.54 | 2.67 | +0.13 | (Referenz aus NB12) |
| BTC | ? | ? | ? | ? |
| ... | ... | ... | ... | ... |

**D. SHAP-Rang-Stabilität pro Feature:**

| Feature | SHAP-Rang FX | SHAP-Rang Crypto | SHAP-Rang Indices | Std-Dev über Klassen |
|---|---:|---:|---:|---:|
| `hour_sin` | 2 | ? | ? | ? |
| `realized_vol_20` | 3 | ? | ? | ? |
| `htf_ltf_agree_bull` | 5 | ? | ? | ? |
| ... | ... | ... | ... | ... |

---

## 4. Decision (wird nach NB13-Run gefüllt)

⏳ TBD nach Colab-Run.

Decision-Matrix-Skelett:

```
H1 (universale Strafe quantifizierbar)
├── TRUE → erwarteten Effekt dokumentiert, NB15 macht Architektur-Wahl
└── FALSE (unerwartet wenig Strafe) → Universal-Modell-Variante in NB15 stark gewichten

H5 (Consensus generalisiert)
├── TRUE → V1.5-Backend mit Consensus ist unverhandelbar
└── FALSE → ANN-004 revisited, V1.5 nur Continuous Retraining

H6 (XGBoost systematisch besser)
├── TRUE → ADR-Update: V1-Modell wechselt von LGBM auf XGBoost. NB17 Pine-Generator XGB-spezifisch.
└── FALSE → LightGBM bleibt V1, NB12-Verdict final

Per-Asset-Cluster-Pattern (für NB15)
├── Klare Cluster mit ähnlichem PF → Variante B (Per-Cluster-Cutoffs) gewinnt
├── Random Mix → Variante A (Universal) oder C (Router) gewinnt
└── Crypto bricht hart → spezielles Crypto-Modell als V2-Feature einplanen
```

---

## 5. Konsequenz (vorbereitet, finalisiert nach NB13)

Wird folgende Files updaten:

- `/docs/model_registry.md` — V1-Sieger bestätigt oder gewechselt
- `/docs/decisions/ANN-004-consensus-filter-v1.5-not-v1.md` — Status bleibt Active oder wird Superseded
- `/docs/decisions/ANN-006-XX.md` (neu) — Per-Asset-Generalisierungs-Pattern dokumentieren
- `/docs/roadmap.md` — Phase B abgeschlossen, Phase C ACTIVE
- `/docs/feature_registry.md` — Neue Spalte "Generalisiert über Asset-Klassen?"
- `/research/shap_analysis.md` — Phase-B-Sektion mit echten Per-Asset-SHAP-Daten

---

## Output-Pfade (für NB13-Code)

Files die NB13 schreiben muss nach `/results/`:

- `per_symbol_metrics/nb13_per_asset_pf_{date}.csv`
- `per_symbol_metrics/nb13_consensus_per_asset_{date}.csv`
- `per_symbol_metrics/nb13_xgboost_vs_lgbm_per_asset_{date}.csv`
- `benchmark_tables/nb13_asset_class_means_{date}.csv`
- `json_exports/nb13_cross_asset_{date}.json` — full snapshot inkl. per-Asset-SHAP
