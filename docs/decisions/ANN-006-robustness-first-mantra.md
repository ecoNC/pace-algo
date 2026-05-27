# ANN-006: Robustheits-First-Mantra (Strategy Lock)

**Status:** Active
**Datum:** 2026-05-27
**Locked-By:** Nico-Decision, override für jede zukünftige Locked-Rule-Diskussion
**Related:** [[ANN-005]] (V1-vs-V1.5-Scope) [[ANN-003]] (Gold-Pattern)

---

## 1. Hypothese

Bei jedem ML-Forschungsprojekt entsteht der Drang, eine einzelne beeindruckende Zahl zu produzieren ("FX PF 2.015"). Diese Zahl wird zum Self-Goal — was zu **Curve-Fitting, Single-Market-Optimierung und ehrlosen Marketing-Versprechen** führt.

Hypothese: Wenn wir das Produkt-Ziel **explizit** auf Robustheit/Generalisierung/Konsistenz statt auf "höchste Zahl" verschieben, treffen wir bessere Architektur-Entscheidungen UND vermeiden den klassischen Quant-Self-Sabotage.

## 2. Experiment

**Quelle:** Aggregierte Lessons aus NB05–NB12 (6 Monate Forschung) + strategischer Reset durch Nico am 2026-05-27.

**Was wir beobachtet haben:**

1. **NB11 produzierte FX-only PF 2.015** — beeindruckende Zahl. Aber: nur 2 Symbole im Training, Gold (XAUUSD) bricht (PF 1.03), Crypto-Performance unbekannt. Wenn V1 nur "EURUSD-Optimizer" wäre, hätten wir nichts.

2. **NB12 zeigte XGBoost +0.135 PF auf GBPUSD-Hold-Out.** Verlockend, einen Modellwechsel daraus zu machen. ABER: 1 Symbol, Stability-CV schwächer. Phase B muss zeigen, ob das systemisch ist. → Disziplin gewinnt vor "neuer Top-PF" zu jagen.

3. **NB12 Consensus-Filter PF 2.93 auf GBPUSD-Hold-Out.** Massive Zahl. Versuchung: Pine V1 mit Consensus überladen. **Aber:** CatBoost passt nicht in Pine, also würde es V1 zu Backend-Hybrid degradieren. Disziplin: Consensus → V1.5, V1 bleibt LightGBM-Only.

4. **Bestätigung durch Phase 1:** Reduktion 37 Features → 27 Features brachte +0.875 PF. "Weniger ist mehr" — wir wollten 37 weil Plausibilität, brauchten aber 27. Disziplin hat hier Edge produziert.

## 3. Resultat

Wir formulieren das Robustheits-First-Mantra als **4 Lock-Sätze**, die jede zukünftige Architektur-Entscheidung dominieren — auch wenn sie eine niedrigere Spitzen-Zahl bedeuten:

### Lock 1: Generalisierung > Maximierung eines einzelnen PF-Werts

Eine Edge auf 8 Asset-Klassen mit Mean-PF 1.6 schlägt eine Edge auf 1 Asset mit PF 2.5.

**Operationalisierung:**
- Phase D (NB15) Entscheidungs-Matrix priorisiert Min-PF-pro-Asset-Klasse über Mean-PF
- Bei Tradeoff "+0.1 PF auf EURUSD vs -0.05 PF auf Crypto" wird **Crypto-Stabilität** gewichtet

### Lock 2: Robustheit > Benchmark-Chasing

Eine Architektur die in 3 Marktregimen (Trend, Range, Crisis) stabil läuft, schlägt eine die in einem einzelnen Regime brilliert.

**Operationalisierung:**
- Stability-CV ist gleichwertiges Decision-Kriterium wie Mean-PF
- Per-Year-PF darf in keinem Jahr unter 1.3 fallen (HANDOFF 12.4 Target)
- Wenn ein neues Feature/Modell in einem Hold-Out-Symbol bricht (PF < 1.0), wird es zurückgestellt — selbst wenn der Mean steigt

### Lock 3: Konsistenz > Cherry-Picking

Wir kommunizieren NIE selektive Ergebnisse. Was wir behaupten, muss reproducibel auf dem User-Chart sichtbar sein.

