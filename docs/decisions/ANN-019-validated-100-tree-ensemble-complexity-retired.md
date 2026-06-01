# ANN-019 — Validated 100-Tree Ensemble: Cluster/Relative-Cutoff/Behavioral Complexity Retired

- **Status:** Active
- **Datum:** 2026-06-01 (UTC)
- **Locked-By:** HANDOFF Section 12.1 (Research Rules — kein Workaround ohne Root-Cause), Section 12.5 (Produkt-First / Anti-Eskalation)
- **Related:** supersedes **ANN-013** (Cluster-Based Premium Detection) und **ANN-014** (Per-Model Relative Cluster + Behavioral Stability); klärt **ANN-012** Cutoff-Mechanik (zurück zu plain VAL-Quantilen); bestätigt **ANN-011** (5m + VAL-Quantil-Cutoffs)

---

## 1. Hypothese

Die historische Symptom-Kaskade — ultra-discrete Probability-Distributions, „Cluster"-Bänder, Cutoff-Konvergenz (das berüchtigte 0.4026), Seed-Instabilität, Behavioral-Stability-Failures und schließlich 0 Signale im Pine — wurde über Monate als **Modell-Eigenschaft** interpretiert und mit zunehmender Komplexität umbaut (Cluster-Detection ANN-013, Per-Model-Relative-Cutoffs + Behavioral-Stability ANN-014).

**Neue Hypothese (Nico, 2026-06-01):** All diese Symptome sind Artefakte **eines einzigen Bugs** — `early_stopping` reduziert den LightGBM-Booster auf einen degenerierten 1–2-Tree-Stump. Falls echte Ensembles stabil laufen, ist die gesamte Cluster-/Relative-Cutoff-/Behavioral-Komplexität ein Workaround um ein kaputtes Modell und kann entfallen.

## 2. Experiment

`scripts/model_validation_suite.py` — kontrollierte Retraining-Matrix, **identische Daten / Features / Splits / Holdouts** für jede Variante:

- **Daten:** Dukascopy 2022-2026, 5m, 7 FX-Paare (`data/processed_v2/`), Train-Pool = FX_TRAIN_SYMBOLS, Holdout = GBPUSD/AUDUSD/USDCHF/USDCAD.
- **Splits:** Train < 2025-01-01, Val < 2025-07-01, Test danach (mirror retrain_v2.py).
- **Matrix × Seeds 42/1/7:** `lgbm_es10_30` (early_stopping=10), `lgbm_noes_30`, `lgbm_noes_100`, `lgbm_noes_300`, `xgb_100` (Baseline).
- **Gemessen:** num_trees, effective_trees (>0 gain), unique probabilities, Tier-Separation (VAL q90/q97/q99), Kalibrierung (ECE), Seed-Drift, Holdout-PF/WR pro Paar, Regime-Stabilität (Test in 3 Zeitscheiben).

## 3. Resultat

Pfad: [`results/model_validation/2026-06-01T08-40-18Z/REPORT.md`](../../results/model_validation/2026-06-01T08-40-18Z/REPORT.md) (+ `audit.json`)

| Variante | trees | eff | uniq_probs | sep q90→q99 | ECE | Befund |
|---|---|---|---|---|---|---|
| **lgbm_es10_30** | **2** | **2** | **14** | **0.005** (kollabiert ~0.40) | 0.01 | **degenerierter Stump** |
| lgbm_noes_30 | 30 | 30 | 1405 | 0.022 | 0.08 | gesund |
| lgbm_noes_100 | 100 | 100 | 2051 | 0.046 | 0.106 | gesund (Prod) |
| lgbm_noes_300 | 300 | 300 | 2712 | 0.067 | 0.107 | gesund |
| xgb_100 | 100 | 100 | 2115 | 0.047 | 0.106 | gesund |

