# Feature Registry

Single source of truth über alle Features. Jeder neue Feature-Eintrag braucht:
- **SHAP-Wert** (aus letztem relevanten NB)
- **OOS-PF-Lift** in Ablation (≥ +0.05 = behalten, sonst raus)
- **Status:** `active`, `research_only`, `deprecated`

**Locked Rule (HANDOFF 12.2):** Kein Feature ohne messbaren OOS-Mehrwert. SHAP-Relevanz ist notwendig, aber nicht hinreichend.

---

## Aktive Features (NB11-Sieger-Config, FX-only, 27 Features)

Quelle: `artifacts/reports/phase1_best_config.json` bzw. NB12 Hardcoded Fallback.

### Timing & Session

| Feature | SHAP-Rang | OOS-Beitrag | Status | Notiz |
|---|---|---|---|---|
| `hour_sin` | hoch | active | active | Session-Timing |
| `hour_cos` | mittel | active | active | Session-Timing |

### Volatility

| Feature | SHAP-Rang | OOS-Beitrag | Status | Notiz |
|---|---|---|---|---|
| `realized_vol_20` | hoch | active | active | 20-bar realized volatility |
| `atr_percentile_100` | hoch | active | active | ATR relativ zur 100-bar rolling distribution |
| `atr_pct` | mittel | active | active | ATR als % vom Close |
| `rvol_20` | mittel | active | active | Volume relativ zu 20-bar mean |
| `volume_z_score` | mittel | active | active | Volume-Z-Score |

### Structure & Distance

| Feature | SHAP-Rang | OOS-Beitrag | Status | Notiz |
|---|---|---|---|---|
| `dist_to_swing_low_atr` | sehr hoch | active | active | Strukturelle Distanz |
| `dist_to_swing_high_atr` | hoch | active | active | Strukturelle Distanz |
| `ema_20_dist_atr` | mittel | active | active | EMA20-Distanz ATR-normalisiert |
| `ema_20_slope_atr` | mittel | active | active | EMA20-Slope |
| `momentum_composite` | mittel | active | active | Komposit-Momentum |
| `adx_14` | mittel | active | active | Trend-Stärke |

### HTF Context (1H + 4H)

| Feature | SHAP-Rang | OOS-Beitrag | Status | Notiz |
|---|---|---|---|---|
| `htf_1h_rsi_14` | hoch | active | active | 1H-RSI als HTF-Kontext, shift(1) |
| `htf_1h_atr_percentile_100` | mittel | active | active | 1H-ATR-Percentile |
| `htf_ltf_agree_bull` | hoch | +0.06 PF | active | Bull-Übereinstimmung HTF/LTF |
| `htf_ltf_agree_bear` | mittel | active | active | Bear-Übereinstimmung |
| `htf_ltf_counter_trend` | mittel | active | active | Counter-Trend-Flag |
| `htf_ltf_alignment_score` | mittel | active | active | Score über Multi-TF-Alignment |
| `ltf_rsi_minus_htf_rsi` | mittel | active | active | Cross-TF-RSI-Spread |

### Regime / Combined States

| Feature | SHAP-Rang | OOS-Beitrag | Status | Notiz |
|---|---|---|---|---|
| `both_rsi_oversold` | mittel | active | active | Multi-TF-Regime |
| `both_rsi_overbought` | mittel | active | active | Multi-TF-Regime |
| `vol_pct_diff_htf` | mittel | active | active | Volatility-Differential HTF/LTF |
| `both_high_vol` | niedrig | active | active | Doppelt hohe Vola |
| `both_low_vol` | niedrig | active | active | Doppelt niedrige Vola |
| `pullback_in_bull` | mittel | active | active | Trend-Pullback |
| `pullback_in_bear` | mittel | active | active | Trend-Pullback |

---

## Verworfene Features

### SMC / Smart Money Concepts — DEPRECATED

| Feature-Gruppe | Wann verworfen | Warum |
|---|---|---|
| FVG (Fair Value Gaps) | NB11 | PF-Reduktion von 1.80 auf 1.56 in Ablation. Pine-Budget kann's nicht tragen. |
| BOS / CHoCH | NB11 | SHAP-dead trotz theoretischer Relevanz. |
| Order Blocks | NB11 | Dito. |
| Liquidity Pools | NB11 | Dito. |

**Wichtigste Quant-Erkenntnis bisher:** Komplexe Trading-Konzepte (SMC/FVG/BOS/CHoCH) waren weniger wertvoll als robuste einfache Features (Session-Timing, Volatility, HTF-Kontext, strukturelle Distanz). Datengetrieben gilt: simpel + ATR-normalisiert > theoretisch komplex.

### Macro — DEPRECATED auf Intraday-Ebene

| Feature | Wann verworfen | Warum |
|---|---|---|
| VIX (Daily) | NB02 | SHAP-dead bei Intraday-Predictions. Daily-Daten helfen nicht bar-by-bar. |
| DXY (Daily) | NB02 | Dito. |
| TNX (Daily) | NB02 | Dito. |

Macro-Daten bleiben in `core/features/macro.py` für zukünftige Higher-TF-Modelle (Daily/Weekly V2+), nicht aktiv auf 5M/15M.

### Andere

| Feature | Wann verworfen | Warum |
|---|---|---|
| Binance Funding Rates | Phase 0 | API US-blocked, nie erreichbar gewesen. |
| Open Interest | Phase 0 | Dito. |
| 37-Feature-Set (NB05) | NB05 | Zu viele Features für 30 Trees, SHAP zeigte 17–21 dead. |
| 57-Feature-Phase-1-Full | NB11 | PF 1.53 < Baseline 1.80. Pine-Budget. |

---

## Phase-B-Vorbereitung (Cross-Asset)

In NB13 wird pro Asset-Klasse die SHAP-Verteilung neu berechnet. Erwartet wird, dass **einige Features asset-spezifisch sind** (z.B. Session-Features für FX, Volatility für Crypto). Die Tabelle oben wird nach NB13 um eine Spalte **"Generalisiert über Asset-Klassen?"** erweitert.
