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

## Phase C — Multi-Timeframe Comparison (NB14) ✅ ABGESCHLOSSEN 2026-05-27

**Verdict:** Nur 5m ist V1-deploybar. Quality-Anchor SOFT_ONLY ✓ (alle 7 strict bestanden, 1/2 soft). 15m BLOCKED (PF 1.23, MDD 34%), 30m + 1h BLOCKED (PF < 1.05, MDD > 100%).

**5m Eckdaten:**
- Premium PF 2.00 (in-sample), 2.39 (Hold-Out auf 3 nie trainierten FX-Symbolen)
- WR 57.2% in-sample → **60.9% Hold-Out** (Hold-Out outperformt = kein Overfit)
- MDD 2.9%, Stability CV 0.145
- 3.5 Premium-Signale/Tag/Symbol
- SHAP-Top-1: `hour_sin` (Time-of-Day Edge)
- Yearly PF 2024=1.79 → 2025=2.04 → 2026=2.52 (Edge wird besser)

**Wichtige Befunde:**
- 66.6% aller Premium-Signale fallen in die NY-Session (Research-Item R-13)
- Auf 1h verschwindet die `hour_sin`-Edge komplett — `adx_14` wird Top-1 (anderes Edge-Paradigma)
- Pooled-Modell schlägt Single-TF auf allen 4 TFs (+0.08 bis +0.20 PF) — Kandidat für V1.5+

**User-Profile-Mapping REVIDIERT:** Profile sind NICHT verschiedene TFs sondern verschiedene Tier-Cutoffs auf 5m. Aggressive=Standard / Balanced=High / Conservative=Premium. Locked in [ANN-011](decisions/ANN-011-v1-timeframe-and-profile-setup.md).

**Volle Analyse:** [/research/timeframe_comparisons.md](../research/timeframe_comparisons.md). **ADR:** [ANN-011](decisions/ANN-011-v1-timeframe-and-profile-setup.md).

---

## Phase D — Architecture Decision (NB15) 🟡 NEXT — ACTIVE

**Status nach NB13/NB14:** Architektur ist bereits gelockt via [ANN-009](decisions/ANN-009-multi-model-router-architecture.md) (Multi-Model Router). NB15 ist daher kein "A vs B vs C"-Entscheidung mehr, sondern **Architecture-Validation** für V1:

**Frage NB15:** Funktioniert das Router-Skelett im Pine-Code-Stub korrekt mit dem 5m-FX-Modell als einzigem aktiven Branch?

**Validation-Tasks:**
1. `core/router/pine_router_codegen.py` V1-Stub auf konkretes FX-Modell anwenden
2. Bit-exact Validation: Python-Probability == Pine-Probability (auf Test-Sample)
3. Pine-Budget-Check: tree-cascade + features + router-overhead < 5000 ops/bar
4. UI-Warning für nicht-5m-Charts korrekt eingebaut
5. Asset-Detection-Stub für FX vs (Crypto/Indices/Commodity = "Coming Soon")

**Output:**
- `/results/nb15/pine_validation_{date}.json`
- `/docs/architecture.md` Update mit V1-Pine-Architektur final
- Pine-Code-Skelett in `deploy_pine/pace_algo_v1.pine` (Draft)

---

## Phase E — Pine Export + Backtest UI (NB09 / NB16 / NB17) ⚪ NEXT+1

**Erst nach Phase D abgeschlossen.** Vorher kein vollständiger Pine-Code-Generator.

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
