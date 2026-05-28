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
| EXP-009 | Per-Asset-Klasse SHAP-Verteilung | NB13 ✅ ABGESCHLOSSEN | ⇒ NB13 belegt: SMC-Features identisch verteilt aber semantisch nicht prädiktiv auf Crypto |
| EXP-010 | Per-TF SHAP-Verteilung | NB14 ✅ ABGESCHLOSSEN | ⇒ `hour_sin` Top-1 auf 5m/15m/30m, verschwindet auf 1h (dort `adx_14` Top-1) |
| EXP-011 | Order-Book-Imbalance (nur für Backend V2) | V2 | Erwarte signifikanter Lift wenn Daten verfügbar |
| EXP-012 | Sentiment-Daten (Twitter/Reddit) | V2+ | Spekulativ — Datenqualität fragwürdig |
| **R-12** | **15m-Anomalie: In-Sample 1.23 vs Hold-Out 1.83** | V1.5-Research | Mögliche Ursachen: Sampling-Bias, Asset-Mix, Trainings-Period — verdient eigene Untersuchung |
| **R-13** | **NY-Session-Konzentration: 66.6% aller Premium-Signale** | hoch (Marketing-relevant) | Feature-Bug oder echter Markt-Effekt? Decomposition-Test pro Session |
| **R-14** | **Tier-Cutoff-Konvergenz: Standard- und High-Tier kollabieren auf 5m** | hoch (V1 UX-blockend) | VAL-Verteilung-Analyse + Re-Stratifikation vor V1-Release |
| **R-15** | **WR-Boost-Suche 57% → 60%+ ohne PF-Verlust** | V1.5 | Optuna-Tuning der Hyperparams im Pine-Budget |
| **R-20** | **Training-Pool-Breite als Behavioral-Stability-Treiber** (NB14f v1 → ANN-015) | hoch (V1-blockend) | NB14f v2 mit erweitertem Pool (NZDUSD ins Training, USDCAD ins Hold-Out). Wenn `signal_frequency_cv` < 0.30 + `holdout_pf_mean` ≥ 1.3 auf ≥ 2 Profilen → These bestätigt, Pool-Breite war Hebel. Wenn weiterhin FAIL → Eskalation zu Feature-Engineering oder Pair-Spezialisierung. |

**Hinweis zur R-Nummerierung:** R-11 = Quality-Anchor SOFT_ONLY (WR-Marketing) ist in HANDOFF Section 16a getrackt, hier nicht als Forschungs-Item geführt (es ist Marketing-Operationalisierung, kein Research-Plan). R-16 bis R-19 sind Risiken (kein Research) — in HANDOFF Section 16a getrackt.

---

## Research-Items aus NB14 (detailliert)

### R-12: 15m-Anomalie — In-Sample-Schwäche bei Hold-Out-Stärke

**Beobachtung NB14 Run 1 (2026-05-27):**
- 15m In-Sample-Premium-PF: **1.23** (BLOCKED durch Quality-Anchor strict)
- 15m Hold-Out-Premium-PF (3 Symbole gemittelt): **1.83** (würde Hold-Out-Schwelle 1.4 erfüllen)
- Min Hold-Out: 1.67

**Atypisches Pattern:** Üblicherweise verschlechtert sich Performance auf Hold-Out (klassisches Overfit). Hier ist das **umgekehrt** — Hold-Out outperformt In-Sample um +0.60 PF.

**Mögliche Ursachen (zu testen):**
1. **Symbol-Mix in Training:** EURUSD + USDJPY haben evtl. spezifisch schwierige 15m-Phasen während 2024 H2 – 2026 H1
2. **Periodischer Effekt:** Bestimmte Marktphasen (z.B. 2024 Q3 Yen-Intervention) verzerren EURUSD/USDJPY-Performance asymmetrisch
3. **Sampling-Bias:** VAL-Cutoffs (Top 1%) treffen auf 15m anders als auf 5m wegen Verteilungs-Asymmetrie
4. **Asset-Mix:** GBPUSD/AUDUSD/USDCHF könnten "saubere" 15m-Märkte sein, EUR/USD/JPY noisy

