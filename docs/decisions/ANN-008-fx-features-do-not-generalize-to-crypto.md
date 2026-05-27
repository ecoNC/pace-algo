# ANN-008: FX-trainiertes Modell generalisiert NICHT auf Crypto

**Status:** Active
**Datum:** 2026-05-27
**Locked-By:** ANN-006 (Robustheits-First — wir folgen den Daten, nicht der Hoffnung)
**Related:** [[ANN-003]] (Gold) [[ANN-005]] (V1-Scope) [[ANN-006]] (Robustheits-Mantra)

---

## 1. Hypothese

Wenn die Features (`hour_sin`, `realized_vol_20`, `dist_to_swing_low_atr`, HTF-Interactions etc.) **strukturell universal** sind, sollte ein FX-trainiertes LightGBM-Modell auf Crypto-Daten zumindest mittelstarken Edge zeigen — vielleicht reduziert (Universal-Strafe), aber statistisch klar besser als random (PF > 1.3 als Threshold).

Falls die FX-Edge **asset-spezifisch** ist, würde Crypto-PF bei ~1.0 (random) liegen.

## 2. Experiment

**Notebook:** NB13 (Cross-Asset Generalization, Run 2026-05-27, commit `8a7bf8d`)

**Setup:**
- Training: LightGBM auf FX-only (EURUSD + USDJPY), 30 trees, depth 3, 27 Features (NB11-Winner)
- Inferenz: Cross-Asset Out-of-Distribution auf 5 Crypto-Symbolen (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, ADAUSDT) × 4 TFs (5m, 15m, 30m, 1h)
- Tier-Cutoffs: VAL-derived aus FX-Training-Set (top 1%, 3%, 10%)
- Identische Walk-Forward-Splits (TRAIN_END 2024-01-01, VAL_END 2024-07-01)
- Random Seed: 42 (reproduzierbar)

**Schwellen:**
- H1-Threshold: Mean-PF über Asset-Klassen ≥ 1.4, Min-PF-per-Class ≥ 1.3 (aus `core.config.PHASE_B_THRESHOLDS`)
- "Crypto generalisiert" wenn: Min-Crypto-Premium-PF ≥ 1.3 auf ≥3 von 5 Symbolen

## 3. Resultat

**Premium-Tier PF pro Crypto-Symbol (FX-trained, Out-of-Distribution):**

| Symbol | 5m | 15m | 30m | 1h | Mean | Verdict |
|---|---:|---:|---:|---:|---:|---|
| BTCUSDT | 1.053 | 0.750 | 0.750 | 0.962 | 0.879 | ❌ |
| ETHUSDT | 0.835 | 1.059 | 1.500 | 1.057 | 1.113 | ❌ |
| SOLUSDT | 0.973 | 1.417 | 0.600 | 0.953 | 0.986 | ❌ |
| BNBUSDT | 1.045 | 0.916 | 0.750 | 0.994 | 0.926 | ❌ |
| ADAUSDT | 1.014 | 0.935 | 1.306 | 0.984 | 1.060 | ❌ |
| **Crypto Mean** | **0.98** | **1.02** | **0.98** | **0.99** | **0.99** | ❌ |

**Vergleich FX (Same-Run, Same-Training):**

| TF | FX Mean PF | Crypto Mean PF | Spread |
|---|---:|---:|---:|
| 5m | **2.49** | 0.98 | -1.51 |
| 15m | 1.60 | 1.02 | -0.58 |
| 30m | 1.48 | 0.98 | -0.50 |
| 1h | 1.18 | 0.99 | -0.19 |

Quelle: [results/nb13/metrics/cross_asset_matrix_2026-05-27.csv](../../results/nb13/metrics/cross_asset_matrix_2026-05-27.csv) — 121 Rows, alle Symbole × TFs × Tiers belegt.

**SHAP-Stabilität (überraschend wichtig):**

Die Features haben **fast identische SHAP-Werte** in FX und Crypto:
- `hour_sin`: FX 0.0374 / Crypto 0.0387 — fast gleich
- `ema_20_dist_atr`: FX 0.0170 / Crypto 0.0190 — fast gleich
- `dist_to_swing_low_atr`: FX 0.0135 / Crypto 0.0120 — fast gleich

**Bedeutung:** Das Modell nutzt die GLEICHEN Patterns in beiden Asset-Klassen. Aber die Patterns produzieren nur in FX prädiktive Signale. **Die Features sind syntaktisch übertragbar, aber semantisch FX-spezifisch.**

Quelle: [results/nb13/shap/shap_per_class_2026-05-27.csv](../../results/nb13/shap/shap_per_class_2026-05-27.csv) — 216 Rows.

**Auto-Decision-Engine Output:**

