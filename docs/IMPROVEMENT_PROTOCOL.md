# PaceAlgo — Improvement Protocol (verbindliches Designprinzip, 2026-06-02)

**Die Verbesserungs-Maschine ist eine GESCHLOSSENE SCHLEIFE. Kein freies Tweaken.**

## Die Schleife

1. **Messen:** Benchmark-Suite (`BENCHMARK_SUITE.md`) — fix, versioniert, OOS-Split →
   Standard-Scorecard pro Messpunkt.
2. **Detektieren:** `needs-work` wenn OOS-PF < 1.1 **oder** Erwartungswert R ≤ 0 auf
   einem in-scope-Messpunkt (Coverage-Matrix ≠ WAIT).
3. **Iterieren (Protokoll):**
   - **EINE prinzipielle Hypothese** pro Iteration (kein Bündel, kein Knopf-Drehen)
   - OOS über die **GANZE Klasse** validieren (≥ alle Suite-Messpunkte der Klasse)
   - **Promotion-Gate:** Median-PF der Zielklasse steigt **UND keine andere Klasse
     regrediert** → behalten. Sonst: verwerfen oder Asset/Klasse → WAIT/Tool-Only.
   - ML-Hebel erst, wenn Regel-Hebel erschöpft sind.
4. **Dokumentieren:** Scorecard-Run in `results/benchmark_runs/`, Coverage-Matrix
   aktualisieren, HANDOFF §19.

## Autonomie-Grenze (hart)

**Claude Code DARF autonom:** Suite laufen lassen · scoren · detektieren · EINE
Hypothese implementieren und messen · berichten · Coverage-Matrix-WERTE updaten.

**Claude Code DARF NICHT autonom:**
- PF gegen WR tauschen (PF ist Primärmetrik — Tausch ist CEO-Call)
- Schwellen senken, damit etwas „besteht"
- Per-Asset-Sonderfälle/Parameter einführen (Optimierung NUR auf Klassen-Ebene)
- einen Edge behaupten/Status auf `Edge-Validated` heben ohne OOS-Beleg
→ Diese vier sind **Nicos Call**, immer.

## Verbesserungs-Leiter (Reihenfolge der Hebel)

**Exit-Geometrie → Selektion → Klassen-Router (ANN-009) → ML-Overlay (V1.5).**
Jede Stufe läuft DURCH die Schleife oben. Details: `roadmap_2026-06-01.md` §6.

## Ehrlichkeits-Boden

Bleibt ein Asset trotz aller Stufen bei PF ~1.0 → **WAIT**. Dort nicht traden, keinen
Edge faken. Ziel ist „≥50% WR / PF >1.2 überall wo wir FEUERN" — nicht überall feuern.

## Präzedenzfälle (kalibrieren das Urteil)

- ✅ **HTF-Gate (iter2):** eine Hypothese, breit gemessen, WR überall +, Verluste im
  Chop gedrittelt → behalten. Musterbeispiel.
- ⚠️ **Multi-TP+BE (iter3):** WR überall +, aber PF NICHT breit gestiegen (US500
  1.15→1.14, GOLD flat, BTC 1.01→0.85). Per Disziplin-Regel **kein Perf-Gewinn** →
  eingestuft als **Varianz-/UX-Feature**: Exit-Modus bleibt TOGGLE (Single vs. Multi),
  **Crypto default Single-TP**. So vermarkten (Risk-Mgmt, nicht Edge). (ANN-023)
- ❌ **ADX-Persistenz (iter2):** Hypothese gemessen, wirkungslos (94→94 Trades) →
  ehrlich dokumentiert, kein Wert behauptet.
