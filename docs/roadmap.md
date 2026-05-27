# Roadmap — Phasen A bis E + V-Releases

**Architektur-Pivot 2026-05-27 (gelocked):** "Universal UX + Specialized Intelligence" — Multi-Model Router ([ANN-009](decisions/ANN-009-multi-model-router-architecture.md)). NB13 belegt: Single-Universal-Modell funktioniert nicht (FX-Edge 2.49 / Crypto-Edge 0.99 random). V1 = FX-only mit Router-Skelett, V2 = Multi-Model aktiv.

**Strategische Prämisse:** Robustheit, Cross-Asset-Generalisierung, Multi-Timeframe-Stabilität, langfristige Produktqualität ([ANN-006](decisions/ANN-006-robustness-first-mantra.md) Mantra). FX-Premium-PF ~2.0 ist Quality Anchor ([ANN-010](decisions/ANN-010-quality-anchor.md)).

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

## Phase B — Cross-Asset Generalization (NB13) ✅ ABGESCHLOSSEN 2026-05-27

**Verdict:** FX-trainiertes Modell generalisiert SAUBER auf andere FX-Symbole (GBPUSD/AUDUSD/USDCHF Premium-PF 2.5+), bricht KOMPLETT auf Crypto (alle 5 Crypto-Symbole PF ≈ 1.0 = random). Architektur-Hint aus Auto-Decision-Engine: **Variante C (Router)**. Volle Analyse: [/research/asset_generalization.md](../research/asset_generalization.md). Locked in [ANN-008](decisions/ANN-008-fx-features-do-not-generalize-to-crypto.md).

**Konsequenz für V1-Marketing:** "Universal AI Trading Indicator" wird zu "AI Trading Indicator für FX Major Pairs". Crypto/Indices = V1.5/V2.

---

## Phase C — Multi-Timeframe Comparison (NB14) 🟡 NEXT — ACTIVE

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
