# Pine Constraints

**Quelle:** HANDOFF.md Section 12 (Locked Rule 10) + Section 13.4

Diese Limits sind hart. Verletzung erfordert explizite Backend-V1-Freigabe von Nico.

## Hard Limits

```python
PINE_BUDGET = {
    'max_trees':            30,    # per model
    'max_tree_depth':       3,     # max 7 leaves per tree
    'max_features_used':    15,    # nach SHAP-Reduktion
    'max_operations_bar':   5000,  # Pine limit ist 9000 — wir bleiben unter 56% für Sicherheits-Buffer
    'max_request_security': 12,    # Pine limit ist 40
}
```

## Warum diese Limits?

| Limit | Warum |
|---|---|
| 30 trees | Erfahrung NB05–NB11: tiefer/mehr Bäume = overfitting, kein OOS-Lift |
| Depth 3 | Pine kann tiefere if/else-Cascades, aber lesbar bleiben + Inference-Speed |
| 15 features | SHAP zeigt typisch 12–15 als nicht-tot; mehr = noise im Pine-Code |
| 5000 ops/bar | TradingView hat 9000 als Hard-Limit; wir lassen Buffer für Plot/Box-Rendering |
| 12 request.security | Pine limit ist 40, aber jeder Security-Call kostet 100ms Lag |

## Aktueller Verbrauch (NB10 Stand)

- Pine-Code: ~1055 Linien
- Ops/Bar: ~215 (4.3% von 5000-Limit)
- Trees: 30 (max ausgenutzt)
- Features: 12–15 (typisch nach SHAP-Reduktion)

## Modelle und ihre Pine-Eignung

| Modell | Pine-export-fähig? | Begründung |
|---|---|---|
| LightGBM | ✅ JA | Native tree-cascade, gut verstanden, unsere Baseline |
| XGBoost | ✅ JA | Ähnliche Tree-Struktur, exportierbar mit ähnlichem Aufwand |
| CatBoost | ❌ NEIN | Oblivious Trees + categorical embeddings — komplex/unmöglich in Pine |
| Voting Ensemble (LGBM+XGB+Cat) | ⚠️ TEILWEISE | Wenn CatBoost dabei: nein. LGBM+XGB only: ja, aber ~3x Code-Größe |
| Voting (LGBM+XGB only) | ✅ JA | Möglich, aber bulky — ~2x Linien |

**Konsequenz:** CatBoost bleibt im Research-Set (NB12 Vergleich), aber für V1-Pine-Export kommen nur LGBM, XGB oder ein 2-Modell-Voting in Frage.

## Hybrid V1.5 / Backend V2 — entspannte Constraints

Sobald Backend aktiv ist, fallen diese Limits weg. CatBoost, größere Modelle, mehr Features werden möglich. Der Migrationspfad in [deployment_plan.md](deployment_plan.md) hält das offen.
