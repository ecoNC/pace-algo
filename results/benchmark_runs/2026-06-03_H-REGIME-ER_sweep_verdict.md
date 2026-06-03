# Benchmark-Run — H-REGIME (Efficiency Ratio) Sweep + Verdikt

**Datum:** 2026-06-03 (Heim-PC, TV 3.2.0, CDP)
**Hypothese (H-REGIME):** Kaufman Efficiency Ratio (ER) trennt Trend/Chop besser als das grobe
ADX-Gate und hebt den PF breit — über (a) Runner-Routing (ER hoch → Runner läuft, sonst Capped)
und (b) Entry-Gate (nur traden wenn ER effizienten Trend bestätigt).
**Prior (Nico-locked, kein Buffet):** ER allein. `erLen=10`, `erTrend=0.30` (Kaufman-Konvention), global.
**Konstanten:** Balanced/Intraday/RR1.2. Daily/4h Full-History, 1h/5m OOS 2026. `Off` = bit-identisch Baseline (Sanity ✓ auf allen 6).

## Scorecard (Net PF / Trades)

| Markt | Klasse | TF/Fenster | Off | Runner-routing | Entry-gate | Both |
|---|---|---|---|---|---|---|
| US500  | Index  | D / full  | 1.38 (18) | 1.48 (17) | 3.75 (4)* | 2.55 (3)* |
| NAS100 | Index  | 4h / full | 1.05 (55) | **0.98 (49)** | 1.21 (15) | 0.61 (10) |
| GOLD   | Metall | D / full  | 2.13 (12) | 2.48 (10) | inf (2)* | – |
| BTC    | Crypto | 1h / OOS  | 1.04 (56) | **0.90 (51)** | **0.95 (20)** | – |
| EURUSD | FX     | 5m / OOS  | 1.21 (61) | 1.24 (57) | **0.95 (10)** | – |
| GBPUSD | FX     | 1h / OOS  | 0.85 (26) | 0.85 (26) | **0.33 (5)** | – |

\* Frequenz-Kollaps (≤4 Trades) — Metrik degeneriert, nicht belastbar.

## Verdikt — ER (dieser Prior) BESTEHT DAS PROMOTION-GATE NICHT

- **Runner-routing:** hilft US500 +0.10 / GOLD +0.35 / EURUSD +0.03, aber **regrediert NAS100 4h
  −0.07 (in-scope!)** und BTC −0.14. Index-Median bleibt flach. → „keine Klasse regrediert" verletzt.
- **Entry-gate:** einziger belastbarer In-Scope-Gewinn = NAS100 4h (+0.16, 15t); aber **Frequenz-
  Kollaps auf Daily** (US500 18→4, GOLD 12→2 = degeneriert) und **regrediert FX hart** (EURUSD
  1.21→0.95, GBPUSD 0.85→0.33) + BTC. → klar durchgefallen.
- **Both:** überall dominiert (US500 2.55/3t, NAS100 0.61).
- **Kein Schwellen-Tuning** versucht (verboten). EIN prinzipieller Prior getestet, er trägt nicht.

## Strategische Erkenntnis (wichtiger als das Einzelergebnis)

**Zweites sauberes Negativ-Ergebnis in Folge** (H-EXIT, jetzt H-REGIME-ER). Beide universellen
Verstärker (roadmap §7 **Teil 1**) scheitern am selben Grund: die Märkte sind **echt regime-/TF-
heterogen**, ein einzelnes globales Maß (ADX, ER) bzw. eine globale Exit-Geometrie hebt den PF
nicht breit — was Klasse A hilft, schadet Klasse/TF B (ER-Routing: GOLD +0.35 vs. NAS100 4h −0.07;
ER-Gate: NAS100 4h + vs. FX −). Auch der Runner-Giveback (H-EXIT) ist mit einem Entry-Maß nicht
fixbar, weil der Trend WÄHREND der Runner-Phase zerfällt.

→ **Empfehlung: Teil 1 (universelle Verstärker) ist ausgereizt; Pivot auf Teil 2 — den
architektonischen Hebel (Klassen-/Regime-Router, ANN-024).** Die ehrliche Antwort auf „das
richtige Verhalten ist regime-verschieden" ist Routing, nicht ein weiterer globaler Knopf.

## Konsequenzen

- **ER-Research-Wiring wird zurückgebaut** (kein Footgun-Toggle ausliefern; Live = bit-identisch
  Baseline). ER-Implementierung bleibt in git-History (Commit `d0b13c7`) — **wiederverwendbar als
  Mess-Größe für den ANN-024-Router**, wo ER pro Klasse/Regime (nicht als globaler Knopf) greift.
- Runner-Modi bleiben router-gated intern (Capped live), wie nach H-EXIT.
- **Nächste Iteration → Nico-Call:** Teil 2 (H-MR + Regime-Router, ANN-024) als eigener Zyklus —
  ODER vorher H-CONFLUENCE (Teil 1, letzter universeller Versuch: cross-sektionale Bestätiger).
  Empfehlung: ANN-024-Router, da die Daten zweimal dorthin zeigen.
