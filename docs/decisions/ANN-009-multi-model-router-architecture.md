# ANN-009: Multi-Model Router Architecture (Strategy Pivot Lock)

**Status:** Active — **OVERRIDES architecture assumptions in ANN-005**
**Datum:** 2026-05-27
**Locked-By:** Nico-Decision nach NB13-Verdict + ANN-006 Robustheits-Mantra
**Related:** [[ANN-006]] (Robustness Mantra) [[ANN-005]] (V1-Scope) [[ANN-008]] (FX→Crypto Bruch)

---

## 1. Hypothese

Wenn ein Single-Universal-Modell auf einer Asset-Klasse (FX) gut performt aber auf einer anderen (Crypto) komplett bricht (ANN-008 belegt: PF 2.49 vs 0.99 mean), dann ist die richtige Architektur **NICHT** "ein Modell für alle". Sondern: **mehrere asset-spezialisierte Modelle, die hinter einer einheitlichen User-Experience verborgen sind**.

Die strategische Annahme: **User sieht ein Produkt, intern arbeiten mehrere Spezialisten.**

Hypothese ist gleichzeitig eine Korrektur der ursprünglichen "Universal Indicator"-Annahme aus ANN-005. Wir wechseln von Single-Model-Universal zu Multi-Model-Universal-UX.

## 2. Experiment

Kein klassisches Experiment — strategische Architektur-Entscheidung, basiert auf:

**Evidenz aus NB13 (siehe ANN-008):**
- FX-trainiertes Modell auf FX: Premium-PF 2.49 (5m), 2.5+ auf 3 nie trainierten FX-Symbolen
- Gleiches Modell auf Crypto: Premium-PF 0.99 = statistisch random
- SHAP-Werte identisch zwischen Klassen (Feature-Patterns übertragbar, aber semantisch nicht prädiktiv)

**Logische Konsequenz:**
- Variante A (Universal-Single-Model) **kann nicht** funktionieren — die Daten widerlegen es
- Variante B (Per-Cluster-Cutoffs) hilft nicht — Edge fehlt grundsätzlich, nicht Kalibrierung
- Variante C (Router + Spezialmodelle) **muss** der Weg sein, weil:
  - FX-Edge ist solide und groß (PF 2.5 auf 5m)
  - Crypto-Edge braucht andere Features/Training — keine Universal-Lösung möglich
  - Pine-Skript kann mehrere Modell-Subgraphs hosten + via `syminfo` routen

**Locked Rule Konfiguration (HANDOFF Section 12.4):**
- Existing Lock: "Universal first" wird neu interpretiert: **Universal UX**, nicht Universal Model
- Existing Lock: "No single-asset optimization" wird neu interpretiert: KEIN Modell wird auf ein Asset-Symbol getunt, aber WIR akzeptieren Asset-Klassen-Modelle

## 3. Resultat

**Neue Zielarchitektur (V2+, V1 reduziert):**

```
PaceAlgo Indicator (Pine Script v6)
│
├─ Asset Detector (Pine: syminfo.type, syminfo.tickerid, ggf. tag overrides)
│   ├─ FX        → routes to fx_model()
│   ├─ Crypto    → routes to crypto_model()
│   ├─ Indices   → routes to indices_model()
│   └─ Commodity → routes to commodity_model()
│
├─ Shared Feature-Engineering Layer
│   ├─ Base features (ATR, EMA, RSI, swing levels)
│   ├─ HTF context (1h/4h)
│   └─ Session features (für FX/Crypto unterschiedlich gewichtet)
│
├─ Model Subgraphs (jeweils embedded tree-cascade)
│   ├─ fx_model.predict(features) → probability_fx
│   ├─ crypto_model.predict(features_plus_crypto_extras) → probability_crypto
│   ├─ indices_model.predict(features) → probability_indices
│   └─ commodity_model.predict(features) → probability_commodity
│
├─ Tier Engine (shared)
│   ├─ Standard / High / Premium thresholds (VAL-derived per Modell)
│   └─ Confidence calibration
│
└─ User UI (shared)
    ├─ BUY/SELL labels + entry/TP/SL boxes
    ├─ Backtest dashboard (PF/WR/MDD live auf aktivem Chart)
    ├─ Tier badge (Premium signal indicator)
    └─ 3 Profile (Conservative/Balanced/Aggressive)
```

