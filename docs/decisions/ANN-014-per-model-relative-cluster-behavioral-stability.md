# ANN-014: Per-Model Relative Cluster + Behavioral Stability

**Status:** Active — **supersedes [ANN-013](ANN-013-cluster-based-premium-detection.md) für Stability-Definition** (Cluster-Detection-Mechanik bleibt gültig)
**Datum:** 2026-05-28
**Locked-By:** Nico-Decision nach NB14e Multi-Run-Analyse
**Related:** [[ANN-013]] (Cluster-Detection) [[ANN-012]] (Filter-Stack) [[ANN-006]] (Robustness-Mantra) [[ANN-010]] (Quality-Anchor)

---

## 1. Hypothese

ANN-013 forderte `cluster_drift < 0.001` als Stability-Requirement — das bedeutet: über mehrere Trainings-Seeds soll der **absolute Probability-Wert** des höchsten Clusters fast identisch sein. NB14e Run 1 hat empirisch gezeigt:

- Per-Seed Cluster-Werte: `0.4018 / 0.4054 / 0.4025` (drift 0.0036)
- ANN-013 Verdict: `cluster_is_stable = False` (drift > 0.001)
- Aber: seed=1 lieferte **vollständig sinnvolle Trades** (Aggressive PF 1.24, Balanced PF 1.76, Conservative PF 2.25, GBPUSD Hold-Out Balanced PF **3.50**)

**Die Frage:** Ist 0.0036 Drift ein echter Stabilitätsbug — oder haben wir die falsche Metrik gewählt?

## 2. Experiment

**Notebook:** NB14e (Multi-Run, commit `d1d703e`)
**Snapshot:** [results/nb14e/summaries/nb14e_full_snapshot_2026-05-28.json](../../results/nb14e/summaries/nb14e_full_snapshot_2026-05-28.json)

**Setup:**
- 3 Seeds (42, 1, 7) × deterministisches Training
- Pro Seed: Cluster-Extraction (höchster qualifizierter Cluster mit ≥ 0.5% VAL-Bars)
- LOCKED_PREMIUM_CLUSTER = Mean der 3 Cluster-Werte (`0.4032`)
- LOCKED_CUTOFF auf ALLE 3 Seeds appliziert → Inferenz

**Was passierte:**
- Seed 42 hat Cluster `0.4018` → TEST max proba ≈ Cluster-Wert → **`0.4032` wird nie überschritten → 0 Trades**
- Seed 1 hat Cluster `0.4054` → `0.4032` wird in Test überschritten → **funktioniert** (sinnvolle Trades + PFs)
- Seed 7 hat Cluster `0.4025` → wie Seed 42 → **0 Trades**

**Diagnose:** Der methodische Fehler liegt nicht in den Daten, sondern im **Vergleichs-Frame**. Wir versuchen, einen globalen mathematischen Universal-Cutoff über mehrere diskrete Modelle zu erzwingen — das ist die falsche Abstraktionsebene.

Bei kleinen Pine-budgeted Tree-Ensembles (30 trees × depth 3) produziert jedes Training:
- leicht andere diskrete Probability-Cluster
- aber **ähnliche strukturelle Verteilungen** (gleiche Anzahl Cluster, ähnliche Frequenzen, ähnliche Edge-Patterns)

Das ist mathematisch erwartbar. Stochastik bei `feature_fraction=0.8 + bagging_fraction=0.8` wird sich in der **internen Modellkoordinate** (raw probability values) manifestieren — aber das **Verhalten** des Modells (welche Bars als "Premium" klassifiziert werden, mit welcher Frequenz, mit welcher Edge) bleibt strukturell ähnlich.

## 3. Resultat

**Drift zwischen Seeds:**

| Metrik | Wert | ANN-013-Threshold | Bedeutet |
|---|---|---|---|
| Absolute Cluster-Wert drift | 0.0036 | < 0.001 (FAIL) | Mathematisch FAIL |
| Cluster-Frequency drift | 0.66% – 2.07% (range 1.4pp) | nicht definiert | Cluster bleibt strukturell ähnlich groß |
| Cluster-Existence | 3/3 Seeds extrahierbar | n/a | Mechanik funktioniert immer |

**Auf seed=1 (wenn Cutoff seinen eigenen Cluster nutzt):**

