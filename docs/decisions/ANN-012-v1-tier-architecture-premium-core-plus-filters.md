# ANN-012: V1 Tier-Architektur — Premium Core + Secondary Filters

**Status:** Active — **supersedes Profile-Map in ANN-011** (Profile-Mechanik), ANN-011 V1-TF-Lock bleibt gültig
**Datum:** 2026-05-27
**Locked-By:** Nico-Decision nach NB14b R-14 Cutoff-Konvergenz-Beweis
**Related:** [[ANN-009]] (Router) [[ANN-010]] (Quality-Anchor) [[ANN-011]] (V1-TF + Whitelist) [[ANN-006]] (Robustheits-Mantra)

---

## 1. Hypothese

Vor NB14b: Wir können drei klar getrennte Probability-Cutoffs (Top 10% / 3% / 1%) auf der LightGBM-Output-Verteilung definieren, die Aggressive / Balanced / Conservative Profile bilden. Das ist das ursprüngliche Tier-Konzept aus NB11/NB12 und ANN-011 §0b.

**Falsifizierungs-Hypothese (in NB14b explizit getestet):** Sollte die Probability-Verteilung KEINE drei sauber trennbaren Bänder zeigen, dann ist Probability-basierte Multi-Tier-Cutoff-Calibration **fundamental kaputt** für unsere aktuelle Modell-Architektur — und wir brauchen einen anderen Tier-Mechanismus.

## 2. Experiment

**Notebook:** [notebooks/14b_cutoff_calibration.ipynb](../../notebooks/14b_cutoff_calibration.ipynb)
**Run-ID:** `nb14b_2026-05-27T16-48-52Z_81f2316` (commit `5a3576b`)

**Setup:**
- Modell: V1-FX-LightGBM (30 trees × depth 3, `is_unbalance=True`, 27 Features, 5m TF)
- 3 Cutoff-Strategien parallel getestet:
  - **linear-quantile** — gleichmäßige Top-N%-Cutoffs
  - **logit-space-quantile** — Cutoffs im Logit-Space (kompensiert sigmoid-Sättigung)
  - **density-target** — Cutoffs aus VAL-Probability-KDE bei Ziel-Density
- 4 Constraints pro Strategie:
  1. PF-Schwellen: Aggressive ≥ 1.3 / Balanced ≥ 1.5 / Conservative ≥ 1.8
  2. Sigs/Tag-Range pro Profil: Aggressive 15–30 / Balanced 5–10 / Conservative 1–4
  3. Cutoff-Separation ≥ 0.005 (Probability-Abstand zwischen Tiers)
  4. Cross-Asset-Stabilität ±20% über die 5 FX-Symbole
- Winner-Auswahl: NICHT "max PF", sondern "alle 4 Constraints konsistent erfüllt"

## 3. Resultat

**ALLE 3 Strategien FAILED.** Winner war `density` mit 6/11 Constraints erfüllt — das ist Random-Niveau.

**Per-Strategie Cutoffs:**

| Strategie | Aggressive | Balanced | Conservative |
|---|---:|---:|---:|
| linear-quantile | 0.4067 | 0.4067 | 0.4096 |
| logit-space-quantile | 0.4067 | 0.4067 | 0.4096 |
| density-target | 0.4067 | 0.4067 | 0.4203 |

**Aggressive und Balanced kollabieren auf IDENTISCHEN Cutoff `0.4067` in allen 3 Strategien.** Per-Symbol-Calibration zeigt: EURUSD + AUDUSD haben `Agg = Bal = Cons = 0.4067` — vollständiger Kollaps.

**Probability-Verteilungs-Analyse:**

```
< 0.4067   →  no signal (Modell hat kein Confidence)
~ 0.4067   →  Cluster (Modell saturiert hier — alle Splits enden in diesem Leaf-Bereich)
> 0.4096   →  Premium-Tier (klar separierbar, PF 2.0 in-sample / 2.39 Hold-Out)
```

**Root-Cause:** LightGBM-Output mit 30 Trees × Depth 3 + `is_unbalance=True` saturiert die sigmoid-Outputs in **3 diskrete Bänder** statt graduellem Confidence-Gradient. Das Modell verhält sich **wie ein harter Pattern-Detector** ("Premium-Signal: ja/nein"), nicht wie ein kontinuierlicher Confidence-Ranker.

Quelle: [results/nb14b/summaries/nb14b_full_snapshot_2026-05-27.json](../../results/nb14b/summaries/nb14b_full_snapshot_2026-05-27.json), per-symbol-tabelle in [results/nb14b/metrics/per_symbol_winner_2026-05-27.csv](../../results/nb14b/metrics/per_symbol_winner_2026-05-27.csv).

