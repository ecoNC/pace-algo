# ANN-015: V1 Training-Pool Expansion + Robustness Re-Validation

**Status:** Active
**Datum:** 2026-05-28
**Locked-By:** Nico-Decision nach NB14f Behavioral-Stability-FAIL
**Related:** [[ANN-014]] (Per-Model Cluster + Behavioral Stability — bleibt Quality-Gate), [[ANN-006]] (Robustness-Mantra), [[ANN-008]] (FX-Edge generalisiert auf FX), [[ANN-013]] (Cluster-Detection-Mechanik), [[ANN-012]] (Filter-Stack-Architektur)

---

## 1. Hypothese

**Die NB14f-Behavioral-Stability-FAIL ist KEINE fundamentale Modell-Schwäche, sondern Konsequenz eines zu schmalen Trainings-Pools** (aktuell nur `EURUSD + USDJPY`).

Belege aus dem Repo-Wissen:
- **NB13 (`8a7bf8d`):** FX-Edge **generalisiert sauber** auf 5 FX-Symbole. GBPUSD/AUDUSD/USDCHF Hold-Out Premium-PF zwischen 2.58–2.66 auf 5m mit `top-1%`-Cutoff. Volle Tabelle: [research/asset_generalization.md §1](../../research/asset_generalization.md).
- **NB14f (`2845025`):** Gleiche Symbole, aber mit **Cluster-basiertem** Cutoff (breiterer Tier, ~2% statt 1%): Aggressive-Aggregat-PF 0.97 / 0.86 / 0.70. `signal_frequency_cv` 0.45–0.77 (Threshold 0.30) → **FAIL** auf allen 3 Profilen.

**These:** Der Pool von 2 Symbolen produziert zu wenige Marktregime im Training. Das LightGBM-Cluster bei `0.4054` wird über Seeds nicht stabil reproduziert, weil 2 Symbole × 4 Trainingsjahre nicht genug stochastische Diversität in der Probability-Landschaft erzeugen. Mehr Symbole = mehr Regime = stabilerer Cluster + konsistentere Signal-Häufigkeit.

**Erwartung nach Pool-Expansion:**

| Behavioral-Metrik | NB14f Ist | Erwartung Re-Run | Threshold |
|---|---:|---:|---:|
| signal_frequency_cv (Aggressive) | 0.45 | < 0.30 | 0.30 |
| signal_frequency_cv (Balanced) | 0.77 | < 0.30 | 0.30 |
| signal_frequency_cv (Conservative) | 0.74 | < 0.30 | 0.30 |
| holdout_pf_mean (Aggressive) | 0.85 | ≥ 1.3 | 1.3 |
| holdout_pf_mean (Conservative) | 0.50 | ≥ 1.3 | 1.3 |
| mdd_relative_std (Balanced) | 0.83 | < 0.5 | 0.5 |
| mdd_relative_std (Conservative) | 0.75 | < 0.5 | 0.5 |
| Per-Symbol-Range (Aggressive HO-PF) | 0.70–0.97 | engerer Spread | n/a |

Sekundär: **hour/session-Dominanz** sollte schwächer werden (R-13). Mit mehr Symbolen im Training fließen Asia + London + NY Marktregime stärker ein — der 66.6%-NY-Anteil aus NB14 sollte sinken.

## 2. Experiment

### Setup — neue Pool-Konfiguration

| Pool | Vorher (NB14f) | Nachher (ANN-015) |
|---|---|---|
| **FX_TRAIN_SYMBOLS** | EURUSD, USDJPY | EURUSD, USDJPY, **NZDUSD** |
| **FX_HOLDOUT_SYMBOLS** | GBPUSD, AUDUSD, USDCHF | GBPUSD, AUDUSD, USDCHF, **USDCAD** |
| **Total FX-Universum** | 5 | 7 |

**Begründung der Symbol-Wahl:**

