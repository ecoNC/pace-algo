# Benchmark-Run — H-EXIT Baseline (vor Trailing-Runner)

**Datum:** 2026-06-03 (Heim-PC, TV Desktop 3.2.0, CDP)
**Hypothese:** H-EXIT — Trailing-Runner statt TP2-Cap (Stufe 1 abschließen)
**Dies ist die BASELINE** (aktueller Stand: Multi-TP mit hartem TP2-Deckel @ RR).
**Konstanten:** Profile=Balanced · Style=Intraday · RR=1.2 · Multi-TP=on · `statsFrom`=2026-01-01 (OOS-Block).
**Feed:** CAPITALCOM (FX/Index/Metall), BINANCE (Crypto) — Suite-konform.

## Scorecard — 4 Anker-Märkte (OOS ab 2026-01-01)

| Markt | Net PF | Avg R | WR | Trades | TP2/Trail | BE/Loss | Max DD (R) | Regime (Recommended) |
|---|---|---|---|---|---|---|---|---|
| US500 D  | 1.25 | 0.13 | 50.0% | 4  | 2/0  | 0/2  | 2.0 | ADX 35.6 trending |
| GOLD D   | 1.25 | 0.13 | 50.0% | 2  | 1/0  | 0/1  | 1.0 | ADX 24.4 trending |
| BTC 1h   | 1.04 | 0.02 | 50.0% | 56 | 20/1 | 7/28 | 7.7 | ADX 59.7 trending |
| EURUSD 5m| 1.21 | 0.09 | 54.1% | 61 | 23/0 | 10/28| 5.8 | ADX 16.4 ranging (WAIT) |

## Befunde

1. **H-EXIT-These EMPIRISCH BESTÄTIGT:** Trail-Outcomes = 0/0/1/0 über alle 4 Anker.
   Der Runner wird praktisch nie über das Trailing in Gewinn beendet — er hängt am
   harten TP2-Deckel (RR=1.2R). Die seltenen großen Trendläufe (die den PF tragen)
   werden bei 1.2R abgeschnitten. Code-Ursache: `pace_algo_v1.pine` Z.203-205 / 224-226
   (`high >= tp2P` → Exit, capped `0.5*(1+rrRatio)`).
2. **Daily-OOS zu dünn für Arbitrierung:** US500 D = 4 Trades, GOLD D = 2 Trades
   (OOS-Block ~5 Monate). Auf Daily ist der OOS-Block statistisch nicht belastbar.
   Die Intraday-Anker (BTC 1h = 56, EURUSD 5m = 61) tragen das Entscheidungssignal.
   → Erwägen: für die H-EXIT-Arbitrierung zusätzlich Full-History auf den Daily-Ankern
     lesen (statsFrom=2024) ODER mehr Intraday-Messpunkte der Suite ziehen.
3. **EURUSD 5m OOS PF 1.21** (Coverage-Label „WAIT/PF 0.85" stammt aus Full-History) —
   das Recommended-Panel sagt aber korrekt WAIT (ADX 16.4 ranging). 2026-OOS war milder.

## Nächster Schritt

Trailing-Runner-Variante bauen (TP2-Deckel entfernen/weit hinausschieben), Re-Sweep,
PF BREIT vergleichen (≥4 Assets OOS). Design-Entscheidung an Nico offen (siehe Session).
