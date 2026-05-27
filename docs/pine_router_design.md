# Pine Router Design

**Lock-Basis:** [ANN-009 Multi-Model Router Architecture](decisions/ANN-009-multi-model-router-architecture.md)

Dieses Dokument beschreibt **wie der Router in Pine Script v6 funktioniert** — nicht ob (das ist in ANN-009 gelocked).

---

## 1. Architektur-Skelett

```
┌─────────────────────────────────────────────────────────────────┐
│                  PaceAlgo Pine Script v6                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ASSET DETECTOR (Router Entry)                           │   │
│  │  • syminfo.type                                          │   │
│  │  • syminfo.tickerid pattern matching                     │   │
│  │  • optional user override input                          │   │
│  │                                                          │   │
│  │  Output: asset_class ∈ {fx, crypto, indices, commodity, │   │
│  │                          unsupported}                    │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                          │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │  SHARED FEATURE ENGINEERING                              │   │
│  │  • Base features (ATR, EMA, RSI, swing levels, vol)      │   │
│  │  • HTF context (1h/4h via request.security)              │   │
│  │  • Session features (hour_sin/cos)                       │   │
│  │  • Volume features (where available — FX has limits)     │   │
│  │                                                          │   │
│  │  Output: 27-feature vector (same as NB11 winner)         │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                          │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │  MODEL ROUTER (Switch by asset_class)                    │   │
│  │                                                          │   │
│  │  if asset_class == "fx":                                 │   │
│  │      probability := fx_model_predict(features)           │   │
│  │  else if asset_class == "crypto":                        │   │
│  │      probability := crypto_model_predict(features)       │   │
│  │  else if asset_class == "indices":                       │   │
│  │      probability := indices_model_predict(features)      │   │
│  │  else if asset_class == "commodity":                     │   │
│  │      probability := commodity_model_predict(features)    │   │
│  │  else:                                                   │   │
│  │      probability := na                                   │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                          │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │  TIER ENGINE (per-model VAL-derived cutoffs)             │   │
│  │  • Premium cutoff (top 1%)                               │   │
│  │  • High cutoff (top 3%)                                  │   │
│  │  • Standard cutoff (top 10%)                             │   │
│  │  • Cutoffs are PER-MODEL (different per asset class)     │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                          │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │  UI LAYER (shared across all asset classes)              │   │
│  │  • BUY/SELL labels                                       │   │
│  │  • Entry / TP / SL boxes                                 │   │
│  │  • Backtest dashboard (PF/WR/MDD)                        │   │
│  │  • Tier badge for Premium signals                        │   │
│  │  • Profile selector (Conservative/Balanced/Aggressive)   │   │
│  │  • "Beta" / "Coming Soon" badge for non-active classes   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Asset Detection

### Primary: `syminfo.type`

TradingView liefert einen Asset-Type pro Chart:

| `syminfo.type` Wert | Unsere Asset-Klasse |
|---|---|
| `"forex"` | `fx` |
| `"crypto"` | `crypto` |
| `"index"` | `indices` |
| `"stock"` | `indices` (ETFs wie SPY/QQQ) |
| `"fund"` | `indices` (Index-ETFs) |
| `"futures"` | `commodity` (zunächst, dann verfeinern) |
| `"cfd"` | depends — XAUUSD CFD = commodity, EURUSD CFD = fx |
| anderes | `unsupported` |

### Fallback: Symbol-String-Matching

`syminfo.type` ist nicht immer eindeutig (CFDs!). Backup: Pattern-Matching auf `syminfo.tickerid`:

```pine
// Pseudo-Code Pine v6
is_fx_pair() =>
    s = syminfo.tickerid
    str.contains(s, "EUR") or str.contains(s, "USD") or str.contains(s, "JPY") or
    str.contains(s, "GBP") or str.contains(s, "AUD") or str.contains(s, "CHF") or
    str.contains(s, "CAD") or str.contains(s, "NZD")
    // Hinweis: das matched auch XAUUSD! daher Gold-Check VORHER

