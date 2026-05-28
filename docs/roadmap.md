# Roadmap — FX als Reference Blueprint → Multi-Asset-Plattform

**Strategischer Pivot 2026-05-28 (gelocked):** [ANN-016 FX as Reference Blueprint](decisions/ANN-016-fx-as-reference-blueprint-industrialization-first.md). FX wird **NICHT V1-Shortcut** sondern **Core-Blueprint** — vollständig industrialisiert, dann auf Crypto/Indices/Commodity repliziert. **V1-Launch erst wenn ≥ 2 Asset-Klassen über denselben Blueprint laufen.**

**Architektur-Pivot 2026-05-27 (gelocked):** "Universal UX + Specialized Intelligence" — Multi-Model Router ([ANN-009](decisions/ANN-009-multi-model-router-architecture.md)). NB13 belegt: Single-Universal-Modell funktioniert nicht (FX-Edge 2.49 / Crypto-Edge 0.99 random).

**Strategische Prämisse:** Robustheit, Cross-Asset-Generalisierung, Multi-Timeframe-Stabilität, langfristige Produktqualität ([ANN-006](decisions/ANN-006-robustness-first-mantra.md) Mantra). FX-Premium-PF ~2.0 ist Quality Anchor ([ANN-010](decisions/ANN-010-quality-anchor.md)). Override-Discipline ([ANN-016](decisions/ANN-016-fx-as-reference-blueprint-industrialization-first.md) Lock 5): jeder Per-Pair/Asset/Regime-Override braucht statistical proof + market structure + OOS-Lift + reproducibility.

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

## Phase C.6 — Training-Pool Expansion + Robustness Re-Validation ✅ ABGESCHLOSSEN 2026-05-28 (ANN-015)

**NB14f-v2 Ergebnis (Run `nb14f_2026-05-28T12-47-45Z_81f2316`, commit `80bad05`):**

Pool-Expansion hat **deutlich geholfen** vs v1 (nur GBPUSD-Balanced supported → 3 von 4 Pairs sauber gestaffelt), aber **`all_profiles_behavioral_stable: false`** bleibt — **USDCHF ist strukturell anders**.

| Pair | Aggressive | Balanced | Conservative | Verhalten |
|---|---:|---:|---:|---|
| GBPUSD | 1.29 | 1.50 | 1.83 | ✓ sauber gestaffelt |
| AUDUSD | 1.42 | 1.83 | 1.97 | ✓ sauber gestaffelt |
| USDCAD | 1.13 | 1.33 | 1.59 | ✓ sauber gestaffelt |
| USDCHF | 0.97 | 0.63 | **0.17** | ✗ **invertiert** |

**Production-Seed:** seed=7, Cluster=0.40. Balanced/Conservative ho_pf 1.61 bei n=268 trades.

**ANN-015 Pass-Kriterien:**
- `all_profiles_behavioral_stable: true` — ✗ FAIL
- Mean Hold-Out PF ≥ 1.4 auf ≥ 3/4 (Balanced) — ✗ FAIL (nur 2/4)
- Pair-Tiering: ≥ 3 supported (Conservative) — ✓ PASS (3/4)

**Strategischer Reframe per [ANN-016](decisions/ANN-016-fx-as-reference-blueprint-industrialization-first.md) (Nico-Direktive 2026-05-28):**

USDCHF-Bruch ist **kein Bug sondern Architektur-Signal**. Filter-Stack lernt echte Marktstruktur (CHF reagiert auf SNB / EU statt NY). Statt wegoptimieren oder Pair-Tier-V1-Lock → **vollständige FX-Industrialisierung als Reference Blueprint** vor V2-Asset-Klassen.

NB14f-v2-Daten werden **nicht** als V1-Lock genutzt, sondern als Forschungs-Input für Phase D.1 (USDCHF Deep-Dive).

---

## Phase D — FX als Reference Blueprint (Industrialization-First) 🟡 NEXT — ACTIVE

**Lock:** [ANN-016 FX as Reference Blueprint](decisions/ANN-016-fx-as-reference-blueprint-industrialization-first.md).