## 4. Decision

**Probability-basierte Multi-Tier-Cutoffs werden für V1 verworfen. Lock.**

**Neue V1-Tier-Architektur: "Premium Core + Secondary Filters"** (Option A).

| Profil | Mechanik | Filter-Stack | Erwartete Sigs/Tag |
|---|---|---|---:|
| **Aggressive** | Premium pur | nur Probability ≥ 0.4096 | ~3.5 |
| **Balanced** | Premium + HTF-Confirmation | Probability ≥ 0.4096 **AND** HTF-1h-Trend stimmt mit Signal überein | ~3.0 |
| **Conservative** | Premium + HTF-Confirmation + Session-Filter | Probability ≥ 0.4096 **AND** HTF-Confirm **AND** Bar liegt in NY-Session (13:00–22:00 UTC) | ~1.5 |

### Pflicht-Eigenschaften der neuen Architektur

1. **EIN Modell, EIN Probability-Threshold:** Alle 3 Profile basieren auf demselben Premium-Core-Modell mit Cutoff `0.4096`. Profile differenzieren NUR durch nachgelagerte Filter, nicht durch ML-Threshold-Verschiebung.

2. **Edge bleibt PF ~2.0 über alle Profile:** Filter machen das Profil selektiver, aber jedes verbleibende Signal hat die volle Premium-Edge. Kein künstliches Verwässern durch schlechte Lower-Tiers.

3. **Filter sind in ANN-011 Whitelist erlaubt:** HTF-Confirmation und Session-Filter sind als User-Settings bereits whitelist-approved — keine Erweiterung der erlaubten Inputs nötig.

4. **R-13 (NY-Konzentration 66.6%) wird operationalisiert:** Statt als "verstecktes" Pattern wird die NY-Session-Stärke als Conservative-Profil-Feature transparent verkauft.

### Was NICHT in V1 kommt

- ❌ Re-Train mit isotonic calibration (Option B) — V1.5-Territory
- ❌ Mehr Trees / weniger `is_unbalance` (würde aktuellen V1-Modell-Artefakt brechen)
- ❌ Per-Symbol-spezifische Cutoffs (NB14b zeigt: das hilft nicht)
- ❌ User-konfigurierbare Probability-Thresholds (verbotene per ANN-006 Mantra Lock 4 + ANN-011 §0c Whitelist)

### V1.5/V2 offene Tür

Sobald ein Backend mit Continuous-Learning aktiv ist (V1.5), können wir **kalibrierte Probability-Tiers** als zusätzliche Layer einführen — z.B. "Ultra-Premium" via Backend-Consensus-Filter (siehe ANN-004 Consensus-Plan). Für V1 ist das nicht der Pfad.

## 5. Konsequenz

### Strategische Re-Interpretation

> Das Modell verhält sich wie ein **harter Pattern-Detector**, nicht wie ein kontinuierlicher Confidence-Ranker.
>
> **Das ist KEIN Fehler. Das passt zu einem hochwertigen Signalprodukt.**
>
> Wir verkaufen keine "mehr Signale". Wir verkaufen **bessere Marktselektion + Kontextfilterung + höhere Konsistenz**.

Diese Reframing-Aussage geht ins README + Marketing-Material.

### Code-Änderungen (anstehend / committed)

**Anstehend (NB14c):**
- `notebooks/14c_secondary_filter_validation.ipynb` — testet HTF-only, Session-only, beide kombiniert auf Hold-Out (5 FX-Symbole × 5m). Liefert finale Sigs/Day-Zahlen pro Profil.
- Filter-Funktionen in `core/eval/tf_pipeline.py` erweitern: `apply_htf_filter()`, `apply_session_filter()`.
- `core/config.py` — V1_PROFILE_FILTERS dict (Profile → Filter-Stack-Definition).

**Doku-Updates (in diesem Commit):**
- `docs/pine_router_design.md` §0b — Profile-Mapping mit Filter-Mechanik statt Probability-Cutoffs
- `docs/decisions/ANN-011-*.md` — Cross-Link zu ANN-012 ("Profile-Map superseded")
- `docs/roadmap.md` — Phase C abgeschlossen, NB14c als next, NB15 Pine-Router-V1 startet danach
- `docs/decisions/README.md` — ANN-012 in Index
- `docs/model_registry.md` — Profile-Mechanik-Hinweis bei FX-Modell-Slot
- `research/timeframe_comparisons.md` — Section "Profile-Lock via Filter" (NB14c-Skelett)
- `HANDOFF.md` Section 19 + Section 19a (Decision-Marker)

