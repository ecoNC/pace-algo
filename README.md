# PaceAlgo — Universal AI-Powered TradingView Indicator

**Was:** Premium ML-getriebener TradingView-Indikator, der auf **möglichst vielen Asset-Klassen und Timeframes** robust funktioniert.
**Wer:** Retail-Trader, die ML-Signale gegenüber Guru-Style "follow me" bevorzugen.
**Preis (geplant):** $39–49/Monat oder $399–499 Lifetime, Invite-Only über Whop/Stripe.

> **Strategische Prämisse (LOCKED 2026-05-27):** Wir optimieren auf Robustheit, Cross-Asset-Generalisierung und langfristige Produktqualität — NICHT auf den besten Single-Market-PF oder schnellen Release. FX-only PF 2.015 (NB11) ist Forschungs-Baseline, nicht Produktziel.

## Strategy Locks (oberste Hierarchie)

Diese 4 Sätze überschreiben jede andere Locked Rule im Konfliktfall (siehe [ANN-006](docs/decisions/ANN-006-robustness-first-mantra.md)):

1. **Generalisierung > Maximierung eines einzelnen PF-Werts** — PF 1.6 auf 8 Asset-Klassen schlägt PF 2.5 auf 1
2. **Robustheit > Benchmark-Chasing** — Stabilität in 3 Marktregimen schlägt Brillanz in einem
3. **Konsistenz > Cherry-Picking** — Marketing-Zahlen reflektieren das schlechteste Hold-Out, nicht das beste
4. **Gute UX + ehrliches Backtesting > Marketing-Zahlen** — was der User auf seinem Chart sieht IST der Backtest

---

## Produkt-Vision

Ein TradingView-Indikator, den der User auf **jedem Chart** öffnet — FX, Indices, Gold/Commodities, Stocks, ETFs, Crypto — und konsistente, ehrlich validierte BUY/SELL-Signale bekommt. Plus:

- **Integriertes Backtest-Widget** auf dem Chart (PF/WR/Avg-R/MDD live)
- **Historische Trade-Visualisierung** (vergangene Signale als Boxen)
- **3 Profile** (Conservative / Balanced / Aggressive) — keine free Slider, kein Curve-Fitting
- **Tier-Badge** für Premium-Confidence-Signale

---

## Aktueller Stand (2026-05-27)

| Phase | Notebook | Status |
|---|---|---|
| Phase 0 — Pipeline-Bootstrap | NB01–NB04 | ✅ abgeschlossen |
| Phase 1 — Feature & Modell-Iteration | NB05–NB08, NB10 | ✅ abgeschlossen |
| Phase 1.5 — FX-only Best-Config-Finding | NB11 | ✅ Sieger: 27 Features, PF 2.015 |
| **Phase A — Model Battery** | **NB12** | 🟡 **Code patched, wartet auf Colab-Run** |
| Phase B — Cross-Asset | NB13 | ⚪ Vorbereitet, kommt nach Phase A |
| Phase C — Multi-Timeframe | NB14 | ⚪ Geplant |
| Phase D — Architecture Decision | NB15 | ⚪ Geplant |
| Phase E — Pine Export + Backtest UI | NB09, NB16, NB17 | ⚪ ZULETZT |

Siehe [docs/roadmap.md](docs/roadmap.md) für Details pro Phase.

---

## Repository-Struktur

```
pace-algo/
├── core/                Platform-agnostic Python ML (config, data, features, train, analysis)
├── notebooks/           Colab-Notebooks NB01–NB12 (Pipeline + Forschung)
├── deploy_pine/         Pine Script v6 Output (V1 target)
├── deploy_server/       Backend deployment (V2+, noch leer)
├── data_cache/          OHLCV Parquet-Cache (nicht versioniert)
├── artifacts/           Trainierte Modelle, Reports (nicht versioniert)
├── results/             Versionierte Experiment-Outputs (CSV/JSON)  ← NEU
├── research/            Forschungs-Interpretationen + Lessons-Learned ← NEU
├── docs/                Strategie, Architektur, Roadmap ← NEU
├── tests/               Unit-Tests + Pine-Compatibility-Checks
├── HANDOFF.md           Source of truth, Multi-Workstation-Sync-Protokoll
└── README.md            (diese Datei)
```

