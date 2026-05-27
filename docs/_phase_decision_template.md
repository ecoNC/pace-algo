# Phase Decision Template

Pflicht-Format für jede neue Phase-Abschluss-Dokumentation und für ADRs in `/docs/decisions/`.

Kopiere die Struktur unten, fülle aus, lösche Hinweis-Texte (kursiv).

---

# {ANN-XXX | Phase X}: {Kurz-Titel}

**Status:** Active | Superseded | Deprecated
**Datum:** YYYY-MM-DD (UTC)
**Locked-By:** {HANDOFF Section 12 Rule oder leer}
**Related:** {[[andere ADRs]]}

---

## 1. Hypothese

*Was haben wir vorher angenommen oder vermutet?*
*Welches Problem wollten wir lösen oder welche Frage beantworten?*

Beispiel:
> "SMC-Features (FVG, BOS, CHoCH, Order Blocks) sollten messbaren Edge liefern, weil sie in der Trading-Community als hochwertig gelten."

## 2. Experiment

*Wie haben wir es getestet?*
*Welches Notebook, welche Daten, welche Splits?*
*Welche Hyperparameter wurden konstant gehalten?*

Mindestens benennen:
- Notebook: `NB##`
- Daten: Asset-Pool + TF + Zeitraum
- Splits: Train/Val/Test-Cutoffs
- Metrik: PF (Premium Tier) auf welchem Set
- Threshold: Ab wann gilt das Resultat als signifikant?

## 3. Resultat

*Was hat das Experiment quantitativ gezeigt?*
*Verlinke zur `/results/`-Datei.*

Mindestens:
- Hauptzahl (z.B. "Baseline-PF 1.80, Ablation ohne X: PF 1.56, Lift durch entfernen +0.24")
- Stabilität (Stability-CV oder per-year breakdown)
- Hold-Out-Generalisierung wenn anwendbar
- Quelle: `[results/...](../results/...)`

## 4. Decision

*Was haben wir entschieden?*
*Lock oder weiter offen?*
*Welcher Konsens war nötig (mit Nico)?*

Klare Aussage in einem Satz. Beispiel:
> "SMC-Features werden aus dem Modell entfernt. Lock — kein Re-Test ohne neue Datenquelle (Tick-Daten oder Order-Book)."

## 5. Konsequenz

*Was ändert sich dadurch?*
*Code (welche Files), Roadmap, Produkt-Architektur, andere Phasen?*

Konkrete Liste:
- Code: welche `core/`-Module betroffen
- Tests: welche Tests neu/geändert
- Doku: welche Files updated
- Roadmap: welche Phasen verschiebt sich
- ADRs: welche andere ADRs müssen jetzt eventuell updated werden

---

## Anti-Patterns (vermeiden)

❌ **"Wir haben es so gemacht weil es besser ist"** — ohne Zahlen. Eine ADR ohne /results/-Link ist eine Meinung, kein Fakt.

❌ **"Vielleicht später nochmal prüfen"** — entweder Lock oder explizite Re-Test-Bedingung formulieren.

❌ **"Komplex aber funktioniert"** — wenn Komplexität nicht justifiziert ist (z.B. durch Pine-Budget oder Backend-Migration), darf sie nicht ungetestet bleiben.

❌ **Vermischen von operativem und strategischem** — ADRs sind langlebig, HANDOFF Section 19 ist tagesaktuell. Klare Trennung.

## Patterns (anstreben)

✅ **Quantitative Aussagen mit Quelle** — "PF lift +0.06 (siehe results/...)"

✅ **Re-Test-Bedingungen explizit** — "Wenn wir Tick-Daten haben, neu testen"

✅ **Cross-Links** — `Related: [[ANN-001]]` macht Entscheidungs-Ketten sichtbar

✅ **Status-Updates** — Wenn eine ADR superseded wird, das alte File NICHT löschen, nur Status auf `Superseded` setzen und auf den Nachfolger linken