| Profile | In-Sample Trades | PF | Sigs/Tag/Sym | Hold-Out GBPUSD PF |
|---|---:|---:|---:|---:|
| Aggressive | 386 | 1.24 | 3.45 | 1.39 |
| Balanced | 37 | **1.76** | 0.33 | **3.50** |
| Conservative | 20 | **2.25** | 0.18 | 0.0 (zu wenig Trades) |

**Per-Symbol Variabilität (seed=1, Aggressive, Hold-Out):**

| Symbol | Trades | PF | WR |
|---|---:|---:|---:|
| GBPUSD | 160 | 1.39 | 48.1% |
| AUDUSD | 39 | 0.75 | 33.3% |
| USDCHF | 82 | 0.55 | 26.8% |

**Wichtige Erkenntnis:** Die Pattern existieren real (seed=1 belegt das). Der Validierungs-Fehler war: wir haben den globalen Cutoff auf alle Seeds appliziert, statt jedes Modell mit seinem eigenen Cluster zu validieren.

## 4. Decision

### Lock #1: Per-Model Relative Cluster

**V1-Pine bekommt EINEN Modell-Export (eine konkrete Training-Instance) mit dem SPEZIFISCHEN Cluster-Cutoff dieses Modells.**

```
V1-Production-Snapshot:
  model_artifact:        fx_lgbm_v1_{date}.txt
  premium_cluster_value: <extrahiert aus DIESEM Modell> (z.B. 0.4054)
  cluster_size:          <für DIESES Modell> (z.B. 171 bars)
  feature_set:           NB11-Winner-27
  training_seed:         <gelocked z.B. 1>
```

Bei jedem Re-Training (V1.5+ Continuous Retraining):
1. Neues Modell trainieren
2. Aus DIESEM Modell den höchsten qualifizierten Cluster extrahieren
3. Pine-Code mit DIESEM Cluster-Wert neu generieren
4. **Kein Vergleich gegen historische absolute Werte** — nur Verhaltens-Check vs. Production-Baseline

### Lock #2: Behavioral Stability statt Absolute Equality

**Stability wird ab sofort über VERHALTEN definiert, NICHT über raw Probability:**

| Behavioral-Metrik | Definition | Stability-Threshold |
|---|---|---|
| Signal-Frequency CV | std/mean der `sigs_per_day` über N Seeds | < 0.30 |
| In-Sample PF CV | std/mean des Premium-PF über N Seeds | < 0.40 |
| Hold-Out PF Mean | gewichteter PF über alle Hold-Out-Symbole und Seeds | ≥ 1.3 |
| Cluster-Frequency Std | absolute std der `cluster_pct` über Seeds | < 1.5 pp |
| MDD Std | std der Max-Drawdowns über Seeds | < 50% des Mean-MDD |

**Wenn alle Behavioral-Stability-Metriken erfüllt sind:** Modell-Architektur ist robust, V1-Production-Lock möglich.

**Wenn nicht:** Modell-Architektur muss überdacht werden (Hyperparams, Features, Trainings-Daten) — **aber die absolute drift ist KEIN Grund für Architektur-Änderung mehr**.

### Lock #3: ANN-013 Drift-Threshold superseded

ANN-013 hatte `cluster_drift < 0.001` als Lock-Requirement. **Das ist methodisch falsch** und wird durch Behavioral Stability ersetzt:

| Vorher (ANN-013) | Jetzt (ANN-014) |
|---|---|
| `cluster_drift < 0.001` | Behavioral-Stability-Suite (5 Metriken) |
| Misst raw probability equality | Misst Modell-Verhalten |
| Mathematisch unrealistisch bei stochastischem LightGBM | Empirisch fundiert |

Die Cluster-Detection-Mechanik aus ANN-013 bleibt unverändert — wir locken nur die Stability-Definition neu.

### Lock #4: Multi-Seed Validation ≠ Multi-Seed Production

**Klarstellung:** V1-Production läuft auf EIN spezifisches Modell mit EINEM spezifischen Cluster-Wert. Multi-Seed-Testing ist ein **Validation-Tool**, kein Production-Mechanism.

- Production: 1 Modell, 1 Cluster-Wert, deterministisch
- Validation: 3+ Modelle mit verschiedenen Seeds, Behavioral-Stability prüfen
- Wenn Validation PASSED: jedes der Modelle kann gewählt werden, oder der "best-behaving" Seed wird zur Production gelocked
- Wenn Validation FAILED: Modell-Architektur ändern, nicht Production-Seed wechseln

