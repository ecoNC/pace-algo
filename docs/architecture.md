# Architecture

## Code-Layout

```
pace-algo/
├── core/                    # Platform-agnostic Python ML code
│   ├── config.py            # Symbols, TFs, train/val/test cutoffs, holdouts
│   ├── data/                # Multi-source OHLCV fetchers (Binance, KuCoin, Dukascopy, Yahoo)
│   ├── features/            # Feature engineering modules
│   │   ├── engineer.py      # ATR-normalized base features
│   │   ├── smc.py           # SMC/structure features (deprecated post-NB11)
│   │   ├── session.py       # Session/timing features
│   │   ├── htf.py           # Higher-TF interactions
│   │   └── macro.py         # Daily macro (VIX/DXY) — SHAP-dead, mostly unused
│   ├── labeling/            # Triple Barrier labeling (López de Prado)
│   ├── train/               # Walk-Forward training (LGBM/XGB/CatBoost)
│   ├── analysis/            # SHAP, calibration, regime stability
│   ├── models/              # Serialized model artifacts (.pkl, .cbm) — NOT versioned
│   └── export/              # Pine code generation (to be built in Phase E / NB09)
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

## Aktuelle Architektur-Entscheidung (offen)

**Universal vs. Specialized** — wird in **Phase D (NB15)** entschieden:
- Variante A: Ein Universal-Modell für alle Assets × TFs
- Variante B: Core-Modell + per-Cluster Kalibrierung
- Variante C: Mehrere Spezialmodelle + Pine-Router

Entscheidungs-Matrix siehe [roadmap.md](roadmap.md) Phase D.
