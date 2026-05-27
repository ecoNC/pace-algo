# Model Battery Results — NB12 (Phase A)

**Status:** ⏳ WARTET AUF COLAB-RUN

Diese Datei wird nach Nico's NB12-Run mit echten Zahlen gefüllt. Bis dahin enthält sie nur die Test-Setup-Dokumentation und Erwartungen.

---

## Test-Setup (eingefroren in NB12 Code)

| Parameter | Wert | Quelle |
|---|---|---|
| Random Seed | 42 | Cell-3, NB12 Patch 2026-05-27 |
| Feature-Config | NB11-Winner, 27 Features | `phase1_best_config.json` + Hardcoded Fallback |
| Asset-Scope | FX-only (EURUSD, USDJPY) | NB11-Sieger |
| Train/Val/Test-Split | Walk-Forward auf TRAIN_END/VAL_END | `core/config.py` |
| Hold-Out-Symbol | GBPUSD | DEV_HOLDOUT_SYMBOLS |
| Labels | Triple Barrier R=1.5 / 1.0 | NB04 |
| Win/Loss-R | 1.5 / 1.0 | NB12 Cell-3 |
| Tier-Cutoffs | VAL-derived, top 10%/3%/1% | NB12 Cell-17 |
| Pine-Constraint | 30 trees, depth 3 | LOCKED RULE 12.2.10 |

**Identische Hyperparameter über alle 3 Modelle:**
- `n_estimators / iterations / num_iterations`: 30
- `max_depth / depth`: 3
- `learning_rate`: 0.05
- `L2 regularization`: 0.5 (LGBM), 0.5 (XGB), 3.0 (CatBoost — eigene Skala)
- `subsample / bagging_fraction / rsm`: 0.85
- Class-Imbalance-Handling: `is_unbalance` (LGBM) / `scale_pos_weight` (XGB) / `auto_class_weights='Balanced'` (Cat)

---

## Erwartete Ergebnisse (Hypothesen vor Run)

**Diese werden nach dem Run mit echten Zahlen ersetzt.**

| Modell | Erwartete Premium-PF (IS-TEST) | Erwartung GBPUSD HO | Begründung |
|---|---|---|---|
| LightGBM | ~2.015 (NB11-Reproduktion) | ~1.4–1.8 | Baseline, deterministisch |
| XGBoost | ähnlich zu LGBM (±0.05) | ähnlich | Sehr ähnliche Tree-Struktur |
| CatBoost | ähnlich oder etwas besser | ähnlich | Robusterer Default |
| Voting (Mittel) | leicht besser oder schlechter | smoother | Mittelwert glättet |
| Consensus (alle 3 zustimmen) | deutlich höher PF, weniger Trades | strenger | Filter, nicht Modell |

**Threshold für Modell-Wechsel:** `Premium-PF-Lift ≥ +0.05` UND Pine-exportierbar. Sonst bleibt LightGBM.

---

## Per-Year-Stability-Erwartung

Premium PF pro Jahr — wir hoffen auf CV < 0.25 für den Sieger. Falls ein Modell in einem Jahr katastrophal abstürzt (PF < 0.8), ist es disqualifiziert auch wenn der Mittelwert höher ist.

---

## Output-Files (werden geschrieben nach Run)

Pfade relativ zu `/results/`:

- `json_exports/nb12_model_battery_{date}.json` — vollständiger Snapshot
- `benchmark_tables/nb12_pf_wr_expR_{date}.csv` — IS-TEST Tabelle
- `per_symbol_metrics/nb12_gbpusd_holdout_{date}.csv` — Hold-Out
- `yearly_stability_tables/nb12_premium_pf_by_year_{date}.csv` — Per-Year
- `benchmark_tables/nb12_consensus_filter_{date}.csv` — Consensus vs Single

---

## Nach dem Run: zu interpretierende Fragen

1. **Welches Einzelmodell hat höchsten Premium-PF im IS-TEST?**
2. **Hält sich diese Rangordnung auf GBPUSD Hold-Out?** (Generalisations-Test)
3. **Welches Modell hat niedrigsten Stability-CV?** (Robustheit-Test)
4. **Lift des Siegers über LightGBM:** ≥ +0.05? Wenn nein → LightGBM bleibt.
5. **Ist der Sieger Pine-exportierbar?** Wenn nein → Lift muss riesig sein, sonst Backend-V1-Diskussion.
6. **Consensus-Filter:** liefert er signifikant höheren PF bei akzeptabler Trade-Frequency? Falls ja: einbaubar als Pine-Filter-Layer.
7. **Voting vs Einzelmodell:** wenn Voting marginal besser ist (+0.02), lohnt die ~3x Pine-Code-Komplexität nicht.

---

## Decision-Tree nach Run

```
Premium-PF(best) - Premium-PF(LGBM) >= 0.05?
├── NO  → LightGBM bleibt. Verzeichne in /docs/model_registry.md.
└── YES → Best-Model Pine-exportierbar?
         ├── YES → Wechsel auf Best-Model. Update /docs/model_registry.md.
         └── NO  (CatBoost) → Backend-V1-Diskussion mit Nico:
                              │ Option 1: bei LightGBM bleiben, Backend für V2
                              │ Option 2: V1-Architecture ändern auf Webhook-basiert
                              └─→ explizite Entscheidung nötig, default = Option 1
```

---

## ARCHIVED Runs

Noch keine. Erster Run wird hier nach Colab-Ausführung als `## Run 2026-XX-XX` angehängt.