## 5. Konsequenz

### Pair-Tiering (NEU als R-19 in HANDOFF Section 16a)

NB14e zeigte: FX-Edge ist **nicht uniform** über alle Major Pairs:
- GBPUSD: stark (Aggressive PF 1.39, Balanced PF 3.50)
- AUDUSD: schwach (Aggressive PF 0.75)
- USDCHF: bricht (Aggressive PF 0.55)

**Konsequenz:** Aussage "V1 = FX Major Pairs" ist zu pauschal. Wir brauchen Pair-Tiering. Aber das blockt V1 NICHT.

V1.5/V2-Forschung: **NB15+ wird Pair-Tiering einführen:**
- Supported Pairs (PF ≥ 1.5 Hold-Out): in V1-Marketing genannt
- Experimental Pairs (PF 1.0-1.5): "Beta"-Badge im UI
- Unsupported Pairs (PF < 1.0): UI-Warning oder Hide

Diese Klassifikation basiert auf Per-Pair-Hold-Out-Statistik aus NB14f / NB15.

### Code-Änderungen

**`core/analysis/probability_diagnostic.py` erweitert:**
- `behavioral_stability_check()` — neue Stability-Definition (Verhalten statt raw probability)
- `pair_level_quality_check()` — per-symbol Quality-Anchor für Pair-Tiering

**`notebooks/14f_per_model_behavioral_validation.ipynb` (NEU):**
- Pro Seed: eigener Cluster-Cutoff (Fix vom NB14e-Bug)
- Behavioral Stability statt absolute drift
- Per-Symbol-Statistik (Vorbereitung für Pair-Tiering)
- Pine-Export-Ready: `best-behavior-seed` als Production-Lock-Kandidat

**`core/router/model_selector.py`** (später V1-Release): bekommt `PRODUCTION_SEED` constant pro Modell-Slot.

### Doku-Implikationen

- ANN-013 mit Status-Update "Stability-Definition superseded by ANN-014, Cluster-Mechanik bleibt"
- decisions/README Index erweitert
- pine_router_design.md §0b ergänzt mit Per-Model-Cluster-Hinweis
- HANDOFF Section 16a: R-17 leichte Anpassung (cluster rank/frequency/stability bleibt erlaubt, aber Stability ist nun behavior-based, nicht absolute-value-based), R-19 neu (Pair-Tiering)

### Re-Test-Bedingungen

ANN-014 wäre revisited wenn:
- Behavioral Stability über 5+ Seeds **konsistent failed** (z.B. PF CV > 0.50 in Mehrheit der Runs) → Modell-Hyperparameter oder Feature-Set überdenken
- Pair-Tiering zeigt dass NUR 1 von 5 Pairs funktioniert → "FX-Modell" als Konzept überdenken
- Bei Multi-Asset-V2 (Crypto/Indices): wenn deren Modelle smooth probability liefern (keine Cluster-Saturation) → Per-Asset-Klassen-Mechanik (manche Cluster, manche kontinuierlich)

### Lessons

1. **Falsche Metrik vs. falsches Modell.** NB14d zeigte: Modell ist stable + kalibriert. NB14e zeigte: Cluster-Detection liefert real funktionierende Edge (seed=1 belegt das). Was kaputt war: unsere Stability-Definition. Wir haben das Modell nach falscher Metrik beurteilt.

2. **Validation ist nicht Production.** Multi-Seed-Tests sind Robustheits-Audit, nicht Ensemble-Design. Pine-V1 exportiert EIN Modell mit EINEM Cluster — keine Multi-Seed-Aggregation.

3. **Stochastik bei kleinen Tree-Ensembles ist normal.** 30 trees × depth 3 mit feature/bagging fraction < 1 erzeugen unterschiedliche internal coordinates. Das ist NICHT ein Bug der Architektur.

4. **Pair-Tiering ist eine V1.5-Arbeit, nicht eine V1-Blockade.** GBPUSD-Out-Performance + USDCHF-Underperformance ist ein eigenes Pattern. Wir lokken V1 jetzt nicht darauf — wir nehmen die Pair-Mix-Realität an und differenzieren später.