is_gold() =>
    s = syminfo.tickerid
    str.contains(s, "XAU") or str.contains(s, "XAG") or s == "GOLD" or s == "SILVER"

is_crypto() =>
    s = syminfo.tickerid
    str.contains(s, "BTC") or str.contains(s, "ETH") or str.contains(s, "SOL") or
    str.contains(s, "USDT") or str.contains(s, "USDC")

// Reihenfolge wichtig: Commodity-Check VOR FX-Check, weil XAUUSD beide matched
detect_asset_class() =>
    if is_gold()
        "commodity"
    else if is_crypto()
        "crypto"
    else if is_fx_pair()
        "fx"
    else if syminfo.type == "index" or syminfo.type == "stock" or syminfo.type == "fund"
        "indices"
    else
        "unsupported"
```

### Tertiary: User-Override-Input

Falls Detection fehlschlägt (z.B. exotische Asset-Klasse oder neue Symbol-Konvention), gibt es ein optionales User-Input:

```pine
asset_class_override = input.string("auto", "Asset Class",
                                     options=["auto", "fx", "crypto", "indices", "commodity", "off"])
asset_class = asset_class_override == "auto" ? detect_asset_class() : asset_class_override
```

**"off"-Option:** User kann den Indikator komplett deaktivieren auf bestimmten Charts (z.B. für Backtest-Setups).

---

## 3. Shared Feature Engineering Layer

**Prinzip:** Die Feature-Berechnung ist asset-klassenneutral. Jedes Modell entscheidet welche Features es nutzt — aber die Berechnung passiert ein Mal.

**Vorteile:**
- Pine-Code-Größe wird nicht 4× (für jedes Modell die gleichen Feature-Computations)
- Wartung: bei Feature-Definition-Änderung muss nur 1 Stelle gepatcht werden
- Konsistenz: alle Modelle "sehen" die gleichen Inputs

**Implementierung (Pine):**

```pine
// === SHARED FEATURE COMPUTATION ===
// Wird einmal pro Bar berechnet, dann an Models gefüttert

atr14 = ta.atr(14)
ema20 = ta.ema(close, 20)
rsi14 = ta.rsi(close, 14)
// ... weitere 24 Features (siehe core/features/engineer.py)

// HTF Context
htf_1h_rsi = request.security(syminfo.tickerid, "60", ta.rsi(close, 14)[1])
htf_4h_atr_pct = request.security(syminfo.tickerid, "240", ta.atr(14)[1] / close[1])

// Session Features (gleich für alle Asset-Klassen, Modelle entscheiden Gewichtung)
hour_sin = math.sin(2 * math.pi * hour(time) / 24)
hour_cos = math.cos(2 * math.pi * hour(time) / 24)

// (... ca. 27 Features insgesamt)

features = [hour_sin, hour_cos, atr_percentile_100, ...]  // Array für Modell-Inputs
```

**Asset-spezifische Feature-Erweiterung (V2+):**

Manche Features sind nur in bestimmten Asset-Klassen verfügbar:
- **Crypto:** Funding Rate, Open Interest (wenn API-Source vorhanden) — V2+
- **Indices:** VIX-Korrelation, Sektor-Rotation (Daily) — V2+
- **Commodity:** USD-DXY-Korrelation, COT-Daten — V2+

Diese würden als **klassenspezifische Erweiterungen** an die Features angehängt, NUR wenn das jeweilige Modell aktiv ist. Pine-Budget-Check: zusätzliche `request.security` Calls erhöhen Latency.

---

## 4. Model Subgraphs (Embedded Trees)

Jedes Modell ist eine **embedded tree-cascade** im Pine-Code. Generiert von `core/export/pine_codegen.py` aus dem LightGBM-Modell.

**Beispiel-Struktur pro Modell:**

```pine
// === FX MODEL — 30 trees, depth 3 ===
fx_model_predict(features) =>
    // features ist das geteilte 27-element-Array
    // Subset für FX-Modell:
    h_sin = features[0]
    swing_low = features[1]
    // ... nur die Features die FX-Modell nutzt

    sum = 0.0
    // Tree 1
    if swing_low < 2.3
        if h_sin < 0.5
            sum += 0.123
        else
            sum += -0.045
    else
        // ...
    // Trees 2-30 analog
    1.0 / (1.0 + math.exp(-sum))  // sigmoid

