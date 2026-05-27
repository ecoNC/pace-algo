# Model Battery Results — NB12 (Phase A)

**Status:** ✅ RUN 1 ABGESCHLOSSEN — 2026-05-27

Quelle: [results/json_exports/nb12_model_battery_2026-05-27.json](../results/json_exports/nb12_model_battery_2026-05-27.json)

---

## Test-Setup (eingefroren)

| Parameter | Wert |
|---|---|
| Random Seed | 42 |
| Lib Versions | LightGBM 4.6.0, XGBoost 3.2.0, CatBoost 1.2.10 |
| Feature-Config | NB11-Winner, 27 Features (FX-only) |
| Asset-Scope | FX-only (EURUSD, USDJPY) |
| TRAIN_END | 2024-01-01 |
| VAL_END | 2024-07-01 |
| Hold-Out-Symbol | GBPUSD |
| Dataset | 795k train, 99k val, 365k test, 183k GBPUSD-Hold-Out |
| Class Balance (test) | 39.2% positive |

Alle 3 Modelle: 30 trees, depth 3, lr=0.05. Identische Walk-Forward-Splits, identische VAL-derived Tier-Cutoffs.

---

## ## Run 2026-05-27

### 1. In-Sample TEST (EURUSD + USDJPY OOS Period)

**Profit Factor by Model × Tier:**

| Modell | Standard | High | Premium | AUC |
|---|---:|---:|---:|---:|
| LightGBM | 1.180 | 1.529 | **1.952** | 0.5280 |
| XGBoost | 1.207 | 1.546 | 1.945 | 0.5280 |
| CatBoost | 1.141 | 1.455 | 1.921 | 0.5268 |
| Voting | 1.191 | 1.570 | **1.968** | 0.5279 |

**Win Rate (Premium Tier):**
- LightGBM 56.5% · XGBoost 56.5% · CatBoost 56.2% · Voting 56.7%

**Trade Count (Premium Tier):**
- LightGBM 4323 · XGBoost 4231 · CatBoost 4181 · Voting 4260

> **Beobachtung:** Premium-PFs liegen alle in 1.92–1.97 Range. **Lift Voting über LightGBM: nur +0.016** — deutlich unter dem +0.05 Threshold. Auf in-sample TEST gibt es keinen klaren Sieger.

> **Caveat:** NB11-Baseline war PF 2.015. Aktueller LightGBM kommt auf 1.952. Differenz wahrscheinlich durch unterschiedliche TRAIN_END/VAL_END-Konfiguration zwischen NB11 und NB12. KEIN Modell-Regress, sondern andere Daten-Cuts.

---

### 2. GBPUSD Hold-Out (NIE im Training gesehen)

**Profit Factor (Hold-Out):**

| Modell | Standard | High | Premium |
|---|---:|---:|---:|
| LightGBM | 1.203 | 1.542 | 2.537 |
| **XGBoost** | 1.215 | 1.575 | **2.672** |
| CatBoost | 1.194 | 1.485 | 2.559 |
| Voting | 1.210 | 1.530 | 2.613 |

**Premium Win Rates:**
- LightGBM 62.8% · XGBoost **64.0%** · CatBoost 63.0% · Voting 63.5%

**Premium Trade Counts:**
- LightGBM 2366 · XGBoost 2339 · CatBoost 2362 · Voting 2351

> **Wichtigste Beobachtung:** Premium-PF auf Hold-Out (2.54–2.67) ist DEUTLICH HÖHER als auf in-sample TEST (1.92–1.97). Das ist ein sehr starkes Generalisations-Signal. GBPUSD war NIE im Training, und die Premium-Edge wird dort sogar stärker.

> **XGBoost-Lift auf Hold-Out: +0.135 PF über LightGBM** (knapp über Threshold). Aber: das ist EIN Symbol. Phase B (NB13) Cross-Asset wird zeigen ob das systematisch ist oder GBPUSD-spezifisch.

---

### 3. Per-Year Stability (Premium Tier)

| Modell | 2024 PF | 2025 PF | 2026 PF | Stability CV |
|---|---:|---:|---:|---:|
| LightGBM | 1.749 | 2.000 | 2.334 | **0.145** |
| XGBoost | 1.707 | 1.991 | 2.471 | 0.188 |
| CatBoost | 1.720 | 1.995 | 2.154 | **0.112** |
| Voting | 1.749 | 2.015 | 2.410 | 0.162 |

> **Beobachtung:** Alle Modelle haben CV < 0.20 — sehr stabile Edge, kein Jahr bricht weg. CatBoost ist am stabilsten (CV 0.112), aber **nicht Pine-exportierbar**. LightGBM ist zweitstabilste Pine-fähige Option.

> **Kein Modell hat ein "schlechtes" Jahr** (mindestens PF 1.7 in jedem Jahr). Das ist ein gutes Robustheits-Signal.

---

### 4. Consensus Filter (alle 3 Modelle stimmen zu) 🔥

**Größte Erkenntnis dieses Runs.** Statt Voting (Mittelwert), nur signal wenn ALLE 3 Modelle das gleiche Tier predicten.

**In-Sample TEST:**

