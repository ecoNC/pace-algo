# Benchmark-Run — H-EXIT Sweep + Verdikt (Trailing-Runner vs. TP2-Cap)

**Datum:** 2026-06-03 (Heim-PC, TV Desktop 3.2.0, CDP)
**Hypothese (H-EXIT):** Trailing-Runner statt TP2-Cap hebt den PF breit (Stufe 1 abschließen).
**Konstanten:** Profile=Balanced · Style=Intraday · RR=1.2 · Multi-TP=on. Feed: CAPITALCOM / BINANCE.
**Modi:** `Capped @ RR` (1.2R, = bisheriger Default) · `Extended 3R` · `Free trail` (kein Cap).
**Fenster:** Daily/4h = Full-History (OOS zu dünn, s.u.); 1h/5m = OOS ab 2026-01-01.

## Scorecard (Net PF je Modus)

| Markt | TF | Fenster | Regime | Capped | Extended | Free | Trades (Cap/Ext/Free) |
|---|---|---|---|---|---|---|---|
| US500   | D  | full | Trend (ADX 36)        | 1.38 | **1.90** | **3.13** | 18 / 12 / 7 |
| GOLD    | D  | full | Trend (ADX 24)        | **2.13** | 2.00 | inf* | 12 / 9 / 2* |
| NAS100  | 4h | full | Trend (ADX 23)        | **1.05** | — | **0.55** | 55 / – / 42 |
| GBPUSD  | 1h | OOS  | Trend (ADX 32)        | 0.85 | 0.85 | **1.01** | 26 / 21 / 16 |
| BTC     | 1h | OOS  | Trend-instant (ADX 60)| **1.04** | 1.00 | 0.99 | 56 / 51 / 40 |
| EURUSD  | 5m | OOS  | Range/WAIT (ADX 16)   | 1.21 | **1.23** | 1.13 | 61 / 49 / 31 |

\* GOLD D Free = **degeneriert**: nur 2 Closes (Runner reitet den gesamten Gold-Bull 2024–2026) → PF inf statistisch wertlos.

## Verdikt — H-EXIT (reine Form) ABGELEHNT als globaler Default

1. **Free trail ist NICHT robust — hohe Varianz, regredit mehrere Klassen.** Gewinnt groß auf
   glattem Trend (US500 D 1.38→3.13) und rettet GBPUSD 1h marginal (0.85→1.01), aber **zerstört
   NAS100 4h (1.05→0.55, Total R −9.9)** und kostet BTC 1h + EURUSD 5m. Der breite SuperTrend-
   Trail gibt auf allem außer dem glattesten Trend zu viel zurück. **Verletzt das Promotion-Gate
   (keine Klasse darf regredieren) hart.**
2. **Extended 3R** = milder, gemischt: US500 +0.52, aber GOLD −0.13 / BTC −0.04 / EURUSD +0.02.
   Klärt die +0.05-breit-ohne-Regression-Hürde NICHT. Kein globaler Default.
3. **Capped @ RR bleibt Default** — einziger Modus, der KEINE Klasse regredert; bestes oder
   gleichauf bestes Ergebnis auf GOLD / NAS100 / BTC / EURUSD. Nur auf US500 D klar geschlagen.

## Die eigentliche Erkenntnis (für H-REGIME / ANN-024)

Der **TP2-Cap ist NICHT der PF-Engpass**, den die Hypothese annahm. Der Engpass ist die **Trail-
QUALITÄT**: der breite adaptive SuperTrend (≈2.5·ATR) schützt Runner-Gewinne schlecht. Das
Cap-Lockern hilft nur, wo der Trend so glatt ist, dass der weite Trail selten getriggert wird
(US500 Daily) — und schadet, wo es innerhalb des Trends choppy ist (NAS100 4h). **Die Exit-
Geometrie ist ein regime-/TF-abhängiger Hebel, kein universeller.** → gehört in den Regime-Router
(ANN-024), nicht in einen globalen Default.

## Konsequenzen / nächste Schritte

- **Code bleibt:** 3 Modi als User-wählbar ausgeliefert, **Default `Capped @ RR`**. Kein Marketing-
  Claim. Power-User auf glatten Daily-Trends können Extended/Free opt-in wählen (ehrlich dokumentiert).
- **H-EXIT (Stufe 1) = abgeschlossen mit sauberem Negativ-Ergebnis** für die reine Free-Trail-Form.
- **Neue Folge-Hypothese H-EXIT-v2 (notiert, eigene Iteration):** engerer/besserer Runner-Trail nach
  TP1 (Chandelier/ATR-Ratchet statt des weiten Regime-SuperTrends) — fängt Trend OHNE den Giveback.
- **Größerer Hebel laut Leiter:** **H-REGIME** (Stufe 2) — ein besseres Trend/Chop-Maß; es würde
  gleichzeitig steuern, WANN man den Runner laufen lässt (Trend) vs. cappt (Chop). Empfehlung: als
  nächste Iteration H-REGIME, das den Exit-Modus mit-routet.
- **Hinweis Mess-Methodik:** Daily-/4h-OOS-Block (ab 2026) ist mit 2–4 Trades nicht arbitrierbar →
  für Daily/4h Full-History lesen (hier so gemacht); 1h/5m haben belastbare OOS-Counts.