// === CRYPTO MODEL — 30 trees, depth 3 (V2) ===
crypto_model_predict(features) =>
    // Andere Feature-Subset, andere Splits
    // (V1: na, Stub)
    na
```

**Pine-Budget-Implikation (kritisch!):**

| Setup | Total Trees | Ops/Bar | Lines |
|---|---|---|---|
| V1 (FX only) | 30 | ~215 | ~1055 |
| V2 (FX + Crypto) | 60 | ~430 | ~2100 |
| V2 (FX + Crypto + Indices) | 90 | ~645 | ~3150 |
| V2 (alle 4) | 120 | ~860 | ~4200 |

Pine-Limit: 5000 ops/bar, ca. 7000 Linien praktisch nutzbar (TradingView UI-Editor).

**Risiko:** V2 mit allen 4 Modellen könnte das Ops/Bar-Budget zu 17% nutzen. Das ist okay, aber **Plot-Operations + request.security-Calls + UI** kommen oben drauf. Reserve nötig.

**Mitigation-Optionen:**
- **Lazy Evaluation:** Nur das aktive Modell wird ausgeführt. Switch über `if`-Block heißt: andere Modell-Trees werden bei jedem Bar nicht traversed.
- **Tree-Reduction pro Asset:** Falls Crypto nur 20 Trees braucht (weil weniger Variation), Pine-Code für Crypto kürzer.
- **Per-Model Pine-Budget:** Max 30 Trees pro Modell bleibt gelocked (HANDOFF 12.2.10), aber Gesamt-Cap nicht 120.

---

## 5. Tier Engine (Per-Model Cutoffs)

**Wichtig:** Jedes Modell hat **eigene** VAL-derived Cutoffs.

Beispiel:
- FX-Modell: Premium-Cutoff bei probability ≥ 0.523 (NB13 5m)
- Crypto-Modell: Premium-Cutoff vermutlich anders (z.B. ≥ 0.470)
- Indices-Modell: dto.

**Pine-Code:**

```pine
// Cutoffs werden vom Code-Generator als Constants embedded
FX_CUTOFF_PREMIUM = 0.5233
FX_CUTOFF_HIGH = 0.5008
FX_CUTOFF_STANDARD = 0.4932

CRYPTO_CUTOFF_PREMIUM = 0.0  // V1: NA — Crypto inaktiv
// (V2: echte Werte aus crypto_model.pkl VAL-set)

INDICES_CUTOFF_PREMIUM = 0.0  // V1: NA
COMMODITY_CUTOFF_PREMIUM = 0.0  // V1: NA

// Tier Engine wählt cutoffs basierend auf asset_class
get_cutoff_premium() =>
    asset_class == "fx" ? FX_CUTOFF_PREMIUM
        : asset_class == "crypto" ? CRYPTO_CUTOFF_PREMIUM
        : asset_class == "indices" ? INDICES_CUTOFF_PREMIUM
        : asset_class == "commodity" ? COMMODITY_CUTOFF_PREMIUM
        : 1.1  // unreachable threshold = no signal

tier = probability >= get_cutoff_premium() ? "Premium"
     : probability >= get_cutoff_high() ? "High"
     : probability >= get_cutoff_standard() ? "Standard"
     : "none"
```

---

## 6. UI Layer (Shared)

**Prinzip:** Der User sieht ein konsistentes UI, egal auf welchem Chart.

```pine
// === BUY/SELL LABELS ===
if tier != "none"
    label.new(time, low - atr14, "BUY", ...)
    box.new(time, entry_price, time + tp_bars, tp_price, bgcolor=color.green)
    box.new(time, entry_price, time + sl_bars, sl_price, bgcolor=color.red)

// === TIER BADGE ===
if tier == "Premium"
    label.new(time, high + atr14, "★ Premium", textcolor=color.gold)

// === BACKTEST DASHBOARD ===
// (Table mit PF / WR / MDD / Trades — basierend auf historischem Tier-Output)

