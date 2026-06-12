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

### H-SESSION — Session-/Time-of-day-Gate (höchster Prior, hat bereits Evidenz) — ✅ GESCHLOSSEN 2026-06-10
- **Achse:** WANN handeln (Tageszeit), auf Intraday-TFs.
- **Evidenz:** Eigene Phase-3/4-Forschung — FX **1.27 mit NY-Gate vs 1.11 ohne** (der einzige Filter
  mit bereits gemessenem positivem Effekt; siehe `docs/phase3_4_state_and_goalfit.md`, Vision-Update
  HANDOFF §1).
- **Test:** prinzipielle Session-Definition, klassen-skaliert — London/NY-Overlap für FX,
  Cash-Session für Indizes. KEIN per-Asset-Fit der Session-Fenster.
- **VERDIKT (gelockt 2026-06-10, 2 Runden, kein 3. Fenster):** **moderater Qualitäts-Faktor,
  Hard-Gate verworfen (Kosten 44–76 % Frequenz für +0.1–0.3 PF)** — *kein* „Edge". Pre-registriertes
  GRÜN nicht geräumt (Kriterium (a) per Buchstabe: Index erreicht keine 2 verwertbaren Punkte,
  Suite-Abdeckungs-Limit). Substanz real & breit gerichtet (FX 2–3/3 +, Metal 2/2 +, Index 2/2
  gerichtet aber unterpowert, Crypto-Kontrolle flach/invers). **Geparkt als Grade-Faktor-Kandidat**
  fürs Produkt-Verdikt (Session als Input im A/B/C-Grading ODER Toggle Default-AUS).
  **Crypto-Ausschluss explizit:** fließt Session später ins Grading ein, ist der Faktor für **Crypto
  AUS** (Kontrolle flach/invers, kein positiver Crypto-Session-Effekt). Belege:
  `results/benchmark_runs/2026-06-10_h-session.md`, Probe `deploy_pine/experiments/pace_algo_v1_HSESSION_probe.pine`.
- **Lehrstück (Protokoll-Selbstbeweis):** GER40 1h zeigte Runde 1 **+0.82 PF @ n=13/13** → über
  95 Trades (Runde 2) nur **+0.23, IN netto 0.95**. Der „starke" Star-Punkt war Klein-Sample-
  Rauschen. Die Runde-1-WAIT-Disziplin (kein Cherry-Pick auf GER40) hat sich damit selbst bewiesen
  → **Klein-Sample-GRÜNs bleiben verboten** (min-Bucket-n-Schwelle + Einzelpunkt-Rausrechen-Check
  sind Pflicht in jeder Hypothese-Runde).

### H-TRIGGER — Entry-Trigger-Qualität (neue Achse: WO einsteigen, nicht OB) — ❌ GESCHLOSSEN/WIDERLEGT 2026-06-10
- **Achse:** Entry-Location am Pullback-Ende — Momentum-/Engulfing-Bar-Bestätigung statt erstem Touch
  (`ta.crossover(close, fastEma)`).
- **These:** bessere Entry-Location → engerer struktureller SL → mehr TP1-Hits bei gleichem Setup →
  hebt WR + PF über **Geometrie** statt Selektion. Nie getestet.
- **VERDIKT (gelockt 2026-06-10, Spec A = einzige Definition, 1 Runde statsFrom=2025):** **WIDERLEGT
  — invers.** Momentum-Confirmation (Body ≥ 50 %) hebt PF/WR NICHT; auf gut gepowerten FX- und
  Metall-Punkten sind die **NONCONF-Entries (ruhige Crossover-Bars) systematisch besser** (SILVER
  −0.86, GOLD −0.50, GBP −0.23 CONF−NONCONF PF, jeweils auch höhere WR). Einziger Positiver GER40 1h
  (+0.32) → trägt den „Effekt" allein → (b) verfehlt. Kriterium (a) klar nicht erfüllt (FX 0/2,
  Metal 0/2 positiv). Crypto gemischt/flach. **Kein Engulfing-Nachschub (Spec-Lock), kein Round 2
  (gut gepowerte Punkte eindeutig, keine Starvation-Maskierung).** Beleg:
  `results/benchmark_runs/2026-06-10_h-trigger.md`, Probe `…/experiments/pace_algo_v1_HTRIGGER_probe.pine`.
