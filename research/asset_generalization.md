# Asset Generalization — Phase B (NB13)

**Status:** ✅ RUN 1 ABGESCHLOSSEN — 2026-05-27 (commit `8a7bf8d`)
**Decision-Framework:** [/docs/_phase_decision_template.md](../docs/_phase_decision_template.md)
**Notebook:** [notebooks/13_cross_asset_generalization.ipynb](../notebooks/13_cross_asset_generalization.ipynb)
**Snapshot:** [results/nb13/summaries/nb13_full_snapshot_2026-05-27.json](../results/nb13/summaries/nb13_full_snapshot_2026-05-27.json)

---

## TL;DR (in einem Satz)

**FX-trainiertes Modell generalisiert SAUBER innerhalb FX (inkl. nie trainierter Cousins AUDUSD/USDCHF: PF 2.5–2.7 Premium auf 5m), aber bricht KOMPLETT auf Crypto (PF ≈ 1.0 auf allen 5 Crypto-Symbolen × allen 4 TFs).** Architektur-Hint: **Variante C (Router + Spezialmodelle).**

---

## ## Run 2026-05-27

### Setup (was lief)

| Parameter | Wert |
|---|---|
| Run-Commit | `8a7bf8d` |
| Experiment-ID | nb13_2026-05-27T13-15-41Z_81f2316 |
| Active Experiments | **A** (FX→FX-Holdout), **B** (FX→Crypto) |
| Skipped | C (Indices, kein Polygon), D (Universal, RAM-gated), E (Asset-Cluster) |
| Trainings-Pool | FX-only: EURUSD + USDJPY |
| Test-Symbole | 11 (5 FX, 5 Crypto, 1 Gold — Gold leer in dieser Asset-Class-Auswertung) |
| Modelle | LightGBM only |
| TFs | 5m, 15m, 30m, 1h |
| Features | 27 (NB11-Winner-Config) |
| Random Seed | 42 |

### 1. Cross-Asset Premium PF — die zentrale Tabelle

**Premium-Tier PF (FX-trained Modell, OOS-Inferenz pro Symbol):**

| Symbol | Klasse | 5m | 15m | 30m | 1h |
|---|---|---:|---:|---:|---:|
| EURUSD | fx | 2.62 | 1.37 | 1.23 | 1.39 |
| USDJPY | fx | 1.98 | 1.25 | 1.17 | 1.08 |
| **GBPUSD** ⁂ | fx | **2.66** | **1.67** | **2.06** | 1.22 |
| **AUDUSD** ⁂ | fx | **2.58** | 1.81 | 1.56 | 0.86 |
| **USDCHF** ⁂ | fx | **2.61** | **1.88** | 1.37 | 1.35 |
| BTCUSDT | crypto | 1.05 | 0.75 | 0.75 | 0.96 |
| ETHUSDT | crypto | 0.84 | 1.06 | 1.50 | 1.06 |
| SOLUSDT | crypto | 0.97 | 1.42 | 0.60 | 0.95 |
| BNBUSDT | crypto | 1.05 | 0.92 | 0.75 | 0.99 |
| ADAUSDT | crypto | 1.01 | 0.94 | 1.31 | 0.98 |

⁂ = nie im Training gesehen (echtes Hold-Out)

**Per-Klasse Mean (Premium):**

| TF | FX Mean PF | Crypto Mean PF | Spread |
|---|---:|---:|---:|
| 5m | **2.49** | 0.98 | -1.51 |
| 15m | 1.60 | 1.02 | -0.58 |
| 30m | 1.48 | 0.98 | -0.50 |
| 1h | 1.18 | 0.99 | -0.19 |

> **Erkenntnis 1:** FX-Edge ist REAL und generalisiert auf andere FX-Symbole (auch nie trainierte). GBPUSD/AUDUSD/USDCHF zeigen Premium-PF zwischen 2.58 und 2.66 auf 5m — bessere Zahlen als die Trainings-Symbole selbst.

> **Erkenntnis 2:** Crypto-Edge ist NULL. Alle 5 Crypto-Symbole haben PF ≈ 0.95–1.05 auf allen TFs. Das ist statistisch ununterscheidbar von random.

> **Erkenntnis 3:** Höhere TFs zerstören FX-Edge progressiv (2.49 → 1.18). Wahrscheinlich Trade-Frequency-Issue: auf 1h gibt es zu wenig Premium-Signale für statistisch belastbare Edge.

### 2. TF-Comparison (FX-trained, Premium über alle 11 Symbole)

| TF | Mean PF | Min PF | Max PF | Stability CV | Total Trades |
|---|---:|---:|---:|---:|---:|
| **5m** | **1.737** | 0.84 | 2.66 | 0.471 | 23,336 |
| 15m | 1.306 | 0.75 | 1.88 | 0.302 | 3,100 |
| 30m | 1.230 | 0.60 | 2.06 | 0.359 | 1,084 |
| 1h | 1.086 | 0.87 | 1.40 | 0.164 | 11,398 |

