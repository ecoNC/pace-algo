# Model Registry — Multi-Model

**Architektur-Lock:** Multi-Model Router per [ANN-009](decisions/ANN-009-multi-model-router-architecture.md). 4 Modell-Slots, Quality-Anchor per [ANN-010](decisions/ANN-010-quality-anchor.md).

**Locked Rules:**
- Kein CatBoost in Pine-Deployment (Pine-Inkompatibilität)
- Neue Modelle MÜSSEN ANN-010 Quality-Anchor bestehen vor Deployment

## Modell-Slot-Status

| Slot | Status | Modell | TF | Premium PF (OOS) | Hold-Out PF | Quality-Anchor | Notiz |
|---|---|---|---|---:|---:|---|---|
| **fx_model** | 🟡 **Phase D — Industrialization in Progress** | LightGBM 30×3 | **5m only** | 2.00 (NB14 v1, top-1%) | 2.39 (NB14 v1) / 1.61 (NB14f v2, Cluster) | Research-Lock per [ANN-016](decisions/ANN-016-fx-as-reference-blueprint-industrialization-first.md) | Phase D = Reference-Blueprint-Build (D.1 USDCHF Deep-Dive → D.2 Universal-vs-Per-Pair → D.3 Behavior-Map → D.4–D.8 Technical) |
| **crypto_model** | ⏳ V2 — Wartet auf Phase E.1 | TBD | TBD | — | — | — | Bau startet erst nach Phase D Abschluss (ANN-016 Lock 1) |
| **indices_model** | ⏳ V2 — Wartet auf Phase E.3 | TBD | TBD | — | — | — | Plus Polygon-Aktivierung |
| **commodity_model** | ⏳ V2 — Wartet auf Phase E.2 | TBD | TBD | — | — | — | XAU + ggf. XAG/Oil über Blueprint |

**Wichtig (ANN-016 Lock 1):** V2-Asset-Klassen-Modelle (E.1–E.3) starten **erst nach Phase D komplett abgeschlossen**. FX wird vollständig industrialisiert als wiederverwendbarer Blueprint, bevor parallele halbfertige Modell-Familien entstehen.

**V1-Launch-Definition (ANN-016 Lock 3):** Erst nach Phase D abgeschlossen UND mind. 2 Asset-Klassen über Blueprint produktionsreif UND Pine-Router operiert echten Multi-Model-Switch. Kein FX-only-V1-Release.

### V1 FX-Modell — Gelockte Konfiguration (ANN-011, expanded via ANN-015)

| Parameter | Wert |
|---|---|
| Algorithm | LightGBM (binary classification, sigmoid output) |
| Trees | 30 |
| Max Depth | 3 |
| Features (27) | Phase-1-Winner-Set (Baseline 15 + HTF-Interaction 12) |
| Training Symbols | EURUSD, USDJPY, **NZDUSD (NEU per ANN-015)** (Walk-Forward 2020-01 → 2024-01) |
| Validation Window | 2024-01 → 2024-07 |
| Test Window | 2024-07 → 2026-05 |
| Hold-Out Symbols | GBPUSD, AUDUSD, USDCHF, **USDCAD (NEU per ANN-015)** |
| Primary TF | **5m only** |
| HTF Context | 1h, 4h (mit `shift(1)` Anti-Look-Ahead) |
| Cutoff-Mechanik | Per-Model Relative Cluster (ANN-014) — Production-Cluster wird aus NB14f-v2 BEST_SEED extrahiert |
| Filter-Stack (Profile) | Aggressive=Premium-pur, Balanced=Premium+HTF, Conservative=Premium+HTF+NY (ANN-012) |
| Random Seed | TBD nach NB14f-v2 (BEST_SEED via Behavioral Stability) |

### V1 FX-Modell — Performance Snapshots

#### Historical: NB14 v1 (commit `6c2aed4`, 2 Train-Symbole, top-1%-Cutoff)

**5m TEST (in-sample, 596k train rows):**
- Premium PF 2.00 · WR 57.2% · MDD 2.9% · n_trades 3,354

**5m Hold-Out (nie trainiert):**
- GBPUSD: PF 2.57 / WR 63.2%
- AUDUSD: PF 2.47 / WR 62.2%
- USDCHF: PF 2.12 / WR 58.6%
- **Mean: PF 2.39 / WR 60.9%**

**Yearly Stability:** 2024 PF 1.79 / 2025 PF 2.04 / 2026 PF 2.52 (CV 0.145)

> Diese Zahlen waren auf `top-1%`-VAL-Cutoff. Cluster-basierte Cutoffs (ANN-013/14) sind breiter und liefern andere Zahlen — siehe NB14f v1 unten.

#### Historical: NB14f v1 (commit `2845025`, 2 Train-Symbole, Cluster-Cutoff)

**Pair-Aggregat (3 Seeds, Cluster-Cutoff ~0.405):**
- GBPUSD Balanced PF **1.41** (n=293) — einziges Symbol mit PF ≥ 1.4
- AUDUSD alle Profile PF < 1.0
- USDCHF alle Profile PF ≤ 1.0
- Behavioral Stability: **FAIL** auf allen 3 Profilen (signal_frequency_cv 0.45–0.77, threshold 0.30)
- Snapshot: [`results/nb14f/summaries/nb14f_full_snapshot_2026-05-28.json`](../results/nb14f/summaries/nb14f_full_snapshot_2026-05-28.json)

#### Historical: NB14f v2 (commit `80bad05`, 3 Train-Symbole + 4 Hold-Out, Cluster-Cutoff)

**Production-Seed: 7, Cluster: 0.40**

**Pair-Aggregat (Hold-Out, 4 Pairs):**

| Pair | Aggressive PF | Balanced PF | Conservative PF | Verhalten |
|---|---:|---:|---:|---|
| GBPUSD | 1.29 | 1.50 | 1.83 | ✓ sauber gestaffelt |
| AUDUSD | 1.42 | 1.83 | 1.97 | ✓ sauber gestaffelt |
| USDCAD | 1.13 | 1.33 | 1.59 | ✓ sauber gestaffelt |
| USDCHF | 0.97 | 0.63 | **0.17** | ✗ Filter-Stack-Inversion (Architektur-Signal) |

**Best-Seed-Profile (seed=7):**
- Aggressive: IS PF 1.12 / HO PF 1.42 (n=2340)
- Balanced: IS PF 1.42 / HO PF 1.61 (n=268)
- Conservative: IS PF 1.42 / HO PF 1.61 (n=268)

**Behavioral Stability:** `all_profiles_behavioral_stable: FALSE` — aber **kein V1-Blocker**, sondern Architektur-Signal per [ANN-016](decisions/ANN-016-fx-as-reference-blueprint-industrialization-first.md). USDCHF-Verhalten wird in Phase D.1 vollständig diagnostiziert, nicht wegoptimiert.

Snapshot: [`results/nb14f/summaries/nb14f_full_snapshot_2026-05-28.json`](../results/nb14f/summaries/nb14f_full_snapshot_2026-05-28.json)

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
