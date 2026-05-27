# Architecture Decision Records (ADRs)

Jede bedeutende Entscheidung im PaceAlgo-Projekt landet hier als eigener File. Format: `ANN-XXX-kebab-case-title.md`, fortlaufend nummeriert.

## Warum ADRs?

Damit das Repo später wie ein Quant-Research-System lesbar ist und nicht nur wie eine Sammlung von Notebooks. Jede ADR beantwortet die Frage: **"Warum haben wir das so gebaut und nicht anders?"** — auch wenn der ursprüngliche Autor nicht mehr greifbar ist.

## Format pro ADR

Pflichtstruktur (aus [_phase_decision_template.md](_phase_decision_template.md)):

1. **Hypothese** — Was haben wir vorher angenommen?
2. **Experiment** — Wie haben wir's getestet? Welcher Datensatz, welches Notebook, welche Splits?
3. **Resultat** — Was hat das Experiment quantitativ gezeigt? (Mit Pfad zur `/results/`-Datei)
4. **Decision** — Was haben wir entschieden? Lock oder weiter offen?
5. **Konsequenz** — Was ändert sich dadurch im Code / in der Roadmap / in der Produkt-Architektur?

Zusätzlich am Anfang jedes ADRs:
- **Status:** Active | Superseded | Deprecated
- **Datum:** YYYY-MM-DD (UTC)
- **Locked-By:** Welche HANDOFF Section 12 Rule referenziert das (falls relevant)
- **Related:** Verlinkte ADRs

## Index

| Nr | Titel | Status | Datum |
|---|---|---|---|
| [ANN-001](ANN-001-smc-features-deprecated.md) | SMC-Features verworfen unter Pine-Budget | Active | 2026-05-26 |
| [ANN-002](ANN-002-htf-interaction-features.md) | HTF-Interaction-Features behalten (+0.06 PF) | Active | 2026-05-26 |
| [ANN-003](ANN-003-gold-removed-from-training.md) | Gold/XAUUSD aus FX-Trainings-Pool entfernt | Active | 2026-05-26 |
| [ANN-004](ANN-004-consensus-filter-v1.5-not-v1.md) | Consensus-Filter gehört nicht in V1-Pine | Active | 2026-05-27 |
| [ANN-005](ANN-005-v1-vs-v1.5-scope-split.md) | V1 vs V1.5 Scope-Split | Active | 2026-05-27 |
| [ANN-006](ANN-006-robustness-first-mantra.md) | Robustheits-First-Mantra (Strategy Lock) | Active | 2026-05-27 |
| [ANN-007](ANN-007-distribution-architecture.md) | Distribution-Architektur (Website + Stripe + TV-Invite) | Active | 2026-05-27 |
| [ANN-008](ANN-008-fx-features-do-not-generalize-to-crypto.md) | FX-Features generalisieren NICHT auf Crypto | Active | 2026-05-27 |

## Was hier NICHT hingehört

- Tagesgeschäft / operative Notizen → HANDOFF.md Section 19
- Numerische Roh-Ergebnisse → /results/
- Aktuelle Strategie / Roadmap → /docs/roadmap.md
- Feature-Statistiken → /docs/feature_registry.md

ADRs sind **Entscheidungen mit langer Halbwertszeit** — sie sollten relevant bleiben auch wenn das Repo in 2 Jahren komplett anders aussieht.

## Wann wird eine neue ADR geschrieben?

Wenn eine Phase abgeschlossen ist UND mindestens eine der drei Bedingungen erfüllt ist:
1. Eine Architektur-Entscheidung wurde getroffen, die spätere Maintainer verstehen müssen
2. Eine Hypothese wurde empirisch widerlegt und das Feature/der Ansatz wird verworfen
3. Ein neues Designpattern wird etabliert, das auch in zukünftigen Notebooks gilt
