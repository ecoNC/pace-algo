# Benchmark-Run — MR-Modul v1 (ANN-025) Erst-Validierung

**Datum:** 2026-06-03 (Heim-PC, TV 3.2.0, CDP). Build-Commit `d0a5150`.
**Test:** `Module=Mean-Reversion` ALLEIN, OOS (statsFrom 2026, 5m-Charts laden ohnehin nur jüngste History).
BB(20,2.0)-Fade, Range-Gate `not trending AND ADX<18`, Ziel Band-Mitte, Stop jenseits Band.
**Korrektheit:** `Module=Trend-Core` reproduziert exakt die Baseline (NAS100 1h 1.25/109t) ✓. MR feuert + backtestet kohärent ✓.

## Scorecard (Module=Mean-Reversion, OOS)

| Asset | Klasse | TF | PF | n | WR | Total R | Max DD (R) | Regime 2026 |
|---|---|---|---|---|---|---|---|---|
| GBPUSD | FX | 1h | **1.31** | 35 | 45.7% | 4.6 | 4.7 | ranged → MR trägt |
| EURUSD | FX | 5m | 1.03 | 115 | 39.1% | 1.5 | **16.7** | gemischt, hohe DD |
| EURUSD | FX | 1h | **0.54** | 50 | 30.0% | −13.6 | 15.2 | EUR-Rally → MR fadet Trend |
| NAS100 | Index | 1h | 0.85 | 47 | 36.2% | −3.0 | 8.4 | Bull-Trend |
| BTCUSDT | Crypto | 1h | **0.32** | 55 | 21.8% | −20.8 | 20.8 | starker Trend (ADX 62) → Fade tödlich |

## Verdikt — MR v1 BESTEHT DAS GATE NICHT (Default bleibt Trend-Core)

- **Mehrere harte Regressionen:** BTC 1h −20.8R, EURUSD 1h −13.6R, NAS100 1h −3R. MR verliert
  überall, wo das Asset 2026 trendete — die kurzen ADX<18-Dips sind dort **Fortsetzungs-Setups,
  kein Reversionsstoff**; das Fade läuft in den Trend und wird jenseits des Bands gestoppt.
- **Konzept-Beleg positiv:** GBPUSD 1h (genuin gerangt 2026) = **PF 1.31, DD 4.7, n35** — saubere,
  tragfähige Zahl. Fading FUNKTIONIERT in echten Ranges. Das Modul selbst ist richtig gebaut.
- **Der Engpass ist die RANGE-ERKENNUNG, nicht das Fade:** `ADX<18` ist zu grob — es trennt echte
  Range nicht von Trend-Pullback. Genau dieselbe Regime-Detektions-Schwäche wie bei H-REGIME und
  beim Trend-Core-WAIT. **Range-Detektion ist die gemeinsame, blockierende Abhängigkeit für jede
  Coverage-Erweiterung.**

## NACHTRAG 2026-06-03 — MR v2 (Range-Filter) + Bugfix, korrigierter Sweep

