# ANN-016: FX as Reference Blueprint — Industrialization-First Strategy

**Status:** Active — **STRATEGISCHER LOCK** (Core-Architecture-Direction)
**Datum:** 2026-05-28
**Locked-By:** Nico-Direktive nach NB14f-v2 USDCHF-Strukturbruch
**Related:** [[ANN-005]] (V1-Scope, scope-clarified) · [[ANN-006]] (Robustheits-Mantra) · [[ANN-009]] (Multi-Model-Router) · [[ANN-014]] (Per-Model Behavioral Stability) · [[ANN-015]] (Training-Pool-Expansion)

---

## 1. Hypothese

Vor ANN-016 wurde implizit angenommen, dass V1 als FX-only-Release mit Crypto/Indices/Commodity als "Coming Soon"-Stubs reicht (ANN-005). NB14f-v2 hat einen klaren Strukturbefund geliefert: USDCHF reagiert fundamental anders auf den Universal-Filter-Stack (Aggressive PF 0.97 → Balanced 0.63 → Conservative 0.17 — invertierte Edge-Staffelung). Drei verschiedene Interpretationen waren möglich:

- **A** USDCHF ist Bug → wegoptimieren oder Pair-Tier "unsupported" markieren und V1 launchen
- **B** USDCHF ist Datenartefakt → mehr Pool-Expansion versuchen
- **C** USDCHF ist Architektur-Signal → echte Marktstruktur (CHF reagiert auf SNB / EU statt NY) wird vom Modell erkannt; Universal-Filter-Stack ist überangepasst auf USD-Asia-Pacific-Pairs

**Hypothese:** Interpretation **C** ist richtig. Universal-Filter-Logik ohne Per-Pair-Sensitivität skaliert nicht zu Crypto/Indices/Commodity (jede Asset-Klasse hat eigene Marktstruktur). Damit ist es ein **Architektur-Signal**, kein Bug.

Konsequenz-Hypothese: Wenn wir das FX-Modell **nicht vollständig industrialisieren** (Failure-Cases verstehen, Per-Pair-Override-Diskussion führen, Pine-bit-exact validieren, Router-Integration testen), sondern parallel anfangen Crypto/Indices zu bauen, entsteht ein **FX-Sonderprojekt statt einer Plattform** — und wir refactoren später jede Asset-Klasse einzeln.

## 2. Experiment

Kein klassisches Experiment — strategische Architektur-Entscheidung basierend auf:

**Evidenz aus NB13–NB14f (Phase B + C + C.5 + C.6):**
- NB13: FX-Edge generalisiert auf 5+ FX-Symbole (Premium-PF 2.5+ Hold-Out)
- NB14: 5m TF gelocked, andere TFs strukturell unterschiedlich
- NB14b: Probability-Cutoff-Tier-Konzept widerlegt
- NB14d: Ultra-discrete Distribution diagnostiziert
- NB14e/f: Per-Model Relative Cluster + Behavioral Stability funktioniert technisch
- **NB14f-v2:** USDCHF Filter-Stack-Inversion entdeckt (Conservative 0.17 < Aggressive 0.97) bei sauberem 3/4-Pair-Verhalten (GBPUSD/AUDUSD/USDCAD monoton steigend)

**Logische Konsequenz:**
- Universal-Filter-Stack scheitert reproduzierbar auf einem strukturell unterschiedlichen Pair
- Per-Asset/Pair/Regime-Modellierung wird in V2/V3 ohnehin nötig sein (ANN-009-Pivot)
- Wenn wir FX nicht jetzt komplett verstehen, replizieren wir das Verständnis-Defizit auf jeder weiteren Asset-Klasse

## 3. Resultat

**Strategischer Reframe — FX wird Reference Blueprint, nicht Shortcut-V1:**

Das FX-Modell wird zur **Referenz-Architektur** für das gesamte Multi-Model-System. Alles was wir in FX-Industrialisierung bauen — Pipelines, Quality-Gates, Validation-Tests, Doku-Patterns, Pine-Code-Strukturen, User-Layer-Constraints — muss als **wiederverwendbarer Blueprint** designed sein.