- **NZDUSD (Training):** Antipoden-Pair (parallel zu AUDUSD aber andere Macro-Drivers — Milchprodukte/Geldpolitik RBNZ), bringt eine vierte Session-Charakteristik (Asia-Pacific) ins Training. Diversifiziert AUDUSD-Korrelation.
- **USDCAD (Hold-Out):** Major-FX, Öl-Macro-Link (CAD = Petrowährung), NY-Session-Overlap. Testet ob FX-Edge mit anderem Macro-Driver hält und ob NY-Session-Konzentration durch Pool-Expansion abnimmt. Dukascopy hat die historischen Daten.

**Was BEWUSST NICHT geändert:**
- Feature-Set bleibt unverändert (27 NB11-Winner-Features) — wir trennen "Trainings-Pool-Effekt" sauber von "Feature-Effekt"
- Hyperparameter bleiben unverändert (LightGBM 30×3, lr 0.05, is_unbalance=True)
- Cluster-Detection-Mechanik bleibt unverändert (Per-Model Relative Cluster aus ANN-014)
- Behavioral-Stability-Thresholds bleiben unverändert (5 Metriken aus ANN-014 §4)
- Triple-Barrier-Labeling bleibt unverändert (NB04 Standard)

### Pipeline — was Nico in Colab tun muss

1. **NB01 re-run** (`notebooks/01_fetch_data.ipynb`): Fetcht NZDUSD + USDCAD historische OHLCV aus Dukascopy. Erwartete Laufzeit: ~10 min, abhängig von Bandbreite.
2. **NB04 re-run** (`notebooks/04_triple_barrier_labeling.ipynb`): Generiert Triple-Barrier-Labels auf den neuen Symbolen × 4 TFs. Erwartete Laufzeit: ~5–10 min.
3. **NB14f re-run** (`notebooks/14f_per_model_behavioral_validation.ipynb`): Trainiert FX-Modell auf erweitertem Pool, extrahiert Per-Seed-Cluster, validiert Behavioral Stability + Pair-Tiering auf 4 Hold-Out-Symbolen. Erwartete Laufzeit: ~12–15 min (33% mehr Trainingsdaten als vorher).
4. **Auto-Push:** Section 12 pusht `results/nb14f_v2/` Outputs (oder neuer Pfad, je nach Run-ID).

### Erwartete Outputs

- `results/nb14f_v2/summaries/nb14f_v2_full_snapshot_2026-05-28.json` (oder Sub-Datum)
- `results/nb14f_v2/metrics/best_seed_profiles_*.csv`
- `results/nb14f_v2/metrics/pair_aggregated_*.csv` (jetzt mit 4 Hold-Out-Symbolen + USDCAD)
- `results/nb14f_v2/metrics/holdout_per_seed_symbol_profile_*.csv`
- `results/nb14f_v2/metrics/in_sample_per_seed_profile_*.csv`

## 3. Resultat

**Pending.** Outputs werden nach NB14f-v2-Run hier eingefügt.

Decision-Logic für Re-Run-Auswertung:

```
IF (all_profiles_behavioral_stable == True) AND
   (mean Hold-Out Premium-PF ≥ 1.4 auf ≥ 3 von 4 Symbolen) AND
   (per-symbol Pair-Tiering: ≥ 3 Symbole "supported" per ANN-014 §5):
    → V1 RE-VALIDATED, Phase D (NB15) wird freigegeben
    → BEST_SEED + BEST_CLUSTER aus NB14f-v2 werden Production-Lock
    → ANN-014 cross-link: "operationalisiert via ANN-015"

ELIF (all_profiles_behavioral_stable == True) BUT
     (Pair-Tiering: nur 1–2 von 4 Symbolen "supported"):
    → Pair-Tiering harte Realität, V1.5-Mechanik (R-19) wird V1-Pflicht
    → Marketing: "PaceAlgo V1 unterstützt GBPUSD + X + Y" statt "FX Major Pairs"
    → Phase D startet mit eingeschränktem Symbol-Set

ELIF (signal_frequency_cv weiterhin > 0.30 auf ≥ 2 Profilen):
    → These ANN-015 widerlegt: Pool-Breite reicht nicht
    → Eskalation zu Feature-Engineering (NB16) oder Hyperparam-Tuning (Optuna)
    → ANN-014's Architektur-Trigger wird scharf ("Modell-Architektur muss überdacht werden")

ELIF (holdout_pf_mean weiterhin < 1.3 auf ≥ 2 Profilen):
    → FX-Edge ist möglicherweise stärker pair-spezifisch als NB13 vermutet hat
    → NB13-Erkenntnis ("FX generalisiert") muss mit aktueller Cluster-Mechanik neu validiert werden
    → Eskalation zu R-19 Pair-Tiering V1.5 als V1-Standard
```