### Pine-Code-Implikation

Pine-Profile-Mapping ändert sich von Probability-Cutoff-Switch zu Filter-Stack:

```pine
// === V1 TIER ENGINE (per ANN-012) ===
PREMIUM_CUTOFF = 0.4096   // gelocked durch NB14/NB14b — ein Cutoff für alle Profile

probability = fx_model_predict(features)
in_premium  = probability >= PREMIUM_CUTOFF

// Profile-Definition via Filter-Stack
profile = input.string("Balanced", "Signal-Profil",
                        options=["Aggressive", "Balanced", "Conservative"])

htf_trend_aligns = ...   // 1h-Trend stimmt mit Signal-Richtung
in_ny_session    = hour(time, "UTC") >= 13 and hour(time, "UTC") < 22

signal_active = in_premium and (
      profile == "Aggressive"  ? true
    : profile == "Balanced"    ? htf_trend_aligns
    :                            htf_trend_aligns and in_ny_session
)
```

**Pine-Budget-Impact:** Profile-Mechanik wird **einfacher** als ursprünglich geplant — keine 3 verschiedenen Cutoffs zu embedden, nur 1 + 2 boolesche Filter. Ops-pro-Bar-Verbrauch reduziert.

### Marketing-Story (klare Differenzierung)

**Vor ANN-012:** "Drei Confidence-Tiers — wähle dein Risiko-Profil"
**Nach ANN-012:** "Premium AI Signals — wähle wie viele Markt-Kontexte zusätzlich gefiltert werden"

| Profil | Verkaufsargument |
|---|---|
| Aggressive | "Alle Premium-AI-Signale — maximale Frequenz" |
| Balanced | "Premium-Signale, die mit dem 1-Stunden-Trend übereinstimmen" |
| Conservative | "Premium-Signale in der liquidesten Marktphase (NY-Session)" |

Das ist **ehrlicher** und **leichter zu verstehen** als künstliche Probability-Bänder. Es operationalisiert auch R-13 (NY-Konzentration 66.6%) als positives Produkt-Feature statt als verstecktes Bias.

### Quality-Anchor (ANN-010) bleibt Pflicht-Check

Jedes der 3 Profile muss in NB14c den Quality-Anchor passieren:
- PF Premium-Tier OOS ≥ 1.5 (sollte alle 3 Profile bestehen — wir filtern ja nur, schwächen nicht)
- Min Sigs/Jahr ≥ 30 — kritisch für Conservative, das nur ~1.5 Sigs/Tag hat
- Stability-CV ≤ 0.25
- MDD < 18%

Wenn Conservative die statistische Power nicht erreicht (zu wenige Trades pro Jahr), wird das Profil entweder gelockert (Session-Filter aufweichen) oder entfernt — bleibt aber bei 2 Profile statt 3.

### Re-Test-Bedingungen

- Wenn V1.5-Backend Modell-Calibration ermöglicht (mehr Trees, isotonic regression): Option B revisited
- Wenn neue Crypto/Indices/Commodity-Modelle ebenfalls 3-Band-Probability-Verhalten zeigen: ANN-012 wird zur **universellen V2-Tier-Architektur**, alle Asset-Klassen nutzen Filter-Stack
- Wenn ein Crypto/Indices-Modell glatte Probability-Verteilung hat: Per-Asset-Klassen-Tier-Mechanik (manche Filter, manche Probability) — würde ANN-012 verfeinern, nicht umstoßen

### Lessons

1. **Modell-Verhalten ≠ Erwartung.** Wir nahmen kontinuierliche Probability an. NB14b hat das datenbelegt widerlegt. Robustheits-Mantra (ANN-006 Lock 1) befolgt — wir folgen den Daten.

2. **Hard Pattern Detector kann ein Feature sein, kein Bug.** Ein Modell das klar "Signal: ja/nein" sagt ist **leichter zu erklären** und **schwerer zu missbrauchen** als eines mit gradueller Confidence. Das ist Marketing-positiv.

3. **Profile via Filter ist V2-ready.** Wenn wir Crypto/Indices-Modelle dazubauen, können wir die gleiche Filter-Mechanik wiederverwenden — vielleicht mit asset-spezifischen Filtern (z.B. Crypto: BTC-Dominance-Filter, Indices: VIX-Filter). Das skaliert sauber.

4. **Anti-Curve-Fitting (ANN-006 Lock 4) wurde gewahrt.** Wir geben User keine free probability-slider. Wir geben drei vordefinierte Filter-Kombinationen mit transparenter Logik.
