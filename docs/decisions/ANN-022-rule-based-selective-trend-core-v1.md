# ANN-022 — Rule-Based Selective Trend Core als V1-Signalgenerator

**Status:** ACCEPTED (Nico, 2026-06-02)
**Kontext:** Web-Session-Prototyp (pace_algo v6) + Forschungs-Session phase10–13 + Swift-Algo-Analyse.

## Entscheidung

1. **V1-Signalgenerator = regelbasierter, selektiver Trend-Core** (Pine-nativ, selbst-
   kalibrierend): ADX-Regime-Gate + Higher-TF-Alignment + **Pullback-Entry** (Rücksetzer
   im laufenden Trend, NICHT Erschöpfungs-Flip). Exit: fixes TP/SL (SL = Pullback-Struktur,
   geclampt 0.8–3.0 ATR; TP = RR × SL). Non-repaint, skaleninvariant.
2. **ML wird degradiert zu V1.5-Confidence-Overlay** — nur auf Klassen mit validiertem Edge
   (`docs/module_registry.md`). Export-Kette (NB15c/pine_codegen/bit-exact) GEPARKT, nicht gelöscht.
3. **WR-Verbesserung ausschließlich über SELEKTIVITÄT + RR-Geometrie, niemals über
   In-Sample-Optimizer** (Swift-Algo-Weg explizit abgelehnt: deren 144-Kombi-WR-Optimizer
   fittet sichtbare Historie; Anti-Curve-Fitting-Lock bleibt).

## Begründung

- Unabhängige Konvergenz: Web-Prototyp-Philosophie (Pullback im bestätigten Trend) =
  identisch mit den holdout-validierten Modulen INDEX-DIPBUY (PF 1.63 OOS, WR 73%) und
  METAL-TREND_L — zwei getrennte Wege, eine Wahrheit.
- TOOL ≠ EDGE (Produkt-Pivot 2026-06-01): das Tool muss überall laufen; Edge wird pro
  Klasse ehrlich nachgewiesen und zugeschaltet.
- Sub-Zufalls-WR des Flip-Entry-Prototyps (v2/v3) bewies live: Entry-Timing ist der Hebel.

## Konsequenzen

- Build-Reihenfolge: V1 Regel-Core validieren → V1.5a deterministische Klassen-Module via
  Router (DIPBUY, METAL-TREND_L — kein ML-Budget) → V1.5b FX-ML-Overlay (bit-exact) → V2 ANN-009.
- Recommended-Settings-Panel bleibt regime-basiert (Variante A, 0 Overfitting-Risiko);
  Variante B (out-of-sample Backtest-Empfehlung) optional später.
- Ehrliche WR-Erwartung Trend-Core: ~45–55%. Höhere User-WR (Swift-Algo-Gefühl) wird über
  RR-Geometrie (niedrigere RR-Defaults = strukturell höhere WR) und hoch-selektive Module
  (DIPBUY: 73% WR validiert) erreicht — nie über per-Asset-Fit.
