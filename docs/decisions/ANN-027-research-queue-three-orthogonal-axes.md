# ANN-027 — Research Queue: Three Orthogonal, Untested Axes

**Status:** Active (queue defined; experiments not yet run)
**Datum:** 2026-06-10 (UTC)
**Locked-By:** Robustness-First Mantra ([ANN-006](ANN-006-robustness-first-mantra.md)); Promotion-Gate unverändert (kein Feature ohne ≥ +0.05 PF OOS-Lift; Walk-Forward; VAL-Cutoffs only)
**Related:** [ANN-022](ANN-022-rule-based-selective-trend-core-v1.md) (Trend-Core), [ANN-023](ANN-023-exit-model-and-win-accounting.md) (Exit-Modell), [ANN-024](ANN-024-two-routing-dimensions-regime-router.md) (Regime-Router, CLOSED), [ANN-025](ANN-025-mr-module-v1-build-spec.md) (MR, parked)

## Kontext

CEO-Pivot 2026-06-10: ein universeller Indikator, Produkt konvergiert auf die eigene
Website-Copy. Die bisher geschlossenen Forschungs-Tracks waren allesamt **Selektions-Filter**
(welche Signale fallen weg) + **Exit-Geometrie** (H-EXIT, H-REGIME-ER, ANN-024 Router-Input #1 —
alle drei negativ, Trend-Core sitzt an seiner ehrlichen PF-Decke). Diese Queue eröffnet **drei
orthogonale Achsen**, die noch nie getestet wurden — je 1 Hypothese, ≥ 4 Assets/Klasse OOS.

## Hypothese (je Achse)

**Reihenfolge (Prior-gewichtet): H-SESSION → H-TRIGGER → H-TIMESTOP.** Jede einzeln durch die
Benchmark-Suite (`docs/BENCHMARK_SUITE.md`), sauber dokumentiert, bei Fail ehrlich geschlossen.

### H-SESSION — Session-/Time-of-day-Gate (höchster Prior, hat bereits Evidenz)
- **Achse:** WANN handeln (Tageszeit), auf Intraday-TFs.
- **Evidenz:** Eigene Phase-3/4-Forschung — FX **1.27 mit NY-Gate vs 1.11 ohne** (der einzige Filter
  mit bereits gemessenem positivem Effekt; siehe `docs/phase3_4_state_and_goalfit.md`, Vision-Update
  HANDOFF §1).
- **Test:** prinzipielle Session-Definition, klassen-skaliert — London/NY-Overlap für FX,
  Cash-Session für Indizes. KEIN per-Asset-Fit der Session-Fenster.

### H-TRIGGER — Entry-Trigger-Qualität (neue Achse: WO einsteigen, nicht OB)
- **Achse:** Entry-Location am Pullback-Ende — Momentum-/Engulfing-Bar-Bestätigung statt erstem Touch
  (`ta.crossover(close, fastEma)`).
- **These:** bessere Entry-Location → engerer struktureller SL → mehr TP1-Hits bei gleichem Setup →
  hebt WR + PF über **Geometrie** statt Selektion. Nie getestet.

### H-TIMESTOP — Zeit-Stop (neue Achse: tote Trades schneiden)
- **Achse:** Trades, die nach N Bars weder TP1 noch strukturellen Fortschritt zeigen, zu Markt
  schließen. Orthogonal zu allen getesteten preis-basierten Exits.
- **These:** senkt Loss-Größe + Hängepartien (Feel-Faktor). Prior moderat.

## Experiment (Gate, unverändert)

- Benchmark-Suite v1.0: 4 Assets/Klasse × 4 Klassen = 16 Messpunkte, OOS-Block ab 2026-01-01.
- Promotion nur bei **≥ +0.05 PF OOS-Lift** (Klassen-Median) ohne Regression auf einer in-scope Klasse.
- Walk-Forward / VAL-Cutoffs only — Holdout bleibt unangetastet. Kein In-Sample-Optimizer.

## Decision

Queue **definiert und gelockt**, Experimente noch **nicht** gestartet. Jede Achse ist ein
eigenständiger Pass mit eigenem Benchmark-Run-Doc unter `results/benchmark_runs/`. Promotion einer
Achse in den Pine-Core nur nach bestandenem Gate; sonst ehrlicher Close als ANN-Nachtrag.

## Konsequenz

- Keine Code-Änderung am V1-Core durch dieses ADR (reiner Decision-Record).
- Nächster Forschungs-Schritt nach dem CEO-UI-Pivot: **H-SESSION** zuerst (höchster Prior).
- Parallel, eigene fokussierte Session: FX-Overlay „Pace AI" (Site verspricht es wörtlich) —
  Gates unverändert (50t/100t-Reconcile zuerst, bit-exact = harter Ship-Gate, OOS-PF des tatsächlich
  geshippten Modells oder kein Ship). UI-Label „Pace AI — signal quality scoring", aktiv auf FX-Majors.
  Siehe [ANN-026](ANN-026-fx-ship-model-reconcile.md).
