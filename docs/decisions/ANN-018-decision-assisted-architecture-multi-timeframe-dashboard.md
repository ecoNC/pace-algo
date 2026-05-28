# ANN-018: Decision-Assisted Architecture + Multi-Timeframe Market Dashboard

**Status:** Active — **FINAL ARCHITECTURE LOCK** (überstellt Single-Signal-Modell-Annahmen, **KEINE weiteren Sub-ADRs**)
**Datum:** 2026-05-28
**Locked-By:** Nico-Direktive nach NB15b USDCHF-Bestätigung + Swift-Algo-Lessons
**Related:** [[ANN-009]] (Multi-Model-Router) · [[ANN-011]] (User-Settings-Whitelist) · [[ANN-016]] (FX as Blueprint) — alle bleiben aktiv, werden durch ANN-018 erweitert

---

## 🛑 EXECUTION LOCK 2026-05-28 (Nico-Course-Correct)

**ANN-018 ist die LETZTE Architektur-ADR vor V1-Build.** Keine ANN-019 / ANN-020 / ANN-021. Keine weiteren Spec-Validierungs-Notebooks als Pflichtschritt.

Das 4-Layer-Konzept aus dieser ADR bleibt inhaltlich gültig — aber wir **bauen direkt**, statt jede Schicht in separate ADRs + NBs zu splitten.

**Konkrete Umsetzung:** alle 3 Layer (Signal Engine + MTF-Dashboard + Backtest-Transparency) leben in **EINEM** Pine-File (`deploy_pine/pace_algo_v1_skeleton.pine`). Siehe [Roadmap Phase D](../roadmap.md) Build 1.

**Verbotene Aktivitäten ab jetzt (bis V1 läuft):**
- Weitere ANN-Splits
- Separate `core/market_regime/`-Python-Module für Dashboard (Dashboard läuft Pine-nativ)
- `core/eval/filter_interaction_registry.py` mit komplizierter Discipline-Pipeline
- Zusätzliche Forschungs-Notebooks NB15c/d/e/f als Pflicht-Validation
- Weitere Architektur-Decisions vor V1-Live-Test

**Begründung:** Wir verlieren uns nicht in Framework-Komplexität. FX **ist** das Produkt, nicht der Forschungs-Blueprint. Trading-Performance + User-Verständlichkeit im Live-Chart sind die KPIs, nicht Architektur-Eleganz.

---

---

## 1. Hypothese

Bisher (implizit ANN-005/009/011/016): das Produkt war als "intelligenter Signal-Generator" konzipiert — Modell → Tier → Profile → BUY/SELL-Signal an den User.

Nico-Erkenntnis nach NB15b + Swift-Algo-Reverse-Engineering:

> **Erfolgreiche TradingView-Indikatoren liefern Signal + Kontext, nicht nur Signal.**
> Ein PF-2.0-Modell ohne Marktkontext ist für den User schwerer zu vertrauen als ein PF-1.7-Modell mit klarem "Market Regime"-Dashboard.

NB15b hat gezeigt: Filter sind nicht-additiv (Interactions können destructive sein). Das ist nicht nur ein USDCHF-Problem — es ist ein universelles Modellierungs-Problem. Single-Filter-Stacks werden auf jeder neuen Asset-Klasse die gleiche Diagnose-Arbeit erfordern.

**Hypothese:** Ein modulares System aus 4 Layern (Signal Engine + Market Regime Dashboard + Interaction Layer + Backtest Transparency Layer) ist sowohl **produktqualitativ besser** (User-Vertrauen, kein blind-entry) als auch **architekturqualitativ besser** (Replicable für V2-Asset-Klassen, weniger Pair-Sensitivity-Bugs).

## 2. Experiment / Evidenz

Kein klassisches Experiment — strategische Architektur-Direktive, basiert auf:

**Datenlage:**
- **NB15b (`b8e6b76`):** USDCHF interaction_score mean -0.131 / std 0.008 — reproduzierbar destructive über 3 Seeds. Filter-Interaction ist real, nicht Seed-Artefakt.
- **NB14f-v2 (`80bad05`):** 3/4 Pairs funktionieren mit Universal-Filter, 1/4 bricht — kein "alles brennt"-Szenario, sondern Pair-spezifisches Strukturproblem.
- **NB13:** FX-Edge generalisiert, Crypto bricht — Asset-Klassen brauchen unterschiedliche Modellfamilien.
- **NB14:** Time-of-Day-Edge ist real (hour_sin Top-1 SHAP), aber TF-spezifisch — auf 1h verschwindet sie.

