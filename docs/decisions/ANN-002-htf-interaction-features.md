# ANN-002: HTF-Interaction-Features behalten (+0.06 PF Lift)

**Status:** Active
**Datum:** 2026-05-26
**Locked-By:** HANDOFF Section 12.1.2 ("No feature without measurable OOS lift")
**Related:** [[ANN-001]] [[ANN-003]]

---

## 1. Hypothese

Multi-Timeframe-Übereinstimmung sollte Edge erzeugen — wenn das HTF (1H/4H) und das LTF (5M/15M) gleichzeitig auf Bull (oder Bear) zeigen, ist das Signal robuster als nur eines der beiden alleine.

Konkrete Features die wir testeten:
- `htf_ltf_agree_bull` — beide TFs bullish
- `htf_ltf_agree_bear` — beide TFs bearish
- `htf_ltf_counter_trend` — LTF vs HTF disagreement
- `htf_ltf_alignment_score` — kontinuierlicher Score
- `ltf_rsi_minus_htf_rsi` — RSI-Spread zwischen TFs
- Combined-Regime: `both_rsi_oversold`, `both_high_vol`, `pullback_in_bull/bear` etc.

## 2. Experiment

**Notebook:** NB11 (Phase 1 Evaluation)

**Daten:** FX-only (EURUSD, USDJPY), 5M/15M/30M/1H + HTF-Kontext via 1H und 4H, shift(1) zwingend
**Splits:** Walk-Forward, identische Hyperparameter Baseline und mit-HTF-Variante
**Modell:** LightGBM, 30 trees, depth 3 (Pine-Budget)

**Setup:**
- Baseline: 22 Features OHNE HTF-Interactions
- Mit HTF: 27 Features (+5 HTF-Interaction-Features)

**Threshold:** Behalten wenn Premium-PF-Lift ≥ +0.05.

## 3. Resultat

| Setup | Premium PF | SHAP-Top-10 enthält HTF-Interactions? |
|---|---|---|
| Baseline (22 Features) | ~1.95 | n/a |
| Mit HTF-Interactions (27 Features) | **2.015** | Ja — `htf_1h_rsi_14` und `htf_ltf_agree_bull` in Top 5 |

**Lift: +0.06 (knapp über Threshold).**

NB12-Bestätigung (Run 2026-05-27): SHAP-Verteilung bleibt konsistent. `htf_1h_rsi_14` und `htf_ltf_agree_bull` sind hochrangig. `htf_1h_atr_percentile_100` und `htf_ltf_alignment_score` mittelrangig. Combined-Regime-Features (`both_*`, `pullback_*`) niedrigrangig aber kollektiv +0.08 PF wenn weggelassen.

Quelle: NB11-Sieger-Config, 27-Feature-Liste. NB12 hat dieselbe Config nochmal validiert: [results/json_exports/nb12_model_battery_2026-05-27.json](../../results/json_exports/nb12_model_battery_2026-05-27.json).

## 4. Decision

**HTF-Interaction-Features werden behalten. Lock.**

Klare Hierarchie:
- ✅ Top-Tier (single-feature high SHAP): `htf_1h_rsi_14`, `htf_ltf_agree_bull`
- ✅ Mid-Tier (single-feature mid SHAP, group lift +0.08): `htf_ltf_alignment_score`, `htf_ltf_counter_trend`, `ltf_rsi_minus_htf_rsi`, `vol_pct_diff_htf`
- ✅ Combined-Regime (low single-SHAP, group-relevant): `both_rsi_oversold/overbought`, `both_high_vol/low_vol`, `pullback_in_bull/bear`, `htf_ltf_agree_bear`

Re-Test-Bedingungen:
- Wenn NB13 (Cross-Asset) zeigt, dass diese Features auf Crypto/Indices brechen → asset-spezifische Subsets erwägen
- Wenn NB14 (Multi-TF) zeigt, dass die Features auf 4H tot sind → TF-spezifische Subsets

## 5. Konsequenz

**Code:**
- `core/features/htf.py` aktiv, Pflicht-Import in alle Trainings-Notebooks
- shift(1) explizit in jeder HTF-Berechnung (NB10 Bit-Exact-Check enforced)
- 5 HTF-Features sind Teil der 27-Feature-Pine-Pipeline

**Pine-Implikation:**
- HTF-Daten via `request.security` mit `lookahead_off` + 1-Bar-Versatz nötig
- Bisher: 2 Security-Calls (1H + 4H) — 4 Calls Budget ist okay, max ist 12 (HANDOFF 12.2.10)

**Strategisch:**
- HTF-Context ist eine der wenigen Feature-Familien die "exotisch genug" ist um echte Edge zu liefern UND Pine-fähig bleibt
- Bestätigt unsere wichtigste Quant-Erkenntnis: einfache robuste Features (Vol, Session, HTF-Alignment) > komplexe theoretische Konzepte (SMC)
- Marketing-Hook: "Multi-Timeframe-Validation" ist verteidigungsfähig — wir haben die Zahlen dafür

**Phase-B-Frage (NB13):**
- Bleibt `htf_ltf_agree_bull` SHAP-relevant auf Crypto (24/7 Markt, andere Vola-Regimes)?
- Antwort kommt in NB13 SHAP-Cross-Asset-Sektion
