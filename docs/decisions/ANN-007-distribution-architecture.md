# ANN-007: Distribution-Architektur (Website + Stripe + TradingView Invite Automation)

**Status:** Active (V1-Vorbereitung, Implementation post-NB17)
**Datum:** 2026-05-27
**Locked-By:** Nico-Strategy-Decision
**Related:** [[ANN-005]] (V1-vs-V1.5-Scope)

---

## 1. Hypothese

PaceAlgo braucht für den Launch nicht nur das Pine-Script, sondern eine **vollständige Distribution-Pipeline**: Marketing-Website → Stripe-Checkout → User-DB → TradingView-Invite-Management → Auto-Revoke bei Kündigung.

Ohne diese Pipeline kann kein Subscription-Business laufen, egal wie gut das ML-Modell ist.

**Strategische Annahme:** Die Pipeline sollte von Anfang an **modular** geplant werden, auch wenn die erste Iteration simpel bleibt — damit V1.5/V2 (Continuous Retraining, Cloud-Dashboard) auf der gleichen Infrastruktur aufbauen können.

## 2. Experiment

Kein klassisches Experiment — strategische Architektur-Entscheidung basierend auf:
- Nico's bestehende Infrastruktur (IONOS-Domain)
- Industry-Standard für SaaS-MVPs (Stripe + minimaler Stack)
- TradingView-Constraints (Invite-Only via Username, kein offizielles API für Bulk-Invites)

## 3. Resultat

**Komponenten-Inventur:**

| Komponente | Wahl | Begründung |
|---|---|---|
| Domain | **IONOS** (bestehend) | Bereits vorhanden, keine Migration nötig für V1 |
| Frontend-Framework | **Lovable** oder **Next.js (AI-assisted)** | Beides erlaubt schnelles MVP. Lovable für reine Marketing-Landing, Next.js wenn User-Dashboard von Anfang an dazukommt |
| Frontend-Hosting (V1) | **Vercel** | Free-Tier reicht für Marketing-Site, deploy-from-git |
| Backend-Hosting (V1) | **Railway** oder **Hetzner VPS** | Railway = einfaches PaaS für Webhook + DB, Hetzner = günstiger bei mehr Traffic |
| Database | **Supabase (Postgres)** oder **Railway-managed Postgres** | Supabase mit eingebauter Auth ist V2-ready. Railway-Postgres ist einfacher für V1 |
| Payment | **Stripe Subscriptions** | Standard, Webhook-API stabil, supports Trial/Yearly/Lifetime |
| TradingView-Integration | **Self-built Invite-Manager** | TV hat kein public Invite-API; Workflow: Stripe Webhook → User-DB → Selenium/Manual-Trigger zum TV-Invite |

## 4. Decision

**V1-Stack ist gelocked auf:**

```
Frontend (Marketing + Checkout):
  └─> Lovable / Next.js
      └─> Vercel-Hosting
          └─> IONOS-Domain (DNS)
              └─> Stripe-Checkout-Embed

Backend (User-Lifecycle):
  └─> Node.js / Python (TBD bei Implementation)
      └─> Railway / Hetzner VPS
          └─> Postgres (User-DB)
              ├─> Stripe-Webhook-Receiver
              ├─> TradingView-Invite-Manager (semi-automated)
              └─> Subscription-State-Sync

Continuous Operations:
  └─> Cron-Job (Daily):
      ├─> Check expired subscriptions (Stripe)
      ├─> Revoke TradingView access for expired
      └─> Log + Email on errors
```

**Modulares Prinzip:**
- Jede Komponente ist via API-Boundary austauschbar
- Wenn V2 zu Backend-ML wechselt, kann derselbe User-DB-Service genutzt werden
- Wenn wir später von Railway nach Hetzner ziehen, wechselt nur das Deployment-Target, nicht der Code

**KEIN V1-Scope:**
- ❌ Web-Dashboard mit Trade-History (V2-Feature)
- ❌ Multi-Device-Sync (V2)
- ❌ User-spezifisches ML-Tuning (V2+)
- ❌ Discord-Bot-Integration für Premium-Channel (optional V1.5 falls easy)

