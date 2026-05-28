# ANN-013: Cluster-Based Premium Detection (V1 Premium-Tier-Mechanik)

**Status:** Active — **supersedes Cutoff-Mechanik in [ANN-012](ANN-012-v1-tier-architecture-premium-core-plus-filters.md)** (Filter-Stack-Konzept bleibt gültig)
**Datum:** 2026-05-28
**Locked-By:** Nico-Decision nach NB14d Probability-Distribution-Diagnostik
**Related:** [[ANN-006]] (Robustheits-Mantra) [[ANN-009]] (Multi-Model-Router) [[ANN-010]] (Quality-Anchor) [[ANN-011]] (V1-TF + Whitelist) [[ANN-012]] (Premium-Core + Filters)

---

## 1. Hypothese

ANN-012 hat den Premium-Tier als **fixen Probability-Cutoff `0.4096`** gelockt — basierend auf NB14b's VAL top-1%. NB14c Run 1-3 lieferten widersprüchliche Ergebnisse (0 Trades / verwässerte Edge / 0 Trades), was die Frage aufwarf: ist das Modell instabil, oder ist der Cutoff-Mechanismus falsch?

NB14d wurde gebaut um diese Frage **datengetrieben** zu beantworten.

## 2. Experiment

**Notebook:** [notebooks/14d_proba_distribution_diagnostic.ipynb](../../notebooks/14d_proba_distribution_diagnostic.ipynb)
**Run-ID:** `nb14d_2026-05-28T06-51-09Z_81f2316` (commit `fbd0d23`)

**Setup:**
- 6 Trainings-Runs: seeds `[42, 1, 7]` × deterministic `[False, True]`
- Multi-Seed-Consistency-Test: cutoff_drift, max_proba_drift, stable_enough-Klassifikation
- Deterministic-Toggle-Diff: exakter Same-Seed-Vergleich (Correlation, RMSE)
- Cluster-Detection: distinkte Probability-Bands mit ≥10 Bars (4-Decimal-Aggregation)
- Calibration: Reliability-Curve + Expected Calibration Error (ECE)

## 3. Resultat

**Verdict-Klasse: C — Ultra-discrete Distribution, aber stable + well-calibrated**

| Test | Befund | Interpretation |
|---|---|---|
| Cluster top-3 (VAL) | **92.4%** aller Bars in 3 Werten | Ultra-discrete — Modell ist Pattern-Classifier, kein Confidence-Ranker |
| Cluster top-3 (TEST) | 76.8% | dito |
| `proba_test.max()` | 0.4018–0.4054 über 6 Runs | NB14b's `0.4096` ist **physisch unerreichbar** mit aktuellem Modell |
| Multi-Seed cutoff_drift | 0.00445 (< 0.005) | `stable_enough=True` — Multi-Run reproduzierbar |
| Multi-Seed max_proba_drift | 0.00362 (< 0.01) | dito |
| Deterministic Toggle RMSE | **0.0** | `deterministic=True` hat **ZERO Effekt** |
| Deterministic Toggle Correlation | **1.0** | identisches Modell |
| Calibration ECE (VAL) | 0.007 | well-calibrated (< 0.05) |
| Calibration ECE (TEST) | 0.012 | dito |

**VAL Distinct Clusters:**
```
  0.3965 → 63.5% (lowest cluster, ~no-edge band)
  0.3993 → 19.0%
  0.3950 →  9.9%
  0.3972 →  5.6%
  0.4018 →  2.1%  ← höchster Cluster ("Premium")
```

**Schlüssel-Erkenntnis:** Das Modell produziert KEINE kontinuierliche Confidence-Skala. Es produziert **6 diskrete Probability-Cluster**. Das ist die natürliche Konsequenz von:
- 30 trees × depth 3 (Pine-Budget)
- `is_unbalance=True`
- stark selektive FX-Patterns
- limitierte Feature-Dimensionalität