// === BETA / COMING SOON BADGE ===
if asset_class != "fx"  // V1: nur FX aktiv
    label.new(bar_index, high, "🚧 " + asset_class + " — V2 coming",
              textcolor=color.gray)
```

**Wichtig:** V1 zeigt **explizit** "V2 coming" auf Non-FX-Charts. Kein stillschweigendes "no signal" — der User soll wissen warum.

---

## 7. Pine-Code-Generation Workflow

**core/export/pine_codegen.py** (V2+) wird:

1. Liest alle Modelle aus `core/models/{fx,crypto,indices,commodity}/`
2. Liest VAL-derived Cutoffs aus jeweiligen Modell-Configs
3. Generiert Pine-Code-Snippets pro Modell (tree-cascade)
4. Generiert Router-Layer mit Asset-Detection
5. Generiert Shared Feature-Computation
6. Setzt das ganze zu einem `pace_algo_v{X.Y}.pine` zusammen
7. Validiert Pine-Budget (ops/bar, lines, request.security count)
8. Bit-Exact-Test gegen Python-Predictions (NB10-Mechanismus, pro Modell)

---

## 8. Migration V1 → V2

**V1-Pine-Code-Skelett ist bereits V2-bereit, ABER:**
- `crypto_model_predict()` / `indices_model_predict()` / `commodity_model_predict()` returnen `na`
- Cutoffs sind 0.0 (unreachable threshold)
- UI zeigt "Coming Soon"-Badge auf Non-FX

**V1 → V2 Migration ist dann:**
1. Crypto-Modell trainieren (NB13c oder dediziertes NB)
2. Modell-File in `core/models/crypto/` ablegen
3. `core/export/pine_codegen.py` re-run → neues Pine-File
4. Pine-File enthält jetzt echte `crypto_model_predict()` Implementation + echte Cutoffs
5. UI-Badge wechselt automatisch von "Coming Soon" zu "Live"
6. Bit-Exact-Test bestanden → V2-Release

**Kein Pine-Code-Refactor nötig.** Das ist der Punkt der Router-Skelett-V1.

---

## 9. Open Risks (für Tracking)

| Risiko | Impact | Mitigation | Status |
|---|---|---|---|
| Pine-Budget bei 4 Modellen knapp | hoch | Lazy Evaluation + per-model Tree-Reduction | offen |
| `syminfo.type` reicht nicht für CFDs | mittel | Tertiary Override + Symbol-Pattern-Matching | dokumentiert |
| HTF `request.security` Limit (max 40) | niedrig (V1: 2, V2: 8) | Shared HTF-Layer | okay bis V2 |
| Modell-Drift in 4 Modellen parallel | mittel | V1.5-Backend Continuous Retraining | V1.5-Scope |
| User-Verwirrung "warum kein Signal auf Crypto?" | hoch UX | klare "Coming Soon"-Badge + Doku | V1-UI-Item |
| Bit-Exact-Test komplexer mit 4 Modellen | mittel | Pro Modell separat NB10-style validieren | V2-Build-Item |

---

## 10. V1-Implementation Checkliste (für später)

Wenn V1-Pine gebaut wird (NB09/NB17, Phase E), MUSS folgendes vorhanden sein:

- [ ] Asset Detector (`detect_asset_class()`) — auch wenn nur `fx`-Branch aktiv ist
- [ ] User-Override-Input für `asset_class`
- [ ] Shared Feature-Engineering-Layer (27 Features)
- [ ] FX-Modell embedded (30 trees)
- [ ] Crypto/Indices/Commodity-Stubs (return `na`)
- [ ] Tier Engine mit Per-Modell-Cutoffs (Stubs für inaktive Klassen)
- [ ] UI mit "Coming Soon"-Badge auf Non-FX
- [ ] Backtest-Dashboard (shared)
- [ ] User-Profile-Selector (Conservative/Balanced/Aggressive)

**Wenn auch nur EINE dieser Komponenten fehlt → V1 ist nicht V2-bereit → Refactor-Hölle droht.**
