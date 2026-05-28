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

**User-Profile-Mapping (FINALE V1-Version per [ANN-012](decisions/ANN-012-v1-tier-architecture-premium-core-plus-filters.md)):** Probability-Cutoff-Profile wurden durch NB14b falsifiziert (alle 3 Strategien failed, Aggressive+Balanced kollabieren auf identischen Cutoff). **Neue Mechanik: Premium Core + Secondary Filters.**

| Profil | Filter-Stack | Sigs/Tag |
|---|---|---:|
| Aggressive | Premium pur | ~3.5 |
| Balanced | Premium + HTF-Confirmation | ~3.0 |
| Conservative | Premium + HTF-Confirmation + NY-Session | ~1.5 |

Alle Profile teilen denselben Premium-Cutoff (0.4096). Edge bleibt PF ~2.0 über alle Profile. NB14c (anstehend) validiert finale Sigs/Tag-Zahlen und schließt R-14 ab.

**Volle Analyse:** [/research/timeframe_comparisons.md](../research/timeframe_comparisons.md). **ADRs:** [ANN-011](decisions/ANN-011-v1-timeframe-and-profile-setup.md) (V1-TF + Whitelist), [ANN-012](decisions/ANN-012-v1-tier-architecture-premium-core-plus-filters.md) (Tier-Architektur).

---

## Phase C.5 — Secondary-Filter Validation (NB14c/d/e/f) ✅ DIAGNOSTIC ABGESCHLOSSEN 2026-05-28

**Iterations-Verlauf (volle Decision-Kette in [HANDOFF Section 19](../HANDOFF.md)):**

- **NB14c:** Filter-Validation lieferte widersprüchliche Ergebnisse über 3 Runs (0 Trades / PF 1.01 / 0 Trades). Stopped.
- **NB14d:** Pure Diagnostik → Verdict **Ultra-discrete Distribution** (top-3 Cluster 92.4%, stable + kalibriert). NB14b's `0.4096` als Phantom-Wert identifiziert.
- **NB14e:** Cluster-basierte Premium-Detection. Run lieferte seed=1 GBPUSD Hold-Out Balanced PF **3.50** — aber methodischer Bug entdeckt: globaler Mean-Cluster auf alle Seeds appliziert ergab 0-Trades auf seeds 42+7. **[ANN-013](decisions/ANN-013-cluster-based-premium-detection.md)** locked Cluster-Mechanik, **[ANN-014](decisions/ANN-014-per-model-relative-cluster-behavioral-stability.md)** korrigiert zu Per-Model Relative Cluster + Behavioral Stability.
- **NB14f (`2845025`):** Per-Model-Relative-Cluster + Behavioral-Stability-Check sauber implementiert. Verdict: **`all_profiles_behavioral_stable: false`** — `signal_frequency_cv` 0.45–0.77 (Threshold 0.30) und `holdout_pf_mean` 0.50–0.85 (Threshold 1.30) FAIL auf allen 3 Profilen. Pair-Aggregat: nur GBPUSD-Balanced erreicht PF ≥ 1.4 (1.41 bei n=293).

**Quality-Gate aus ANN-014 hat sauber gegriffen** — kein V1-Lock auf ein nicht-stabiles Modell. NB14f-Daten zeigen klar: das Modell hat echten Edge auf GBPUSD, aber Trainings-Pool ist zu schmal (`EURUSD + USDJPY` only) um stabile Cluster-Größen über Seeds zu produzieren.

---

## Phase C.6 — Training-Pool Expansion + Robustness Re-Validation 🟡 ACTIVE (ANN-015)

**Lock:** [ANN-015 V1 Training-Pool Expansion + Robustness Re-Validation](decisions/ANN-015-v1-training-pool-expansion-robustness-revalidation.md).

**Hypothese:** NB14f-Behavioral-Stability-FAIL ist Folge zu schmalen Trainings-Pools — nicht fundamentaler Architektur-Bug. NB13 hat FX-Generalisierung auf 5+ Symbolen belegt (`top-1%`-Cutoff). Cluster-basierte Cutoffs (breiter, ~2%) brauchen breiteren Pool um gleiche Robustheit zu erreichen.

**Setup:**
- `FX_TRAIN_SYMBOLS`: EURUSD, USDJPY, **+ NZDUSD**
- `FX_HOLDOUT_SYMBOLS`: GBPUSD, AUDUSD, USDCHF, **+ USDCAD**
- Feature-Set, Hyperparams, Cluster-Mechanik, Behavioral-Thresholds: **alle unverändert** (saubere isolierte Variable)

**Pipeline:**
1. NB01 re-run für NZDUSD + USDCAD Fetcher (Dukascopy)
2. NB04 re-run für Triple-Barrier-Labels auf neuen Symbolen × 4 TFs
3. NB14f re-run (komplett, mit erweitertem Pool)

**Pass-Kriterien (deterministisch in ANN-015 §3 dokumentiert):**
- `all_profiles_behavioral_stable: true` (alle 5 Behavioral-Metriken passed auf allen 3 Profilen)
- Mean Hold-Out Premium-PF ≥ 1.4 auf ≥ 3 von 4 Symbolen
- Pair-Tiering: ≥ 3 Symbole "supported" per ANN-014 §5

**Erwartete Laufzeit:** ~25–35 min Colab (NB01 ~10 min + NB04 ~5-10 min + NB14f ~12-15 min).

**Fail-Eskalation:** Architektur-Vertiefung (Feature-Engineering / Optuna / Pair-Spezialisierung als V1-Standard).

---

## Phase D — Pine-Router-V1-Validation (NB15) 🔴 BLOCKED auf Phase C.6 Pass

**Status nach NB13/NB14:** Architektur ist bereits gelockt via [ANN-009](decisions/ANN-009-multi-model-router-architecture.md) (Multi-Model Router). NB15 ist daher kein "A vs B vs C"-Entscheidung mehr, sondern **Architecture-Validation** für V1.

**Aktuelle Blockade:** ANN-015 lockt Phase D auf Phase C.6 Pass. Es macht keinen Sinn, Pine-Router gegen ein nicht-behavioral-stabiles Python-Modell zu validieren. NB15-Bau startet erst nach NB14f-v2-Pass.

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