**User-Perception:** EIN Indikator, gleiche UX überall.
**Intern:** 4 spezialisierte Pipelines, plus shared Layers.

## 4. Decision

**Multi-Model Router Architecture wird gelocked als V2-Zielarchitektur.**

**V1-Scope (unverändert von ANN-005):**
- Nur FX-Modell aktiv
- Pine-Code enthält bereits **Router-Layer-Skelett** (Asset-Detector), aber andere Asset-Klassen liefern "no signal" oder klare UI-Warning
- Begründung: V1 nicht über-engineeren, aber so bauen dass V2 nicht refactoring-Hölle wird

**V2-Scope (neu locked):**
- Mindestens 2 weitere Modelle (Crypto + Indices)
- Vollständige Router-Logik
- Asset-Detection via Pine `syminfo` + tag-overrides
- Continuous Retraining im Backend (V1.5+) speist mehrere Modelle

**V3-Scope (V2+):**
- Continuous Training mit User-Feedback
- Adaptive Model-Selection (z.B. "verwende FX-Modell für Indices wenn Indices-Modell unterperformt")
- Cross-Model-Ensemble innerhalb einer Asset-Klasse

**Konkrete V1-Vorbereitungen (NICHT verschiebbar):**
- `core/router/` Modul anlegen (Asset-Detection-Logic in Python für Backtests + spätere Pine-Generation)
- `core/models/{fx,crypto,indices,commodity}/` Ordner-Struktur (auch wenn nur fx/ aktiv)
- Pine-Code-Skelett mit Router-Switch (auch wenn andere Branches "no-op" sind)
- Shared `core/features/` bleibt — Features werden klassenneutral berechnet, Modelle entscheiden ob sie nutzen

**Was NICHT erlaubt ist (per ANN-006 Lock 1):**
- Pine-Code refactoring nach V1-Launch um Router nachzurüsten ("Refactor-Hölle")
- "Wir bauen V1 fertig, dann V2 später" → V1 muss strukturell V2-bereit sein
- Nur ein Modell embedden ohne Router-Layer

## 5. Konsequenz

### Code-Änderungen (anstehend)

```
core/
├── data/            (bestehend, klassenneutral)
├── features/        (bestehend, klassenneutral — wird shared layer in V2)
├── labeling/        (bestehend, klassenneutral)
├── train/
│   ├── lgbm_trainer.py        (bestehend)
│   ├── train_fx.py            (V1: actively trained)
│   ├── train_crypto.py        (V2: stub, NB13c result)
│   ├── train_indices.py       (V2+: Polygon nötig)
│   └── train_commodity.py     (V2+: Gold + Silver + Oil)
├── models/                    NEU
│   ├── fx/
│   │   └── fx_lgbm_v1.pkl    (V1 production model)
│   ├── crypto/
│   │   └── (V2+)
│   ├── indices/
│   │   └── (V2+)
│   └── commodity/
│       └── (V2+)
├── router/                    NEU
│   ├── asset_detector.py      (Asset-Klasse aus Symbol-String ableiten)
│   ├── model_selector.py      (welches Modell für welche Klasse)
│   └── pine_router_codegen.py (Pine-Code-Generator für Router-Layer)
├── analysis/        (bestehend)
└── export/          (bestehend, wird erweitert)
```

### Pine-Code-Skelett (V1, Router-Ready)

