# Model Registry

Alle trainierten Modelle mit Hyperparams + OOS-Metriken. Quelle der Wahrheit für "welches Modell läuft gerade?" und "warum haben wir das gewählt?".

**Locked Rule (HANDOFF 12.2):** Kein CatBoost in V1-Pine-Deployment. CatBoost bleibt im Research-Set.

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

| Modell | Pine-export? | NB12 Status | Wartet auf |
|---|---|---|---|
| LightGBM | ✅ | Baseline für Lift-Threshold | Colab-Run |
| XGBoost | ✅ | Trainiert auf gleichen Splits | Colab-Run |
| CatBoost | ❌ research-only | Trainiert für Vergleich | Colab-Run |
| Voting (LGBM+XGB+Cat avg) | ⚠️ Cat-abhängig | — | Colab-Run |
| Consensus (alle 3 stimmen) | ⚠️ Cat-abhängig | Filter, kein Modell | Colab-Run |

**Entscheidungslogik:** Anderes Modell wird LightGBM nur ersetzen, wenn:
- `Premium-PF-Lift ≥ +0.05` UND
- Pine-exportierbar (oder explizite Backend-V1-Akzeptanz)

Ergebnisse landen in `/results/json_exports/nb12_model_battery_{date}.json` und werden in `/research/model_battery_results.md` interpretiert.

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