- **Degeneracy-Hypothese 100% bestätigt:** `early_stopping` → 2 effektive Trees, 14 unique Probabilities, alle Cutoffs bei ~0.40 zusammengefallen. Das ist exakt die historische Pathologie und erklärt **alle** Symptome (ultra-discrete dist, Cluster, Cutoff-Konvergenz, Seed-Instabilität, Pine-0-Signale).
- **Echte Ensembles sind gesund:** voll effektive Trees, 1400–2700 unique Probabilities, glatte Verteilung, saubere Tier-Separation (breiter mit mehr Trees), winziger Seed-Drift (Cutoff-std ~0.001–0.004).
- **Cross-Algorithm-Beweis:** XGBoost reproduziert die LGBM-100-Verteilung unabhängig (uniq 2115, Cutoffs 0.537/0.557/0.584) → Edge ist kein LGBM-Artefakt.
- **Sanity-Anker:** `lgbm_noes_100 seed=7` reproduziert exakt die Produktions-Cutoffs 0.535/0.554/0.577 → Pipeline ist treu.
- **Robustness (Holdout PF @ q97, mean/std über Seeds):**

  | Variante | GBPUSD | AUDUSD | USDCHF | USDCAD | regime-CV |
  |---|---|---|---|---|---|
  | lgbm_noes_100 | 1.57/0.07 | 0.86/0.10 | 1.44/0.15 | 1.85/0.05 | 0.20 |
  | xgb_100 | 1.69/0.19 | 0.93/0.05 | 1.22/0.10 | 1.96/0.15 | 0.16 |

- **100 Trees = Kapazitäts-Sweet-Spot** (300 verbessert OOS nicht). **AUDUSD model-agnostisch schwach** (PF<1 bei allen gesunden Modellen). Healthy-Modelle ECE ~0.10 (Calibration-Potenzial).

## 4. Decision

1. **Der validierte V1-Modellkern ist ein gesundes 100-Tree-LightGBM-Ensemble OHNE `early_stopping`.** `early_stopping` ist für dieses Setup (flache Trees + `is_unbalance`) verboten — es degeneriert den Booster. Locked in `core/train/lgbm_trainer.py` (default `early_stopping_rounds=None`, bereits gesetzt seit NB16).
2. **Tier-Logik = plain VAL-Quantile q90/q97/q99.** Keine Cluster-Detection, keine Per-Model-Relative-Cutoffs, keine Behavioral-Stability-Gates.
3. **ANN-013 und ANN-014 werden auf `Superseded` gesetzt.** Ihre Mechaniken (Cluster-Extraction, Relative-Cutoff, Behavioral-Stability-Suite) waren Workarounds um den degenerierten Stump und sind für ein gesundes Ensemble gegenstandslos. Der Diagnose-Code in `core/analysis/probability_diagnostic.py` bleibt als Forschungs-/Audit-Werkzeug erhalten, ist aber NICHT mehr Teil des V1-Produktionspfads.
4. **Offen (nicht durch dieses ADR entschieden):** finaler Core `lgbm_noes_100` vs `xgb_100` (xgb minimal robuster, lgbm bereits deployt + bit-exact-exportierbar); AUDUSD supported-Status; Calibration-Layer.

## 5. Konsequenz

- **Code:** V1-Pfad nutzt VAL-Quantil-Cutoffs direkt (wie aktuell in `scripts/pine_export_v2.py` / NB15c S3 bereits umgesetzt). Cluster-/Behavioral-Aufrufe sind kein Pflichtschritt mehr.
- **Roadmap:** Modell-Validierungs-Phase liefert das wissenschaftliche Fundament; offene Threads: AUDUSD-Investigation, Calibration-Deep-Dive, Final-Core-Entscheidung. **Pine-Re-Export erst, wenn der finale Core gelockt ist.**
- **Doku:** ANN-013/014 als Superseded markiert (Index + Header). ANN-012-Filter-Stack-Konzept bleibt als optionale Profil-Differenzierung gültig, ist aber von der Cutoff-Mechanik entkoppelt.
- **Lessons:** Symptome erst root-causen, bevor Komplexität gebaut wird (HANDOFF 12.1). Mehrere Monate Cluster-/Behavioral-Engineering waren vermeidbar, hätte ein früher `effective_trees`-Check den Stump aufgedeckt. → Struktur-Audit (num_trees/effective_trees/unique_probs) ist ab jetzt Pflicht-Gate nach jedem Training.