**Operationalisierung:**
- Marketing-Zahlen MÜSSEN das schlechteste Hold-Out-Asset-Klassen-PF reflektieren, nicht das beste
- KEIN "best year"-Marketing, immer mean-of-years
- KEIN "best symbol"-Marketing, immer mean-of-symbols
- Backtest-Display auf dem Chart IST die einzige Source-of-Truth

### Lock 4: Gute UX + ehrliches Backtesting > Marketing-Zahlen

Ein User der auf seinem Chart PF 1.6 sieht und das matched mit unserem Marketing, ist langfristig wertvoller als einer den wir mit "PF 2.5!"-Behauptungen geködert haben.

**Operationalisierung:**
- Backtest-Widget zeigt RAW Zahlen, kein Marketing-Filter
- "Premium Tier" Schwelle ist transparent als VAL-Percentile dokumentiert
- 3 Profile (Conservative/Balanced/Aggressive) statt freier Slider — User kann sich nicht selbst-optimieren
- Marketing-Hooks (z.B. "WR 66% mit V1.5-Backend") sind quantitativ aus konkreten Hold-Out-Tests belegt, nicht aus In-Sample

## 4. Decision

**Diese 4 Lock-Sätze sind ab 2026-05-27 die obersten Strategy-Locks im Projekt.**

Sie überschreiben jede zukünftige Locked Rule, die mit ihnen in Konflikt steht. Konkret:
- Wenn HANDOFF Section 12 jemals mit diesen 4 Sätzen kollidiert, sind diese 4 Sätze stärker
- Wenn ein zukünftiges Notebook eine optimierende-Single-Asset-Logik einführt, kollidiert sie mit Lock 1 und wird abgelehnt
- Wenn Marketing einen Hook formulieren will der "Best Case" framed, kollidiert mit Lock 3 und wird abgelehnt

**Konkrete Ablehnungen (für künftige Sessions):**

- ❌ Hyperparameter-Tuning das einen Asset-PF hochzieht ohne Cross-Asset-Test
- ❌ Feature-Selection das auf in-sample TEST optimiert ohne Hold-Out-Validation
- ❌ Marketing-Behauptung "WR 85%" wenn Premium-Tier-WR in Hold-Out ~60% ist
- ❌ Per-Symbol-Schalter im UI ("EURUSD-Profile") die User-Curve-Fitting ermöglichen

## 5. Konsequenz

**Daten-getriebene Forschungs-Reorientierung:**

Das NB11-Ergebnis (FX-only PF 2.015) wird **explizit als Research-Baseline, NICHT als Produktziel** redefiniert.

```diff
- Produktziel: maximaler PF auf FX
+ Produktziel: robusteste universelle Architektur

- Erfolgs-Kriterium: PF > 2.0 auf in-sample
+ Erfolgs-Kriterium: Min PF > 1.3 auf JEDER Asset-Klasse + Stability CV < 0.25 + ehrliche User-Reproduktion
```

**Code-Änderungen:**
- Locked Rules in HANDOFF.md Section 12 werden Lock 1-4 als oberste Hierarchie-Ebene ergänzt
- README.md führt das Mantra prominent

**Forschungs-Änderungen:**
- Phase B (NB13), C (NB14), D (NB15) werden alle gegen diese 4 Locks getestet
- NB15 Architektur-Decision-Matrix priorisiert Min-PF + Stability-CV als #1 und #2 Kriterium

**Marketing-Änderungen (für späteres Launch):**
- Marketing-Copy für V1 wird gegen Lock 3+4 reviewed
- "Honest backtest display" wird nicht nur Tech-Feature, sondern Marketing-Hauptbotschaft
- Pricing-Tier-Story: V1 = solide universale Edge, V1.5 = echte Consensus-Validation-Power, V2 = vollständige Cloud-Plattform — kein künstliches Tier-Spaltung

**Lesson (warum dieses Mantra wichtig ist):**

ML-Quant-Projekte sterben fast immer an einem von zwei Fehlern:
1. Sie optimieren auf In-Sample-Zahlen und produzieren ein Modell das in Production bricht
2. Sie launchen mit Marketing-Versprechen die der Backtest nicht hält und verlieren User-Vertrauen

Diese 4 Locks schützen vor beiden. Sie kosten uns potenziell eine "höhere Spitzen-Zahl", aber das ist genau der Trade den wir nehmen.