**V1-Minimum-Viable-Distribution:**
1. Marketing-Landing-Page (Hero, Features, Pricing, FAQ, Buy-Button)
2. Stripe-Checkout (Monthly/Yearly Subscription + One-time Lifetime)
3. Post-Purchase-Form: User gibt TradingView-Username an
4. Backend: Stripe-Webhook → DB-Insert → manual/semi-auto TV-Invite (User wartet ~Stunden)
5. Subscription-Cancel-Webhook → DB-Update → TV-Access-Revoke

## 5. Konsequenz

**Repository-Struktur-Erweiterung (post-NB17, vor V1-Launch):**

```
pace-algo/                       # ML-Forschung (bestehend)
├── core/
├── notebooks/
├── results/
├── research/
├── docs/
└── deploy_pine/                 # V1-Output (Pine-Script)

pace-algo-distribution/          # NEUES SEPARATES Repo (Marketing + Backend)
├── frontend/                    # Lovable export / Next.js Marketing-Site
├── backend/                     # Stripe-Webhook + TradingView-Invite-Manager
├── database/                    # Schema, Migrations
└── docs/                        # Distribution-spezifische Doku
```

**Begründung für separates Repo:** ML-Forschung und Distribution haben unterschiedliche Stakeholder, Release-Cadence (Forschung = monatlich, Marketing = wöchentlich) und Skill-Requirements (Python/Quant vs JS/Web/DevOps). Trennung verhindert Cross-Contamination.

**Was bereits jetzt im pace-algo-Repo bleibt:**
- `deploy_server/` Ordner bleibt für V1.5+ Backend-ML-Code (Consensus-API, Continuous Retraining)
- ABER: Distribution-Stack (Stripe, Website) lebt im neuen Repo

**Zeitplan:**
- **Pre-V1-Launch (Phase E/F):** Distribution-Stack-Setup (~2-4 Wochen) parallel zu NB17 Pine-Compilation
- **V1-Launch:** Marketing-Site live, Stripe aktiv, TradingView-Invite-Workflow funktionsfähig
- **V1.5-Launch (+3-6 Monate):** Backend-ML-API in pace-algo/deploy_server/, Distribution-Backend ruft sie auf für Consensus-Validation
- **V2:** Distribution-Backend + ML-Backend mergen evtl., oder bleiben getrennt mit klarem API-Contract

**Risiken + Mitigationen:**

| Risiko | Mitigation |
|---|---|
| TradingView ändert Invite-Mechanismus | Self-built Manager ist Selenium-basiert, kann an UI-Changes angepasst werden |
| Stripe-Webhook missed → User zahlt aber kein Access | Idempotency-Key + Email-Alert auf Webhook-Failures, Daily-Reconciliation-Cron |
| Auto-Revoke löscht User-Daten zu früh | 7-Tage-Grace-Period nach Cancel + Email-Reminder vor Revoke |
| DB-Verlust | Daily-Backup (Supabase auto) + Restore-Procedure dokumentiert |

**Open-Decisions (vor Implementation zu treffen):**

- ⏳ Lovable vs Next.js: schnellste Time-to-MVP testen wenn V1-Launch nah
- ⏳ Railway vs Hetzner: Skalierung-Forecast machen (geschätzte User-Zahl Y1)
- ⏳ Supabase vs Railway-Postgres: Auth-Anforderungen klären (V1: kein Login, nur Stripe-Customer-ID-Match)

**Marketing-Implikation:**

Die Distribution-Pipeline IST Teil des Produkts. Ein User der nach Stripe-Payment 3 Tage auf TV-Invite wartet, hat ein schlechtes Onboarding-Erlebnis — egal wie gut das Modell ist. Daher:
- Post-Purchase-Email mit "Was kommt jetzt?" (Erwartungs-Management)
- Status-Page bei Verzögerungen
- Klar dokumentierter SLA: "Invite innerhalb 24h"