## 4. Decision

### Lock #1: Pool-Expansion auf 3 Trainings + 4 Hold-Out-Symbole

`core/config.py` wird per Edit angepasst (NZDUSD ins Training, USDCAD ins Hold-Out). Sonst unverändert.

### Lock #2: Phase D (NB15 Pine-Router-V1) ist BLOCKED bis Re-Run passed

Es macht keinen Sinn, die Pine-Implementation gegen ein Python-Modell zu validieren, das nicht behavioral-stable ist. NB15-Bau startet erst NACH dem NB14f-v2-Pass.

### Lock #3: Cluster-Mechanik und Behavioral-Stability-Definition bleiben unverändert

ANN-014 wird **nicht** superseded. Der NB14f-FAIL ist im Sinne von ANN-014 ein Feature, kein Bug — der Lock-Mechanismus weigert sich, einen nicht-stabilen Production-Seed zu locken. ANN-015 testet, ob die Pool-Breite die Ursache war.

### Lock #4: Re-Run-Outcome bestimmt nächsten Architektur-Schritt deterministisch

Die 4 Decision-Branches aus §3 sind vorab festgelegt. Damit vermeidet sich Ad-Hoc-Pivot nach Sicht-Auswertung.

### Lock #5: V1-Modell-Status formal "Pending Re-Validation"

`docs/model_registry.md` wird auf "Pending Re-Validation per ANN-015" gesetzt. Die alten NB13/NB14-Performance-Zahlen werden archiviert (nicht gelöscht — bleiben als Vergleichs-Baseline).

## 5. Konsequenz

### Code-Änderungen (jetzt)

**`core/config.py`** (NEU):
```python
FX_TRAIN_SYMBOLS    = ["EURUSD", "USDJPY", "NZDUSD"]              # +NZDUSD (ANN-015)
FX_HOLDOUT_SYMBOLS  = ["GBPUSD", "AUDUSD", "USDCHF", "USDCAD"]   # +USDCAD (ANN-015)
FX_SYMBOLS          = FX_TRAIN_SYMBOLS + FX_HOLDOUT_SYMBOLS
```

NB01 und NB04 iterieren über `FX_SYMBOLS` bzw. `ASSET_GROUPS['fx']` (von NB13 etabliert) — die neuen Symbole fallen automatisch in die Pipeline.

NB14f braucht **keinen Code-Patch** — es liest `FX_TRAIN_SYMBOLS` / `FX_HOLDOUT_SYMBOLS` direkt aus `core/config.py`.

### Doku-Änderungen (jetzt)

- `docs/roadmap.md`: Phase C.5 wird "Phase C.6 Training-Pool Expansion + Robustness Re-Validation" als NEW ACTIVE. Phase D bleibt NEXT+1 aber BLOCKED.
- `docs/model_registry.md`: V1 FX-Modell Status "Pending Re-Validation per ANN-015". Performance-Snapshot aus NB14 wird als "Historical (NB14 v1)" markiert.
- `docs/decisions/README.md`: ANN-015 in Index.
- `research/asset_generalization.md`: Neue Sektion "NB14f Findings + ANN-015 Re-Validation Plan" mit Cross-Link.
- `research/feature_experiments.md`: R-20 (siehe unten) als neues Research-Item.

### Neues Research-Item R-20 (HANDOFF Section 16a)

