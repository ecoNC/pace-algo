# SHAP Analysis — Zentrale Sammlung

SHAP-Verteilungen aller relevanten Notebooks an einem Ort. Format pro Notebook: Top-Features, dead Features, Notizen.

**Erinnerung (HANDOFF 12.1.2):** SHAP-Relevanz ist NOTWENDIG aber nicht HINREICHEND. Ein Feature muss auch in Ablation `≥ +0.05 PF` liefern.

---

## NB05 (37-Feature LightGBM, FX+Gold)

**Datum:** 2026-05-21
**Daten:** FX + Gold, 5M/15M/30M/1H

**Top-10 SHAP:**
1. `dist_to_swing_low_atr`
2. `hour_sin`
3. `realized_vol_20`
4. `atr_percentile_100`
5. `dist_to_swing_high_atr`
6. `htf_1h_rsi_14`
7. `ema_20_slope_atr`
8. `volume_z_score`
9. `hour_cos`
10. `atr_pct`

**Dead Features (SHAP < 0.001):** 17 Features, hauptsächlich SMC (FVG_count, BOS_dist, OB_*), Macro (VIX, DXY, TNX), Pivot-Points ohne ATR-Normalisierung.

**Notebook-Notiz:** Diese Beobachtung trieb die Reduktion auf 27 Features in NB11.

---

## NB11 (27-Feature LightGBM, FX-only Winner)

**Datum:** 2026-05-26
**Daten:** FX-only (EURUSD, USDJPY), 5M/15M/30M/1H
**Premium PF:** 2.015

**Top-10 SHAP:**
1. `dist_to_swing_low_atr` — strukturelle Distanz
2. `hour_sin` — Session-Timing
3. `realized_vol_20` — Volatilität
4. `htf_1h_rsi_14` — HTF-Momentum
5. `htf_ltf_agree_bull` — Multi-TF-Alignment
6. `atr_percentile_100` — relative Vola
7. `dist_to_swing_high_atr` — Distanz
8. `ema_20_slope_atr` — Trend-Slope
9. `hour_cos` — Session-Timing
10. `momentum_composite` — Composite

**Mittelfeld (SHAP 0.01–0.05):**
- `volume_z_score`, `rvol_20`, `adx_14`, `ema_20_dist_atr`
- `htf_1h_atr_percentile_100`, `htf_ltf_alignment_score`, `htf_ltf_counter_trend`
- `ltf_rsi_minus_htf_rsi`, `vol_pct_diff_htf`
- `both_rsi_oversold`, `both_rsi_overbought`
- `pullback_in_bull`, `pullback_in_bear`

**Niedrig aber behalten (SHAP 0.005–0.01):**
- `both_high_vol`, `both_low_vol`, `atr_pct`, `htf_ltf_agree_bear`

**Beobachtung:** Strukturelle Distanz + Session + Volatility dominieren. HTF-Kontext liefert die zweite Schicht. Combined-Regime-Features liefern den schwächsten aber konsistent positiven Beitrag.

---

## NB12 (Phase A — Model Battery)

**Status:** Wartet auf Colab-Run.

**Was wird verglichen:**
- LightGBM SHAP vs XGBoost SHAP vs CatBoost SHAP auf identischen Features
- Erwartung: Top-5 ist konsistent, Top-10 kann variieren

**Was wird in /results/json_exports/ gespeichert:**
- SHAP-Werte pro Modell und Feature
- Diff: welche Features rangieren bei welchem Modell höher

Wird gefüllt nach NB12-Colab-Run.

---

## Phase B — NB13 Cross-Asset SHAP (geplant)

**Forschungsfrage:** Welche Features haben konsistente SHAP-Werte über Asset-Klassen, welche variieren stark?

**Methodik:**
- Phase-A-Sieger-Modell auf jedem Asset einzeln inferenzen
- SHAP pro Asset berechnen
- Feature-SHAP-Stabilität: Standardabweichung des SHAP-Rangs über Assets

**Erwartung:**
- **Stabil:** `realized_vol_20`, `atr_percentile_100`, `hour_sin/cos`, HTF-Alignment-Features
- **Asset-spezifisch (hohe Varianz):** Session-Features auf Crypto (kein klares Session-Cycle), Volume-Features auf FX (kein echtes Volume bei Dukascopy)

Wird gefüllt wenn NB13 läuft.

---

## Phase C — NB14 Multi-TF SHAP (geplant)

**Forschungsfrage:** Welche Features dominieren auf welchen Timeframes?

**Erwartung:**
- **5M/15M:** Session-Features hoch, Volume hoch, kurzfristige Vola hoch
- **1H/4H:** HTF-Features irrelevanter (weil HTF jetzt Tagesebene wäre), strukturelle Distanz wichtiger, Macro evtl. wiederbelebt

Wird gefüllt wenn NB14 läuft.

---

## Globale SHAP-Heuristiken (Phase 1 gelernt)

1. **ATR-Normalisierung essentiell.** Roh-Distanz-Features haben durchweg niedrigeres SHAP als ATR-normalisierte.
2. **Zyklisches Encoding > Binary Flags.** `hour_sin/cos` schlägt diskrete `session_london/ny/asia`-Flags.
3. **Combined Features > Individual Components.** `htf_ltf_agree_bull` ist single-feature stärker als die zwei Komponenten einzeln.
4. **HTF-Daten brauchen shift(1).** Ohne shift = look-ahead Leakage (vgl. Phase-0-Bug mit PF 7.40).
5. **Volume-Z > Raw Volume.** Symbol-übergreifend vergleichbar nur normalisiert.