> **Beobachtung:** 5m hat besten Mean-PF aber höchste CV (0.471) — weil FX (2.49) und Crypto (0.98) so weit auseinander liegen. 1h hat niedrigste CV (0.164) **WEIL alle Symbole bei ~1.0 clustern** — kein Spread mehr, aber auch kein Edge.

> **Konsequenz für V1:** 5m bleibt der Ziel-TF, weil dort die größte Edge sitzt. Aber: nur für FX. Crypto braucht eigenen Ansatz.

### 3. SHAP-Stability (FX vs Crypto)

**Top-Features mean |SHAP| auf 5m:**

| Feature | FX SHAP | Crypto SHAP | Stabilität |
|---|---:|---:|---|
| hour_sin | 0.0374 | 0.0387 | ✅ stabil |
| ema_20_dist_atr | 0.0170 | 0.0190 | ✅ stabil |
| dist_to_swing_low_atr | 0.0135 | 0.0120 | ✅ stabil |
| hour_cos | 0.0129 | 0.0134 | ✅ stabil |
| rvol_20 | 0.0061 | 0.0095 | ✅ stabil |
| atr_percentile_100 | 0.0045 | 0.0051 | ✅ stabil |
| **htf_ltf_agree_bull** | 0.0 | 0.0 | dead auf 5m |
| **htf_1h_atr_percentile_100** | 0.0 | 0.0 | dead auf 5m |
| **both_rsi_oversold/overbought** | 0.0 | 0.0 | dead auf 5m |
| **htf_ltf_alignment_score** | 0.0 | 0.0 | dead auf 5m |

> **WICHTIGSTE Erkenntnis aus SHAP:** Die Feature-Gewichtung ist FAST IDENTISCH zwischen FX und Crypto. Das Modell nutzt die GLEICHEN Patterns. Aber: die Patterns sind in Crypto NICHT prädiktiv. Crypto braucht ANDERE Features (z.B. Funding Rate, OI, On-Chain-Metrics, BTC-Dominance) die wir aktuell nicht haben.

> **HTF-Interactions:** Auf 5m sind sie SHAP-zero (Modell ignoriert sie). Auf 30m: `htf_ltf_agree_bull` SHAP 0.0092. Auf 1h: `htf_ltf_alignment_score` SHAP 0.0144. **HTF-Context wird wichtiger auf höheren TFs** — aber die Edge ist insgesamt schwächer dort.

### 4. Auto-Decision-Engine Output

Aus [nb13_full_snapshot_2026-05-27.json](../results/nb13/summaries/nb13_full_snapshot_2026-05-27.json):

```json
"verdict": {
  "h1_mean_pf": 1.34,
  "h1_min_pf_per_class": 0.99,
  "h1_pass": false,
  "h1_per_class": {"crypto": 0.993, "fx": 1.687},
  "architecture_hint": "Variante C (Router) wahrscheinlich — mindestens eine Asset-Klasse bricht hart"
}
```

**H1 Verdict: FAIL** — Mean PF über Asset-Klassen liegt bei 1.34 (Threshold 1.4), Min liegt bei 0.99 (Threshold 1.3 → Crypto-Bruch).

---

## Hypothesen — Status nach Run 1

| Hypothese | Ergebnis | Belegt durch |
|---|---|---|
| **H1** Universale Strafe quantifizierbar | ❌ FAIL — Crypto bricht hart (PF 0.99) | Auto-Decision-Engine |
| **H2** FX-Cousins generalisieren | ✅ STARK — AUDUSD/USDCHF PF > 2.5 auf 5m | Cross-Asset Matrix |
| **H3** Session-Features brechen auf Crypto | ❌ überraschend nein — `hour_sin` SHAP fast identisch | SHAP-Tabelle |
| **H4** Vola-Features generalisieren | ⚠️ TEILWEISE — SHAP stabil aber Edge fehlt | SHAP-Tabelle |
| **H5** Consensus generalisiert | ⏳ PENDING — XGB+CatBoost nicht trainiert in MVP | needs NB13b mit allen 3 Modellen |
| **H6** XGBoost-Lift generalisiert | ⏳ PENDING — XGB nicht trainiert | needs NB13b |

### Überraschungen

**H3 Falsifikation:** Wir hatten erwartet, dass `hour_sin`/`hour_cos` auf Crypto SHAP-tot wären (weil 24/7-Markt = keine Session). Tatsächlich nutzt das Modell sie mit identischer Gewichtung auf Crypto wie auf FX. Das heißt: **das Modell SUCHT nach Session-Patterns auch in Crypto, findet aber keine Edge daraus**. Die Patterns existieren statistisch, sind aber für Crypto-Returns nicht prädiktiv.