**Test-Plan (für V1.5-Research-Block):**
- Per-Symbol 15m Premium-PF auf EURUSD/USDJPY (In-Sample) — ist EINER der beiden der Underperformer?
- Per-Periode Premium-PF in 6-Monats-Buckets — gibt es ein "schlechtes Jahr" das den Mittelwert drückt?
- Cross-Validation auf 15m mit allen 5 FX-Symbolen rotierend — wenn Hold-Out konsistent besser ist, ist es echtes Pattern

**Wichtig:** Nicht für V1 deployen. Hold-Out 1.83 ist verlockend aber wir kennen die Ursache nicht. Locked Rule per ANN-006 Mantra.

---

### R-13: NY-Session-Konzentration (66.6%)

**Beobachtung NB14 (5m Premium):**
- NY-Session (13–22 UTC): **66.6% aller Signale**
- Asia: 5.0%
- London: 0.3% (!)
- LDN/NY-Killzone: 0.03%

Premium-Edge ist faktisch ein **NY-Session-Detector**. London nahezu null trotz hoher Liquidität — das ist unerwartet.

**Mögliche Erklärungen:**
1. **Dukascopy-Daten sind Bid-Side:** Spread-Asymmetrien während LDN-Session unterdrücken Triple-Barrier-Hits
2. **Echter Markt-Effekt:** USD-pairs reagieren am stärksten auf US-Daten (NY-Session)
3. **Volatilitäts-Cluster:** ATR-normalisierte Features triggern in High-Vol-NY-Bars öfter
4. **Feature-Bug:** `hour_sin` könnte mit anderen Features in NY-Hours kreuzkorrelieren

