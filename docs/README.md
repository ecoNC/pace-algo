# `/docs/` — Strategic & Structural Documentation

Langlebige Architektur- und Strategie-Dokumente. Im Gegensatz zu `/research/` (was wir gelernt haben) und `/results/` (Rohdaten) beschreibt `/docs/` **wie wir bauen und wohin wir gehen**.

| Datei | Inhalt | Lese-Trigger |
|---|---|---|
| [roadmap.md](roadmap.md) | Phase A–E Forschungs- und Build-Plan | "Was ist als nächstes?" |
| [architecture.md](architecture.md) | Code-Struktur, Pine→Hybrid→Backend-Migration | "Wo gehört Code X hin?" |
| [feature_registry.md](feature_registry.md) | Alle Features: Quelle, SHAP, OOS-Lift, Status | "Sollen wir Feature X einbauen?" |
| [model_registry.md](model_registry.md) | Alle trainierten Modelle, Hyperparams, OOS-Metriken | "Welche Modell-Version läuft?" |
| [pine_constraints.md](pine_constraints.md) | Pine-Budget (30 trees, depth 3, 15 features, 5000 ops/bar) | Vor jedem Modell-Design |
| [backtesting_vision.md](backtesting_vision.md) | User-facing Backtest-Widget, Anti-Curve-Fitting-Design | Vor V1-Pine-Generator (NB09) |
| [deployment_plan.md](deployment_plan.md) | Pine V1 → Hybrid V1.5 → Backend V2 Migrationspfad | Bei jeder Phasen-Entscheidung |
| [colab_auto_push.md](colab_auto_push.md) | Colab→GitHub Auto-Push-Pattern für `/results/`-Files (Token-Setup + Code-Snippet) | Beim Bau jedes neuen Notebooks |
| [_phase_decision_template.md](_phase_decision_template.md) | Pflicht-Template für jede Phase-Abschluss-Dokumentation (Hypothese→Experiment→Resultat→Decision→Konsequenz) | Bei Phase-Abschluss + neuer ADR |
| [decisions/](decisions/) | Architecture Decision Records (ADRs) — fundamentale Entscheidungen mit langer Halbwertszeit | Bei jeder strategischen Entscheidung |

## Verhältnis zu HANDOFF.md

- **HANDOFF.md** = operativ, aktuell, "wo stehen wir gerade", Sync zwischen Workstations
- **/docs/** = langlebig, referenziell, "wie sollen wir bauen"

Wenn ein Doc-Inhalt sich ändert (z.B. neue Phase, gestrichenes Feature), wird `/docs/` geupdated UND HANDOFF.md Section 19 bekommt einen Log-Eintrag, der auf die Änderung verweist.