⚠️ Die v1-Zahlen oben waren durch einen Zähler-Bug verfälscht (Impuls-Bar-Entry ÜBER der Band-
Mitte → sofortiger als „TP2" gelabelter Verlust; nTP2 > wins). **Fix `15eb99d`:** MR-Entry nur wenn
`close < bbBasis` (long) / `close > bbBasis` (short). **v2 `c4a25de`:** Range-Bestätigung
`htfFlat` (kein dominanter HTF-Trend) + `basisFlat` (Mitte driftet nicht) zusätzlich zu ADX<18.

| Asset | TF | PF | n | Total R | DD | vs. v1 |
|---|---|---|---|---|---|---|
| GBPUSD | 1h | **2.61** | 6 | 3.2 | 1.0 | 1.31 → 2.61 |
| NAS100 | 1h | **2.56** | 4 | 1.6 | 1.0 | 0.85 → 2.56 (gedreht +) |
| BTC | 1h | 0.35 | 7 | −3.3 | 3.3 | −20.8R → −3.3R (Blutung −80%) |
| EURUSD | 1h | 0.03 | 6 | −4.9 | 5.0 | verliert weiter |

**Befunde:** (1) Bugfix verifiziert — nTP2==wins jetzt konsistent. (2) htfFlat-Filter ist
RICHTUNGSWEISEND korrekt: NAS100 dreht positiv, BTC/EURUSD-Trade-Zahlen eingedampft (55→7, 50→6),
Blutung −80%. (3) ABER: **alle n=4–7 → weit unter Signifikanz (n≥30) → nichts promotbar.** (4)
BTC/EURUSD lecken weiter Verlust-Trades (PF<1) — der Filter hält die hart trendenden 2026-Assets
nicht ganz draußen.

## MR-v2-Verdikt: richtungsweisend validiert, NICHT promotbar (zu streng / zu dünn)

Der Range-Filter funktioniert (Trend-Fades raus, echte Ranges rein → GBPUSD/NAS100 jetzt 2.6),
aber er ist SO streng, dass kein Asset einen signifikanten Sample hat, und auf hart trendenden
Assets sickern noch ein paar Verlust-Fades durch. → Default bleibt Trend-Core, kein Live-Status.

**Optionen (Nico-Gabel):** (a) Filter LOCKERN (z.B. nur `htfFlat`, `basisFlat` raus → mehr Trades
bei erhaltenem Anti-Trend-Schutz) und auf range-DOMINANTEN Assets mit n≥30 testen; (b) MR parken,
auf Produkt/Ship + FX-Overlay-Entparken pivotieren (Coverage-Matrix: verkaufbarer Edge = Tier B).

## NACHTRAG 2 — MR v3 (Gate gelockert: nur htfFlat, basisFlat raus), OOS-Sweep

Hypothese: v2 zu streng (n=4–7) → basisFlat raus = mehr Trades bei erhaltenem htfFlat-Anti-Trend-Schutz.

| Asset 1h | v2 (htfFlat+basisFlat) | v3 (htfFlat only) |
|---|---|---|
| GBPUSD | 2.61 / 6t | **4.33 / 15t** ✅ |
| BTC | 0.35 / 7t / −3.3R | **0.33 / 20t / −10.0R** ✗ (mehr Blutung) |
| EURUSD | 0.03 / 6t | 0.78 / 20t / −2.4R (besser, weiter <1) |
| NAS100 | 2.56 / 4t | **0.90 / 12t** ✗ (schlechter) |

**Verdikt v3: Wash-zu-negativ.** Lockern hilft GBPUSD massiv (echte Range → 4.33), degradiert aber
BTC/NAS100 (mehr Trend-Fades). basisFlat tat doch nützliche Arbeit. Kein globaler Gate-Setpoint
(ADX<18 / +htfFlat / +basisFlat) trennt Range/Trend sauber über alle Assets.

## MR-FORSCHUNG ABGESCHLOSSEN (v1/v2/v3) — geparkt

Drei Iterationen, ein konsistentes Ergebnis: **MR ist zuverlässig gut NUR auf genuin rangenden
Assets** (GBPUSD 1h: 1.31→2.61→4.33 über die Versionen) und **kein globales Range-Gate hält es aus
Trend-Fades** auf trendenden Assets. **Der Engpass ist die Range-DETEKTION — dasselbe ungelöste
H-REGIME-Problem — nicht das Filter-Tuning.** Modul de-exposed (Footgun), Logik bleibt. Re-aktivieren
nur mit (a) echtem Range-Detektor ODER (b) per-validierter-Klassen-Routing (Metall <4 Symbole, Crypto
geschlossen blockieren das aktuell). Weiteres Filter-Tweaken = negative Erkenntnis-Erwartung → gestoppt.

## Konsequenz / nächster Schritt

- MR-Modul-Code bleibt (Commit `d0a5150`, Default Trend-Core, EXPERIMENTAL-Label in ANN-025) —
  konzeptionell validiert, aber **nicht live-promotbar mit dem ADX<18-Gate.**
- **MR v2 = besserer Range-Filter** (die eigentliche Arbeit): echte Range-Bestätigung statt
  ADX<18 — z.B. Preis seit N Bars im Band eingeschlossen / keine jüngste impulsive Bewegung /
  ADX fallend UND niedrig. Das ist die Range-Detektions-Hypothese, die H-REGIME (Trend-Seite)
  spiegelt. Ein Maß, das Trend/Range sauber trennt, schaltet GLEICHZEITIG: Trend-Core-WAIT,
  MR-Aktivierung, Runner-Modus. = der zentrale verbleibende Hebel.
- COVERAGE_MATRIX-Regime-Spalte: Range-Phasen bleiben WAIT (MR nicht promotet).