**Das ist KEIN Fehler.** Das ist die Modell-Architektur die Pine-Budget + Feature-Set erzwingen.

Quelle: [results/nb14d/summaries/nb14d_diagnostic_full_2026-05-28.json](../../results/nb14d/summaries/nb14d_diagnostic_full_2026-05-28.json).

## 4. Decision

**Cluster-Based Premium Detection wird gelocked als V1-Premium-Tier-Mechanik.**

### Was wird gelocked

| | Vorher (ANN-012) | Jetzt (ANN-013) |
|---|---|---|
| Premium-Tier-Definition | `probability >= 0.4096` (hardcoded) | `probability >= highest_stable_cluster_value` (dynamic) |
| Cutoff-Quelle | NB14b-Lucky-Run (Phantom-Wert) | Cluster-Detection bei jedem Training |
| Pine-Code | `PREMIUM_CUTOFF = 0.4096` hartkodiert | `PREMIUM_CUTOFF = <extracted-cluster-value>` (vom Codegen aus aktuellem Modell extrahiert) |
| Bei Re-Training | Cutoff hartkodiert, Drift unbemerkt | Cutoff wird neu extrahiert, V1.5-ready |

### Mechanik

Bei jedem Modell-Training (initial + Re-Training):

1. Predict auf VAL → `proba_val`
2. Cluster-Detection: `find_discrete_clusters(proba_val, decimal_places=4, min_cluster_size=10)`
3. Sortiere Cluster nach `value` absteigend
4. Wähle den höchsten Cluster der **mindestens 0.5% der VAL-Bars** enthält (statistische Mindest-Power)
5. `PREMIUM_CLUSTER_VALUE = highest_qualifying_cluster.value`
6. `PREMIUM_CUTOFF = PREMIUM_CLUSTER_VALUE` (für boolean mask `proba >= PREMIUM_CUTOFF`)
7. Multi-Seed-Stability-Check: 3 weitere Runs mit anderen seeds → der höchste Cluster sollte um ± 0.001 stabil bleiben
8. Wenn Cluster-Stability < ±0.001: Modell-Architektur ändern, NICHT Cutoff manuell setzen

### Produkt-Reframing (wichtige Marketing-Anpassung)

Das Modell ist KEIN probabilistischer Confidence-Ranker. Es ist ein **diskreter Pattern-Classifier**.

| Vorher (falsch) | Jetzt (korrekt) |
|---|---|
| "höhere Wahrscheinlichkeit eines Wins" | "bestätigtes Premium-Pattern erkannt" |
| "AI-Confidence-Score" | "AI-Pattern-Match" |
| "Top 1% Signal" | "Premium-Cluster-Signal" |

Diese Sprach-Anpassung ist:
- **Ehrlicher** (entspricht der tatsächlichen Modell-Struktur)
- **Leichter zu erklären** (Pattern erkannt vs. nicht erkannt — keine Wahrscheinlichkeits-Mathematik nötig)
- **Marketing-konsistent** mit ANN-006 Lock 4 (Honesty)

### Filter-Stack bleibt unverändert (Aus ANN-012)

3 Profile teilen denselben Cluster-Cutoff. Filter differenzieren:

| Profil | Filter-Stack |
|---|---|
| Aggressive | Premium-Cluster pur |
| Balanced | Premium-Cluster + HTF-Confirmation |
| Conservative | Premium-Cluster + HTF + NY-Session |

## 5. Konsequenz

### Neue Locked Rule (HANDOFF Section 12 Lock — wird als 28b ergänzt)

**"Keine absoluten Probability-Werte mehr hardcoden."**

Erlaubt:
- ✅ Cluster-Rank (z.B. "höchster Cluster", "2. höchster Cluster")
- ✅ Cluster-Frequency (z.B. "Cluster muss ≥ 0.5% der VAL-Bars enthalten")
- ✅ Cluster-Stability (z.B. "Cluster muss ± 0.001 stabil über 3 seeds sein")