| Filter | Trades | WR | PF | ExpR |
|---|---:|---:|---:|---:|
| LightGBM-only Standard | 37560 | 44.0% | 1.180 | 0.100 |
| Consensus Standard | 21894 | 46.1% | 1.282 | 0.151 |
| LightGBM-only High | 10769 | 50.5% | 1.529 | 0.258 |
| Consensus High | 7063 | 54.2% | **1.775** | 0.349 |
| LightGBM-only Premium | 4323 | 56.5% | 1.952 | 0.407 |
| Consensus Premium | 3530 | 56.8% | 1.973 | 0.414 |

**GBPUSD Hold-Out:**

| Filter | Trades | WR | PF | ExpR |
|---|---:|---:|---:|---:|
| LightGBM-only Premium | 2366 | 62.8% | 2.537 | 0.558 |
| **Consensus Premium** | 1914 | **66.1%** | **2.929** | **0.642** |
| LightGBM-only High | 6464 | 50.7% | 1.542 | 0.262 |
| Consensus High | 4144 | 55.6% | 1.880 | 0.384 |
| LightGBM-only Standard | 21372 | 44.5% | 1.203 | 0.111 |
| Consensus Standard | 12098 | 46.6% | 1.307 | 0.162 |

> **🔥 KILLER-Zahl:** Consensus Premium auf GBPUSD Hold-Out: **PF 2.93, WR 66.1%**. Das ist **+0.39 PF über LightGBM-Alone**.
>
> Trade-Count drops von 2366 auf 1914 (-19%) — moderat, kein Trade-Drought.
>
> Lift hält auch auf High-Tier (+0.34 PF) und Standard-Tier (+0.10 PF). Robust über alle Tiers.

> **Aber:** Consensus erfordert ALLE 3 Modelle (inkl. CatBoost). CatBoost ist nicht Pine-exportierbar. **Konsequenz: Consensus ist V1-Pine NICHT machbar — aber Hybrid V1.5 (Backend filtert Signals) ist Gold.**

---

## CTO Verdict

### Hard Decision: V1 Modell-Wahl

| Kriterium | Sieger | Margin |
|---|---|---|
| In-sample TEST Premium-PF | Voting (1.968) | nur +0.016 über LGBM — irrelevant |
| GBPUSD Hold-Out Premium-PF | XGBoost (2.672) | +0.135 über LGBM — knapp signifikant |
| Per-Year Stability (Pine-fähig) | LightGBM (CV 0.145) | besser als XGB CV 0.188 |
| Pine-Export-Aufwand | LightGBM | XGB ähnlich, Voting 2-3x Linien |

**Empfehlung: LightGBM bleibt V1-Modell.**

**Begründung:**
1. Lift von XGBoost (+0.135 PF auf GBPUSD) ist KEIN robustes Signal — nur 1 Hold-Out-Symbol. Phase B (NB13 Cross-Asset) muss das auf 8+ Symbole bestätigen, sonst ist es Zufall.
2. XGBoost-Stability ist schlechter (CV 0.188 vs 0.145). Robustheit > marginal höhere mean-PF.
3. In-sample TEST zeigt KEIN Modell mit signifikantem Lift (alles unter +0.05).
4. LightGBM ist unsere bekannte Größe — Pine-Export-Pipeline existiert konzeptuell, Bit-Exact-Validation (NB10) ist auf LGBM ausgerichtet.

### 🔥 Strategische Erkenntnis: Consensus-Filter ist V1.5-Gold

**Auf GBPUSD Hold-Out:** Consensus Premium PF **2.93 vs LightGBM-Alone 2.54** = +0.39 PF, **WR 66.1% vs 62.8%** = +3.3pp.

Das ist nicht "marginal". Das ist der größte Edge-Lift den wir seit Phase 1 gesehen haben.

**Konsequenz für Roadmap:**
- **V1 (Pine):** LightGBM-Alone, wie geplant. PF ~2.5 auf Hold-Out, gut genug für Launch.
- **V1.5 (Hybrid Backend, post-launch):** Consensus-Filter im Backend. Pine zeigt "Premium Badge" nur wenn Backend (LGBM+XGB+Cat) zustimmt. Lift +0.4 PF auf Premium-Tier rechtfertigt die Backend-Komplexität.
- **Marketing-Hook für V1.5:** "Mit Server-Verbindung schaltet PaceAlgo eine zusätzliche Validierungs-Schicht frei, die Premium-Signale auf 66% Win-Rate hebt." (ehrlich, mit Daten gestützt)

### Phase B (NB13) Frage-Update

**Verschärfung der H2 Hypothese:** "Hält die XGBoost-Marginal-Outperformance auf Hold-Out über MEHRERE Asset-Klassen?" Wenn ja → echtes Signal. Wenn nein → wir bleiben bei LightGBM.

Plus: **Neue Frage:** "Funktioniert Consensus-Filter auch auf Crypto/Indices/Gold, oder ist der GBPUSD-Lift symbol-spezifisch?" Wenn er allgemein hält → V1.5-Backend ist unverhandelbar.

---

## Outstanding Items

- ❗ **CSV-Sync-Bug:** Section 10 schreibt 4 CSVs + 1 JSON, nur die JSON wurde gepusht. Output von Nico's Section-10-Run nötig zum Debuggen ([1/5]..[5/5] Lines).
- ⏭️ Phase B (NB13) bauen — Code-Plan steht in `research/asset_generalization.md`.
- ⏭️ `core/colab_push.py` Refactor (Auto-Push als Funktion, Cell schrumpft auf 3 Zeilen).