```json
{
  "h1_mean_pf": 1.34,
  "h1_min_pf_per_class": 0.99,
  "h1_pass": false,
  "h1_per_class": {"crypto": 0.993, "fx": 1.687},
  "architecture_hint": "Variante C (Router) wahrscheinlich"
}
```

## 4. Decision

**Crypto wird in V1 NICHT unterstützt mit dem aktuellen FX-Modell. Lock.**

Drei mögliche Pfade für Crypto-Support — keiner ist V1-fähig:

1. **Crypto-Spezialmodell trainieren** (eigenes LightGBM auf Crypto-only, ggf. mit anderen Features wie Funding Rate, OI). Erfordert: KuCoin-Funding-API + neuer NB13c-Run. Phase B+ Arbeit.

2. **Universal-Modell auf gemischtem Pool** (Experiment D, blockiert durch RAM). Risiko: Universal-Penalty kann FX-Edge zerstören. Test nötig auf High-RAM-Runtime.

3. **Asset-Type als Feature einbauen** (z.B. `is_crypto = 0/1`). Würde dem Modell erlauben, Crypto-spezifische Sub-Bäume zu lernen — aber bei 30-tree-Pine-Budget wahrscheinlich nicht genug Kapazität.

**V1-Konsequenz:** "Universal Indicator"-Marketing wird zu "Forex Major Pairs Indicator" oder "AI Trading Indicator (FX-validated, Crypto+Indices in V2)".

## 5. Konsequenz

### Code-Änderungen

- `docs/feature_registry.md` bekommt neue Spalte "Cross-Asset SHAP" mit FX-vs-Crypto-Werten
- `docs/model_registry.md` aktualisiert: V1-Scope = FX-Major-Pairs
- `docs/roadmap.md` Phase D Entscheidungs-Matrix bekommt expliziten Crypto-Branch
- Pine-V1-Code (NB17, später) bekommt UX-Warning auf Non-FX-Charts

### Marketing-Korrektur (vor V1-Launch)

- ❌ "Universal AI Trading Indicator" — datenbelegt falsch
- ✅ "AI Trading Indicator für FX Major Pairs (EURUSD, USDJPY, GBPUSD, AUDUSD, USDCHF)"
- ✅ "Crypto + Indices Support coming in V1.5/V2"

Das ist eine wichtige Korrektur. Ohne NB13 wäre V1 wahrscheinlich mit "Universal"-Claim gelauncht und Crypto-Trader hätten zurecht negative Reviews geschrieben.

### Lessons (für Roadmap)

1. **Asset-Cluster sind ML-relevant, nicht nur cosmetisch.** Crypto ist nicht "FX mit anderen Symbolen", sondern ein anderes Regime mit anderen Mikro-Strukturen.

2. **SHAP-Stabilität ist NICHT hinreichend für Generalisierung.** Das Modell kann die gleichen Patterns überall finden, ohne dass sie überall Edge produzieren.

3. **Hold-Out-Symbol-Generalisation ≠ Cross-Asset-Generalisation.** GBPUSD/AUDUSD/USDCHF generalisieren super (sind FX-Cousins). BTC/ETH/SOL brechen (sind anderes Regime). Wir hätten das NIE mit nur GBPUSD-Hold-Out gesehen.

4. **NB13 hat ANN-006 Lock 3 (Konsistenz > Cherry-Picking) bestätigt.** Wenn wir nur die FX-Zahlen genommen und Crypto ignoriert hätten, wäre V1 mit falschen Erwartungen gelauncht.

### Re-Test-Bedingungen

- Wenn KuCoin-Funding-API verfügbar → Crypto-spezifische Features einbauen, neu testen
- Wenn V2-Backend mit größeren Modellen (kein Pine-Budget) → testen ob 100+ Trees + 50+ Features Crypto crackt
- Bei ML-Architecture-Wechsel (z.B. zu Transformer für Sequence-Learning) → Crypto neu evaluieren

## Referenzen

- Cross-Asset Matrix CSV: [results/nb13/metrics/cross_asset_matrix_2026-05-27.csv](../../results/nb13/metrics/cross_asset_matrix_2026-05-27.csv)
- SHAP per Class: [results/nb13/shap/shap_per_class_2026-05-27.csv](../../results/nb13/shap/shap_per_class_2026-05-27.csv)
- Full Snapshot: [results/nb13/summaries/nb13_full_snapshot_2026-05-27.json](../../results/nb13/summaries/nb13_full_snapshot_2026-05-27.json)
- Analyse: [/research/asset_generalization.md](../../research/asset_generalization.md)
- Related ADRs: [ANN-005 V1-Scope](ANN-005-v1-vs-v1.5-scope-split.md), [ANN-006 Robustness-Mantra](ANN-006-robustness-first-mantra.md)
