# ANN-021 — Probability Calibration (Isotonic), entkoppelt von Tier-Selektion

- **Status:** Active
- **Datum:** 2026-06-01 (UTC)
- **Locked-By:** HANDOFF Section 12.1 (Research Rules)
- **Related:** baut auf [ANN-019](ANN-019-validated-100-tree-ensemble-complexity-retired.md) (validierter Core) + [ANN-020](ANN-020-supported-pairs-lock-fx-v1.md) (Produktions-Rezept); relevant für künftige V1.5 Risk-/Sizing-Logik ([ANN-005](ANN-005-v1-vs-v1.5-scope-split.md))

---

## 1. Hypothese

Sind die rohen LGBM-Probabilities als echte Wahrscheinlichkeiten vertrauenswürdig — und ist Kalibrierung nötig für (a) Tier-Definition und (b) spätere Risk-/Sizing-Logik?

## 2. Experiment

`scripts/calibration_analysis.py` — LGBM-100 (seed 7) auf FX_PRODUCTION_TRAIN_PAIRS (ANN-020-Rezept). Kalibratoren auf VAL gefittet, auf TEST evaluiert: raw vs Platt (sigmoid) vs Isotonic. Plus per-Pair-ECE und Monotonie-Check (bleibt die Top-q97-Tier-Zugehörigkeit erhalten?).

## 3. Resultat

Pfad: `results/model_validation/calibration_2026-06-01T09-05-02Z/calibration.json`

- **ECE (Test):** raw **0.105** → Platt 0.0083 → **Isotonic 0.0077** (≈13× besser).
- **Raw ist systematisch über-konfident** (~+0.10): z.B. pred 0.519 → actual 0.414, pred 0.480 → actual 0.374. Konsistent für `is_unbalance`-Boosting.
- **Monotonie-Overlap Top-q97 raw vs isotonic = 1.000** → Tier-Zugehörigkeit identisch. WR/PF pro Tier unverändert.
- **Per supported Pair** (raw→iso ECE): USDJPY 0.107→0.013, NZDUSD 0.089→0.011, GBPUSD 0.109→0.017, USDCHF 0.103→0.005, USDCAD 0.120→0.022 — durchgehend exzellent.

## 4. Decision

1. **Tier-Selektion bleibt VAL-Quantil (q90/q97/q99) auf der rohen Probability.** Kalibrierung ist monoton → ändert die Tier-Zugehörigkeit nicht. „Calibration" ≠ „Tier-Definition".
2. **Isotonic-on-VAL ist die kanonische *kalibrierte* Probability** für Interpretation + künftige Risk-/Sizing-Logik. Platt ist nah dran, Isotonic minimal besser und nicht-parametrisch.
3. **Für V1 (Tier-Signale + Pine) ist KEINE Kalibrierung nötig** — die rohen Quantil-Cutoffs genügen. Kalibrierung wird erst relevant, wenn ein numerischer Wahrscheinlichkeits-Wert / Position-Sizing exponiert wird (V1.5).

## 5. Konsequenz

- **V1:** unverändert. Pine/Tier-Logik braucht keinen Kalibrator (spart Pine-Komplexität — würde sonst eine isotone Stufenfunktion in Pine erfordern).
- **V1.5+ Risk/Sizing:** nutzt den Isotonic-Kalibrator (auf VAL gefittet, mit dem Modell versioniert) als interpretierbare Wahrscheinlichkeit (Kelly/Sizing/Portfolio-Gewichtung).
- **Wissenschaftlich:** das Signal-System liefert jetzt nicht nur Ranking (Tiers), sondern bei Bedarf auch kalibrierte Wahrscheinlichkeiten — ein weiterer Schritt vom „Indikator" zum quantitativen Marktstruktur-System.
- **Lessons:** Über-Konfidenz von Boosted-Trees ist erwartbar; sie ist für Ranking/Tiers irrelevant, für absolute Wahrscheinlichkeiten aber kritisch — daher Kalibrierung gezielt dort einsetzen, wo der absolute Wert zählt.
