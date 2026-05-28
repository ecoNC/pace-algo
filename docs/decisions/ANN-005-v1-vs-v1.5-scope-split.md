# ANN-005: V1 vs V1.5 Scope-Split

**Status:** Active **(Scope verschärft durch [ANN-016](ANN-016-fx-as-reference-blueprint-industrialization-first.md))** — V1-Definition ist jetzt strenger: kein FX-only-Launch, ≥ 2 Asset-Klassen über Reference-Blueprint nötig.
**Datum:** 2026-05-27 (V1-Definition verschärft 2026-05-28)
**Wichtig:** Lies **ANN-016 ZUERST** für aktuelle V1-Launch-Definition, dann ANN-009 für Multi-Model-Architektur, dann dieses ADR für Feature-Scope-Trennung V1/V1.5.
**Locked-By:** HANDOFF Section 12.2.9 ("Backend-compatible from day one") + 12.3.13 ("Universal first") + **ANN-016 Lock 3** (V1-Launch erst bei ≥ 2 Asset-Klassen über Blueprint)
**Related:** [[ANN-016]] (V1-Definition verschärft) [[ANN-009]] (Multi-Model-Architektur) [[ANN-004]] (Consensus → V1.5) [[ANN-001]] (SMC → research only)

---

## 1. Hypothese

Ein klarer Scope-Split zwischen V1 (Pine-only) und V1.5 (Hybrid Backend) ist strategisch besser als V1 zu überladen, weil:

- **V1 lauffähig ohne Server-Infrastruktur** → schneller Launch möglich, niedrige Operations-Kosten
- **V1.5 bringt Backend-Edges (Consensus, Continuous Retraining, Drift-Detection)** → echter Mehrwert, kein künstliches Paywall-Feature
- **Klarer Upgrade-Pfad für User** → von Standalone zu Hybrid mit echtem PF/WR-Lift

## 2. Experiment

**Quelle:** Aggregierte Evidence aus NB05–NB12 + Architektur-Constraints aus HANDOFF Section 12.

**Was wir wissen:**
- Pine-Budget limits: 30 trees, depth 3, 15 features, 5000 ops/bar (HANDOFF 12.2.10) — passt für LightGBM-only, nicht für Consensus
- Consensus-Edge auf Hold-Out: PF 2.93 vs LGBM-Alone 2.54 ([ANN-004](ANN-004-consensus-filter-v1.5-not-v1.md))
- LightGBM-Alone Edge auf Hold-Out: PF 2.54 — bereits stark genug für Launch
- Continuous Learning erfordert Backend-Infrastruktur, in Pine nicht möglich

**Was wir testen müssen vor V1-Launch (Phase E):**
- Bit-Exact Python ↔ Pine (NB10-Mechanismus, schon implementiert)
- Cross-Asset-Generalisierung (NB13 in Phase B, kommt jetzt)
- Multi-TF-Robustheit (NB14 in Phase C)
- Universal/Cluster/Router Architektur-Wahl (NB15 in Phase D)

## 3. Resultat

Klarer Scope-Split-Vorschlag (validiert durch NB12-Daten):

| Feature | V1 (Pine standalone) | V1.5 (Hybrid Backend) | V2 (Full Backend) |
|---|:---:|:---:|:---:|
| LightGBM-Inferenz | ✅ lokal in Pine | ✅ lokal in Pine | ⚪ optional Cloud |
| Tier-System (Standard/High/Premium) | ✅ | ✅ | ✅ |
| GBPUSD-Hold-Out-validierte Edge (PF 2.54) | ✅ | ✅ | ✅ |
| Backtest-Dashboard im Chart | ✅ | ✅ | ✅ |
| Historische Trade-Visualisierung | ✅ | ✅ | ✅ |
| 3 Profile (Conservative/Balanced/Aggressive) | ✅ | ✅ | ✅ |
| Anti-Curve-Fitting (lock Slider-Ranges) | ✅ | ✅ | ✅ |
| Bit-Exact Validation (NB10) | ✅ Pflicht vor Launch | ✅ | ✅ |
| **Consensus-Filter (PF 2.93)** | ❌ | ✅ via Backend-API | ✅ |
| Continuous Retraining | ❌ (manuell monatlich) | ✅ Backend cron-job | ✅ |
| Drift-Detection | ❌ | ✅ Backend Alert | ✅ |
| Auto-deployed Pine-Updates | ❌ | ✅ Update-Channel | ✅ |
| Cloud-Inferenz | ❌ | ❌ (Pine bleibt local) | ✅ optional |
| Web-Dashboard | ❌ | ❌ | ✅ |
| User-Accounts / Multi-Device | ❌ | ❌ | ✅ |
| Continuous Learning aus User-Trades | ❌ | ❌ | ✅ |