**Mission:** FX-Modell vollständig industrialisieren — Pipelines, Quality-Gates, Validation-Tests, Doku-Patterns, Pine-Code-Strukturen, User-Layer-Constraints — als **wiederverwendbarer Blueprint** für Phase E (V2 Multi-Asset).

**Reihenfolge-Lock:** Architektur-First (D.1–D.3) **bevor** Technical (D.4–D.8). Technische Decisions müssen auf den Architektur-Erkenntnissen aufbauen, nicht umgekehrt.

### D.1 — USDCHF Deep-Dive 🟡 NEXT (NB15a)

**Ziel:** Verstehen ob USDCHF-Bruch ist Session-Problem / Regime-Problem / Liquidity-Problem / Filter-Interaction-Problem.

**Tests:**
- Per-Session SHAP-Decomposition (Asia/London/NY/LDN-NY-Overlap)
- Filter-Impact-Decomposition (welcher Filter macht USDCHF schlechter — HTF-Confirm oder NY-Session?)
- Volatility-Regime-Analyse (verhält sich USDCHF in High-Vol vs Low-Vol-Regimes anders?)
- Liquidity-Proxy-Analyse (Volume-Z, RVOL pro Session)
- Vergleich mit verhaltensähnlichen Pairs (z.B. USDCAD funktioniert — was unterscheidet?)

**Output:** Strukturbefund-Doku, vermutete CHF-spezifische Marktstruktur belegt.

### D.2 — Universal-vs-Per-Pair-Decision (ANN-017, nach D.1)

**Harte Architekturfrage basierend auf D.1-Daten:**
- a) Filter-Stack bleibt universal?
- b) FX braucht Pair-Level-Overrides?
- c) Adaptive Session-Profile (z.B. CHF nutzt London/EU-Session statt NY)?

**Override-Discipline (ANN-016 Lock 5):** Jede Per-Pair-Lösung muss erfüllen:
1. Klarer statistischer Nachweis
2. Dokumentierte Marktstruktur-Begründung
3. OOS-Lift ≥ +0.05 PF
4. Reproduzierbares Verhalten (3+ Seeds, verschiedene Time-Periods)

**Output:** ANN-017 lockt Architektur-Decision + ggf. Code-Skelett für Override-Mechanik.

### D.3 — Pair-/Session-Behavior Map (NB15b)

**Ziel:** Wann funktioniert das Modell strukturell gut/schlecht?

**Output:**
- Per-Pair × Per-Session × Per-Volatility-Regime Matrix
- Operational-Boundary-Karte (klare Aussage: "Modell funktioniert robust unter Bedingungen X, Y, Z")
- Marketing-Story-Material (ehrliche Beschreibung wann User mit Signalen rechnen kann)

### D.4 — Failure-Case Documentation (research/failure_cases.md)

**Was bricht das Modell?**
- Vol-Regime-Shifts (Plötzliche Vol-Expansion → Modell-Output?)
- News-Events (NFP, FOMC, ECB → wie reagiert)
- Session-Mismatches (USDCHF-Pattern)
- Illiquide Phasen (Holiday-Gaps, Year-End)

**Output:** Failure-Templates die in V2 für Crypto/Indices/Commodity als Test-Sets dienen.

### D.5 — Pine bit-exact Validation (NB15c)

**Test:** Python-Probability == Pine-Probability auf 10k-Sample TEST-Bars.

**Tolerance:** absolute deviation < 1e-5 (bit-exact under float32).

**Output:** Bit-exact Validation Report pro Pair, Pine-Code-Snippets klassen-agnostisch.

### D.6 — Non-repaint + Live-Bar Validation (NB15d)

**Tests:**
- Repaint-Test: Signal an Bar t muss nach Bar-Close immer noch identisch sein (kein Look-Ahead)
- Live-Bar-Behavior: was zeigt Pine während Bar offen? Strategy-Display vs Signal-Trigger.
- Race-Condition-Tests: Multi-TF-`request.security`-Lookahead-off bestätigen.

