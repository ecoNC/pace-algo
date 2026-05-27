# Asset Generalization — Phase B (NB13)

**Status:** ⏳ NOCH NICHT GESTARTET — wartet auf Phase A (NB12) Abschluss

Diese Datei enthält den Plan + die zu testenden Hypothesen. Wird mit echten Zahlen gefüllt, sobald NB13 gebaut und gelaufen ist.

---

## Forschungs-Frage

**Kann das in Phase A gewählte Modell** (LightGBM oder Phase-A-Sieger) **auf FX-Daten trainiert die Edge auf andere Asset-Klassen übertragen?**

Konkret: ohne Retraining, pure Out-of-Distribution-Test.

---

## Test-Setup (geplant)

| Element | Wert |
|---|---|
| Trainings-Daten | FX-only (EURUSD, USDJPY) — Phase-A-Sieger |
| Test-Daten | Crypto (BTC, ETH, SOL), Indices (SPY, QQQ), Gold (XAUUSD), Commodities (USO) |
| Retraining | KEINS — pure Inferenz |
| Tier-Cutoffs | Mit zwei Varianten getestet: (a) FX-VAL-derived, (b) Asset-spezifisch VAL-derived |
| Evaluation | Per-Asset PF/WR/Trade-Count, OOS-Period |

**Vorbedingung:** Polygon.io-Aktivierung ($29/Monat) für SPY/QQQ/USO. Crypto via KuCoin ist bereits verfügbar.

---

## Hypothesen (zu prüfen)

### H1: "FX-trainiertes Modell generalisiert eingeschränkt"

**Erwartung:** Mean-PF über alle Asset-Klassen ≈ 1.2–1.5, deutlich unter FX-only 2.015. Die "Universalitäts-Strafe" wird messbar sein.

**Falls H1 stimmt:** Universal-Single-Model (Variante A in Phase D) ist suboptimal. Per-Asset-Kalibrierung (Variante B) wird wahrscheinlich gewählt.

### H2: "Crypto bricht, FX-Cousins (GBPUSD, USDCHF) generalisieren"

**Erwartung:** Per-Asset-Ranking:
- Top: GBPUSD, USDCHF, EURJPY (FX-Familie) — PF > 1.5
- Mitte: SPY, QQQ (Indices) — PF 1.1–1.4
- Bottom: BTC, ETH (Crypto, andere Vola-Regimes) — PF < 1.1, evtl. random

**Falls H2 stimmt:** Asset-Cluster-basierte Modellierung wird sinnvoll (Variante B oder C).

### H3: "Session-Features sind FX-spezifisch und brechen auf Crypto"

**Erwartung:** SHAP-Verteilung zeigt, dass `hour_sin/cos` auf Crypto SHAP-Rang verlieren, weil Crypto 24/7-Markt ist ohne klare Sessions.

**Falls H3 stimmt:** asset-spezifische Feature-Subsets sind sinnvoll, oder Universal-Modell braucht ein Asset-Type-Indikator als Feature.

### H4: "Volatilitäts-Features generalisieren"

**Erwartung:** `realized_vol_20`, `atr_percentile_100` haben über alle Asset-Klassen ähnliche SHAP-Werte und tragen zur Edge bei.

**Falls H4 stimmt:** Vola-Features sind das Rückgrat der Universalität.

---

## Erfolgs-Kriterien für Phase B

**Minimum** für Phase C zu starten:
- Mindestens 4 Asset-Klassen mit PF > 1.3
- GBPUSD-Hold-Out hält sich bei PF > 1.4 (bereits in NB12 getestet)
- Mean-Asset-PF > 1.4

**Falls Minimum verfehlt:** Phase D direkt anziehen (Variante B oder C — Universal-Modell verworfen).

---

## Was in /results/ landet

- `per_symbol_metrics/nb13_per_asset_pf_{date}.csv` — Tabelle PF/WR/Trades pro Symbol × Tier
- `json_exports/nb13_cross_asset_{date}.json` — vollständiger Snapshot inkl. per-Asset-SHAP
- `benchmark_tables/nb13_asset_class_means_{date}.csv` — aggregiert auf Klassen-Ebene

---

## Implementierungs-Notizen für NB13 (für späteren Build)

- Lade Phase-A-Sieger-Modell aus `artifacts/models/`
- Für jedes neue Asset:
  1. Build extended features (analog NB12 Section 2.5)
  2. Filter auf OOS-Window (`>= VAL_END`)
  3. Inferenz mit Phase-A-Modell
  4. Apply FX-VAL-Cutoffs UND Asset-VAL-Cutoffs (zwei Varianten parallel)
  5. Compute PF/WR/Trades
- SHAP pro Asset berechnen (TreeExplainer auf Phase-A-Modell, Asset-Daten)
- Export nach `/results/` strukturiert