**Späteres Crypto/Indices/Commodity-Modell durchläuft denselben Blueprint** statt eigene Pipelines zu bekommen. Damit:

- Maintenance-Burden bleibt konstant (1 Blueprint statt N Pipelines)
- Quality-Niveau wird über Asset-Klassen vergleichbar
- Failure-Cases aus FX werden zu Test-Templates für alle anderen Klassen
- USDCHF-artige Strukturbefunde werden in V2 schneller erkannt

## 4. Decision

### Lock 1 — FX-Industrialization-First

FX-Modell wird vollständig industrialisiert (Phase D, siehe Sektion 5.2) **bevor** V2-Asset-Klassen-Modelle gestartet werden. Kein paralleler Crypto/Indices/Commodity-Bau während Phase D läuft.

### Lock 2 — Replicable-Blueprint-Design

Alles was in Phase D gebaut wird, muss als **Blueprint** designed sein:
- Pipelines (NB-Notebook-Strukturen) müssen Asset-Klasse-parametrisierbar sein
- Quality-Gates (Quality-Anchor, Behavioral-Stability, Pair-Tiering) werden klassen-agnostisch formuliert
- Pine-Code-Strukturen (Router-Branch-Templates, Filter-Stack-Patterns) müssen für 4 Asset-Klassen extensible bleiben
- Doku-Patterns (ADR-Format, research/*-Sektionen, results/-Subfolders) bekommen Templates

### Lock 3 — V1-Launch-Definition (verschärft)

**V1-Launch erfolgt erst wenn:**
1. FX Phase D vollständig abgeschlossen (D.1–D.8 alle locked) UND
2. Mindestens **2 Asset-Klassen produktionsreif** über denselben Industrialization-Blueprint UND
3. Pine-Router-Code echten Multi-Model-Switch operiert (kein Stub mit "Coming Soon"-only)

**Bedeutet:** Kein FX-only-V1-Release. ANN-005's "V1 = FX-only + Stubs"-Annahme wird durch ANN-016 **scope-verschärft, nicht überstellt** — ANN-005's Scope-Trennung V1/V1.5 bleibt aber V1-Definition wird strenger interpretiert.

### Lock 4 — Core Engine vs User Layer Trennung

Diese Architektur-Schichtung wird gelocked:

| Layer | Verantwortung | Eigenschaften |
|---|---|---|
| **Core Engine** | Edge-Generation pro Asset/Pair/Regime | strikt non-repainting · Pine-bit-exact · spezialisierte Modelle · robuste Default-Configs · universelle UX via Router · keine User-Eingriffe |
| **User Layer** | Personalisierung + Backtest-Display | Settings nur in statistisch validierten Grenzen · keine freien Curve-Fit-Parameter · ein-Indikator-Experience |

Diese Trennung gilt in **jeder zukünftigen Code-Decision** — Pine-Code-Struktur, Backend-Migration (V2/V3), API-Design.

### Lock 5 — Override-Discipline (Anti-Curve-Fit-Lock auf Architektur-Ebene)

Per-Pair / Per-Asset / Per-Regime / Per-TF-Overrides sind **erlaubt** — aber jeder Override muss vier Kriterien erfüllen **bevor** er in den Code wandert:

1. **Klarer statistischer Nachweis** — Signifikante Performance-Verbesserung gegenüber Universal-Default (mind. p < 0.05 oder Effect-Size ≥ vereinbarter Threshold)
2. **Dokumentierte Marktstruktur-Begründung** — Warum hat dieses Pair/Asset/Regime andere Dynamik (Liquiditäts-Quellen, Session-Effekte, Korrelations-Struktur, etc.)
3. **OOS-Lift** — Mindestens +0.05 PF auf Hold-Out-Symbolen oder unseen Time-Period
4. **Reproduzierbares Verhalten** — Stabil über mind. 3 Seeds UND verschiedene Time-Periods

**Verboten:** Manuelle Curve-Fit-Hacks "weil USDCHF besser performt mit Filter X". Wenn der Override diese 4 Kriterien nicht erfüllt → Override wird nicht eingebaut, Pair bleibt unsupported.

### Lock 6 — Anti-FX-Sonderprojekt

Wir verwenden keine FX-spezifischen Strukturen die später für Crypto/Indices/Commodity nicht übertragbar sind. Jede in Phase D entstehende Lösung muss durch eine **Blueprint-Doku** dokumentiert werden, die erklärt:

- Was ist FX-spezifisch (Daten, Sessions, etc.)?
- Was ist klassen-agnostisch (Pipeline, Validation, UX)?
- Wie wird das Pattern in V2 für andere Klassen instanziiert?

Wenn eine Lösung das nicht erfüllen kann → re-design.

## 5. Konsequenz

### 5.1 Reihenfolge-Lock (Phase D Sub-Phases)

Architektur-First (D.1–D.3) **bevor** Technical (D.4–D.8) — weil technische Decisions auf den Architektur-Erkenntnissen aufbauen müssen, nicht umgekehrt.

```
Phase D — FX als Reference Blueprint (Industrialization-First)
│
├── D.1  USDCHF Deep-Dive  ────────────────────► NB15a
│         Ziel: Verstehen ob Session-Problem / Regime-Problem / 
│               Liquidity-Problem / Filter-Interaction-Problem.
│         Output: Per-Session SHAP, Filter-Impact-Decomposition,
│                 vermutete CHF-spezifische Marktstruktur belegt.
│
├── D.2  Universal-vs-Per-Pair-Decision ───────► ANN-017 (nach D.1)
│         Harte Architekturfrage basierend auf D.1-Daten:
│         a) bleibt Filter-Stack universal?
│         b) braucht FX später Pair-Level-Overrides?
│         c) oder adaptive Session-Profile?
│         Output: Architektur-Lock, eventuell Code-Skelett für Overrides.
│
├── D.3  Pair-/Session-Behavior Map ───────────► NB15b
│         Wann funktioniert das Modell strukturell gut/schlecht?
│         Per-Pair × Per-Session × Per-Volatility-Regime Matrix.
│         Output: Operational-Boundary-Karte, Marketing-Story-Material.
│
├── D.4  Failure-Case Documentation ───────────► research/failure_cases.md
│         Was bricht das Modell? Vol-Regime-Shifts, News-Events,
│         Session-Mismatches, illiquide Phasen, Holiday-Gaps.
│         Output: Failure-Templates die in V2 für andere Klassen 
│                 als Test-Sets dienen.
│
├── D.5  Pine bit-exact Validation ────────────► NB15c
│         Python ↔ Pine Output-Match auf TEST-Sample.
│         Output: Bit-exact Validation Report pro Pair, Pine-Code-Snippets.
│
├── D.6  Non-repaint + Live-Bar Validation ────► NB15d  
│         Was passiert während Bar offen vs. geschlossen?
│         Output: Live-Bar-Behavior-Spec, Repaint-Test-Suite (klassen-agnostisch).
│
├── D.7  Router-Integration ───────────────────► NB15e
│         AssetClass.FX-Route operativ, Non-FX zeigt klare UI-Message.
│         Pine-Code mit funktionierendem Router-Switch.
│         Output: Pine-Code-Skelett als Blueprint für V2.
│
└── D.8  User-Layer Constraint Tests ──────────► NB15f
          User-Settings bewahren Backtest-Statistik (keine Curve-Fit).
          Whitelist-Verification, OOS-Grenzen pro User-Setting.
          Output: User-Layer-Spec, statistisch validierte Setting-Ranges.
```

### 5.2 Phase E — V2 Asset-Klassen über Blueprint

Sobald Phase D komplett abgeschlossen:

```
Phase E — V2 Multi-Asset-Klassen (via Blueprint)
├── E.1  Crypto-Modell    ◄── nutzt Blueprint aus Phase D
├── E.2  Commodity-Modell ◄── nutzt Blueprint aus Phase D
├── E.3  Indices-Modell   ◄── nutzt Blueprint aus Phase D (sobald Polygon)
└── E.4  Pine-Router-Production mit Multi-Model-Stack
```

**V1-Launch erst nach Phase E.1 + E.4 minimum** (FX + 1 weitere Asset-Klasse über Router).

### 5.3 Code-Änderungen

```
core/
├── eval/
│   ├── tf_pipeline.py              (bestehend, Router-kompatibel)
│   ├── failure_case_tests.py       NEU (D.4 — klassen-agnostische Tests)
│   ├── pine_bitexact_validator.py  NEU (D.5)
│   ├── repaint_validator.py        NEU (D.6 — Live-Bar-Tests)
│   └── override_validator.py       NEU (Lock 5 — 4-Kriterien-Check)
├── analysis/
│   ├── probability_diagnostic.py   (bestehend)
│   └── session_decomposer.py       NEU (D.1 — Per-Session SHAP/PF)
└── router/
    ├── asset_detector.py           (bestehend)
    ├── model_selector.py           (bestehend, evtl. extended um override-flag)
    └── pair_override_registry.py   NEU wenn D.2 → Per-Pair-Overrides
```

### 5.4 Doku-Änderungen (in diesem Commit-Batch)

- `docs/roadmap.md` — Phase D komplett neu (D.1–D.8 architecture-first), Phase E (V2 Multi-Asset)
- `docs/model_registry.md` — FX-Status "Industrialization in Progress (Phase D)", V2-Slots bleiben Stubs
- `docs/pine_router_design.md` — Core Engine vs User Layer Sektion (Lock 4 verankert)
- `docs/decisions/README.md` — ANN-016 in Index
- `docs/decisions/ANN-005-v1-vs-v1.5-scope-split.md` — Cross-Reference "Scope verschärft durch ANN-016, nicht überstellt"
- `HANDOFF.md` Section 16 + 19 — Pivot dokumentiert, NB15a (D.1) als nächste Action

### 5.5 Marketing-Implikation

V1-Marketing wird **nicht** "AI Trading Indicator für FX Major Pairs" sondern:

> "**Multi-Asset AI Trading System** — spezialisierte Modelle für FX + [Crypto / Indices / Commodity] mit einheitlicher Chart-Experience."

Damit ist die Marketing-Story von Anfang an die echte Produkt-Story, nicht ein FX-Tool das nachträglich "auch Crypto kann".

### 5.6 Lessons

**Was NB14f-v2 + ANN-016 lehren:**

1. **Robuste Architektur > schneller Release.** Mit Pair-Tiering + USDCHF-"unsupported"-Badge wäre V1 in wenigen Wochen launchbar gewesen. Aber das wäre ein Sonderprojekt — V2 (Crypto/Indices/Commodity) hätte die gleichen Architektur-Lücken neu entdeckt.

2. **Failure-Cases sind Forschungs-Goldminen.** USDCHF-Bruch ist keine Schwäche unseres Modells, sondern ein Hinweis dass das Modell echte Marktstruktur lernt. Wegoptimieren wäre Information-Vernichtung.

3. **Override-Discipline ist Anti-Curve-Fit auf Architektur-Ebene.** Die 4-Kriterien-Regel (statistical / structural / OOS / reproducible) muss in jeder Architektur-Entscheidung mitgedacht werden, nicht nur bei User-Settings.

4. **Universal-First ≠ Universal-Forever.** Wir bauen NICHT künstlich universell wenn Daten Per-Pair-Strukturen zeigen — aber jeder Override wird strikt diszipliniert.

5. **Plattform-Denken vor Produkt-Denken.** FX-Industrialisierung produziert nicht nur ein FX-Modell, sondern die Templates für alle V2-Asset-Klassen. Das ist der Hebel.
