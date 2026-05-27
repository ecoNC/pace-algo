# Deployment Plan — V1 → V1.5 → V2 → V3 Migration

**Architektur-Lock seit 2026-05-27:** Multi-Model Router per [ANN-009](decisions/ANN-009-multi-model-router-architecture.md). Pine-Router-Details: [pine_router_design.md](pine_router_design.md).

## V1: Pine-Only (FX-Modell aktiv, Router-Skelett ready) — Target Q3–Q4 2026

**Was läuft:**
- **EIN** Pine Script v6 Indikator mit Router-Layer-Skelett
- **EIN** aktives Modell: `fx_model` (LightGBM, 30 trees × depth 3, 27 Features)
- Pine-Code enthält bereits Asset-Detection + Stubs für Crypto/Indices/Commodity
- Non-FX-Charts zeigen "🚧 V2 coming"-Badge im UI
- Inferenz bar-by-bar im TradingView-Browser
- Keine Server-Komponente

**Wie deployed:**
- Pine-Code generiert in `deploy_pine/pace_algo_v{X.Y}.pine` (NB09 in Phase E)
- Nico published via TradingView Invite-Only-Mechanismus
- Manuelles monatliches Retraining lokal → neue Pine-Version → manual republish

**User-Workflow:**
1. Subscription via Whop/Stripe Shop
2. TradingView-Username an Nico
3. Invite-Only-Access wird freigeschaltet
4. User öffnet Indicator auf beliebigem Chart (FX/Indices/Crypto/Stocks/Commodities)
5. Sieht live BUY/SELL-Signale + integriertes Backtest-Dashboard

**Constraints:**
- Pine-Budget hart enforced (siehe [pine_constraints.md](pine_constraints.md))
- CatBoost ausgeschlossen
- Kein Server-State, keine Webhooks
- Modell-Update = neuer Pine-File-Release

**Erfolgs-Kriterien für V1-Launch:**
- Mean Premium-PF über Asset-Klassen ≥ 1.4
- Min PF pro Asset-Klasse ≥ 1.3
- Hold-Out-Symbole (GBPUSD, NDX/QQQ) validiert
- Bit-exact Validation Python ↔ Pine bestanden (NB10-Mechanismus)

---

## V1.5: Hybrid (Post-Launch, 3–6 Monate nach V1)

**Was sich ändert:**
- Pine läuft weiterhin LightGBM-Modell lokal (kein Inferenz-Lag, kein Webhook-Risiko)
- Backend (in `deploy_server/`) wird aktiviert für Continuous Retraining
- Backend trainiert monatlich automatisch auf neuen Daten + Drift-Detection
- Neue Pine-Version wird auto-generated und an User über Update-Channel ausgeliefert
- **Consensus-Filter (LGBM + XGB + CatBoost)** läuft im Backend — Pine fragt Backend an, ob Premium-Signal "Consensus-validated" ist. Datenbasis: NB12 zeigt PF-Lift 2.54 → 2.93 auf GBPUSD-Hold-Out wenn alle 3 zustimmen.

**Komponenten:**
- `deploy_server/retrain_pipeline/` — Cron-job (Cloud-Run oder ähnliches)
- `deploy_server/pine_publisher/` — Auto-publish neue Pine-Version
- User-Notification-Channel (Email oder Whop-Discord-Bot)

**User-Workflow Veränderung:**
- User bekommt: "PaceAlgo v1.5.3 verfügbar — auto-update aktiv"
- Klick → Pine-Version wird in TV automatisch ausgetauscht
- Sonst gleiche UX wie V1

**Warum nicht direkt V2?**
- Webhook-basierte Live-Signals haben Lag-Risiko (Server-Down, Network-Issues)
- Pine-Lokal-Inferenz ist robust gegen Server-Outage
- User-Feedback zeigt: lokale Pine-Inferenz wird stark präferiert

---

## V2: Multi-Model Router (Crypto + Indices + Commodity hinzu)

