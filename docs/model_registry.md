# Model Registry — Multi-Model

**Architektur-Lock:** Multi-Model Router per [ANN-009](decisions/ANN-009-multi-model-router-architecture.md). 4 Modell-Slots, Quality-Anchor per [ANN-010](decisions/ANN-010-quality-anchor.md).

**Locked Rules:**
- Kein CatBoost in Pine-Deployment (Pine-Inkompatibilität)
- Neue Modelle MÜSSEN ANN-010 Quality-Anchor bestehen vor Deployment

## Modell-Slot-Status

| Slot | V1 Status | Modell | Premium PF | Notiz |
|---|---|---|---|---|
| **fx_model** | ✅ Aktiv | LightGBM 30 trees | 2.49 (5m mean, 5 Symbole) | V1-Sieger, NB13 belegt |
| **crypto_model** | ⏳ V2 — Stub | TBD (Crypto-Spezialmodell) | — | NB13c Test ausstehend |
| **indices_model** | ⏳ V2 — Stub | TBD | — | braucht Polygon-Aktivierung |
| **commodity_model** | ⏳ V2 — Stub | TBD (XAU + ggf. XAG + USO) | — | Gold Phase 1 = random (ANN-003) |

In V1-Pine: Aktive Slots haben echte Modelle, Stub-Slots returnen `na` → UI-Badge "🚧 V2 coming". Router-Skelett ist ready, kein Refactor-Bedarf für V2.

---

## Aktiver V1-Kandidat: NB11 Winner

**Modell:** LightGBM
**Config:** FX-only, 27 Features, 30 trees, depth 3
**OOS-Metriken (in-sample TEST):**
- Premium-Tier PF: **2.015**
- Premium-Tier WR: 57.3%
- Premium-Tier ExpR: +0.4264

**Hold-Out (GBPUSD) Validation:** ausstehend in NB12

**Status:** Research-Baseline. **NICHT Produktziel** — universeller Indikator ist das Ziel. Wird in Phase B (NB13) auf Cross-Asset-Generalisierung getestet.

**Hyperparams:**
```python
{
    'objective': 'binary', 'metric': 'binary_logloss',
    'num_leaves': 7, 'max_depth': 3, 'min_data_in_leaf': 200,
    'learning_rate': 0.05, 'num_iterations': 30, 'lambda_l2': 0.5,
    'feature_fraction': 0.85, 'bagging_fraction': 0.85, 'bagging_freq': 5,
    'is_unbalance': True,
    'seed': 42, 'deterministic': True,  # added in NB12 patch
}
```

---

## Phase A — Model Battery (NB12)

NB12 vergleicht **identische Hyperparameter** (30 trees, depth 3, lr=0.05, RANDOM_SEED=42) über 4 Modelle:

| Modell | Pine-export? | In-Sample Premium PF | GBPUSD Hold-Out PF | Stability CV | Verdict |
|---|---|---:|---:|---:|---|
| **LightGBM** | ✅ | 1.952 | 2.537 | 0.145 | **V1-Sieger** |
| XGBoost | ✅ | 1.945 | 2.672 | 0.188 | Marginal, Stability schwächer |
| CatBoost | ❌ research-only | 1.921 | 2.559 | 0.112 | Research-Komponente für Consensus |
| Voting (avg LGBM+XGB+Cat) | ⚠️ Cat-abhängig | 1.968 | 2.613 | 0.162 | Lift +0.016 — nicht signifikant |
| **Consensus (alle 3 stimmen)** | ⚠️ Cat-abhängig | 1.973 | **2.929** 🔥 | — | **V1.5-Backend-Gold** |

**Entscheidung:** LightGBM bleibt V1-Modell. Lift kein anderer Pine-fähiger Modell ≥ +0.05 auf in-sample TEST. Auf GBPUSD-Hold-Out hat XGBoost marginal +0.135 PF, aber nur 1 Symbol, kein robustes Signal — Phase B (NB13) muss das auf mehrere Asset-Klassen bestätigen.

**Strategische Reservierung:** Consensus-Filter (alle 3 Modelle) liefert auf GBPUSD-Hold-Out PF 2.93 (+0.39 über LightGBM-Alone). Das ist die größte Edge-Steigerung seit Phase 1 — aber erfordert CatBoost, also NICHT Pine-fähig. Reserviert für **V1.5 Hybrid-Backend**.

Volle Analyse: [research/model_battery_results.md](../research/model_battery_results.md).
Run-Snapshot: [results/json_exports/nb12_model_battery_2026-05-27.json](../results/json_exports/nb12_model_battery_2026-05-27.json).

---

## Historische Iterationen

| NB | Modell | Asset-Scope | OOS Premium PF | Status |
|---|---|---|---|---|
| NB05 | LightGBM (37 features) | FX+Gold | 1.14 | ⛔ ersetzt — zu viele dead features |
| NB06 | LightGBM + Meta-Labeling | FX | 1.06 | ⛔ ersetzt — Primary-Rule PF 0.99 |
| NB07 | Voting Ensemble (Exp.) | mixed | 1.06 | ⛔ ersetzt — kein Lift |
| NB08 | LightGBM Pine-validated | FX+Gold | 1.79 | ⛔ ersetzt — VAL-cutoff bug, NB10 fix |
| NB10 | LightGBM (bit-exact) | FX+Gold | 1.80 (?) | ⛔ Baseline, ersetzt durch NB11 |
| NB11 | LightGBM | FX-only | **2.015** | 🟡 aktueller Research-Sieger |

**Wichtige Korrektur in der Historie:** NB07/NB08 hatten VAL-cutoff bug (cutoffs aus TEST abgeleitet). NB10 hat das gefixt (cutoffs aus VAL). Alle Zahlen vor NB10 sind potenziell optimistisch.

---

## Modell-Artefakte

Trainierte Modelle leben in `artifacts/models/` (NICHT versioniert, lokal/Drive only). Naming:
- `lgbm_{config_tag}_{date}.pkl`
- `xgb_{config_tag}_{date}.pkl`
- `cat_{config_tag}_{date}.cbm`

Der **Hyperparameter-Snapshot** wird parallel in `results/json_exports/` versioniert — so können wir Modelle re-trainieren auch wenn `.pkl` lokal verloren ist.
