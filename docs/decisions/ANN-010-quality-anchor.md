# ANN-010: Quality Anchor (Premium PF ≥ 2.0 für neue Asset-Klassen-Modelle)

**Status:** Active
**Datum:** 2026-05-27
**Locked-By:** Nico-Decision nach NB13 + ANN-006 Mantra
**Related:** [[ANN-006]] (Robustheits-Mantra) [[ANN-009]] (Router-Architektur) [[ANN-008]] (Crypto-Bruch)

---

## 1. Hypothese

Wenn wir auf Multi-Model-Router-Architektur umstellen ([ANN-009](ANN-009-multi-model-router-architecture.md)), entsteht ein Risiko: **jedes neue Asset-Klassen-Modell könnte mit niedrigerer Edge akzeptiert werden, "weil es besser als nichts ist"**. Das würde die Produktqualität verwässern und die ANN-006 Locks (Robustheit, Konsistenz) bedrohen.

Hypothese: Wenn wir einen **expliziten Quality Anchor** definieren — die FX-Premium-Edge — und jedes neue Modell daran messen, schützt uns das vor schleichender Qualitätserosion.

## 2. Experiment

Quelle: Aggregierte NB11/NB12/NB13 Daten.

**Was wir wissen (als Anchor verwendbar):**

| Datenpunkt | Wert | Belegt durch |
|---|---|---|
| NB11 FX-only (2 Symbole, 5m+15m) Premium PF | 2.015 | NB11 Best-Config-JSON |
| NB12 FX-only Premium PF in-sample TEST | 1.952 | results/json_exports/nb12_model_battery_2026-05-27.json |
| NB12 GBPUSD Hold-Out Premium PF | 2.537 | dto. |
| NB13 FX 5m Premium PF (5 Symbole, inkl. 3 Hold-Out) | **2.49** (mean) | results/nb13/metrics/cross_asset_matrix_2026-05-27.csv |
| NB13 FX 1h Premium PF | 1.18 (mean) | dto. — höhere TFs schwächer |
| Per-Year Stability CV (LGBM) | 0.145 | NB12 yearly stability |

**Der Quality Anchor wird über mehrere Datenpunkte definiert, NICHT eine einzelne Zahl:**

- **Premium PF Mean (5m, OOS):** ≥ 2.0
- **Premium PF auf JEDEM trainierten Asset-Symbol:** ≥ 1.5 (kein einzelnes Symbol bricht)
- **Premium PF auf JEDEM Hold-Out-Symbol (gleiche Klasse):** ≥ 2.0 (Generalisierung muss halten)
- **Stability CV über Jahre:** < 0.20

## 3. Resultat

**Definition: Quality Anchor für PaceAlgo Modelle**

Ein neues Asset-Klassen-Modell (oder ein modifiziertes bestehendes Modell) darf **NUR** in V1/V2/V3 deployed werden, wenn ALLE der folgenden Kriterien erfüllt sind:

### Strikte Kriterien (alle MÜSSEN erfüllt sein)

| Kriterium | Schwelle | Quelle |
|---|---|---|
| Premium-Tier Mean PF (OOS, primary TF) | ≥ **1.5** | aus Cross-Asset Test |
| Premium-Tier Mean PF auf Hold-Out-Symbolen | ≥ **1.4** | echtes OOS, nie trainiert |
| Min PF pro trainiertem Symbol | ≥ **1.3** | kein Symbol darf brechen |
| Stability CV über Jahre | ≤ **0.25** | aus per-year breakdown |
| Min PF pro Jahr (2020–latest) | ≥ **1.2** | kein Jahres-Bruch |
| Min Trades pro Tier pro Jahr | ≥ **30** | statistische Power |
| Pine-Budget-Check | grün (siehe pine_constraints.md) | NB10-bit-exact + Ops/Bar |

### Soft Kriterien (mindestens 2 von 3)

| Kriterium | Soft-Threshold |
|---|---|
| Mean PF auf primärem TF | ≥ 2.0 (matched FX-Anchor) |
| Win Rate Premium-Tier | ≥ 60% |
| SHAP-Top-5 Features konsistent über Symbole | ja (Stabilitäts-Test) |

### Soft Anchor: FX-PF 2.0 als Vergleichspunkt

**Der FX-Quality-Anchor ist NICHT ein absoluter Mindestwert für alle Asset-Klassen — sondern ein Referenzpunkt.** Es ist möglich dass Crypto inhärent schwierigere Edge hat (effizientere Märkte, weniger institutionelle Edge-Sources). In dem Fall könnte Crypto-Modell mit PF 1.5 akzeptabel sein — aber:

- **Marketing muss diese Differenz transparent kommunizieren:** "FX-Modell historisch PF 2.5, Crypto-Modell PF 1.5 — beides positiver Edge, aber FX ist unsere stärkste Asset-Klasse"
- **Tier-Cutoffs müssen per Modell unterschiedlich sein:** Premium auf FX = top 1%, Premium auf Crypto vielleicht = top 0.5% wenn Edge schwächer

