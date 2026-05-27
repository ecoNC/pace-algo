# Architecture

**Locked seit 2026-05-27:** Multi-Model Router Architecture per [ANN-009](decisions/ANN-009-multi-model-router-architecture.md). Siehe auch [/docs/pine_router_design.md](pine_router_design.md) für Pine-spezifische Details.

**Tagline:** "Universal UX + Specialized Intelligence" — ein Indikator, mehrere asset-spezialisierte Modelle.

## Code-Layout

```
pace-algo/
├── core/                    # Platform-agnostic Python ML code
│   ├── config.py            # Symbols, TFs, train/val/test cutoffs, holdouts, ASSET_GROUPS
│   ├── data/                # Multi-source OHLCV fetchers (Binance, KuCoin, Dukascopy, Yahoo)
│   ├── features/            # SHARED Feature Engineering Layer (klassenneutral)
│   │   ├── engineer.py      # ATR-normalized base features
│   │   ├── smc.py           # SMC/structure features (deprecated per ANN-001)
│   │   ├── session.py       # Session/timing features
│   │   ├── htf_interaction.py # Higher-TF interactions
│   │   └── macro.py         # Daily macro — deprecated for intraday
│   ├── labeling/            # Triple Barrier labeling (López de Prado)
│   ├── train/               # Walk-Forward training (LGBM/XGB/CatBoost)
│   │   ├── lgbm_trainer.py  # Shared trainer
│   │   ├── train_fx.py      # V1 — actively trained
│   │   ├── train_crypto.py  # V2 — wartet auf NB13c
│   │   ├── train_indices.py # V2+ — wartet auf Polygon
│   │   └── train_commodity.py # V2+
│   ├── analysis/            # SHAP, calibration, regime stability
│   │   ├── diagnostics.py
│   │   └── quality_check.py # NEU — ANN-010 Quality Anchor enforcement
│   ├── models/              # Multi-Model storage (ANN-009)
│   │   ├── fx/              # V1 production
│   │   ├── crypto/          # V2+
│   │   ├── indices/         # V2+
│   │   └── commodity/       # V2+
│   ├── router/              # NEU — V1-Skelett, V2-vollständig
│   │   ├── asset_detector.py    # Python-Spiegel der Pine-Logik
│   │   ├── model_selector.py    # Per-Klasse Modell-Routing
│   │   └── pine_router_codegen.py # Pine-Code-Generator für Router
│   └── export/              # Pine code generation (Phase E)
├── deploy_pine/             # Pine Script v6 output
├── deploy_server/           # Future backend deployment (V2+, not yet active)
├── notebooks/               # Colab notebooks — monthly workflow
├── data_cache/              # Cached OHLCV (Parquet) — NOT versioned
├── artifacts/               # Models, reports, generated Pine code — NOT versioned
├── results/                 # Versioned experiment outputs (CSV, JSON)
├── research/                # Strategic interpretation of results
├── docs/                    # This folder — architecture, roadmap, registries
├── tests/                   # Unit tests + Pine compatibility checks
└── HANDOFF.md               # Operative source of truth, multi-workstation sync
```

## Architektur-Prinzipien (LOCKED)

Aus HANDOFF.md Section 12.2 (Architecture Rules):

1. **Backend-kompatibel von Tag 1.** Jedes Modul in `core/` muss platform-agnostisch sein. Deployment-spezifisch in `deploy_pine/` oder `deploy_server/`.
2. **Pine-Budget enforced.** Siehe [pine_constraints.md](pine_constraints.md). Violation requires explicit Backend-V1 acknowledgment.
3. **Kein CatBoost in V1.** Oblivious Trees + categorical embeddings = nicht Pine-exportierbar. Nur LightGBM, XGBoost oder Voting (LGBM+XGB only) in Pine.
4. **Modulare Features.** Jede Feature-Gruppe = eigenes Modul. Einfach für Ablation enable/disable.

## Daten-Pipeline

```
Raw OHLCV (data_cache/raw/)
  └─> Feature Engineering (core/features/)
        └─> Triple Barrier Labels (core/labeling/)
              └─> Walk-Forward Splits (core/train/walk_forward_split)
                    ├─> Train (← TRAIN_END)
                    ├─> Val (TRAIN_END → VAL_END)   ← Tier-Cutoffs werden HIER abgeleitet
                    └─> Test (VAL_END →)            ← OOS-Evaluation
```

**Hold-Out-Symbole** (NIE im Training gesehen): GBPUSD, NDX/QQQ (wenn Polygon aktiv). Diese liefern den ehrlichsten OOS-Indikator.

## Migrations-Pfad

```
V1 (Pine-only, Phase E Output)
├── ML-Modell direkt in Pine Script v6 embedded
├── Tree-Cascade max 30 trees, depth 3, ~15 Features
├── User-facing Backtest-Widget in Pine
└── Monatliches manuelles Retraining → neue Pine-Version

V1.5 (Hybrid, post-launch)
├── Pine läuft weiterhin ML-Modell lokal
├── Backend (deploy_server/) retrainiert monatlich automatisch
├── Auto-generated neue Pine-Version → User bekommt Update-Notification
└── KEIN Webhook-Lag, lokale Inferenz bleibt

V2 (Full Backend)
├── ML-Inferenz auf Cloud-Server 24/7
├── Live-Signals via Webhook → Pine-Receiver
├── Web-Dashboard mit voller History + Analytics
├── User Accounts, Multi-Device-Sync
└── Continuous Learning (Signal-Outcomes feed retraining)
```

Siehe [deployment_plan.md](deployment_plan.md) für Migrations-Details.

## Aktuelle Architektur-Entscheidung — GELOCKED 2026-05-27

**Multi-Model Router (Variante C)** ist gelocked per [ANN-009](decisions/ANN-009-multi-model-router-architecture.md).

**Begründung:** NB13 hat empirisch gezeigt, dass ein Single-Universal-Modell nicht funktionieren kann — FX-trainiertes Modell liefert PF 2.49 auf FX, aber PF 0.99 (random) auf Crypto. Universal-Penalty existiert nicht "linear", sondern Crypto braucht komplett andere Patterns.

**Konkrete V1-V3 Konsequenz:**
- **V1:** Pine-Code enthält Router-Layer-Skelett. Nur `fx_model_predict()` ist aktiv. Andere Klassen liefern "Coming Soon"-UI.
- **V2:** Crypto + Indices + Commodity Modelle werden trainiert und in Pine eingebettet. Router routet zu aktivem Modell.
- **V3:** Cloud-Backend orchestriert Modell-Updates, Continuous Learning, asset-spezifisches Drift-Tracking.

**Pine-Router-Details:** siehe [pine_router_design.md](pine_router_design.md).

**Quality-Anchor:** Neue Asset-Klassen-Modelle müssen die Anchor-Kriterien aus [ANN-010](decisions/ANN-010-quality-anchor.md) erfüllen bevor sie in V2 deployed werden.
