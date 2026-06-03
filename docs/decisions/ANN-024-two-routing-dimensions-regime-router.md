# ANN-024 — Two Routing Dimensions: Class Router + Regime Router

**Status:** ACCEPTED (Nico, 2026-06-02)
**Kontext:** Edge-Ausbau-Roadmap (Web-Session). Der Trend-Core verliert auf vielen
Assets/TFs strukturell, weil sie in RANGING-Regimes sind — ein Trend-Follower kann dort
nicht gewinnen. Breite Coverage entsteht NICHT durch Erzwingen des Trend-Cores in Ranges
(unmöglich/Curve-Fit), sondern durch ein zweites, regime-passendes Modul.

## Entscheidung

**Coverage = VEREINIGUNG regime-passender Edges.** Zwei orthogonale Routing-Dimensionen:

1. **KLASSEN-Router (ANN-009, bestehend):** nach Asset-Klasse (FX / Indizes / Metalle /
   Crypto) — adressiert Mikrostruktur (Session/RTH/Weekend).
2. **REGIME-Router (NEU):** nach Markt-Regime innerhalb des Assets:
   - Trend-Regime → Trend-Core (bestehend)
   - Range-Regime → Mean-Reversion-Modul (NEU, eigenständig validiert)
   - Transition/unklar → WAIT

**MR-Modul:** Fade an Band-Extremen mit Rückkehr zur Mitte (Bollinger/Keltner-Band oder
RSI-Extrem im bestätigten Range-Kontext), Ziel = Range-Mitte, Stop jenseits des Bands.
Skaleninvariant (ATR/Band-basiert). **NUR in Range-Regimes aktiv.**

Der Regime-Detektor (aus Hypothese H-REGIME, siehe roadmap) ist GLEICHZEITIG der
Router-Schalter — ein Maß, zwei Funktionen (Gate + Routing).

## Curve-Fit-Verbot (hart)

Das MR-Modul wird NUR promotet, wenn es OOS über die KLASSE bzw. regime-weit besteht
(Benchmark-Maschine, ≥4 Assets, PF breit). **NIE per-Asset gefittet.** Ein Modul, das nur
ein Asset rettet, ist Overfit und wird verworfen. Wo kein regime-passender Edge besteht →
WAIT, keine 100%-Coverage erzwingen.

## Konsequenzen

- COVERAGE_MATRIX bekommt eine REGIME-Dimension: pro (Asset, TF) das zuständige Modul
  (Trend / MR / WAIT) + OOS-Status.
- Der Coverage-Sprung (MR-Modul + Regime-Router) ist ein größeres Vorhaben → eigener
  Zyklus, NACH den universellen Verstärkern (H-EXIT, H-REGIME, H-CONFLUENCE).
- ML-Overlay (V1.5) bleibt die letzte Sprosse, rankt Signale beider Module.
