# Roadmap — Phasen A bis E

**Strategische Prämisse (2026-05-27 reaffirmiert):**
Wir optimieren auf **Robustheit, Cross-Asset-Generalisierung, Multi-Timeframe-Stabilität und langfristige Produktqualität** — NICHT auf den besten Einzelmarkt-PF oder den schnellsten Release. FX-only PF 2.015 aus NB11 bleibt **Forschungs-Baseline**, nicht Produktziel.

Jede Phase muss abgeschlossen sein, bevor die nächste startet. Phasen-Ergebnisse landen als JSON in `/results/` und als Bericht in `/research/`.

---

## Phase A — Model Battery (NB12) ✅ ABGESCHLOSSEN 2026-05-27

**Frage:** Welches Modell generalisiert am besten unter identischen Walk-Forward-Splits?

**Vergleich auf NB11-Best-Config (FX-only, 27 Features):**
- LightGBM (Pine-budget: 30 trees, depth 3) — Baseline
- XGBoost (gleiche Constraints) — Pine-exportierbar
- CatBoost (gleiche Constraints) — research-only, NICHT Pine-exportierbar
- Voting Ensemble (Mittelwert der 3 Probabilities)
- Consensus-Filter (alle 3 müssen zustimmen)

**Entscheidungskriterien:**
1. Premium-Tier PF auf in-sample TEST
2. Premium-Tier PF auf GBPUSD Hold-Out (wichtigster Test)
3. Per-Year Stability CV (kein Jahr darf brechen)
4. Pine-Export-Eignung

**Schwellenwert:** Anderes Modell als LightGBM nur, wenn `Premium-PF-Lift ≥ +0.05` UND Pine-exportierbar.

**Output:**
- `/results/json_exports/nb12_model_battery_{date}.json`
- `/research/model_battery_results.md` (Interpretation der Zahlen)

**Status:** ✅ Run abgeschlossen 2026-05-27. **Verdict: LightGBM bleibt V1-Modell.** Kein Pine-fähiges Modell schlägt LGBM um ≥ +0.05 PF. **Strategische Erkenntnis:** Consensus-Filter (alle 3 Modelle stimmen zu) liefert PF 2.93 auf GBPUSD-Hold-Out vs LGBM-Alone 2.54 — reserviert für V1.5-Backend.

Volle Analyse: [/research/model_battery_results.md](../research/model_battery_results.md).

---

## Phase B — Cross-Asset Generalization (NB13) 🟡 NEXT — ACTIVE

**Frage:** Welche Features generalisieren über Asset-Klassen, welche sind asset-spezifisch?

**Setup:**
- Phase-A-Sieger als Trainings-Modell
- Inferenz auf: BTC, ETH, SOL (Crypto), SPY, QQQ (Indices — Polygon-Aktivierung nötig), USO/Gold
- KEIN Retraining auf neuen Assets — pure Out-of-Distribution-Test

**Forschungsfragen:**
- Welche Features generalisieren? (SHAP-Vergleich pro Asset-Klasse)
- Welche Assets brechen? (PF < 1.3 markiert "no edge")
- Wie stark ist die Universalitäts-Strafe? (Mean-PF über Klassen vs FX-only)
- Welche Features sind asset-spezifisch? (Hohe SHAP-Varianz zwischen Klassen)

**Vorbedingung:** Polygon.io-Aktivierung ($29/Monat) — separate Nico-Entscheidung.

**Output:**
- `/results/per_symbol_metrics/nb13_cross_asset_{date}.json`
- `/research/asset_generalization.md`

---

## Phase C — Multi-Timeframe Comparison (NB14) ⚪ NEXT+1

**Frage:** Welche Timeframes liefern die stabilsten OOS-Ergebnisse?

**Vergleich:** 5M, 15M, 30M, 1H, 4H als Primary-TF

**Forschungsfragen:**
- Welche TFs generalisieren am besten?
- Welche liefern die stabilsten OOS-Ergebnisse?
- Wo ist Noise am geringsten?
- Welche TF/Asset-Kombinationen sind dauerhaft tot?

**Vorbedingung:** `core/config.py PRIMARY_TIMEFRAMES` muss 30M unterstützen (aktuell evtl. unvollständig).

**Output:**
- `/results/benchmark_tables/nb14_per_tf_{date}.csv`
- `/research/timeframe_comparisons.md`

---

## Phase D — Architecture Decision (NB15) ⚪ NEXT+2

**Variante A:** Universal-Modell — ein Modell für alle Asset-Klassen × TFs
**Variante B:** Core-Modell + per-Cluster Kalibrierung (VAL-derived cutoffs pro Asset-Klasse)
**Variante C:** Mehrere Spezialmodelle + Pine-Router (basierend auf `syminfo.type`)

**Entscheidungs-Matrix (Priorität von oben nach unten):**
1. Mean PF über Asset-Klassen
2. Min PF pro Asset-Klasse (Threshold: ≥ 1.3)
3. Stability-CV (max 0.25)
4. Pine-Code-Complexity (Linien, Ops/Bar)
5. Maintenance-Burden (Anzahl zu retrainender Modelle pro Monat)

**Output:**
- `/results/json_exports/nb15_architecture_decision_{date}.json`
- `/research/architecture_comparison.md` (wird angelegt wenn Phase D startet)
- `/docs/architecture.md` Update mit gewählter Variante

---

## Phase E — Pine Export + Backtest UI (NB09 / NB16 / NB17) ⚪ ZULETZT

**Erst nach Phase A–D abgeschlossen.** Vorher kein Pine-Code-Generator.

**Deliverables:**
- NB09: Tree-to-Pine Cascade-Generator (LightGBM/XGBoost)
- NB16: Backtest-Widget-Design (Trade-Boxes, PF/WR/MDD-Dashboard, Profile-Switching)
- NB17: Final Pine Compilation + bit-exact Validation gegen Python-Predictions

**User-Features:**
- BUY/SELL Labels + Entry-Line + TP/SL-Boxen
- 3 Profile (Conservative / Balanced / Aggressive)
- Limitierte sichere Parameter-Slider (Anti-Curve-Fitting)
- Historische Trade-Visualisierung
- PF/WR/Avg-R/MDD-Anzeige pro aktuellem Chart/TF

---

## Phase F (V1.5+) — Hybrid Backend (post-launch)

Nach V1-Launch + User-Feedback. Pine bleibt der Runtime, Backend retrainiert monatlich, neue Pine-Versionen werden auto-deployed.

## Phase G (V2) — Full Backend

ML-Inferenz auf Cloud-Server, Webhooks an TradingView, Web-Dashboard, Continuous Learning aus Signal-Outcomes.

---

## Was wir NICHT tun

- ❌ Kein NB09 (Pine Generator) vor Phase D Abschluss
- ❌ Keine Asset-Spezialisierung "weil EURUSD besonders gut funktioniert"
- ❌ Kein Release-Pressure — Quality > Speed
- ❌ Keine Features ohne `≥ +0.05` PF-Lift in OOS-Ablation
- ❌ Keine theoretischen ML-Konzepte ohne empirische Evidenz

Diese Negativliste ist genauso wichtig wie die Positiv-Roadmap.
