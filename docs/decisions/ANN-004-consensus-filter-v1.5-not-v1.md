# ANN-004: Consensus-Filter gehört nicht in V1-Pine (Reserviert für V1.5-Backend)

**Status:** Active
**Datum:** 2026-05-27
**Locked-By:** HANDOFF Section 12.2.11 ("No CatBoost in V1") + 12.2.10 (Pine-Budget)
**Related:** [[ANN-005]] [[ANN-002]]

---

## 1. Hypothese

Wenn drei unterschiedliche Modelle (LightGBM + XGBoost + CatBoost) unabhängig trainiert werden und alle drei ein Signal als "Premium" einstufen, sollte dieses Signal robusterer Edge haben als ein Einzelmodell-Signal — weil die Modelle unterschiedliche Bias-Varianz-Tradeoffs haben und ihre Übereinstimmung Signal über Noise filtert.

Test-Variante: **Consensus** (alle 3 stimmen zu) vs. **Voting** (Mittelwert der Probabilities).

## 2. Experiment

**Notebook:** NB12 (Model Battery, Phase A)

**Daten:** FX-only (EURUSD, USDJPY) Walk-Forward + GBPUSD Hold-Out
**Modelle:** LightGBM, XGBoost, CatBoost — alle 30 trees, depth 3, lr=0.05, RANDOM_SEED=42
**Tier-Cutoffs:** VAL-derived top 1% pro Modell (NICHT übertragen, jedes Modell hat eigene Cutoffs)
**Consensus-Definition:** Signal ist "Premium" wenn ALLE 3 Modelle gleichzeitig den jeweiligen Premium-Cutoff überschreiten

## 3. Resultat

**In-Sample TEST:**

| Filter | Trades | WR | PF | ExpR |
|---|---:|---:|---:|---:|
| LightGBM-only Premium | 4323 | 56.5% | 1.952 | 0.407 |
| Voting (avg) Premium | 4260 | 56.7% | 1.968 | 0.412 |
| **Consensus Premium** | 3530 | 56.8% | 1.973 | 0.414 |

In-sample Lift: marginal (+0.02 PF über LightGBM). NICHT signifikant über 0.05-Threshold.

**GBPUSD Hold-Out (NIE im Training):**

| Filter | Trades | WR | PF | ExpR |
|---|---:|---:|---:|---:|
| LightGBM-only Premium | 2366 | 62.8% | 2.537 | 0.558 |
| Voting (avg) Premium | 2351 | 63.5% | 2.613 | 0.575 |
| **Consensus Premium** | **1914** | **66.1%** | **2.929** | **0.642** |

Hold-Out Lift: **+0.392 PF über LightGBM**, **+3.3 Prozentpunkte WR**. 19% weniger Trades, aber kein Drought.

Quelle: [results/json_exports/nb12_model_battery_2026-05-27.json](../../results/json_exports/nb12_model_battery_2026-05-27.json) → `consensus_vs_lgbm_only`.

## 4. Decision

**Consensus-Filter wird NICHT in V1-Pine eingebaut. Reserviert für V1.5-Backend.**

**Begründung:**

1. **Pine-Inkompatibilität:** Consensus erfordert CatBoost. CatBoost verwendet oblivious trees + categorical embeddings, die in Pine Script nicht clean exportierbar sind (HANDOFF 12.2.11 lockt das).
2. **In-sample Lift zu klein:** Ohne den Hold-Out-Faktor wäre der +0.02 PF nicht überzeugend.
3. **Single-Symbol-Hold-Out:** PF 2.93 auf GBPUSD ist EIN Symbol. Phase B (NB13) muss zeigen ob das auf Crypto/Indices generalisiert. Vor NB13-Bestätigung ist die +0.4 PF nicht als robustes Signal zu werten.
4. **Architektur-Hygiene:** V1 muss standalone Pine sein, kein Backend-Dependency. Consensus-Filter würde V1 zu einem Hybrid degradieren.

**Aber gleichzeitig:**

- Consensus-Filter ist die **größte Edge-Steigerung seit Phase 1** (wenn auf Hold-Out gemessen)
- Marketing-Hook für V1.5-Backend ist greifbar: "Server-validation hebt Premium WR auf 66%"
- Technisch implementierbar im Backend: alle 3 Modelle trainieren, Pine fragt Server via API ob Premium-Signal "consensus-validated" ist

## 5. Konsequenz

**Code (V1):**
- KEIN Consensus-Code im Pine-Export-Pfad
- LightGBM-Only-Inferenz in Pine
- `core/train/` trainiert weiterhin alle 3 Modelle (für Research-Continuity), aber nur LightGBM-Modell wird in Pine eingebettet

**Code (V1.5 Backend-Vorbereitung):**
- `deploy_server/` bleibt leer für V1
- Bei V1.5-Start: Endpoint `POST /validate` mit Inputs={features, candidate-signal-tier}, Output={consensus-validated: bool, validation-tier: "Premium"|"UltraPremium"}
- Pine ruft Backend nur für Premium-Tier-Validation an (low-volume, max ~3 Calls/Tag/Symbol)

**Roadmap:**
- Phase E (Pine Export) Architektur: LightGBM-Only, kein Backend-Hook
- V1.5 Definition expand: "Backend liefert Continuous Retraining + Consensus-Validation"

**Marketing:**
- V1: "AI-driven signals, validated offline via 30-tree LightGBM"
- V1.5: "Plus: real-time multi-model validation hebt Premium WR auf 66% in unseren Backtests"
- KEINE V1-Marketing-Behauptung mit den Consensus-Zahlen — die sind V1.5-only

**Phase B (NB13) Auftrag:**
- Verschärfte Forschungsfrage: "Hält der Consensus-Lift auch jenseits FX?" konkret testen
- Falls JA → V1.5-Backend ist unverhandelbar
- Falls NEIN (Lift nur auf GBPUSD) → Consensus-Filter wird wieder fallengelassen, V1.5-Backend macht "nur" Continuous Retraining

**Lesson:**
- Generalisations-Test (GBPUSD-Hold-Out) ist wichtiger als In-Sample-Lift. +0.02 in-sample, +0.39 on Hold-Out ist ein WICHTIGES Signal — aber nur eines, das auf einer Stichprobe von 1 Symbol basiert.
- Ensemble-Methoden auf TEST oft marginal, auf Hold-Out manchmal massiv — wegen Bias-Decorrelation. Das macht Consensus zum Tool für Generalisations-Probleme.
