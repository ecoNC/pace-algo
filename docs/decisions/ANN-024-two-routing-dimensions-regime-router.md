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

## Nachtrag 2026-06-03 — Regime-Detektor routet AUCH die Exit-Geometrie (H-EXIT-Befund)

H-EXIT (Sweep 6 Märkte) hat gezeigt: der optimale Runner-Cap ist **regime-abhängig** — glatter
Trend will laufen (US500 D PF 1.38→3.13 ohne Cap), Chop will cappen (NAS100 4h 1.38→0.55 ohne
Cap). Damit hat der Regime-Detektor aus H-REGIME eine DRITTE Funktion (zusätzlich zu Gate +
Modul-Routing): **Exit-Routing.**
- Trend-Regime (ER hoch) → Runner darf laufen (Extended/Free).
- Range/Chop-Regime (ER niedrig) → Runner cappt (Capped @ RR).
Die Runner-Modi (`runnerMode`) sind deshalb bewusst KEIN User-Live-Toggle (Footgun), sondern
der Mechanismus, den der Router schaltet. Capped bleibt Live-Default bis der Router validiert ist.
Promotion auch hier nur klassen-/regime-weit OOS, nie per-Asset.

## ROUTER-CONTRACT v1 (Nico-locked 2026-06-03, nach H-EXIT + H-REGIME-ER)

Zwei saubere Negative haben den Router teil-spezifiziert. Lehre: **global-uniform trägt nicht,
pro Klasse/TF kalibriert kann tragen.** Der Router wird INKREMENTELL gebaut — ein validierter
Input nach dem anderen, kein Big Bang.

**Contract:**
- **Was der Router wählt:** Modul-/Verhaltenswahl pro Klasse (Trend-Core / MR / WAIT) UND
  per-Klasse/Regime-Parameter (z.B. Runner-Cap-Modus).
- **Input-Set v1:** `{ ER (per-Klasse/TF-Schwelle), cross-sektionale Confluence (klassen-gepaart:
  DXY→FX/Metalle, Alt↔BTC→Crypto) }`. Weitere Inputs nur, wenn sie scoped das Gate bestehen.
- **Promotion (unverändert):** per-Klasse OOS, „keine Klasse regrediert". Besteht ein Input das
  Gate scoped → promotet; sonst → raus, nächster Input.
- **Curve-Fit-Guard:** per-Klasse-Schwelle aus einer PRINZIPIELLEN Regel (z.B. fixes ER-Quantil
  über die Klassen-/Instrument-Historie), NIE per-Asset handgetunt. Validierung OOS ≥4 Assets/Klasse.

**Erster Validierungs-Zyklus (konkret):** ER-Runner-routing **klassen-skaliert** auf die Klassen
testen, wo es Signal zeigte = **Index-Daily + Metall-Daily** (Struktur aus dem H-REGIME-Sweep),
mit per-Klasse-Schwelle aus fixem ER-Quantil (gleiche Regel überall, self-calibrating pro
Instrument → kein Hand-Tuning). Besteht es scoped OOS → ER als Router-Input #1 promotet. Dann
Confluence als Input #2, gleiche Mechanik, nur in ihrer natürlichen Klasse.

**Produkt-Strang parallel (Nico):** Zwei Negative = Tier-A-Regel-Core sitzt an seiner ehrlichen
PF-Decke. Der Router ist ein **Coverage-Erweiterungs-Track** (holt Assets über Zeit von
WAIT/Tool-Only → Edge-Validiert) und läuft als EIGENER Strang. Parallel: Tier-A-Tool + ehrliche
Coverage-Labels auf dem bereits Laufenden Richtung verkaufbar polieren — kein Warten auf den
fertigen Router fürs Shipping.
