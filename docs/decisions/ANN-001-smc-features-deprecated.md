# ANN-001: SMC-Features verworfen unter Pine-Budget

**Status:** Active
**Datum:** 2026-05-26
**Locked-By:** HANDOFF Section 12.1.2 ("No feature without measurable OOS lift")
**Related:** [[ANN-002]]

---

## 1. Hypothese

SMC-Features (Smart Money Concepts) — konkret: FVG (Fair Value Gaps), BOS (Break of Structure), CHoCH (Change of Character), Order Blocks, Liquidity Pools — sollten messbaren OOS-Edge liefern. Begründung:

- Hohe Popularität in der Retail-Trading-Community
- Theoretische Plausibilität (institutionelles Verhalten manifestiert sich in Markt-Mikrostruktur)
- Visuelle Evidenz auf Charts wirkt überzeugend

## 2. Experiment

**Notebook:** NB11 (Phase 1 Evaluation)

**Daten:** FX + Gold, 5M/15M/30M/1H, 6.3 Jahre OHLCV
**Splits:** Walk-Forward, identical mit Baseline-Test
**Modell:** LightGBM, 30 trees, depth 3 (Pine-Budget)
**Hyperparameter:** Konstant über Baseline und Ablation

**Setup:**
- Baseline: 37-Feature-Set MIT SMC-Features
- Ablation: gleicher Set OHNE SMC-Features (~10 Features entfernt)

**Threshold:** Ablation gilt als "feature relevant" wenn Premium-PF-Drop ≥ +0.05 nach Entfernung. Umgekehrt: wenn Entfernen die PF VERBESSERT, gilt das Feature als noise.

## 3. Resultat

| Setup | Premium PF | SHAP-Top-Rank für SMC |
|---|---|---|
| Mit SMC (37 Features) | 1.56 | 17–21 Features SHAP-dead |
| Ohne SMC (~27 Features) | **1.80** | — |

**Lift durch ENTFERNEN: +0.24 PF.**

SHAP-Analyse vor Ablation hatte schon gezeigt: alle SMC-Features im SHAP-Rang ≥ 20 (von 37 Features), mit SHAP-Werten < 0.001. Ablation hat das numerisch bestätigt.

Quelle: NB11-Sieger-Config in `phase1_best_config.json` (Hardcoded Fallback in `notebooks/12_model_battery.ipynb` Cell 5). 27-Feature-Liste enthält NULL SMC-Features.

## 4. Decision

**SMC-Features werden aus dem V1-Modell entfernt. Lock.**

Re-Test-Bedingungen (klar definiert):
- Wenn wir Tick-Daten oder Order-Book-Daten bekommen → SMC-Konzepte neu evaluieren (bessere Mikrostruktur-Auflösung)
- Wenn V2-Backend Constraint-Frei läuft (kein 30-Tree-Limit) → SMC-Features mit anderem Modell (z.B. CatBoost mit auto-feature-interaction) testen
- Sonst: nicht wieder anfassen

## 5. Konsequenz

**Code:**
- `core/features/smc.py` bleibt im Repo (für Re-Test-Szenarien), wird aber NICHT mehr in der Default-Feature-Pipeline genutzt
- Keine Pine-Code-Generation für SMC-Features (würde Pine-Budget sprengen)

**Roadmap:**
- Phase E (Pine Export) Budget-Schätzung berücksichtigt KEIN SMC mehr
- V2-Backend kann SMC-Re-Test als Forschungs-Item übernehmen, niedriger Prio

**Strategisch:**
- Bestätigt Locked Rule "Data trumps intuition" (HANDOFF 12.1.3)
- Bestätigt "Pine-Budget zwingt zu disciplined feature selection" → Reduktion bringt Lift, nicht Verlust
- Lesson: Populäre Trading-Konzepte sind in der ML-Praxis oft Noise, nicht Edge. Empirie regiert.

**Marketing-Implikation:**
- KEIN "SMC-powered"-Marketing. Wir nutzen es nicht.
- Stattdessen: "ML-driven structural distance + multi-TF alignment" — was wir tatsächlich tun.