**Output:** Live-Bar-Behavior-Spec, klassen-agnostische Repaint-Test-Suite.

### D.7 — Router-Integration (NB15e)

**Tasks:**
- AssetClass.FX-Route operativ (echte Pine-Code-Pfad)
- Non-FX zeigt klare UI-Message ("🚧 V1 supports FX Major Pairs — Crypto coming in V2")
- USDCHF (oder ggf. andere unsupported Pairs nach D.2) bekommen separate UI-Behandlung

**Output:** Pine-Code-Skelett (`deploy_pine/pace_algo_v1.pine`) als Blueprint für V2.

### D.8 — User-Layer Constraint Tests (NB15f)

**Tests pro User-Setting aus Whitelist (ANN-011):**
- Backtest-Statistik bleibt valid unter Profile-Switch
- Session-Filter behält PF (kein Curve-Fit-Hack möglich)
- HTF-Confirmation behält statistische Power
- Alert-Frequency-Cap bricht nichts

**Output:** User-Layer-Spec, statistisch validierte Setting-Ranges (Anti-Curve-Fit auf User-Side).

---

## Phase E — V2 Multi-Asset-Klassen (via Blueprint) ⚪ POST PHASE D

**Voraussetzung:** Phase D komplett abgeschlossen, Blueprint dokumentiert.

```
E.1  Crypto-Modell    ◄── nutzt Blueprint (Test-Templates aus D.4, Pipeline aus D.1–D.3, Pine-Code-Pattern aus D.5–D.7)
E.2  Commodity-Modell ◄── XAU + ggf. XAG/Oil
E.3  Indices-Modell   ◄── sobald Polygon-Aktivierung
E.4  Pine-Router-Production mit Multi-Model-Stack
```

**V1-Launch erst nach E.1 + E.4 minimum** (FX vollständig + 1 weitere Asset-Klasse + Multi-Model-Pine-Router operativ). Per ANN-016 Lock 3.

---

## Phase F — Pine Export + Backtest UI ⚪ TEIL VON PHASE D + E

Phase F-Deliverables sind jetzt in Phase D / E verteilt:
- **D.5 / D.7** decken Pine bit-exact + Router-Integration ab
- **E.4** finalisiert den Multi-Model-Pine-Router
- Backtest-UI / Profile-Switch / Trade-Boxen werden als Teil von D.7 designed (Blueprint-fähig für alle Asset-Klassen)

---

## Phase G (V1.5+) — Hybrid Backend (post-launch)

Nach V1-Launch + User-Feedback. Pine bleibt der Runtime, Backend retrainiert monatlich, neue Pine-Versionen werden auto-deployed. Pro Asset-Klasse separater Retraining-Cycle.

## Phase H (V2/V3) — Full Backend

ML-Inferenz auf Cloud-Server, Webhooks an TradingView, Web-Dashboard, Continuous Learning aus Signal-Outcomes. Multi-Model-Inference parallel pro Asset-Klasse.

---

## Was wir NICHT tun (gelocked)

- ❌ **Kein NB16 (Crypto-Modell) bevor Phase D abgeschlossen** (ANN-016 Lock 1)
- ❌ **Kein FX-only-V1-Launch** (ANN-016 Lock 3 — min. 2 Asset-Klassen über Blueprint nötig)
- ❌ Kein Pine-Generator bevor D.5 + D.7 locked
- ❌ Keine Asset-Spezialisierung "weil EURUSD besonders gut funktioniert"
- ❌ Keine Per-Pair-Overrides ohne ANN-016-Lock-5-Discipline (statistical / structural / OOS / reproducible)
- ❌ Kein Release-Pressure — Quality > Speed
- ❌ Keine Features ohne `≥ +0.05` PF-Lift in OOS-Ablation
- ❌ Keine FX-spezifischen Lösungen die später für Crypto/Indices nicht übertragbar sind (ANN-016 Lock 6)

Diese Negativliste ist genauso wichtig wie die Positiv-Roadmap.
