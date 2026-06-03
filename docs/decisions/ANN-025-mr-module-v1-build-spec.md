# ANN-025 — Mean-Reversion-Modul v1 (konkrete Build-Spec)

**Status:** ACCEPTED (Nico, 2026-06-03, „go" mit BB / ADX<18 / Single-TP)
**Kontext:** Umsetzung des MR-Moduls aus ANN-024 (zweite Routing-Dimension). Der Exit/Regime-
Knopf-Pfad ist erschöpft (3 Negative); MR ist der verbliebene echte Coverage/PF-Hebel —
eine NEUE Edge-Quelle in Range-Regimes, wo der Trend-Core strukturell schweigt.

## Architektur
- Neuer Input `Module` = `Trend-Core` (Default = bit-identisch Baseline) / `Mean-Reversion` / `Both`.
- MR nutzt dieselbe Trade-State- + Backtest-Maschine, eigener Entry/Exit-Zweig (`posKind`: 0=Trend, 1=MR).
- In Isolation testbar (Validierung) und additiv kombinierbar (Both).

## Signal-Logik (v1, gelockt)
- **Range-Gate (additiv, disjunkt zum Trend-Core):** MR feuert nur wenn `not trending` (Trend-Gate
  aus, per Konstruktion kein Overlap) UND `adxVal < 18` (Range-Bestätigung) UND Preis am Band-Extrem.
- **Band:** Bollinger, Länge 20, Mult 2.0 (`basis = SMA20`, `dev = 2·stdev20`). Skaleninvariant.
- **Entry (Reversal-Bestätigung, kein fallendes Messer):**
  - Long: `ta.crossover(close, lowerBB)` (Close kreuzt von unten zurück übers untere Band).
  - Short: `ta.crossunder(close, upperBB)`.
- **Ziel (Single-TP):** Band-Mitte `basis`.
- **Stop (jenseits des Bands = strukturelle Invalidierung):** Long `lowerBB − 0.5·ATR`,
  Short `upperBB + 0.5·ATR`.
- **Exit:** Single-TP an der Mitte + SL. Kein Multi-TP/Trail/BE. Win = Netto-R>0, R = Stop-Distanz.
  `closedR` am Ziel = `(basis − entry)/stopDist` (long) — variabel, geometrieabhängig.

## Validierungs-Plan (vor jedem Live-Status)
1. `Module=Mean-Reversion` ALLEIN auf range-lastige Assets OOS, ≥4/Klasse (FX-Chop EURUSD 5m,
   GBPUSD 1h; + Index/Metall/Crypto Range-Phasen).
2. Promotion-Gate: Klassen-Median-PF über Schwelle, KEINE Klasse regrediert, n ausreichend
   (harte Signifikanz-Regel der COVERAGE_MATRIX: n≥~30, Bootstrap-CI-Untergrenze>1.0).
3. Dann `Both`: bestätigen Trend-PF unverändert (additiv) UND MR füllt WAIT-Lücken.
4. Default bleibt `Trend-Core` bis MR das Gate besteht. Kein Live-Edge-Claim vorher.
   COVERAGE_MATRIX-Regime-Spalte: Range-Phasen wandern erst nach Promotion von WAIT → MR.

## Curve-Fit-Guard
- Parameter (BB 20/2.0, ADX<18, Stop-Buffer 0.5·ATR) global, nie per-Asset getunt.
- Promotion nur klassen-/regime-weit OOS (ANN-024). Ein Asset bekommt nie eigene Werte.

## Offen / später
- Recommended-Panel könnte bei Range-Regime auf MR hinweisen (UX-Guidance, nach Promotion).
- Regime-Router (auto Trend/MR/WAIT) bleibt die spätere Architektur-Stufe (ANN-024); v1 = manueller
  `Module`-Schalter für die Validierung.