```pine
//@version=6
indicator("PaceAlgo")

// === ASSET DETECTION (Router Layer) ===
asset_class = syminfo.type == "forex" ? "fx"
           : syminfo.type == "crypto" ? "crypto"
           : syminfo.type == "index" or syminfo.type == "stock" ? "indices"
           : syminfo.type == "fund" ? "commodity"
           : "unsupported"

// === SHARED FEATURE ENGINEERING ===
// (Code wird in core/export/ generiert)
features = compute_shared_features(...)

// === MODEL ROUTER ===
if asset_class == "fx"
    probability := fx_model_predict(features)
else if asset_class == "crypto"
    probability := na  // V1 stub — UI shows "Crypto Beta — V2 coming"
else if asset_class == "indices"
    probability := na  // V1 stub
else if asset_class == "commodity"
    probability := na  // V1 stub
else
    probability := na  // unsupported chart

// === TIER ENGINE (shared) ===
tier = probability >= premium_cutoff ? "Premium"
     : probability >= high_cutoff ? "High"
     : probability >= standard_cutoff ? "Standard"
     : "none"

// === UI (shared) ===
plot signals, draw boxes, backtest table, ...
```

### Doku-Implikationen

- `docs/architecture.md` muss Router-Layer aufnehmen
- `docs/pine_router_design.md` (NEU) für Pine-spezifische Details
- `docs/roadmap.md` muss V1-V3 mit Router-Architektur zeigen
- `docs/model_registry.md` listet alle 4 Modell-Slots (auch wenn 3 leer)
- `docs/deployment_plan.md` V2-Sektion mit Router
- `README.md` Tagline-Update: "Universal UX + Specialized Intelligence"
- ANN-005 wird durch ANN-009 architektonisch überstellt (V1-Scope bleibt aber gelockt)

### Marketing-Implikation

- **V1 (FX-only):** "AI Trading Indicator für FX Major Pairs"
- **V2 (Multi-Model):** "Ein Indikator, vier spezialisierte AI-Modelle — ein Tool für FX, Crypto, Indices und Commodities"
- **V3 (Cloud Backend):** "Continuous Learning — die AI passt sich an deinen Trading-Stil an"

Die Story ist jetzt klarer und ehrlicher als "Universal Model":
- V1 = "spezialisiertes FX-Tool" (klare Erwartung, klare Edge)
- V2 = "Multi-Asset-Tool mit asset-spezifischer Intelligence" (Differenzierung gegen Konkurrenz)

### Risk-Implikationen

| Risiko | V1 | V2 |
|---|---|---|
| Pine-Budget-Verbrauch | ~4% (1 Modell) | Möglicherweise 30%+ (4 Modelle × 30 Trees) — siehe pine_router_design.md |
| Backtest-Komplexität | Linear (1 Modell) | Quadratisch (4 Modelle × 5 Asset-Klassen × 5 TFs Tests nötig) |
| Code-Maintenance | 1 Pipeline | 4 Pipelines + Router + Shared Layers |
| Model-Drift-Tracking | 1 Modell | 4 Modelle parallel zu monitoren |

Mitigation: V1 baut Router-Skelett aber Branches sind no-op. V2 fügt nur die Branches dazu, kein architektureller Refactor.

### Lessons (warum NB13 NICHT gescheitert war)

NB13 lieferte den wahrscheinlich wichtigsten Architektur-Pivot der ganzen Forschung. Ohne diesen Test hätten wir:
- V1 mit "Universal"-Marketing gelauncht
- Crypto-Trader hätten enttäuschend gehandelt
- User-Vertrauen wäre beschädigt
- Refactor zu Multi-Model wäre post-launch nötig gewesen → "Refactor-Hölle"

NB13 ist damit eine **erfolgreiche Falsifikation** der Universal-Single-Model-Hypothese. Die Daten sprechen klar, die Architektur folgt. Das ist exakt die Disziplin aus ANN-006 (Robustheits-Mantra).