Verboten:
- ❌ Hardcoded Probability-Thresholds wie `0.4096`
- ❌ Hardcoded Percentile-Cutoffs ohne Cluster-Verifikation
- ❌ Single-Run-basierte Cutoffs ohne Multi-Seed-Stability-Check

Begründung: Absolute Werte können zwischen Modell-Trainings driften (NB14c Run 1-3 belegt das). Die **Struktur der diskreten Cluster** bleibt aber stabil — wir locken die Struktur, nicht die Werte.

### Code-Änderungen

**`core/analysis/probability_diagnostic.py` erweitert:**
- `extract_premium_cluster(proba, min_cluster_size_pct=0.5)` → liefert höchsten qualifizierten Cluster
- `cluster_stability_test_multi_seed(...)` → Multi-Seed-Stability-Check
- `apply_cluster_cutoff_mask(proba, cluster_value)` → boolean mask für Premium-Bars

**`notebooks/14e_cluster_premium_calibration.ipynb` (NEU):**
- Cluster-Extraction
- Multi-Seed-Stability
- Cluster-Rank vs PF/WR-Map
- Filter-Profile auf Cluster-Cutoff
- Quality-Anchor-Check
- Multi-Run mean ± std (Nicos neue Regel)
- Pine-Export-Ready Cluster-Value

**`core/export/pine_codegen.py` (V2-Phase, später):**
- Liest extracted cluster value aus `core/models/fx/fx_lgbm_v1.json`
- Schreibt es als `PREMIUM_CUTOFF = <value>` in Pine-Code
- Bei Re-Training neu generiert

**`docs/pine_router_design.md` Update:**
- §0b mit Cluster-Mechanik (statt fixer Cutoff)
- §5 mit Pine-Code-Beispiel das extracted cluster value nutzt

### Roadmap-Implikation

**Phase C.5 (NB14e) wird zur "Cluster-Premium-Calibration":**
- ANN-013-Mechanik implementiert + validiert
- Multi-Run-Statistics (mean ± std über 3 seeds) für Premium-PF, Sigs/Tag, MDD
- Lock-fähige Werte für Pine-Export

**Phase D (NB15) bleibt:** Pine-Router-V1-Validation, jetzt mit Cluster-Cutoff statt hartcoded Value.

### Re-Test-Bedingungen (wann ANN-013 revisited werden müsste)

- Wenn ein neuer Modell-Run **mehr als 10 distinct cluster** produziert → Distribution wird kontinuierlicher → Probability-Cutoff-Mechanik könnte wieder sinnvoll sein
- Wenn Cluster-Stability über 3 seeds **schlechter als ± 0.005** ist → Modell-Architektur muss angepasst werden, dann ANN-013 neu evaluieren
- Wenn V1.5-Backend isotonic-calibration einführt → smooth proba möglich → ANN-013 evtl. neu denken

### Lessons

1. **NB14b's `0.4096` war ein Phantom-Wert.** Single-Run-basierte Cutoffs sind unwissenschaftlich. Nicos neue Multi-Run-Robustheits-Regel (mindestens 3 reruns mit mean/std) ist die Lehre.

2. **`deterministic=True` ist redundant in unserem Setup.** RMSE 0.0 / Correlation 1.0 zwischen toggled-Runs. Mein Run-3-Verdacht war falsch. Lehre: erst diagnostizieren, dann patchen.

3. **Modell-Struktur ≠ Modell-Verhalten.** Das gleiche Modell mit gleicher Architektur kann ULTRA-DISCRETE Probabilities produzieren (NB14d) statt smooth confidence. Pine-Budget zwingt zu dieser Struktur. Das ist okay, aber Produkt-Sprache muss das reflektieren.

4. **Diagnose-First-Workflow funktioniert.** Statt 4. NB14c-Iteration zu raten haben wir NB14d gebaut, die echten Daten gesehen, datenbelegt entschieden. Das ist exakt ANN-006 ("Folge den Daten").
