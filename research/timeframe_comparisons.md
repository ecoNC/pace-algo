# Timeframe Comparisons — Phase C (NB14)

**Status:** ⏳ NOCH NICHT GESTARTET — wartet auf Phase B (NB13) Abschluss

Diese Datei enthält Plan + Hypothesen. Echte Zahlen kommen nach NB14-Run.

---

## Forschungs-Frage

**Welche Timeframes liefern die robustesten OOS-Ergebnisse?**

Konkret: trainiere separates Modell pro TF (5M, 15M, 30M, 1H, 4H) und vergleiche Premium-PF, Stability-CV, Trade-Frequency.

---

## Test-Setup (geplant)

| Element | Wert |
|---|---|
| Trainings-Daten | Phase-B-Sieger-Asset-Pool |
| Modell | Phase-A-Sieger-Architektur (vermutlich LightGBM) |
| Timeframes | 5M, 15M, 30M, 1H, 4H |
| HTF-Context | TF * 4 und TF * 16 für jedes Primary-TF |
| Tier-Cutoffs | VAL-derived pro TF |

**Vorbedingung:**
- `core/config.py PRIMARY_TIMEFRAMES` muss 30M unterstützen
- Dukascopy-Fetcher kann `INTERVAL_MIN_30`
- KuCoin kann `"30min"`

---

## Hypothesen

### H1: "Mittlere TFs (15M/30M) generalisieren am besten"

**Erwartung:** 15M und 30M sind der Sweet-Spot zwischen Noise (5M) und Trade-Frequency (1H/4H).

**Reasoning:**
- 5M: zu viel Noise, niedrige PF, hohe Trade-Count
- 1H/4H: zu wenige Trades für statistische Power, weniger Bars für Walk-Forward
- 15M/30M: genug Daten + sauberer als 5M

### H2: "Premium-Tier Trade-Frequency variiert stark"

**Erwartung pro Symbol:**
- 5M: ~3/Tag (NB11-Referenz)
- 15M: ~1/Tag
- 30M: ~0.5/Tag
- 1H: ~0.2/Tag
- 4H: ~0.05/Tag

**Konsequenz:** Längere TFs sind für aktive Trader uninteressant. V1-Default wahrscheinlich 5M oder 15M.

### H3: "Session-Features dominieren auf kurzen TFs, verschwinden auf langen"

**SHAP-Erwartung:**
- 5M: `hour_sin/cos` Top-3
- 4H: `hour_sin/cos` SHAP-Rang 20+

**Konsequenz:** Feature-Set könnte TF-spezifisch optimiert werden (aber: Pine-Budget zwingt zu universellem Set).

### H4: "Längere TFs sind stabiler über Jahre"

**Erwartung:** Stability-CV von 4H < 5M, weil weniger Trades = weniger Outlier-Jahre.

**ABER:** Wenn ein 4H-Modell in einem Jahr nur 20 Premium-Trades hat, ist die statistische Aussage ohnehin schwach.

---

## Erfolgs-Kriterien

Für eine **TF-Empfehlung** in V1 muss gelten:
- PF > 1.4 auf in-sample TEST
- PF > 1.3 auf cross-asset OOS (aus Phase B)
- Stability-CV < 0.25 über Jahre
- Mindestens 30 Premium-Trades pro Jahr (statistische Power)

**Vermutete Auswahl:** 5M + 15M als V1-Default, 30M+ als optional. 4H wahrscheinlich nicht V1.

---

## Was in /results/ landet

- `benchmark_tables/nb14_per_tf_pf_{date}.csv` — Tabelle PF pro TF × Tier
- `yearly_stability_tables/nb14_per_tf_stability_{date}.csv` — Stability-CV pro TF
- `json_exports/nb14_timeframe_comparison_{date}.json` — vollständiger Snapshot

---

## Implementierungs-Notizen für NB14

- Pro TF eine separate Model-Training-Schleife
- HTF-Context-TFs scalieren: für 5M → 1H+4H, für 15M → 1H+4H, für 30M → 4H+1D, für 1H → 4H+1D, für 4H → 1D+1W
- Daten-Volumen prüfen: 4H × 6.3 Jahre = nur ~14k Bars/Symbol. Pro-Symbol-PF wird sehr noisy.
- Eventuell pro TF einen anderen Asset-Pool aggregieren (auf 4H würden wir vielleicht nur 4-5 Top-Liquidity-Symbole nehmen)
