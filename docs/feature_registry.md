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

## Cross-Asset / Currency-Factor Features (Lean-4) — ⚠️ RESEARCH-ONLY (Claim zurückgezogen 2026-06-01)

**KORREKTUR 2026-06-01:** Der ursprüngliche „+0.154 PF"-Claim wurde auf dem
**verzerrten 10%-FVG-Sample** (5m, brutto) gemessen — siehe FVG-NaN-Bug (HANDOFF).
**Clean Re-Validation** (`scripts/clean_revalidate.py`, 30m, Walk-Forward×3-Seeds,
NETTO, volle Daten): **Lean-4-Lift = +0.006 bis +0.008** → **netto-neutral, KEIN
validierter Produktions-Lift.** Status: `research_only`. NICHT als bewiesener
Edge im Produktions-Set führen, bis ein sauberer ≥+0.05-Netto-Lift gezeigt ist.

Quelle: `core/features/cross_asset.py` (Modul bleibt, korrekt + getestet).
Historischer (verzerrter) Test: `scripts/factor_lean.py` + `factor_lean_perpair.py`.

| Feature | Bedeutung | OOS-Beitrag | WF-Importance | Status |
|---|---|---|---|---|
| `usd_idx_vol_20` | USD-Index-Return-Volatilität (broad USD-Regime-Vol, 20-bar) | Teil von +0.154 PF | #3/77 | active |
| `usd_corr_50` | rollende Korr. Pair-Return ↔ USD-Index (wie USD-getrieben) | Teil von +0.154 PF | #5/77 | active |
| `idio_mom_20` | idiosynkratisches Momentum (Pair-Move minus USD-Beta×USD-Move) | Teil von +0.154 PF | #7/77 | active |
| `usd_beta_50` | rollende Beta Pair↔USD-Index (Kopplungs-Stärke) | Teil von +0.154 PF | #8/77 | active |

**Lift:** +0.154 PF (mean über 3 Seeds, min +0.106), **broad-based** (6/6 Paare positiv: USDCAD +0.41, NZDUSD +0.32, GBPUSD +0.16, USDCHF +0.10, AUDUSD +0.06, USDJPY +0.05). USD-Index = vorzeichen-korrigiertes Mittel der 7 FX-Majors (`USD_SIGN`).

**Lean by design:** Vertiefung auf 10 Features (4× idio-Horizonte, 3× corr-Fenster) verwässerte den Lift (+0.044 < +0.154) → Signal ist niedrig-dimensional.

### Verworfen im Cross-Asset-Research (Record)

| Familie | Ergebnis | Warum |
|---|---|---|
| Broad-USD-Momentum (usd_mom_5/20, breadth) | schwach (Rang 29-50) | low signal, aus Lean-Set geprunt |
| Vol-Term-Structure (vts_*, atr_accel) | REJECT (inkr. −0.024 über Lean-4) | Importance ≠ OOS-Wert; kein inkrementeller Edge, schon abgedeckt |

**Methodische Regel (verschärft):** Feature-Aufnahme NUR via **inkrementellem** Multi-Seed-Walk-Forward (≥ +0.05 PF über aktuelles Produktions-Set). Importance/SHAP ist diagnostisch, NICHT hinreichend (VTS rankte top-4 by gain, addierte aber 0 OOS).

---

## Phase-B-Vorbereitung (Cross-Asset)

In NB13 wird pro Asset-Klasse die SHAP-Verteilung neu berechnet. Erwartet wird, dass **einige Features asset-spezifisch sind** (z.B. Session-Features für FX, Volatility für Crypto). Die Tabelle oben wird nach NB13 um eine Spalte **"Generalisiert über Asset-Klassen?"** erweitert.