**Was sich ändert:**
- Aus den 1-aktiv-3-stub-Modellen werden **alle 4 aktiv**
- `crypto_model_predict()` wird befüllt — Voraussetzung: NB13c (Crypto-Spezialmodell) bestand Quality-Anchor (ANN-010)
- `indices_model_predict()` befüllt — Voraussetzung: Polygon-Aktivierung + Indices-Cross-Asset-Test
- `commodity_model_predict()` befüllt — XAUUSD-Modell + ggf. Silber/Oil
- UI-Badge "Coming Soon" verschwindet auto auf den entsprechenden Charts
- Pine-Code-Generator (Phase E) re-runs → neuer Pine-File mit allen 4 Modellen embedded
- **Kein architektureller Pine-Refactor nötig**, weil Router-Skelett in V1 schon vorhanden

**Pine-Budget-Implikation:**
- V1 (1 Modell): ~215 ops/bar, ~1055 lines
- V2 (4 Modelle): ~860 ops/bar, ~4200 lines — passt unter 5000/7000 Limit
- Lazy Evaluation im Router: nur aktives Modell wird traversed

**Quality-Anchor-Gate vor V2-Modell-Aktivierung:**
- Jedes neue Modell muss [ANN-010](decisions/ANN-010-quality-anchor.md) bestehen
- Wenn Crypto-Modell PF Premium < 1.5: **wird nicht aktiviert**, UI zeigt weiter "Coming Soon"
- Quality-Check-Report wird in `/results/quality_checks/` versioniert

## V3: Full Cloud Backend (V2 + 6–12 Monate, abhängig von User-Demand)

**Was sich ändert:**
- ML-Inferenz läuft auf Cloud-Server 24/7 (optional, Pine-Lokal bleibt Default)
- Live-Signals an TradingView via Webhook → Pine-Receiver (für High-Latency-Premium-Validation)
- Web-Dashboard mit voller Trade-History + Analytics
- User-Accounts, Multi-Device-Sync
- Continuous Learning: Signal-Outcomes feed retraining (mit Opt-In)
- Adaptive Model-Selection: z.B. "wenn Indices-Modell unterperformt, fallback auf FX-Modell für ähnliche Setups"
- Cross-Model-Ensemble: innerhalb einer Asset-Klasse mehrere Modelle (z.B. FX-Trend + FX-Range)

**Neue Komponenten:**
- `deploy_server/inference_api/` — FastAPI Endpoint, Latenz < 200ms
- `deploy_server/database/` — PostgreSQL: Users, Signals, Trades
- `deploy_server/dashboard/` — Web UI (Next.js)
- `deploy_server/auth/` — Magic-Link oder OAuth

**Komplexere Modelle möglich:**
- CatBoost wird einsatzbereit
- Deeper Trees, mehr Features
- Multi-Task-Learning (BUY/SELL + Magnitude-Prediction)
- Reinforcement-Learning auf User-Trade-Outcomes

**Migrations-Strategie für bestehende V1.5-User:**
- Opt-In zu V2 — V1.5-Pine bleibt funktional, kein Forced-Upgrade
- User die V2 aktivieren bekommen Web-Dashboard + Webhook-Pine als Alternative
- 12-Monate-Sunset für V1.5 nach V2-Launch, dann nur noch Cloud

---

## Architektur-Anforderung an V1-Code

**Schon JETZT, in `core/`:**

Alle Module müssen Plattform-agnostisch sein. Konkret:
- Keine Pine-spezifischen Hacks in `core/features/`
- Keine `print()`-debugging in Inferenz-Pfaden
- Modell-Serialisierung muss `.pkl`/`.cbm` für Server + Tree-Export für Pine unterstützen
- Features berechnen identisch in Python (Server) und Pine (Browser) — Bit-Exact-Validation NB10

Wenn V2 startet, muss `core/` ohne Änderung wiederverwendbar sein. Nur `deploy_pine/` und `deploy_server/` unterscheiden sich.

---

## Risiken und Mitigationen

| Risiko | Wann relevant | Mitigation |
|---|---|---|
| TradingView Pine-Limits ändern sich | V1 | Wir nutzen nur ~4.3% des Ops-Budgets → großer Puffer |
| Webhook-Lag in V2 | V2 | V1.5-Hybrid bleibt verfügbar als Fallback |
| Server-Down in V2 | V2 | Health-Checks, Multi-Region, Status-Page |
| User-Drift (Modell veraltet) | V1.5+ | Monatliches Retraining, Drift-Metrics-Alerting |
| Data-Source-Loss (Binance/Polygon API-Wechsel) | alle | Multi-Source-Fetcher in `core/data/`, jederzeit austauschbar |