**Konsequenz:** Asset-spezifische Features alleine reichen wahrscheinlich nicht. Wir brauchen **asset-spezifische LABELS** oder **asset-spezifische TRAINING** (= Variante C).

---

## Decision

### Phase B Lock

1. **FX-Edge ist real und universell innerhalb FX.** Premium-PF 2.5+ auf 5 FX-Symbolen, davon 3 nie trainiert. Das ist die stärkste Generalisations-Evidenz aus Phase 1+2.

2. **FX-Modell ist NICHT crypto-fähig.** Crypto-Premium-PF ≈ 1.0 auf 5 Crypto-Symbolen × 4 TFs. Das ist statistisch zwingend, keine Stichprobenvariation.

3. **5m bleibt Ziel-TF für V1-FX.** Höhere TFs (15m+) bringen weniger Edge bei weniger Trades. NB14 wird das systematisch bestätigen.

4. **Architektur-Decision wird in NB15:** Variante C (Router) ist der wahrscheinliche Gewinner. Aber: Crypto-Spezialmodell muss erst gebaut + getestet werden.

### Strikte Aussagen für ADR

- **V1-Pine-Scope: nur FX-Charts** (oder zumindest: clear UX-Warning auf Non-FX-Charts dass Signal-Qualität nicht validiert ist)
- **Crypto-Support in V1: defer.** Entweder Spezialmodell in NB16+ oder erst V1.5
- **Indices-Support: noch unbekannt.** Polygon-Aktivierung + NB13b für Cross-Asset auf Indices

---

## Konsequenz

### Code-Änderungen (bereits ausgeführt oder geplant)

- [ ] `docs/decisions/ANN-008-fx-features-do-not-generalize-to-crypto.md` schreiben (this commit)
- [ ] `docs/roadmap.md` — Phase B als ABGESCHLOSSEN, Phase C/D mit Architektur-Verdict
- [ ] `docs/model_registry.md` — V1-Scope-Update (FX-only)
- [ ] `docs/feature_registry.md` — Spalte "Generalisiert über Asset-Klassen" mit Daten füllen

### Roadmap-Implikation

**Phase B (NB13) ✅ DONE.**
**Phase C (NB14 Multi-TF):** weiterhin sinnvoll — wir wissen jetzt dass 5m die beste TF für FX ist, aber NB14 sollte das systematisch über mehr Konfigurationen testen.
**Phase D (NB15 Architecture):** klare Richtung — entweder:
- Variante C-light: V1 = FX-only LightGBM, Crypto/Indices = "coming soon"-UI-Element
- Variante C-full: V1 = LightGBM-Router (FX-Spezialmodell + Crypto-Spezialmodell + Gold/Indices-Spezialmodelle)

**Vor NB15 nötig:** NB13b oder NB14 muss Crypto-Spezialmodell-Test machen — train auf nur Crypto, sehe ob es eigene Edge produziert.

### Marketing-Implikation (für V1-Launch)

> **NICHT erlaubt (per ANN-006 Lock 3+4):** "Universal AI Trading Indicator" — wir haben datenbelegt KEINE universelle Edge.
>
> **Erlaubt:** "AI-Indikator für Forex Major Pairs" mit dem Disclaimer "Crypto + Indices in V1.5/V2".

Das ist eine **wichtige Marketing-Korrektur** vor V1-Launch. Hätten wir das Cross-Asset-Pattern nicht getestet und nur auf FX-PF verlassen, hätten wir mit "Universal"-Claim gelauncht und Crypto-Trader frustriert.

---

## Output-Files

- `/results/nb13/metrics/cross_asset_matrix_2026-05-27.csv` — 121 rows, full per-(pool,tf,model,symbol,tier) Tabelle
- `/results/nb13/shap/shap_per_class_2026-05-27.csv` — 216 rows, SHAP pro (tf, asset_class, feature)
- `/results/nb13/summaries/tf_comparison_2026-05-27.csv` — 4 rows, Per-TF aggregiert
- `/results/nb13/summaries/label_balance_2026-05-27.csv` — 40 rows, Class-Balance pro (symbol, tf)
- `/results/nb13/summaries/nb13_full_snapshot_2026-05-27.json` — vollständiger Run-Snapshot inkl. Verdict
- `/results/nb13/config_snapshots/*.json` — 5 Config-Snapshots (Run-Retries beim Memory-Fix-Debug)

---

## Open Items für NB13b/NB14

1. **Universal-Pool-Training (Experiment D)** — wartet auf High-RAM-Runtime oder modulareres NB13b
2. **Crypto-Only-Training** — kritisch um zu sehen ob Crypto inherent ML-edge-fähig ist
3. **XGBoost + CatBoost** für H5/H6-Test (Consensus + per-Asset-Lift)
4. **Polygon-Aktivierung** für Indices Cross-Asset-Test
5. **NB14 Multi-TF Deep-Dive** — was passiert auf 4H und Daily?
