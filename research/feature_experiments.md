# Feature Experiments — Ablation History

Chronologische Sammlung aller Feature-Experimente. Format: was getestet, wann, OOS-Effekt, Verdict.

**Locked Rule:** Kein Feature wird ins V1-Modell aufgenommen, wenn der OOS-PF-Lift in Ablation < +0.05 ist.

---

## Aktive Features (NB11-Winner, 27 Features)

Siehe [/docs/feature_registry.md](../docs/feature_registry.md) für vollständige Liste mit SHAP-Werten.

---

## Ablation-Experimente

### EXP-001: SMC-Features entfernen (NB11, 2026-05)

**Hypothese:** SMC-Konzepte (FVG, BOS, CHoCH, OB) sind in der Trading-Community populär — sollten messbare Edge liefern.

**Setup:**
- Baseline: 37-Feature-Set MIT SMC-Features
- Ablation: gleicher Set OHNE SMC-Features
- Walk-Forward, identical splits

**Ergebnis:**
- Baseline PF: 1.56
- Ohne SMC PF: 1.80
- **Lift durch ENTFERNEN: +0.24** (positiv negative Test bestanden)

**Verdict:** ❌ SMC verworfen. Quote-würdig: "Wir wurden besser, indem wir Trader-Theorie weggeworfen haben."

> Lesson: Populäre Trading-Konzepte sind in der ML-Praxis oft noise. SHAP + Ablation regieren, nicht Plausibilität.

---

### EXP-002: HTF-Interaction-Features hinzufügen (NB11)

**Hypothese:** `htf_ltf_agree_bull` und Verwandte erfassen Multi-TF-Übereinstimmung, sollten Premium-PF heben.

**Setup:**
- Baseline: 22 Features ohne HTF-Interactions
- Mit HTF-Interactions: 27 Features

**Ergebnis:**
- Baseline PF: ~1.95
- Mit HTF PF: 2.015
- **Lift: +0.06** (knapp über Threshold)

**Verdict:** ✅ HTF-Interactions behalten. Bestanden den +0.05-Threshold.

---

### EXP-003: Macro-Features (VIX/DXY/TNX) testen (NB02)

**Hypothese:** Macro-Kontext sollte Intraday-Predictions verbessern, besonders in Risk-On/Risk-Off-Regimen.

**Setup:**
- Daily VIX/DXY/TNX als Features (mit shift(1))
- 5M-Modell

**Ergebnis:**
- SHAP-Werte: alle <0.001 → effectively dead
- Kein PF-Effekt messbar

**Verdict:** ❌ Macro-Daily für Intraday verworfen. Bleibt in `core/features/macro.py` für eventuelle Daily-Modelle V2+.

> Lesson: Sampling-Frequency-Mismatch tötet Edge. Daily-Macro hilft Daily-Predictions, nicht 5M-Predictions.

---

### EXP-004: Volume-Features (NB02 → NB11)

**Tests:**
- `volume_z_score` — Z-Score über 20-bar rolling mean
- `rvol_20` — Volume / 20-bar mean
- Raw `volume` — verworfen, nicht ATR-normalisiert genug

**Ergebnis:**
- `volume_z_score` SHAP-mittel, behält Edge
- `rvol_20` SHAP-mittel, parallel zu Z-Score, behalten (geringe Redundanz okay bei 30 Trees)
- Raw `volume` SHAP-dead

**Verdict:** ✅ Volume-Z + RVOL behalten, raw volume raus.

---

### EXP-005: Session-Features (NB11)

**Hypothese:** Trading-Stunden haben markant unterschiedliche Vola/Liquidität → sollten Edge erzeugen.

**Tests:**
- `hour_sin` / `hour_cos` (zyklisch encoded)
- `session_london` / `session_ny` / `session_asia` (binary flags)

**Ergebnis:**
- `hour_sin` / `hour_cos` SHAP-hoch → behalten
- Binary session-flags SHAP-mittel, aber redundant mit cyclical encoding

**Verdict:** ✅ Cyclical encoding behalten, binary flags weniger wichtig (in `core/features/session.py` immer noch verfügbar für Tests).

---

### EXP-006: Combined-Regime-Features (NB11)

**Tests:**
- `both_rsi_oversold` (LTF + HTF beide oversold)
- `both_rsi_overbought`
- `both_high_vol`, `both_low_vol`
- `pullback_in_bull`, `pullback_in_bear`

**Ergebnis:** Alle SHAP-mittel, gemeinsam +0.08 PF in Ablation.

**Verdict:** ✅ Alle behalten als Gruppe (einzeln zu schwach, zusammen relevant).

---

### EXP-007: 37-Feature-Set vs 27-Feature-Set (NB05 → NB11)

**Hypothese:** Mehr Features = mehr Information = besser? Nein.

**Setup:**
- 37 Features (NB05-Pool inkl. SMC, mehr Volume, mehr Macro)
- 27 Features (NB11-Reduktion auf SHAP-relevante)

**Ergebnis:**
- 37 Features PF: 1.14
- 27 Features PF: 2.015
- **Lift durch REDUKTION: +0.875**

**Verdict:** ✅ Reduktion lohnt sich massiv. 30 Trees können 27 Features deutlich besser lernen als 37.

> Lesson: Pine-Budget zwingt uns zu disciplined feature selection, was sich auch im OOS auszahlt. "Mehr Features = besseres Modell" ist falsch bei begrenzter Tree-Capacity.

---

### EXP-008: Voting-Ensemble in NB06

**Setup:** LightGBM + XGBoost + LogReg, Mittelwert der Probabilities.

**Ergebnis:**
- Single LightGBM Premium-PF: 1.79
- Voting Premium-PF: 1.06

**Verdict:** ❌ Voting verworfen — schlechter als Einzelmodell. Wahrscheinlich weil LogReg auf einem Probleme mit High-Cardinality-Features hatte.

**Hinweis:** NB12 testet Voting nochmal mit anderen Komponenten (LGBM+XGB+CatBoost), evtl. andere Outcome.

---

## Pending Experiments (zu testen)

| ID | Experiment | Wann | Erwartung |
|---|---|---|---|
| EXP-009 | Per-Asset-Klasse SHAP-Verteilung | NB13 (Phase B) | Manche Features generalisieren, andere asset-spezifisch |
| EXP-010 | Per-TF SHAP-Verteilung | NB14 (Phase C) | Erwarte: Session-Features hoch auf 5M/15M, niedrig auf 4H |
| EXP-011 | Order-Book-Imbalance (nur für Backend V2) | V2 | Erwarte signifikanter Lift wenn Daten verfügbar |
| EXP-012 | Sentiment-Daten (Twitter/Reddit) | V2+ | Spekulativ — Datenqualität fragwürdig |

---

## Methodische Standards für neue Ablations

1. **Identische Walk-Forward-Splits** (TRAIN_END, VAL_END constants in `core/config.py`)
2. **Identische Hyperparameter** beim Vergleich
3. **VAL-derived Cutoffs** (nie TEST!)
4. **Mindestens 30 Trades pro Tier** für valide Statistiken
5. **Per-Year Stability prüfen** — wenn ein Feature nur in einem Jahr funktioniert, ist es Noise
6. **SHAP UND Ablation** — beide nötig (SHAP allein nicht hinreichend wegen feature-correlation)
