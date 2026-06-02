# PaceAlgo — Benchmark-Suite (Messfundament der Verbesserungs-Maschine)

**Zweck:** Fixe, versionierte Mess-Suite. JEDE Signal-/Exit-Hypothese läuft über diese
Suite — vorher/nachher, gleiche Assets, gleiche TFs, gleiches Scorecard-Format. Keine
Iteration zählt ohne Suite-Lauf.

**Version:** v1.0 (2026-06-02). Änderungen an Asset-Liste/Split = neue Version + Vermerk.

## Asset+TF-Matrix (fix — 4 pro Klasse, 16 Messpunkte)

| Klasse | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| FX-Majors | EURUSD 5m | GBPUSD 1h | USDJPY 4h | USDCAD Daily |
| Indizes | US500 Daily | NAS100 4h | GER40 1h | JPN225 Daily |
| Metalle | GOLD Daily | GOLD 4h | SILVER Daily | SILVER 1h |
| Crypto | BTCUSDT 1h | BTCUSDT 4h | ETHUSDT 1h | SOLUSDT 4h |

(Symbole: CAPITALCOM für FX/Indizes/Metalle, BINANCE für Crypto — Feed konstant halten.)

## Train/OOS-Split

- **Soll-Zustand:** Indikator bekommt einen `Stats from date`-Input (nächste Code-
  Iteration); Scorecard liest ZWEI Blöcke: Full-History und **OOS = ab 2026-01-01**
  (rollt jährlich). Entscheidungsmaßstab ist der OOS-Block.
- **Übergangszustand (bis Input existiert):** Full-History-Werte, explizit als
  *preliminary* gekennzeichnet (siehe COVERAGE_MATRIX-Vermerk).
- Die deterministischen Module (DIPBUY etc.) haben ihre eigenen, härteren OOS-Standards
  (Walk-Forward/Holdout) in der Python-Pipeline — diese Suite misst den PINE-Core.

## Scorecard-Format (pro Messpunkt)

| Feld | Quelle |
|---|---|
| Net PF | Backtest-Panel „Net PF" |
| Erwartungswert (Avg R) | „Avg R" |
| WR | „Win Rate" |
| Max DD (R) | „Max DD (R)" |
| Trades | „Trades" |
| Outcome-Split | „TP2 / Trail" + „BE / Loss" |
| Regime z. Messzeitpunkt | Recommended-Panel (ADX/Vola/Suggestion) |

**Detektions-Schwellen (needs-work):** OOS-PF < 1.1 **oder** Avg R ≤ 0 auf einem
Messpunkt, der laut Coverage-Matrix in-scope (nicht WAIT) ist.

## Ausführung (wiederholbare TV-MCP-Routine)

Claude-Code-Prozedur pro Lauf (automatisierbar, ~16 × 30s):
1. `chart_set_symbol` + `chart_set_timeframe` für jeden Messpunkt der Matrix
2. `data_get_pine_tables(study_filter="PaceAlgo")` → Scorecard-Felder extrahieren
3. Ergebnis als Markdown-Tabelle in `results/benchmark_runs/<datum>_<hypothese>.md`
4. Vorher/Nachher-Vergleich pro Klasse: **Median-PF der Klasse** + Einzelwerte
5. COVERAGE_MATRIX.md aktualisieren (Datum, Werte, ggf. Status-Vorschlag an Nico)

Konstanten pro Lauf: Profile=Balanced · Style=Intraday · RR=1.2 · Multi-TP=on
(Crypto-Messpunkte zusätzlich mit Multi-TP=off, solange Single-TP dort Default ist).
Abweichungen nur, wenn die HYPOTHESE genau diese Einstellung betrifft — dann beides messen.