## 4. Decision

**Diese Quality Anchor Kriterien werden gelocked. Jedes neue Modell durchläuft den Check vor Deployment.**

### Operationalisierung in Code

`core/config.py` bekommt:
```python
QUALITY_ANCHOR = {
    "strict": {
        "min_premium_pf_oos":          1.5,
        "min_premium_pf_holdout":      1.4,
        "min_pf_per_symbol":           1.3,
        "max_stability_cv":            0.25,
        "min_pf_per_year":             1.2,
        "min_trades_per_year_tier":    30,
    },
    "soft_reference": {
        "fx_premium_pf_anchor":        2.0,
        "premium_wr_target":           0.60,
    },
    "deployment_action": {
        "all_strict_passed":  "auto-deploy candidate",
        "missing_1_strict":   "requires Nico explicit override",
        "missing_2plus":      "deployment blocked — re-research required",
    }
}
```

`core/analysis/quality_check.py` (NEU) wird ein Modul:
```python
def check_quality_anchor(model_metrics: dict) -> tuple[bool, str, dict]:
    """
    Returns (passed, severity, details).
    severity: "passed" | "soft_only" | "missing_1_strict" | "blocked"
    """
```

Wird automatisch von jedem Trainings-Notebook (NB05+) am Ende aufgerufen.

### Feature-Regel-Verschärfung (per Nico-Anweisung)

Locked Rule Update zu HANDOFF Section 12 (oder hier verankert):

**Ab sofort gilt strikt:**
1. ❌ Keine neuen Features ohne explizite Hypothese (im jeweiligen Notebook + research/feature_experiments.md)
2. ❌ Keine neuen Features ohne **OOS-Lift ≥ +0.05 PF in Ablation** (HANDOFF 12.1.2 verschärft)
3. ❌ Keine neuen Features ohne **SHAP-Evidenz auf mindestens 2 Asset-Klassen** (für universelle Features)
4. ❌ Keine neuen Features ohne **Pine-Budget-Check** (Ops/Bar + Tree-Depth-Impact)
5. ❌ Keine neuen Features ohne **Stability-CV-Check** (CV darf sich um max +0.05 verschlechtern)

### Was passiert wenn ein neues Asset-Klassen-Modell durchfällt?

**Beispiel Crypto-Spezialmodell:**

1. Wenn Crypto-only Training PF Premium-Tier OOS = 1.2 (unter strict Threshold 1.5):
   - Modell wird NICHT deployed
   - Crypto bleibt im UI als "Coming Soon" oder "Beta — Premium nicht validiert"
   - Re-Research: andere Features (Funding, OI), andere Hyperparams, anderes Training-Window

2. Wenn Crypto-only Training PF Premium = 1.6 (über strict, unter FX-Anchor 2.0):
   - Modell darf deployed werden
   - Marketing-Korrektur: Crypto-Tier-Erwartung explizit kommunizieren
   - Continuous Monitoring auf Drift

3. Wenn Crypto-only Training PF Premium ≥ 2.0:
   - Vollständig V2-ready
   - Standard Marketing-Story möglich

## 5. Konsequenz

### Code-Änderungen

- `core/config.py` bekommt `QUALITY_ANCHOR` constants
- `core/analysis/quality_check.py` (NEU) als wiederverwendbares Quality-Check-Modul
- Notebooks NB12+ rufen `check_quality_anchor()` am Ende auf
- `/results/quality_checks/` (NEU) Subdir für historische Quality-Reports

### Doku-Implikationen

- `docs/model_registry.md` bekommt Spalte "Quality Anchor Status" (passed/soft_only/blocked)
- `research/feature_experiments.md` bekommt explizite "Quality Check Result"-Section pro Experiment
- `HANDOFF.md` Section 12 (Locked Rules) verschärft Feature-Regeln

### Strategische Implikation

Der Quality Anchor ist **Anti-Schleichende-Qualitätsverwässerung**. Ohne ihn würden wir bei jedem neuen Asset-Klassen-Modell vor der Versuchung stehen "naja, PF 1.3 ist immerhin positiver Edge". Mit dem Anchor zwingen wir uns zur disziplinierten Datenanalyse — entweder das Modell hält die Latte, oder es darf nicht in V2.

### Lessons (warum dieser Anchor jetzt locked werden muss)

Aus NB11→NB12→NB13 sehen wir: Edge ist nicht linear stabil über Setups. Ein PF 2.5 auf 5m FX wird zu PF 1.18 auf 1h FX (NB13 TF-Comparison). Wenn wir keine harten Anchor-Werte haben, würden wir die schwächeren Konfigurationen "akzeptieren" weil sie "immerhin nicht random sind". Das hilft dem User nicht — er kauft das beste Tool, nicht das durchschnittliche.

Der Anchor zwingt uns: **Wenn FX 5m PF 2.5 möglich ist, dann ist das der Vergleichspunkt. Alles deutlich darunter braucht Begründung.**
