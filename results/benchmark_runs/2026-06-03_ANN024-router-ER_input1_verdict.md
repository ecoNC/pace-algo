# Benchmark-Run — ANN-024 Router Input #1 (ER-Runner-routing, klassen-skaliert) — Verdikt

**Datum:** 2026-06-03 (Heim-PC, TV 3.2.0, CDP)
**Test:** Erster Router-Validierungs-Zyklus. ER-Runner-routing, scoped per manuellem Klassen-Label
(`classSel`), nur Index + Metall (wo H-REGIME Signal zeigte). Schwelle = ER-Perzentil
(`ta.percentrank(er,200) ≥ 0.50`, self-calibrating pro Instrument = prinzipiell, kein per-Asset-Fit).
**Konstanten:** Balanced/Intraday/RR1.2, Full-History (OOS-Daily zu dünn). `Off` = Baseline (✓ US500 D 1.38/18t).

## Scorecard (Net PF / Trades, Off → Router-on)

| Markt | Klasse | Off | Router-on (q0.50) | Δ |
|---|---|---|---|---|
| US500  | Index  | 1.38 (18) | 1.29 (18) | −0.09 |
| NAS100 | Index  | 4.75 (12) | 8.75 (11) | +4.0 *(11t/1loss = Rauschen)* |
| GER40  | Index  | 1.25 (13) | 1.26 (11) | +0.01 |
| JPN225 | Index  | — | — | Feed n/a (CAPITALCOM) |
| GOLD   | Metall | 2.13 (12) | 2.48 (10) | +0.35 |
| SILVER | Metall | 1.50 (10) | 1.00 (9)  | **−0.50** |

**Klassen-Median-PF:** Index 1.38 → **1.29 (regrediert)** · Metall ~1.82 → **1.74 (regrediert)**.

## Verdikt — ER-Runner-routing BESTEHT DAS GATE NICHT (auch scoped). ER raus als Input #1.

- Beide In-Scope-Klassen-Mediane **regredieren**. Die einzigen klaren Plus sind GOLD (+0.35,
  konsistent mit H-REGIME) und NAS100 (+4.0, aber 11 Trades / 1 Loss = Rausch-Spike, kein Edge).
- US500 regrediert (−0.09) — derselbe Markt, der bei H-REGIME mit ABSOLUTER Schwelle 0.30 noch
  +0.10 hatte. Das Ergebnis ist **nicht robust gegen die Schwellen-Parametrisierung** → ein
  weiteres Footgun-Signal, kein Edge.
- SILVER (−0.50) und GER40 (flat) waren NICHT im H-REGIME-Sample — die dortige „Struktur" (US500+,
  GOLD+) war ein 2-Asset-Artefakt; über die VOLLE Klasse + prinzipielle Schwelle hält sie nicht.
- Per Router-Contract: **besteht nicht → ER raus, nächster Input.** Kein Schwellen-Fishing.

## Meta-Befund (der eigentliche Wert)

**Drittes Negativ-Ergebnis auf dem Exit/Regime-Knopf-Pfad** (H-EXIT → H-REGIME-ER → Router-ER).
Hinzu kommt eine harte Mess-Grenze: **Exit-/Runner-Routing lässt sich mit unseren Daten nicht
validieren** — Daily liefert nur 9–18 Trades (Full-History!), PF-Differenzen sind dort von 1–2
Trades dominiert (Rauschen); Intraday hat genug Trades, aber dort SCHADET Runner-Routing
(NAS100 4h, BTC 1h aus H-REGIME). Es gibt kein TF, auf dem der Hebel sauber UND positiv messbar ist.

→ **Der Trend-Core (Tier A) sitzt an seiner ehrlichen PF-Decke.** Exit-Geometrie und Single-Measure-
Regime-Gating auf dem bestehenden Core sind ausgereizt. Weiteres Knopf-Drehen ist negative
Erwartung an Erkenntnis-Gewinn.

## Empfehlung (Strategie-Fork an Nico)

Nicht Confluence als Router-Input #2 blind nachschieben (gleiche Daily-Dünnheit / Mess-Grenze
droht). Stattdessen die zwei Wege, die NICHT vom Exit-Knopf abhängen:
1. **Coverage-Track (echter Hebel):** das **MR-Modul für Range-Regimes** (ANN-024 Teil 2 Kern) —
   neue Trades wo der Trend-Core schweigt, nicht denselben Core feiner justieren.
2. **Produkt-Track (sofort verkaufbar):** Tier-A + ehrliche Coverage-Labels polieren; der Core ist
   an seiner Decke = gut genug zum Shippen, Coverage wächst als eigener Strang.

Router-Mechanik (classSel-Scaffolding) bleibt in git (`5ec23ae`) für den Confluence-/MR-Input
wiederverwendbar; ER-Wiring wird wieder zurückgebaut (Live = Baseline).
