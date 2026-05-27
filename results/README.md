# `/results/` — Quantitative Output Storage

Maschinen-lesbare Ergebnisse aller Experimente. Jede Datei hier ist Output eines Notebooks, kein manuell editierter Text.

**Regel:** Jeder substanzielle Notebook-Run schreibt seine Ergebnisse hierher. Wir analysieren `/results/`-Dateien später, ohne das Notebook neu laufen lassen zu müssen.

## Struktur

| Ordner | Inhalt | Schreibt rein |
|---|---|---|
| `json_exports/` | Vollständige Experiment-Snapshots als JSON (Modelle, Hyperparams, Metriken) | NB05, NB07, NB11, NB12, NB13+ |
| `benchmark_tables/` | Modell-Vergleichstabellen (PF/WR/ExpR pro Modell × Tier) als CSV/JSON | NB07, NB12, NB15 |
| `walk_forward_summaries/` | Per-Fold-Metriken über Walk-Forward-Splits | NB05, NB11, NB12 |
| `per_symbol_metrics/` | PF/WR/Trade-Count aufgeschlüsselt pro Symbol | NB08, NB11, NB12, NB13 |
| `yearly_stability_tables/` | PF pro Jahr × Modell/Konfiguration (Stability-CV-Quelle) | NB11, NB12 |

## Naming Convention

`{notebook}_{experiment-tag}_{date}.{ext}`

Beispiele:
- `nb12_model_battery_2026-05-27.json`
- `nb12_premium_pf_by_year_2026-05-27.csv`
- `nb13_cross_asset_per_symbol_2026-06-XX.json`

Datum ist UTC-Datum des Runs, nicht des Commits.

## Was hier NICHT hingehört

- Trainierte Modell-Artefakte (`.pkl`, `.cbm`) → die leben in `artifacts/models/`
- Rohdaten (`.parquet` OHLCV) → die leben in `data_cache/`
- Strategische Interpretation der Zahlen → die lebt in `/research/`
- Architektur-/Roadmap-Entscheidungen → die leben in `/docs/`

## Lese-Pattern für neue Sessions

Wenn ein neuer Claude wissen will, was der aktuelle Stand ist:
1. Check `/results/json_exports/` chronologisch (letzte Datei = letzter Stand)
2. Open korrespondierenden Bericht in `/research/{notebook}_results.md`
3. HANDOFF.md Section 16 (Open Action Items) für Kontext
