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

## Konsequenz / nächster Schritt

- MR-Modul-Code bleibt (Commit `d0a5150`, Default Trend-Core, EXPERIMENTAL-Label in ANN-025) —
  konzeptionell validiert, aber **nicht live-promotbar mit dem ADX<18-Gate.**
- **MR v2 = besserer Range-Filter** (die eigentliche Arbeit): echte Range-Bestätigung statt
  ADX<18 — z.B. Preis seit N Bars im Band eingeschlossen / keine jüngste impulsive Bewegung /
  ADX fallend UND niedrig. Das ist die Range-Detektions-Hypothese, die H-REGIME (Trend-Seite)
  spiegelt. Ein Maß, das Trend/Range sauber trennt, schaltet GLEICHZEITIG: Trend-Core-WAIT,
  MR-Aktivierung, Runner-Modus. = der zentrale verbleibende Hebel.
- COVERAGE_MATRIX-Regime-Spalte: Range-Phasen bleiben WAIT (MR nicht promotet).