## 4. Decision

**Lock dieses Scope-Splits.**

V1, V1.5 und V2 sind klar abgegrenzt. Kein Feature darf "von V1.5 nach V1 wandern" außer mit expliziter ADR-Begründung (z.B. wenn Pine-Limits sich ändern).

**Konkret nicht erlaubt:**
- Webhook-basierte Live-Signals in V1 (V1.5-only)
- CatBoost im Pine-Code (V1.5-Backend only)
- User-Accounts in V1 (V2 only)

**Konkret erlaubt:**
- V1-Code MUSS Backend-kompatibel sein (HANDOFF 12.2.9) → `core/` bleibt platform-agnostisch
- V1 darf Hooks/Stubs für V1.5-Backend-Calls vorbereiten (aber nicht aktivieren)

## 5. Konsequenz

**Code-Architektur (was wird wo gebaut):**

```
core/                  ← Platform-agnostic, lebt durch alle Versionen
├── data/              ← V1-Datenpipeline, V1.5+ Backend nutzt es auch
├── features/          ← V1-Pine-fähig (27 Features), V2 kann erweitern
├── train/             ← V1: monatlicher manueller Run, V1.5: Backend-Cron
├── analysis/          ← SHAP, Validation — alle Versionen
└── export/            ← V1: Pine-Export-Generator (NB09)

deploy_pine/           ← V1, V1.5 (Pine ist FE), V2 (Pine ist optional)
├── pace_algo_v1.0.pine
└── pace_algo_v1.5.pine ← include() oder Backend-API-Call zu /validate

deploy_server/         ← V1: leer. V1.5: aktiv. V2: erweitert.
├── retrain_pipeline/  ← V1.5+
├── consensus_api/     ← V1.5+ (siehe ANN-004)
├── pine_publisher/    ← V1.5+ (auto-update channel)
├── inference_api/     ← V2 only (cloud inference)
├── dashboard/         ← V2 only (Web UI)
└── auth/              ← V2 only
```

**Marketing-Komms-Plan:**

- **V1-Launch:** "Standalone AI-Indikator. Premium-Signale mit 63% Win-Rate, validiert auf Hold-Out-Symbol. Lokal in TradingView ohne Server-Abhängigkeit."
- **V1.5-Announcement:** "Plus: Server-Verbindung schaltet Multi-Model-Consensus frei. Premium-Signale steigen auf 66% WR und PF 2.9 (in unserem Hold-Out-Test). Auto-Updates für Modell-Drift inklusive."
- **V2-Announcement:** "Vollständige Cloud-Plattform: Web-Dashboard, Multi-Device-Sync, Continuous Learning aus Live-Signal-Outcomes."

Ehrliche Sprache, mit Zahlen belegt. Kein Paywall-Theater.

**Zeitplan (gross):**
- V1: Phase A–E (jetzt bis Q3 2026)
- V1.5: 3–6 Monate post-V1-Launch, abhängig von User-Feedback
- V2: 6–12 Monate post-V1.5, abhängig von User-Demand für Web-Plattform

**Strategische Implikation:**

- **Kein Pressure auf V1 für Consensus.** Phase B (NB13) testet ob Consensus-Lift jenseits FX hält. Falls JA → V1.5 sicher. Falls NEIN → V1.5 ist "nur" Continuous Retraining.
- **V1 muss alleine stehen können.** Wenn User kein Backend-Tier kauft, soll V1 trotzdem ein gutes Produkt sein. PF 2.54 auf Hold-Out reicht dafür.
- **V1.5 ist der echte Money-Maker.** Höherer Preis-Tier rechtfertigt durch echten Edge-Lift, nicht durch künstliche Features.
