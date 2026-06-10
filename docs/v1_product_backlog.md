# PaceAlgo V1 — Produkt-Backlog (PIVOT 2026-06-10)

**Kontext:** Ein universeller Indikator (`pace_algo_v1`), alle Assets/TFs (Swift-Algo-Kategorie, hochwertiger).
**Messlatte (neu):** PF ≥ ~1.0 breit (kein Ausbluten) + WR-Optik + DD-Gefühl + Plausibilität — NICHT „validierter
Edge oder nichts". **Ehrlichkeits-Floor (nicht verhandelbar):** keine gefitteten WR-Versprechen; kein „AI-Edge"-Claim
ohne Validierung; Live-Backtest deskriptiv. **Anti-Curve-Fit:** kein In-Sample-Optimizer als Edge verkauft;
Verbesserungen über diverse Assets gegen-gecheckt; **Ops-Kosten je Feature VOR Einbau via `estimate_pine_ops` proben.**

**Ops-Budget-Stand:** `pace_algo_v1` aktuell ~1867 ops = **37%** Budget → ~63% Headroom (5000 ops/bar Heuristik).
Alle Schätzungen unten sind grob + VOR Build per Draft-Probe zu bestätigen. **Noch NICHTS gebaut.**

---

## Priorität 1

### (a) Signal-Grading A/B/C je Signal
**Was:** Jedes Buy/Sell-Signal bekommt eine Güte-Note (A/B/C) aus **Regime-Stärke (ADX) + MTF-Confluence**
(wie viele TFs im Dashboard stimmen mit der Signalrichtung). Anzeige als Suffix am Label („BUY A" / „SELL C").
**Ops-Schätzung:** sehr billig — reine Vergleiche auf **schon berechneten Serien** (adxVal, MTF-Trends, ATR-Pctile),
keine neuen `request.security`. ~+30–80 ops (~1–2% Budget). Vor Build proben.
**Effekt auf Messlatte:** HOCH. Trennt A-Setups (klarer Trend + Confluence) sichtbar von C-Setups (Chop) →
WR-Optik ↑, Plausibilität ↑, DD-Gefühl ↑ (User filtert auf A). **Adressiert direkt den BTC-1m-Befund:**
Verlust-Signale im Chop sind dann sichtbar C-grade, nicht ununterscheidbar von echten Trend-Setups.
**Guardrail:** Grade ist regime-/confluence-abgeleitet (deskriptiv), KEIN Win-Prob-Claim.

### (d) Multi-TP-Default-Frage neu bewerten
**Was:** Unter der neuen Messlatte (DD/WR-Optik zählt) neu entscheiden: `useMTP` (TP1@1R + BE + Trail) vs Single-TP
als Default. ANN-023 hielt fest: Multi-TP = Varianz-/UX-Feature, kein PF-Gewinn — aber jetzt zählt WR-/DD-Optik,
und Multi-TP hebt genau die.
**Ops-Schätzung:** **0** (reine Default-Entscheidung, Logik existiert).
**Effekt:** MITTEL. Multi-TP-an → höhere WR-Optik + glattere Equity (TP1 sichert früh) = besseres „Gefühl".
**Vorgehen:** Cross-Asset-Messung WR/DD/PF mit MTP an vs aus auf diversen Charts → Nico-Entscheidung. Kein Curve-Fit
(Strukturentscheidung, nicht per-Asset).

---

## Priorität 2

### (b) Sensitivity-Achse als User-Regler (Swift/Flux-Standard)
**Was:** Ein prominenter Regler „mehr vs. selektivere Signale". **Existiert bereits teilweise** als `sens`-Input
(int −2..+2, füttert ADX-Schwelle/Trend-Bänder/Pullback). Aufgabe: als primäre Frequenz/Qualität-Achse ausbauen +
klar labeln (UX wie Swift/Flux).
**Ops-Schätzung:** niedrig — Mechanik vorhanden, ggf. +0–30 ops für feinere Stufung/Display.
**Effekt:** MITTEL–HOCH. User-Agency über Frequenz/Qualität = Kategorie-Standard, steigert wahrgenommenen Wert + „Feel".
**Guardrail:** Regler ändert Selektivität, NICHT verkaufte Performance; mehr Signale ≠ mehr Profit (im Tooltip ehrlich).

---

## Priorität 3 (höchstes Potenzial, höchste Sorgfalt — probe-first)

### (c) Klassen-Bewusstsein light
**Was:** Asset-Klasse via `syminfo` erkennen → **destillierte Research-Heuristiken** als leichte Anpassungen:
FX → NY-Session-Gewichtung; Index → Dip-Buy-Neigung; je Klasse passende Regime-Gates. Nutzt die Priors aus der
Research (FX-NY-Edge, INDEX-DIPBUY), OHNE die geparkten ML-Module.
**Ops-Schätzung:** moderat + feature-abhängig — `syminfo`-Detection billig; je Heuristik (z.B. Session-Stunden-Gewicht
= kein security; Dip-Buy-Tiefe = ein Pullback-Check) grob +20–60 ops. Gesamt grob +50–150 ops. **Je Heuristik VOR
Einbau einzeln proben** (Nico-Lock).
**Effekt:** HOCH (Potenzial). Tool fühlt sich „pro Markt klug" an ohne per-Asset-Fit → breitere PF + Plausibilität.
**Guardrail (kritisch):** NUR **Klassen-Ebene** + destillierte Research-Priors, über diverse Assets gegen-gecheckt.
KEIN per-Asset-Tuning, KEIN In-Sample-Optimizer. Wo eine Heuristik nicht breit hält → raus, kein Forcieren.

---

## Reihenfolge-Empfehlung
1. **(a) Signal-Grading** — billigster + größter Hebel auf die neue Messlatte, fixt den Chop-Signal-Befund.
2. **(d) Multi-TP-Default** — 0 Ops, schnelle WR/DD-Optik-Entscheidung nach Cross-Asset-Messung.
3. **(b) Sensitivity-Regler** — größtenteils vorhanden, ausbauen + labeln.
4. **(c) Klassen-Bewusstsein** — höchstes Potenzial, aber Ops-Probe + Anti-Curve-Fit-Sorgfalt je Heuristik.

**Querschnitt vor jedem Build:** Draft → `estimate_pine_ops` → erwarteter Messlatten-Effekt benennen → bauen →
Cross-Asset-Sanity (kein Ausbluten) → Compile-Check. Ein Feature/Iteration.