**Markt-Lessons (Swift-Algo-Vergleich):**
- Top-Indikatoren zeigen User **immer** Multi-Timeframe-Context (Trend/Strength/Range pro TF)
- Backtest-Display ist **eingebaut**, nicht nachträglich — User können Parameter-Sensitivity selbst sehen
- Aggregierter Market-State (Bias-Score über TFs) reduziert Overtrading mehr als jeder Probability-Threshold

**Konvergente Schlussfolgerung:** Wir haben empirische Evidenz für Interaction-aware Architektur, plus Markt-Bestätigung dass Multi-Timeframe-Context der User-Erwartung entspricht.

## 3. Resultat

**Neue Zielarchitektur — 4 Layer (modular, replicable):**

```
┌────────────────────────────────────────────────────────────────┐
│                      PaceAlgo System                           │
│                                                                │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │   CORE SIGNAL        │  │   MARKET REGIME DASHBOARD      │  │
│  │   ENGINE             │  │   (NEU per ANN-018)            │  │
│  │                      │  │                                │  │
│  │  - Modell pro        │  │   Pro TF (1m/5m/15m/1h/4h):    │  │
│  │    Asset-Klasse      │  │     • Trend (up/dn/neutral)    │  │
│  │  - Cluster-Detection │  │     • Strength (hi/med/lo)     │  │
│  │  - Tier-Mechanik     │  │     • Ranging-State            │  │
│  │  - Non-repainting    │  │                                │  │
│  │  - Pine bit-exact    │  │   Overall Market State:        │  │
│  │                      │  │     • Aggregierter Bias        │  │
│  │  Output: Probability │  │     • TF-gewichtete Bewertung  │  │
│  │          + Tier      │  │     • Context-Score            │  │
│  │                      │  │                                │  │
│  │                      │  │  Output: Market-Context-Object │  │
│  └─────────┬────────────┘  └──────────────┬─────────────────┘  │
│            │                              │                    │
│            ▼                              ▼                    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │           INTERACTION LAYER (NEU per ANN-018)          │    │
│  │                                                        │    │
│  │   Empirisch validierte Filter-Kombinationen pro        │    │
│  │   Pair/Asset/Regime (NICHT naiv linear AND).           │    │
│  │                                                        │    │
│  │   Liest:  Signal-Probability + Market-Context          │    │
│  │   Wendet: getestete Combination-Logic an               │    │
│  │   Output: Final-Trade-Decision + Confidence-Label      │    │
│  │                                                        │    │
│  │   Wichtig: NB15b-artige Multi-Seed-Validation für      │    │
│  │            jede neue Combination Pflicht (Discipline). │    │
│  └─────────────────────┬──────────────────────────────────┘    │
│                        │                                       │
│                        ▼                                       │
│  ┌────────────────────────────────────────────────────────┐    │
│  │      BACKTEST + PARAMETER TRANSPARENCY LAYER           │    │
│  │      (NEU per ANN-018 — first-class component)         │    │
│  │                                                        │    │
│  │   - "Current Settings" vs "Backtested Settings"        │    │
│  │   - Performance pro Setting (PF, WR, MDD)              │    │
│  │   - Multi-TF Ergebnisübersicht                         │    │
│  │   - Walk-Forward / Regime-Split Display                │    │
│  │                                                        │    │
│  │   Discipline: User-Settings nur in validierten Grenzen │    │
│  │   (ANN-011 Whitelist + ANN-016 Override-Discipline)    │    │
│  └─────────────────────┬──────────────────────────────────┘    │
│                        │                                       │
│                        ▼                                       │
│              ┌─────────────────────┐                           │
│              │      USER UI        │                           │
│              │                     │                           │
│              │ Sieht Signal +      │                           │
│              │ Market-Context +    │                           │
│              │ Backtest-Verhalten  │                           │
│              │ Entscheidet selbst  │                           │
│              └─────────────────────┘                           │
└────────────────────────────────────────────────────────────────┘
```

## 4. Decision

### Lock 1 — Decision-Assisted, nicht Blind-Entry-System

PaceAlgo ist **kein Black-Box-Signal-Generator**. Es liefert:
- Signal (mit Tier/Confidence)
- Market-Context (Multi-TF Dashboard)
- Backtest-Transparenz

