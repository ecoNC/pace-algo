# ANN-003: Gold/XAUUSD aus FX-Trainings-Pool entfernt

**Status:** Active (Re-Test in Phase B)
**Datum:** 2026-05-26
**Locked-By:** HANDOFF Section 12.1.4 ("No single-asset optimization") — aber mit Klausel zu Asset-Selection
**Related:** [[ANN-001]] [[ANN-005]]

---

## 1. Hypothese

Gold (XAUUSD) hat ähnliche Eigenschaften wie FX (24h Quotes, ähnliche Vola-Regimes, USD-quote, Dukascopy-Datenquelle) — daher sollte ein gemeinsames FX+Gold-Modell mindestens so gut sein wie ein FX-only-Modell, vielleicht sogar besser durch mehr Trainings-Daten.

## 2. Experiment

**Notebook:** NB11 (Phase 1 Evaluation)

**Daten:**
- Pool 1: FX-only (EURUSD, USDJPY), Walk-Forward
- Pool 2: FX + Gold (EURUSD, USDJPY, XAUUSD)
- Pool 3: Gold-only (XAUUSD)

**Modell:** LightGBM identische Hyperparameter über alle Pools
**Splits:** Walk-Forward, identisch

## 3. Resultat

| Pool | Premium PF (in-sample TEST) |
|---|---|
| FX-only | **2.015** |
| FX + Gold (combined) | ~1.85 (gemessen, vor Reduktion) |
| Gold-only | **1.03** (random) |

**Beobachtung:**
- Gold-only PF = 1.03 → effectively random, kein eigener Edge
- FX+Gold combined < FX-only → Gold zieht den Combined-Pool nach unten
- Gold scheint andere Mikrostruktur zu haben als FX (Commodity vs Currency)

Quelle: NB11 internal evaluation (results in HANDOFF.md Section 14).

## 4. Decision

**XAUUSD wird aus dem V1-Trainings-Pool entfernt. Lock vorläufig.**

**Re-Test-Bedingungen:**
- Phase B (NB13) Cross-Asset-Generalization: Gold wird als "Commodity-Cluster"-Hold-Out getestet
- Falls ein zukünftiges multi-cluster Modell (Variante C in NB15) per-asset-class Cutoffs hat, kann Gold als eigener Cluster (Commodity) wieder rein
- Falls V2-Backend ein Commodity-spezifisches Modell rechtfertigt (eigene Pipeline, eigene Hyperparameter), neu evaluieren

## 5. Konsequenz

**Code:**
- `METAL_SYMBOLS` Konstante in `core/config.py` bleibt definiert (XAUUSD enthält), aber nicht im FX-Pool
- NB11+ Code filtert Gold raus
- `data_cache/raw/` enthält weiterhin XAUUSD-OHLCV (für Cross-Asset-Tests)

**Tests:**
- Gold-only Re-Test in NB13 als Hold-Out-Symbol bestätigt oder widerlegt die "no edge"-Beobachtung

**Strategisch:**
- Asset-Selection ist ein Feature, kein neutraler Schritt
- "Mehr Daten = besseres Modell" ist falsch wenn die zusätzlichen Daten anderes Regime haben
- Phase B (NB13) wird zeigen ob das Pattern (FX generalisiert auf manche, nicht alle) ein systemischer Trend ist

**Produkt-Implikation:**
- V1-Indikator wird auf Gold-Charts SIGNAL geben können (Pine-Code läuft überall), aber die Signal-Qualität ist nicht validiert. Wir kommunizieren das offen im V1-Marketing oder gaten Gold-Charts.
- Alternative: V1.5/V2 trainiert per-asset-class und liefert dann auch auf Gold echte Edge.

**Lesson:**
- Niemals annehmen "ähnliche Daten = ähnlicher Edge". Empirisch testen.
- Ein Gold-PF von 1.03 mit unserem FX-Modell heißt nicht dass "ML auf Gold nicht funktioniert" — es heißt dass DIESES Modell mit DIESEN Features auf Gold nicht funktioniert. Gold könnte mit Commodity-spezifischen Features (z.B. Sessions: Asia-Premarket-Gold-Spike) Edge haben.
