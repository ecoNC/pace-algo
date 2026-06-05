# ANN-026 — FX-Ship-Modell: 50t/100t-Reconcile

**Status:** ACCEPTED (Nico, 2026-06-03) · **Kontext:** FX-Overlay-Unpark Schritt 1 (Modell-Reconcile vor Export).

## Entscheidung

**Geshippt wird die OOS-validierte Lock-Config = 50 Bäume** (`fx_lock.json`: 9-Feat-Primary +
full-73-Meta, je 50t, NY-Gate, POOLED top10/Tag, R=1.5). OOS-Robustheit: net PF **1.51 @0.5pip**
(walk-forward 10 Folds, 80% Folds+, alle Jahre +). Das ist zugleich die Pine-budget-taugliche
Variante (4 Cascades @50t ≈ 88% Ops).

**Die 1.73 (100t) wird NICHT vererbt.** Falls aus Pine-/Compile-Gründen 50t gewählt wird (ist es),
muss das tatsächlich geshippte 50t-Modell **eigenständig OOS-revalidiert** werden (PF + cross-symbol
Holdout), bevor es das Edge-Validated-Badge bekommt.

## Reconcile-Befund (kritisch)

Die im Repo getrackten Artefakte matchen die Lock-Ship-Spec NICHT:
- `fx_v1_lgbm_seed7_100trees` UND `fx_v2_..100trees` nutzen **beide das volle ~73-Feature-Set**
  (ema_20/50/200, adx, rsi, macd, FVG, BOS, …), **100 Bäume**. Keines ist das **9-Feature-50t-Primary**.
- Das 9-Feat-Primary wird in der Validierung (`phase7_fx_lock.py`) **pro Fold neu trainiert** (kein
  gespeichertes File); ein Production-50t-9-Feat-Modell wurde NICHT committet.
- **`data_cache/` (Feature-Daten) existiert auf dem Heim-PC nicht** → Production-Retrain hier nicht
  sofort fahrbar; Daten+Pipeline liegen auf dem **Arbeits-PC** (CLAUDE.md: dort wurde Forschung gebaut).

→ Konsequenz: Das geshippte 50t-Modell muss **(re)produziert** werden (9-Feat-Primary + 73-Feat-Meta,
seed=7, Production-Cutoff), aus (neu aufgebauten) Daten — das gehört auf den **Arbeits-PC** (Daten+Pipeline),
während die **Bit-exact-Compile-Validierung den Heim-PC (TV) braucht**. = cross-Workstation-Ablauf.

## Harte Gates (unverändert)

1. **Bit-exact** Python↔Pine über das Validierungs-Set — sonst KEIN Ship.
2. **OOS-PF des tatsächlich geshippten 50t-Modells** über Schwelle (Lock-Bar net PF≥1.3, alle Jahre+,
   cross-symbol Holdout) — sonst KEIN Edge-Badge → COVERAGE_MATRIX bleibt Tool-Only.
3. FX-Majors → Edge-Validated in der COVERAGE_MATRIX **erst** nach (1)+(2).

## Nächste Schritte (Reihenfolge, Nico-locked)

1. ✅ Reconcile-Entscheidung (dieses ADR).
2. **Production-50t-Modelle (re)trainieren** (Arbeits-PC): data_cache via NB01/02 aufbauen → 9-Feat-Primary
   50t + 73-Feat-Meta 50t (seed 7) auf Production-Cutoff; Modelle + Feature-Order + Cutoffs committen.
3. Feature-Order fixieren & gegen Trainings-Setup prüfen.
4. `lgbm_to_pine_cascade` auf die 50t-Booster → Pine-Cascade.
5. `bit_exact_check` vs. Validierungs-Set (harter Gate).
6. Skelett `pace_algo_v1_ml_export_PARKED.pine` patchen → TV-Compile (Heim-PC) → Ship-Form.
7. OOS-PF des Ship-Modells bestätigen → COVERAGE_MATRIX FX-Majors auf Edge-Validated.

**Env-Status (Heim-PC):** lightgbm 4.6.0 + numpy + pytest auf py3.14 vorhanden; `pine_codegen` Tests 7/7 grün.
Codegen-Kette funktioniert — es fehlen die korrekten 50t-Modelle + Trainings-/Validierungsdaten.

## NACHTRAG 2026-06-03 — BLOCKER AUFGEHOBEN: Daten sind lokal da, Pipeline + bit-exact verifiziert

Der „data_cache fehlt"-Blocker war ein FEHLALARM: die FX-Daten liegen in **`data/processed_v2/`**
(gitignored, aber lokal vorhanden — nicht `data_cache/`, das ich zuerst prüfte). Alle 7 FX-Symbole,
5m/1h/4h, 2022-01→2026-05 (GBPUSD 5m = 329.620 Zeilen). **Das FX-Projekt ist VOLL am Heim-PC fahrbar.**

Verifiziert (2026-06-03):
- `build_pool()` (phase3_density) läuft lokal → POOL 1.624.145 Zeilen, 5 FX-Symbole, FEATURES_9 +
  Labels (_lab_long/_short) + Gates (_in_ny/_tradeable) gebaut. = komplette Daten/Feature/Label-Pipeline ok.
- **bit-exact HARD GATE auf echtem Modell BESTANDEN:** Production-Primary-Long (9-Feat, 50t, seed 42,
  train<2025-07) → `lgbm_to_pine_cascade` (21 KB) → `bit_exact_check` auf 5000 Holdout-Samples:
  **max_abs_diff 0.0, rmse 0.0.** Die Pine-Cascade == der LightGBM-Booster. (Script:
  `scripts/fx_primary_export_smoke.py`.) → der riskanteste Teil des Exports ist geknackt.

**Revidierte Rest-Schritte (alle lokal, Heim-PC):**
2'. Alle 4 Cascades produktiv trainieren (Primary L/S 9-Feat + Meta L/S 73-Feat, 50t, seed, Cutoff)
   + Thresholds snapshotten (generous gen, POOLED top10, Sizing-Tiers).
3'. Volles System ins Skelett replizieren: Feature-Engine (9 Feats inkl. NY-Gate + vol_tradeable +
   htf_4h), 4 Cascades, gen→meta→POOLED-Selektion, Sizing — bit-exact über die GESAMTE Kette.
4'. OOS-Revalidierung der tatsächlich geshippten 50t-Modelle (alle Jahre + cross-symbol Holdout).
5'. TV-Compile + Ship-Form → COVERAGE_MATRIX FX-Majors auf Edge-Validated.