User entscheidet anhand aller drei Informationen, wann er handelt.

**Marketing-Implikation:** "AI Trading **Assistant**", nicht "AI Trading **Signals**". Subtile aber wichtige Differenzierung.

### Lock 2 — Multi-Timeframe Market Dashboard ist PFLICHT

Phase D bekommt Multi-Timeframe Dashboard als **gleichrangigen Build-Task** zur Signal-Engine-Industrialisierung. Kein Pine-Release ohne diese Schicht.

**Pflicht-Bestandteile pro TF:**
- Trend (Up / Down / Neutral) — basiert auf EMA/Price-Position
- Strength (High / Medium / Low) — basiert auf ADX oder Trendstärke-Proxy
- Ranging-State (Yes / No / Weak / Strong) — basiert auf Bollinger-Width oder ATR-Compression

**Pflicht-Aggregat:**
- Overall Market State (bullish / bearish / neutral / mixed)
- TF-gewichtet (höhere TFs stärker, z.B. 4h=4× / 1h=2× / 15m=1× / 5m=0.5×)
- Context-Score 0–100 als numerischer Wert

### Lock 3 — Interaction-aware Filter Layer

Filter werden **nicht naiv linear kombiniert**. Jede neue Filter-Combination muss empirisch validiert werden via:

- Multi-Seed-Test (NB15b-Pattern, mind. 3 Seeds)
- Per-Pair-Test (alle Pairs in Asset-Klasse)
- Interaction-Score-Check (Δ(both vs max(single)) ≥ -0.05 für additive/neutral verdict)

Wenn ein Pair `destructive`-Verdict triggert → wird in Interaction-Registry als "exception" markiert, nicht silent in Universal-Logic gestopft.

**Code-Konsequenz:** Neue Modul `core/eval/filter_interaction_registry.py` — strukturierte Datenbank welche Filter-Combinations für welche Pair/Asset/Regime-Combos getestet sind.

### Lock 4 — Backtest + Parameter Transparency Layer als first-class

Wird **von Anfang an** mitgedesignt (nicht nachträglich). Bedeutet:

- Pine-Code-Struktur reserviert UI-Bereich für Backtest-Dashboard
- Jede Parameter-Änderung im UI triggert Live-Re-Calc von PF/WR/MDD auf visible bars
- "Current Settings" vs "Backtested Settings" Vergleichs-Anzeige
- Walk-Forward-Visualisierung als optionales Layer (Toggle)

**Discipline-Anker:** User-Settings bleiben in ANN-011-Whitelist-Grenzen. Aber Transparenz wird drastisch erhöht.

### Lock 5 — Architektur ist Interaction-aware

Generelles Architektur-Prinzip: keine isolierten Filter-Annahmen mehr. Jeder neue Filter, jeder neue Layer wird auf Cross-Layer-Interaction validiert.

Konkret für Phase D + spätere Phasen:
- Signal + MTF-Dashboard: testen ob MTF-Bias-Score den Signal-Edge bestätigt oder widerspricht
- Interaction-Layer + User-Settings: testen ob User-Profile-Wechsel die Statistik bewahren
- V2-Asset-Klassen: gleiche Validation-Pipeline für jede neue Modellfamilie

## 5. Konsequenz

### 5.1 Phase D — komplette Re-Strukturierung

```
Phase D — FX Reference Blueprint (4-Layer-Industrialization)
│
├── D.1  USDCHF Deep-Dive (NB15a/b) ✅ ABGESCHLOSSEN
│         Verdict: destructive_reproducible_single_pair
│         → Input für D.3 Interaction Layer (nicht isolierte Pair-Override)
│
├── D.2  Multi-Timeframe Market Dashboard Spec (ANN-019, NB15c) 🟡 NEXT
│         Spec: welche Trend/Strength/Range-Metriken pro TF, welche TF-Gewichte,
│               welcher Aggregat-Algorithmus (additive vs weighted vs voting)
│         Output: ANN-019 + NB15c Validation auf historischen FX-Daten
│
├── D.3  Interaction Layer Design + Implementation (ANN-020, NB15d)
│         core/eval/filter_interaction_registry.py
│         Multi-Seed/Multi-Pair Validation für Filter-Combinations
│         USDCHF-Pattern als first registry entry
│
├── D.4  Backtest + Parameter Transparency Spec (ANN-021, NB15e)
│         UI-Layout, "Current vs Backtested" Logik
│         Walk-Forward Display Design
│         Anti-Curve-Fit-Grenzen pro User-Setting
│
├── D.5  Failure-Case Documentation (bleibt aus alter Roadmap)
├── D.6  Pine bit-exact Validation (verschoben hinter D.2/D.3/D.4)
├── D.7  Non-repaint + Live-Bar (parallel zu D.6)
├── D.8  Router-Integration mit allen 4 Layern
└── D.9  User-Layer Constraint Tests (erweitert um Backtest-UI-Constraints)
```

