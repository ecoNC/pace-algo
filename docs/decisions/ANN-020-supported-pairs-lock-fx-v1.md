# ANN-020 — Supported-Pairs Lock (FX V1) + Production-Recipe + LOPO als stehender Robustheits-Test

- **Status:** Active
- **Datum:** 2026-06-01 (UTC)
- **Locked-By:** HANDOFF Section 12.1 (Research Rules), ANN-006 (Robustheits-First-Mantra), ANN-009 (Multi-Model-Router)
- **Related:** baut auf [ANN-019](ANN-019-validated-100-tree-ensemble-complexity-retired.md) (validierter 100-Tree-Core); konkretisiert [ANN-016](ANN-016-fx-as-reference-blueprint-industrialization-first.md) (FX als erstes vertikales Produkt); Pair-Level-Evidenz für [ANN-009](ANN-009-multi-model-router-architecture.md)

---

## 1. Hypothese

Generalisiert der FX-Edge **universell** über alle Majors, oder ist er pair-spezifisch? Bisher wurde implizit „universell FX" angenommen (alle Majors gleich behandelt). Gegenhypothese (nach AUDUSD-Concept-Shift-Befund): der Edge ist **ungleich über Paare verteilt** und korreliert invers mit Markt-Effizienz.

## 2. Experiment

`scripts/supported_pairs.py` — LGBM-100 (seed 7, no early_stopping, ANN-019-Core), alle 7 FX-Majors, identische Features/Splits/Labels, **zwei Protokolle:**

- **IN-POOL (time-OOS):** Modell auf allen 7 Paaren trainiert (= Produktions-Rezept), jedes Paar auf seinem eigenen Test-Zeitraum (≥ 2025-07-01) bewertet.
- **LOPO (true OOS):** pro Paar Training auf den anderen 6, Bewertung auf dem ausgelassenen Paar → Cross-Pair-Generalisierung.

Klassifikations-Kriterium (auf IN-POOL): `supported` = monotone Tier-Separation ∧ PF@q97 ≥ 1.30 ∧ PF@q99 ≥ 1.50; `conditional` = Edge nur @ q99 (≥1.50) oder PF@q97 ∈ [1.10, 1.30); sonst `unsupported`.

## 3. Resultat

Pfad: `results/model_validation/supported_<UTC>/supported_pairs.json`

**IN-POOL (PF @ q90 / q97 / q99):**

| Paar | q90 | q97 | q99 | Klasse | LOPO-q99 |
|---|---|---|---|---|---|
| GBPUSD | 1.28 | 1.60 | 2.19 | **supported** | 2.00 (generalisiert) |
| USDCAD | 1.19 | 1.58 | 2.57 | **supported** | 3.08 (generalisiert) |
| NZDUSD | 1.16 | 1.50 | 1.89 | **supported** | 2.68 (generalisiert) |
| USDJPY | 1.15 | 1.31 | 1.74 | **supported** | 1.64 (generalisiert) |
| USDCHF | 1.11 | 1.36 | 1.75 | **supported** | 1.50 (grenzwertig) |
| AUDUSD | 1.01 | 0.98 | 1.65 | **conditional** (nur q99) | 1.33 (in-pool-abhängig) |
| EURUSD | 0.95 | 0.83 | 1.12 | **unsupported** | 1.04 (kein Edge) |

- **EURUSD trägt keinen verlässlichen Edge** (q97 0.83, q99 1.12 in-pool; LOPO q99 1.04). Ökonomisch konsistent: liquidestes/am stärksten arbitragiertes Major → geringster struktureller Edge. Ein ehrliches Signal-System darf das nicht überdecken.
- **AUDUSD ist conditional** — in-pool nur am Conservative-Tier (q99 PF 1.65) tragfähig, OOS schwach (Concept-Shift, siehe AUDUSD-Investigation 2026-06-01).
- **5 Paare sind sauber supported**, monoton, mit OOS-Generalisierung. Der Edge konzentriert sich in den **weniger effizienten Paaren** (CAD/NZD/GBP/JPY/CHF).

## 4. Decision

1. **Supported (alle Tiers exponiert):** USDJPY, NZDUSD, GBPUSD, USDCHF, USDCAD.
2. **Conditional (nur Conservative/q99 exponiert, als „experimental" gelabelt):** AUDUSD.
3. **Unsupported (KEINE Signale exponiert):** EURUSD.
4. **Produktions-Rezept:** Das Shipping-Modell wird auf den **supported + conditional Paaren in-pool** trainiert (jedes Paar in-distribution), Walk-Forward-Time-Split. EURUSD wird NICHT als Signal-Paar exponiert; ob EURUSD-Daten im Training den anderen Paaren helfen oder schaden ist ein offener Follow-up-Test (Default: ausgeschlossen, um No-Edge-Rauschen zu vermeiden).
5. **LOPO ist ab jetzt stehender Robustheits-Gate:** Bevor ein neues Paar „supported" wird, muss es sowohl in-pool als auch LOPO PF@q97 ≥ 1.0 zeigen.

## 5. Konsequenz

- **Produkt/Marketing:** V1 führt NICHT mit EURUSD. Supported-Liste ist gelockt; AUDUSD nur Conservative/experimental.
- **Training:** `core/config.py` Supported-Set spiegeln; Produktionsmodell auf supported+conditional trainieren.
- **Architektur:** verstärkt die Multi-Model-These (ANN-009) auf Pair-Ebene — schon innerhalb FX existiert Concept-Shift. Langfristig: Shared Infrastructure / Feature-Engine / Validation-Layer + spezialisierte Modelle pro Asset-Klasse und teils pro Pair.
- **Standing test:** LOPO + In-Pool als Pflicht-Doppelprotokoll für jede künftige Pair-/Asset-Aufnahme.
- **Lessons:** „Universell über alle Majors" war eine unbelegte Annahme. Ehrliche per-Pair-Validierung > erzwungene Universalität.