- **Kurzform (gelockt):** widerlegt — invertiert auf gepowerten Punkten; **CONF verliert PF UND WR**
  → keine Geometrie, Extension-Mechanismus plausibel; **GER40-Einzelpunkt kein Override.**
- **Post-hoc-Beobachtung (NICHT verifiziert, NICHT als H-TRIGGER-Rebrand verfolgt):** „ruhiger
  Pullback-Entry nahe EMA schlägt decisive-bar-Entry" — plausibel (Momentum-Bar = Preis extended).
  Höchstens eigene, neu pre-registrierte Hypothese am Queue-Ende, niedrige Prio — und dann **als
  Grade-Faktor-Kandidat interessanter denn als Gate** (ruhige Entry-Bar = höheres Grade), gleiche
  Schublade wie der Session-Faktor aus H-SESSION.

### H-TIMESTOP — Zeit-Stop (neue Achse: tote Trades schneiden) — ⏸ GESCHLOSSEN/WAIT 2026-06-10 (teil-positiv)
- **Achse:** Trades, die nach N Bars weder TP1 noch strukturellen Fortschritt zeigen, zu Markt
  schließen. Orthogonal zu allen getesteten preis-basierten Exits.
- **These:** senkt Loss-Größe + Hängepartien (Feel-Faktor). Prior moderat.
- **Spec (gelockt):** N_punkt = round(2 × Median-Bars-bis-TP1 der Baseline-TP1-Gewinner), k=2 fix
  (ersetzt „struktureller Fortschritt"); Guards: Median nur Baseline, ≥10 Gewinner sonst nicht-
  verwertbar. Dual-Engine-A/B-Probe (kausaler laufender Median), 1 Runde statsFrom=2025.
- **VERDIKT (gelockt 2026-06-10): WAIT — kein breites GRÜN, aber stärkste der 3 Achsen.** Strikte
  Kriterien gerissen: **Metal scheitert (a)** (GOLD4h −0.04, SILVER1h −0.04 → 0/2); nur **Index**
  räumt das +0.05-Gate (NAS100 4h +0.58, GER40 1h +0.25, beide WR↑), **FX** positiv aber sub-
  threshold (+0.02…+0.05), Crypto flach (Kontrolle ok; positive Crypto-Lifts durch große Entry-
  Deltas confounded). **Mechanismus real wo positiv** (AvgLossR 1.00→0.68–0.84, Dauer↓, **DD stark↓:
  GER40 19.1→10.2**) bei **null Frequenz-Kosten**. Kein Round 2 (entscheidende Klassen gut gepowert).
  Beleg: `results/benchmark_runs/2026-06-10_h-timestop.md`, Probe `…/pace_algo_v1_HTIMESTOP_probe.pine`.
- **Folge-Kandidat (NICHT jetzt, kein Rebrand):** „Zeit-Stop nur Index/FX, DD-fokussiert" als eigene
  neu pre-registrierte Hypothese — der no-cost-DD-Effekt rechtfertigt das, aber nicht als Override
  des gerissenen broad-Kriteriums.

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
- ~~Nächster Forschungs-Schritt nach dem CEO-UI-Pivot: **H-SESSION** zuerst (höchster Prior).~~
  → H-SESSION ✅ geschlossen 2026-06-10 (moderater Qualitäts-Faktor, kein Hard-Gate).
  → H-TRIGGER ❌ geschlossen/widerlegt 2026-06-10 (Momentum-Confirmation invers).
  → H-TIMESTOP ⏸ WAIT/teil-positiv 2026-06-10 (kein broad GRÜN; realer no-cost DD-Effekt Index/FX).
  **ANN-027-Queue ERSCHÖPFT** — alle 3 orthogonalen Achsen getestet. Status: Active → abgearbeitet.
- Parallel, eigene fokussierte Session: FX-Overlay „Pace AI" (Site verspricht es wörtlich) —
  Gates unverändert (50t/100t-Reconcile zuerst, bit-exact = harter Ship-Gate, OOS-PF des tatsächlich
  geshippten Modells oder kein Ship). UI-Label „Pace AI — signal quality scoring", aktiv auf FX-Majors.
  Siehe [ANN-026](ANN-026-fx-ship-model-reconcile.md).