| ID | Risiko | Impact | Status | Owner | Mitigation |
|---|---|---|---|---|---|
| R-20 | **Training-Pool-Breite als Behavioral-Stability-Treiber** | hoch (V1-blockend) | aktiv (ANN-015) | Research | NB14f-v2-Run nach Pool-Expansion. Wenn pass: Pool-Breite war Bottleneck. Wenn fail: Architektur-Vertiefung nötig (NB16 Feature-Eng oder Optuna). |

### Phase-D-Blockade — Konsequenz für Roadmap

| Was | Vorher (NB14f-v1) | Nachher (ANN-015) |
|---|---|---|
| Phase C Status | ABGESCHLOSSEN | erweitert um "C.6 Re-Validation" |
| Phase D Status | NEXT+1, planbar | **BLOCKED bis Re-Run pass** |
| Phase E Status | NEXT+1 | unverändert (blockt sowieso auf D) |
| V1-Launch-Vorbereitung | aktiv | pausiert (~1–2 Tage Verschiebung) |

### Re-Test-Bedingungen — wann wird ANN-015 revisited?

ANN-015 ist **operational** (führt zu konkretem Re-Run). Nach dem Re-Run:

- **PASS-Path:** ANN-015 wird zu "Closed — successful pool expansion validated robustness". V1 geht in Phase D. Optional kommt eine `ANN-016` die den finalen Production-Lock dokumentiert.
- **FAIL-Path:** ANN-015 bleibt Active, ein Nachfolger-ADR (z.B. `ANN-016 Feature Engineering for FX Stability` oder `ANN-016 Pair-Tiering as V1 Standard`) wird geschrieben.

### Lessons (vorab, falls Re-Run pass)

1. **Behavioral-Stability ist trainings-data-sensitiv, nicht nur architektur-sensitiv.** Wer mit 2 Symbolen trainiert, bekommt brittle Cluster — egal wie sauber die Mechanik darüber ist.
2. **NB13's "FX generalisiert"-Verdict galt für `top-1%`-Cutoff, nicht für Cluster-Mechanik.** Cluster-basierte Cutoffs (ANN-013/-014) sind breiter und stellen härtere Anforderungen an Pool-Diversität. Das ist ein methodischer Punkt für künftige Cutoff-Strategie-Entscheidungen.
3. **Quality-Anchor war richtig (ANN-010 strict).** Wir wären ohne den Anchor bei Behavioral-FAIL auf den seed=1-GBPUSD-3.50-Wert reingefallen und hätten 30 Trades zur Production gelocked.

### Lessons (vorab, falls Re-Run fail)

1. **FX-Edge ist möglicherweise pair-spezifischer als bisher angenommen.** GBPUSD-Outperformance + AUDUSD/USDCHF-Schwäche aus NB14f ist ein konsistentes Muster.
2. **Cluster-Detection-Granularität muss verfeinert werden.** Vielleicht ist `rank=0`-Cluster zu breit; Rank-1 oder Rank-2 könnte den eigentlichen Premium-Kern besser einfangen.
3. **Feature-Set muss pair-aware werden.** Symbol-spezifische Features (Session-Offset, Macro-Driver) wurden bisher bewusst vermieden — könnte nötig werden.

---

**Linked Risks (HANDOFF Section 16a):** R-17 (hardcoded values), R-18 (multi-run robustness), R-19 (pair-tiering V1.5), **R-20 NEU (training pool width)**.

**Cross-Links:**
- [NB14f Run Snapshot (V1)](../../results/nb14f/summaries/nb14f_full_snapshot_2026-05-28.json) — Behavioral-FAIL Datenpunkt
- [research/asset_generalization.md](../../research/asset_generalization.md) — NB13 FX-Generalisierungs-Evidenz
- [ANN-014 §5](ANN-014-per-model-relative-cluster-behavioral-stability.md) — Pair-Tiering-Definition
- [HANDOFF Section 16a R-20](../../HANDOFF.md) — Risiko-Tracking
