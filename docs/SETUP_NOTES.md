# PaceAlgo — Setup Notes (Onboarding / Support)

Kurze, wiederverwendbare Hinweise für Nutzer-Onboarding und Support-Prävention.
Diese Datei wächst zur Guide-Library; ein Eintrag = ein konkreter Stolperstein + Fix.

---

## TradingView behält beim Skript-Update die ALTEN Input-Werte

**Symptom:** Nach einem Indikator-Update (neue Version in den Pine-Editor gepastet, oder
neue Version vom Anbieter) verhält sich der Indikator auf einem **bereits geladenen Chart**
nicht wie die neuen Defaults erwarten lassen — z.B. tauchen Linien/Elemente auf, die laut
neuer Version standardmäßig aus sein sollten.

**Ursache:** TradingView speichert die Input-Einstellungen **pro Chart-Instanz**. Beim
Update eines bereits hinzugefügten Skripts werden die **gespeicherten alten Input-Werte
beibehalten** — geänderte *Defaults* der neuen Version greifen NUR bei einer **frisch
hinzugefügten** Instanz, nicht auf bestehenden Charts.

**Fix:** Nach einem Update einmal die Indikator-Settings öffnen →
**„Defaults" → „Reset settings"** (oder „Einstellungen zurücksetzen"). Damit übernimmt der
Chart die neuen Default-Werte. Alternativ den betroffenen Toggle manuell setzen.

**Konkretes Beispiel (2026-06-10):** „Show Entry / SL / TP lines" wurde auf Default *aus*
gestellt (saubereres Chart-Bild). Auf bestehenden Charts blieben die Linien + Marker
sichtbar, weil der alte Input-Wert (an) erhalten blieb. „Reset settings" → weg.

> Merksatz für den Onboarding-Guide: **„Nach jedem Update einmal Reset settings."**
