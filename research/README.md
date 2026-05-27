# `/research/` — Forschungs-Erkenntnisse & Interpretation

Hier leben **Erkenntnisse** (was wir gelernt haben), nicht Rohdaten (`/results/`) und nicht Strategie (`/docs/`).

Jede Datei interpretiert quantitative Ergebnisse und destilliert sie zu nutzbaren Aussagen.

| Datei | Inhalt | Wann aktualisiert |
|---|---|---|
| [phase1_findings.md](phase1_findings.md) | NB05–NB11 Erkenntnisse, FX-only PF 2.015 Forschungsbaseline | Phase 1 abgeschlossen |
| [feature_experiments.md](feature_experiments.md) | Welche Features funktionierten, welche nicht (SMC verworfen, Session/Vol gewonnen) | Bei jeder Ablation |
| [shap_analysis.md](shap_analysis.md) | Zentrale SHAP-Sammlung über alle Notebooks | Pro NB mit SHAP-Output |
| [asset_generalization.md](asset_generalization.md) | Phase B (NB13) — Cross-Asset-Erkenntnisse | Wenn NB13 läuft |
| [timeframe_comparisons.md](timeframe_comparisons.md) | Phase C (NB14) — Multi-TF-Erkenntnisse | Wenn NB14 läuft |
| [model_battery_results.md](model_battery_results.md) | Phase A (NB12) — Modellvergleich-Interpretation | Nach jedem NB12-Run |

## Regeln

1. **Kein Hand-Wedeln.** Jede Aussage muss auf eine `/results/`-Datei verweisen.
2. **Datum stempeln.** Wann gemessen? Auf welcher Daten-Version?
3. **Versions-Snapshot.** Wenn sich eine Erkenntnis ändert (z.B. neuer Run liefert andere Zahlen), alte Sektion mit `## ARCHIVED — {date}` versehen, NICHT löschen.
4. **Lessons Learned explizit markieren** mit `> Lesson:` Block-Quote.

## Lese-Reihenfolge für neuen Claude

Wenn ein neuer Claude sich orientieren will:
1. `phase1_findings.md` — was haben wir bis NB11 herausgefunden
2. `feature_experiments.md` — welche Features sind tot, welche leben
3. `model_battery_results.md` — Phase A Verdict (sobald NB12 gelaufen)
4. Dann je nach Phasen-Stand: `asset_generalization.md` / `timeframe_comparisons.md`