**Doku-Hierarchie:**
- **HANDOFF.md** — operativ ("wo stehen wir gerade?"), Sync zwischen Workstations
- **/docs/** — Strategie ("wie sollen wir bauen?"), langlebig
- **/research/** — Erkenntnisse ("was haben wir gelernt?"), pro Phase
- **/results/** — Rohdaten (versioniertes JSON/CSV pro Notebook-Run)

---

## Architektur-Prinzipien (LOCKED)

Aus HANDOFF.md Section 12 (Locked Rules). Verkürzte Liste:

1. **No feature without measurable OOS lift** (≥ +0.05 PF in Ablation)
2. **Data trumps intuition** — SHAP-dead Features raus, egal wie theoretisch plausibel
3. **No single-asset optimization** — Universal-Indikator ist Ziel
4. **VAL-derived cutoffs only** — niemals TEST-Set für irgendwelche Hyperparameter
5. **Walk-Forward Validation always** — kein random shuffle auf Time-Series
6. **Bit-exact Python ↔ Pine** — NB10-Mechanismus enforced
7. **No look-ahead leakage** — HTF muss shift(1), Macro muss shift(1)
8. **Pine Budget enforced** — max 30 trees, depth 3, 15 features, 5000 ops/bar
9. **Quality > Speed** — kein Release-Pressure
10. **Honest backtests** — was User auf Chart sieht IST der Backtest

Volle Liste in HANDOFF.md Section 12.

---

## Performance-Targets (V1, Universal)

| Metrik | Schwellwert |
|---|---|
| Mean Premium-PF über Asset-Klassen | ≥ 1.4 |
| Min PF pro Asset-Klasse | ≥ 1.3 |
| Hold-Out-Symbole (GBPUSD, NDX/QQQ) PF | ≥ 1.4 |
| Min PF pro Jahr (2020–2025) | ≥ 1.3 |
| Stability CV über Jahre | < 0.25 |
| Max Drawdown | < 18% |
| Bit-exact Python↔Pine | Pflicht, NB10 enforces |

**Kein Launch ohne alle obigen.**

---

## Daten-Quellen

### Phase 1 (aktuell, frei)
- **Dukascopy** — EURUSD, USDJPY, GBPUSD, XAUUSD (5M+)
- **KuCoin** — BTC, ETH, SOL (5M+, OHLCV; kein OI/Funding US-blocked)
- **Yahoo Finance** — VIX, DXY, TNX (macro, daily — derzeit SHAP-dead, deprecated für V1)

### Phase 2 (geplant, $29/Monat)
- **Polygon.io** — SPY, QQQ, USO, EWG (US Indices/ETFs/Commodities)

Aktivierung erfordert Nico-Entscheidung, wird in Phase B (NB13) relevant.

---

## Monatlicher Workflow (V1, post-launch)

```
01_fetch_data.ipynb              → frisches OHLCV (~10 min)
02_feature_engineering.ipynb     → Feature-Matrizen (~5 min)
03_asset_clustering.ipynb        → K-Means-Asset-Cluster (~2 min)
04_triple_barrier_labeling.ipynb → R=1.5 Labels (~3 min)
05_train_lgbm.ipynb              → LGBM-Retraining (~15 min)
12_model_battery.ipynb           → Sanity-Check Modell-Vergleich (~30 min)
17_pine_compilation.ipynb        → neuer Pine-Code (~5 min, Phase E)
                                  └→ manual TradingView Publish
```

Total: ~70 Minuten/Monat. Phase 1.5 macht Backend (V1.5) das automatisch.

---

## Multi-Workstation-Sync

Dieses Repo läuft auf zwei Maschinen (Arbeits-PC + Heim-PC) mit unterschiedlichen Anthropic-Accounts. Sync ausschließlich über Git.

**Vor jeder Session:** `git pull --ff-only origin main` + Read HANDOFF.md.
**Nach jeder Session:** Append HANDOFF Section 19 + commit + push.

Volle Doku in HANDOFF.md Sections 0, 0a, 20.

---

## Lizenz

Proprietary — © 2026 Nico Flotz. All rights reserved.
