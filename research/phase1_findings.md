# Phase 1 Findings — NB05 bis NB11

**Zeitraum:** Phase 0 (Frühjahr 2026) bis 2026-05-26
**Endpunkt:** NB11 — FX-only Premium PF 2.015

---

## TL;DR

NB11 lieferte einen FX-only Premium-Tier PF von **2.015** auf 27 Features mit 30-tree / depth-3 LightGBM. Das ist **Research-Baseline**, nicht Produktziel. Der Wechsel zum **Universal-Indikator-Ziel am 2026-05-26** macht NB11 zur Vergleichsmessgröße für alle zukünftigen Experimente — KEIN Optimierungsziel.

> Lesson: Hoher Single-Asset-PF ist NICHT der Produkt-Erfolg. Die Frage ist, ob diese Edge auf BTC, SPY, Gold etc. überlebt. Antwort kommt in Phase B (NB13).

---

## Erfolgsfaktoren

### 1. Triple-Barrier-Labeling (Marcos López de Prado)

R=1.5 TP / R=1.0 SL produziert sauberere Labels als statische horizon-Labels. Klare Win/Loss/Neutral-Trichotomie statt arbitrary regression target.

### 2. VAL-derived Tier-Cutoffs

Nach NB08-Bug (cutoffs aus TEST → optimistic bias) lockten wir das ab: cutoffs werden NUR aus VAL-Set abgeleitet. Premium = top 1% von VAL-Probability-Verteilung.

> Lesson: Data leakage via cutoff-Definition ist subtil und tödlich. Niemals TEST-set für ANY cutoff/threshold/hyperparameter-Tuning verwenden.

### 3. Walk-Forward-Validation

Train < Val < Test strikt nach Zeit. Random shuffling war nie eine Option für Time-Series. Cross-fold CV wurde nie verwendet.

### 4. HTF-Interaktions-Features

`htf_ltf_agree_bull` lieferte +0.06 PF in Ablation. Multi-TF-Übereinstimmung ist messbar relevant. Andere HTF-Features (`htf_1h_rsi_14`, `htf_1h_atr_percentile_100`) sind ebenfalls high-SHAP.

### 5. ATR-Normalisierung

Alle Distanz-Features (`dist_to_swing_low_atr`, `ema_20_dist_atr`) sind ATR-normalisiert. Macht Features asset-vergleichbar und robust gegen Vola-Regime-Wechsel.

---

## Misserfolge (Was NICHT funktioniert hat)

### 1. SMC / Smart Money Concepts

FVG, BOS, CHoCH, Order Blocks, Liquidity Pools — alle SHAP-dead bei intraday-Frequenzen. Die theoretische Plausibilität von SMC ist hoch, die empirische Edge ist null.

> Lesson: Trading-Theorien klingen gut, Daten regieren. Wenn SHAP "dead" zeigt, ist es dead — auch wenn YouTube anderes behauptet.

### 2. Macro-Features auf Intraday

VIX, DXY, TNX als Daily-Inputs: SHAP-dead für 5M/15M Predictions. Bleibt in `core/features/macro.py` für eventuelle Daily-V2-Modelle, nicht aktiv für V1.

### 3. Meta-Labeling (NB06)

Primary-Rule (z.B. RSI-overbought + EMA-cross) als Filter, ML als Magnitude-Predictor: Premium-PF 1.06, marginal. Problem: unsere Primary-Rule hatte PF 0.99 (random). Meta-Labeling auf einem random Primary funktioniert nicht.

### 4. 37-Feature-Set (NB05)

Zu viele Features für 30 Trees. SHAP zeigte 17–21 Features als komplett dead. Lift kam nur von 16–20 Features → Reduktion.

### 5. Full 57-Feature-Phase-1 (NB11 Iteration)

Versuch alle möglichen Features einzubauen: PF 1.53 < Baseline 1.80. Noise-Overload. Reduktion auf 27 Features war der Winning-Move.

### 6. Gold-only Optimierung

XAUUSD-only PF: 1.03 (random). Gold ist im FX+Gold-Pool eine Belastung — Combined-PF sinkt, wenn Gold drin ist. Wurde aus dem Trainingsset für FX-Modell entfernt.

> Lesson: Asset-Selection ist ein Feature. Nicht alles, was OHLCV hat, gehört ins gleiche Modell.

### 7. Binance Funding Rates / Open Interest

Phase-0-Plan war's. Binance-API US-blocked aus Colab → diese Features waren nie verfügbar. Crypto läuft jetzt über KuCoin (gleiche OHLCV, keine Derivative-Metrics).

---

## Wichtigste Quant-Erkenntnis aus Phase 1

**Robuste einfache Features schlagen theoretisch komplexe Konzepte.**

| Wertvoll | Weniger wertvoll |
|---|---|
| Session-Timing (`hour_sin`, `hour_cos`) | SMC-Strukturen |
| Volatilität (`atr_percentile`, `rvol`) | Klassische TA-Indikatoren ohne ATR-Normalisierung |
| HTF-Kontext (`htf_1h_rsi`, alignment) | Macro Daily |
| Strukturelle Distanz (`dist_to_swing_*_atr`) | Pivot-Punkte ohne Distanz-Normierung |
| Regime-Information (`htf_ltf_agree_*`, `pullback_in_bull`) | Komposite Stoch+RSI+MACD-Konstrukte |

Diese Hierarchie soll die zukünftige Forschung leiten. Bevor wir ein neues "exotisches" Feature einbauen, müssen wir prüfen: hat es eine empirische Begründung, oder klingt es nur gut?

---

## Numerische Referenzpunkte (für künftige Vergleiche)

| Setup | OOS Premium PF | Verwendung |
|---|---|---|
| Random Baseline (kein Modell) | 0.98–1.00 | Jedes Modell sollte das schlagen |
| Phase 0 mit Leakage | 7.40 (FAKE) | Erinnerung warum bit-exact + shift(1) wichtig sind |
| Phase 0 honest Baseline | 1.14 | Threshold-PF auf 30-tree Pine-Modell, schwach |
| NB08 Pine-validated | 1.79 | Erster echter OOS-Edge |
| **NB11 FX-only winner** | **2.015** | **Aktuelle Research-Baseline** |
| Industrie Retail-Quant-Ceiling | 2.0–2.5 | Was mit Retail-Daten realistisch ist |
| Industrie Institutional-Ceiling | 2.5–4.0 | Orderbook/microstructure data nötig |

> Lesson: Wir sind nahe am Retail-Ceiling für FX. Weitere FX-spezifische Optimierung bringt diminishing returns. Universal-Pivot ist quantitativ richtig.

---

## Trade-Frequenz-Referenz (NB11 winning config)

- Standard Tier: ~82 Trades/Tag über alle Symbole (~27/Tag pro Symbol)
- High Tier: ~24 Trades/Tag (~8/Tag pro Symbol)
- Premium Tier: ~8.6 Trades/Tag (~3/Tag pro Symbol)

Für V1-Default wahrscheinlich High-Tier (24/Tag) — aktiv genug zu sein, selektiv genug PF > 1.3 zu halten.

---

## Was Phase 2 entscheiden muss

1. **Generalisiert NB11's Edge?** (NB13 Cross-Asset)
2. **Welches Modell?** (NB12 Battery — LGBM bleibt wahrscheinlich, aber wir testen)
3. **Welche Timeframes?** (NB14 Multi-TF)
4. **Universal oder per-Asset-Cluster kalibriert?** (NB15 Architecture Decision)