### 5.2 V1-Launch-Definition (verschärft per ANN-018)

V1-Launch erfolgt erst wenn (ergänzend zu ANN-016 Lock 3):
- ✅ FX Phase D vollständig abgeschlossen
- ✅ Mind. 2 Asset-Klassen über Blueprint
- ✅ Pine-Router operiert echten Multi-Model-Switch
- **NEU:** Multi-Timeframe Market Dashboard funktioniert auf allen aktiven Asset-Klassen
- **NEU:** Interaction Layer hat dokumentierte Combinations pro Asset-Klasse
- **NEU:** Backtest-UI ist eingebaut und zeigt aktuelle Settings transparent

### 5.3 Code-Änderungen (kommende NBs)

```
core/
├── market_regime/                  NEU (D.2)
│   ├── __init__.py
│   ├── trend_classifier.py         per-TF Trend/Strength
│   ├── range_detector.py           Ranging-State pro TF
│   ├── mtf_aggregator.py           TF-gewichteter Aggregat-Score
│   └── context_object.py           Market-Context-Output (dataclass)
│
├── eval/
│   ├── tf_pipeline.py              (bestehend)
│   ├── filter_interaction_registry.py  NEU (D.3)
│   └── ...
│
└── analysis/
    └── (bestehend, plus diagnostic_decomposer.py)
```

```
deploy_pine/
└── (V1-Pine-Code wird 4-Layer-strukturiert):
    Layer 1: Signal-Engine (existing modell-export)
    Layer 2: MTF-Dashboard (NEU)
    Layer 3: Interaction-Logic (NEU)
    Layer 4: Backtest-UI + Settings-Panel (NEU)
```

### 5.4 ANN-Folge

Diese ADRs sind die nächsten Schritte (in Reihenfolge):

- **ANN-019:** Multi-Timeframe Market Dashboard Spec (welche Metriken, TF-Gewichte, Aggregat-Algorithmus)
- **ANN-020:** Interaction Layer Architecture (Registry-Format, Validation-Pflicht-Tests)
- **ANN-021:** Backtest UI/Logic Spec (Layout, Settings-Comparison, Walk-Forward-Display)

**Wichtig:** ANN-017 (Universal-vs-Per-Pair) entfällt als isolierte Decision — wird in ANN-020 (Interaction Layer) integriert. USDCHF-Pattern ist der erste Entry in der Filter-Interaction-Registry.

### 5.5 Strategische Implikation

PaceAlgo wird damit klar positioniert als:
- **NICHT:** "noch ein AI-Signal-Indikator"
- **DOCH:** "Decision-Assistance-System mit echter Architektur-Tiefe"

Konkurrenzdifferenzierung:
- Andere TradingView-Indikatoren = single-layer Signal-Generator
- PaceAlgo = 4-Layer-System mit Backtest-Transparenz und Multi-Asset-Skalierung

### 5.6 Lessons

1. **Modell-Edge allein ist nicht genug.** PF 2.0 ist research-würdig, aber das Produkt braucht mehr als nur Signale.

2. **Filter-Interactions sind universell.** USDCHF war nicht ein Sonderfall — es war der erste Beweis dass linear-additive Filter-Logik nicht skaliert. Jede neue Asset-Klasse wird ähnliche Findings produzieren.

3. **Multi-TF-Dashboard ist nicht ein "Nice-to-have".** Erfolgreiche Trading-Tools zeigen User immer Kontext. Wir hatten es als nachträgliches Feature geplant — falsch.

4. **Backtest-UI von Anfang an.** Wenn wir Backtest erst am Ende einbauen, müssen wir Pine-Code refactoren. Von Anfang an mitdenken = kein Refactor.

5. **Interaction-aware ist Reference-Blueprint-Eigenschaft.** Wenn FX-Blueprint diese Discipline hat, erben Crypto/Indices/Commodity das automatisch — und entdecken ihre eigenen USDCHF-Pattern in der Validierungs-Pipeline.