**Test-Plan:**
- Per-Session SHAP-Decomposition (welche Features dominieren in NY vs London?)
- Per-Session Win-Rate-Analyse (ist die Edge in NY tatsächlich höher oder gibt's nur mehr Signal-Volumen?)
- Dukascopy Ask-Side-Daten testen (gleicher Symbol, andere Side) — sollte den Bug-Verdacht ausschließen
- Vergleich mit unabhängiger Datenquelle (OANDA-Tick-Daten falls verfügbar)

**Marketing-Implikation falls echter Effekt:** "Optimiert für NY-Session" als ehrliche Positionierung, statt "All-Day Indicator" zu vermarkten.

---

### R-14: Tier-Cutoff-Konvergenz

**Beobachtung NB14 (5m):**
- Standard-Cutoff (Top 10% VAL): 0.4067
- High-Cutoff (Top 3% VAL): 0.4067 ← identisch!
- Premium-Cutoff (Top 1% VAL): 0.4096

**Problem:** Profile "Aggressive" (Standard) und "Balanced" (High) hätten **identische** Signal-Mengen. Das macht das 3-Profile-Konzept löchrig — User-UX ist beschädigt.

**Wahrscheinliche Ursache:** LightGBM-Probability-Output ist auf 5m bimodal/heavy-tailed verteilt. Die Top 10% und Top 3% haben fast denselben unteren Cut.

**Lösungsansätze (vor V1-Release zu validieren):**
1. **Logit-Transform vor Quantil:** Statt `np.quantile(proba, 0.9)` arbeiten wir auf `logit(proba)` — entzerrt die Verteilung
2. **Manual Cutoff-Stratifikation:** Cutoffs basierend auf "Wir wollen ~35 / ~10 / ~3.5 sigs/day" fest definieren statt aus Quantilen ableiten
3. **Re-Train mit `lambda_l1` regularization:** könnte die Probability-Verteilung glätten
4. **Verschiedene Test-Period-Splits:** Re-Sampling der VAL-Periode

**Sofortmaßnahme:** NB14b-Run nur für Cutoff-Recalibration. ~10 Minuten Aufwand, klärt R-14.

---

### R-20: Training-Pool-Breite als Behavioral-Stability-Treiber

**Beobachtung NB14f v1 (2026-05-28, commit `2845025`):**
- Per-Model Relative Cluster (ANN-014) hat technisch sauber funktioniert (keine 0-Trade-Bugs wie NB14e)
- ABER: Behavioral Stability FAILED auf allen 3 Profilen
  - Aggressive: `signal_frequency_cv = 0.45` (Threshold 0.30) FAIL
  - Balanced: `signal_frequency_cv = 0.77` FAIL, `mdd_relative_std = 0.83` (Threshold 0.50) FAIL
  - Conservative: `signal_frequency_cv = 0.74` FAIL, `holdout_pf_mean = 0.50` (Threshold 1.30) FAIL, `mdd_relative_std = 0.75` FAIL
- Per-Symbol Pair-Aggregat zeigt nur GBPUSD-Balanced mit PF ≥ 1.4 (1.41), AUDUSD + USDCHF unsupported
- Trade-Count-Variation zwischen Seeds: 939 (seed 42) / 386 (seed 1) / 401 (seed 7) Aggressive in-sample — 2.4× Range

**Hypothese (Nico-Lock 2026-05-28):** Trainings-Pool ist zu schmal (`EURUSD + USDJPY` only). Cluster-Mechanik braucht mehr Marktregime im Training um Cluster-Größen über Seeds zu stabilisieren. NB13 hat empirisch belegt dass FX-Edge generalisiert auf 5+ Symbole — aber mit `top-1%`-Cutoff, nicht Cluster-Cutoff. Cluster-Cutoffs sind breiter und stellen höhere Anforderungen an Pool-Diversität.

**Test-Plan (ANN-015):**
- FX_TRAIN_SYMBOLS: + NZDUSD (Asia-Pacific Session, RBNZ-Macro, Antipoden-Pair zu AUDUSD)
- FX_HOLDOUT_SYMBOLS: + USDCAD (NY-Overlap, Öl-Macro)
- NB14f komplett re-runnen mit identischem Setup sonst (Features, Hyperparams, Mechanik unverändert)
- Erwartung: signal_frequency_cv sinkt unter 0.30, holdout_pf_mean steigt über 1.3, hour/session-Dominanz schwächer

**Wichtig (Nico-Direktive):** Wir interpretieren NB14f v1 nicht als "Modell broken". Frame ist "Produkt-Robustheits-Stabilisierung läuft". Grundmodell hat echten FX-Edge (NB13 belegt). Wir testen jetzt sauber ob Pool-Breite die fehlende Variable ist BEVOR wir auf Feature-Engineering oder Pair-Spezialisierung pivotieren.

**Fail-Eskalation (falls Re-Run auch FAILED):**
1. Entweder FX braucht wirklich Pair-Spezialisierung (R-19 als V1-Standard)
2. Oder die aktuelle Cluster/Tiering-Mechanik ist grundsätzlich zu fragil (Feature-Engineering NB16 oder Optuna)

→ Eskalation nicht vorab entscheiden, mit Daten aus Re-Run.

---

### R-15: WR-Boost-Suche

**Beobachtung NB14 (5m Premium):**
- In-Sample WR: 57.2%
- Soft-Anchor-Target (ANN-010): 60.0%
- Gap: -2.8pp

Quality-Anchor SOFT_ONLY weil WR nicht erreicht. PF 2.0 + niedrige MDD + stabile CV gleichen das aus für die Strict-Schwellen — aber Marketing-Sprache muss WR ehrlich kommunizieren.

**Anmerkung:** Hold-Out WR ist **60.9%** (über Target!). Das ist ein weiteres Indiz dass der WR-Wert maßgeblich vom Training-Symbol-Mix abhängt.

**Test-Plan (V1.5-Research):**
- Optuna-Hyperparameter-Search mit WR als Optimierungsziel, PF/MDD/CV als Constraints
- Loss-Function-Variation: focal loss statt binary_logloss (klassen-imbalanced)
- Feature-Engineering: zusätzliches Filtering vor LGBM-Stage (z.B. confidence-stratifiziertes Re-Sampling)

**Wichtig:** Nicht V1-blockend. Marketing-Sprache "Win Rate 57% in-sample, 61% auf Hold-Out" ist ehrlich und stark genug.

---

## Methodische Standards für neue Ablations

1. **Identische Walk-Forward-Splits** (TRAIN_END, VAL_END constants in `core/config.py`)
2. **Identische Hyperparameter** beim Vergleich
3. **VAL-derived Cutoffs** (nie TEST!)
4. **Mindestens 30 Trades pro Tier** für valide Statistiken
5. **Per-Year Stability prüfen** — wenn ein Feature nur in einem Jahr funktioniert, ist es Noise
6. **SHAP UND Ablation** — beide nötig (SHAP allein nicht hinreichend wegen feature-correlation)
