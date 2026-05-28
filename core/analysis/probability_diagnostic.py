"""
Probability Distribution Diagnostic — wiederverwendbar für V1-FX + V2-Asset-Klassen.

**Erstellt 2026-05-28** nach NB14c Run 1-3 (alle widersprüchlich):
    Run 1: hardcoded cutoff 0.4096 → 0 Trades
    Run 2: dyn cutoff (no floor)   → cutoff 0.4022 → fiel ins Cluster → PF 1.01
    Run 3: dyn cutoff + floor 0.4070 + deterministic=True → 0 Trades

Wir wissen nicht ob:
- deterministic=True das Modell kaputt macht
- 0.4096 ein stochastischer Lucky-Run war
- Distribution generell instabil ist
- Cutoff-Mechanismus falsch ist

Dieses Modul liefert die Daten um das zu entscheiden.

**Locked Rule (Nico, 2026-05-28):** Wichtige Zahlen (Premium PF, Cutoff, Trade-Count,
Max-Proba, Sigs/Tag) brauchen MINDESTENS 3 reruns mit mean/std-Reporting.
Single-Run-Entscheidungen sind ab jetzt verboten.

Klassen-agnostisch — funktioniert mit jedem trainiertem Modell das `.predict()`
zurückgibt-eine-numpy-Array hat (LightGBM, XGBoost, CatBoost).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# DISTRIBUTION SUMMARY
# ---------------------------------------------------------------------------

def distribution_summary(proba: np.ndarray, name: str = "proba") -> dict[str, Any]:
    """
    Vollständige Distribution-Statistik einer Probability-Array.

    Args:
        proba: numpy array, typischerweise model.predict(X) Output
        name: Bezeichner für Reporting

    Returns:
        dict mit allen wichtigen Statistiken — JSON-serializable.
    """
    if len(proba) == 0:
        return {"name": name, "error": "empty array"}

    # Basics
    s = pd.Series(proba)
    summary: dict[str, Any] = {
        "name":           name,
        "n":              int(len(proba)),
        "min":            float(s.min()),
        "max":            float(s.max()),
        "mean":           float(s.mean()),
        "std":            float(s.std()),
        "median":         float(s.median()),
    }

    # Quantiles — engmaschig bei oberen Tails (relevant für Premium-Tier-Cutoff)
    for q in [0.50, 0.75, 0.90, 0.95, 0.97, 0.98, 0.99, 0.995, 0.999, 0.9999]:
        summary[f"q{q:.4f}".rstrip('0').rstrip('.')] = float(np.quantile(proba, q))

    # Unique-Value-Cluster-Analyse — wichtig für discreteness check
    # Run zu 4 decimal places (LightGBM-Probs sind oft auf ~6-8 decimals exakt aber
    # mit floating-point-noise; aggregierung auf 4 decimal places zeigt echte Bands)
    rounded = np.round(proba, 4)
    unique_vals, counts = np.unique(rounded, return_counts=True)
    summary["n_unique_rounded_4dp"] = int(len(unique_vals))

    # Top-20 häufigste Werte
    top_idx = np.argsort(counts)[::-1][:20]
    summary["top20_values"] = [
        {"value": float(unique_vals[i]), "count": int(counts[i]),
         "pct_of_total": float(counts[i] / len(proba) * 100)}
        for i in top_idx
    ]

    # Counts über typischen Cutoff-Schwellen (für Sanity-Check)
    cutoff_schwellen = [0.35, 0.38, 0.40, 0.4022, 0.4067, 0.4070, 0.4096, 0.42, 0.45, 0.50]
    summary["counts_at_cutoffs"] = {
        f"{c:.4f}": {
            "n_bars_above": int((proba >= c).sum()),
            "pct_above":    float((proba >= c).mean() * 100),
        }
        for c in cutoff_schwellen
    }

    return summary


# ---------------------------------------------------------------------------
# HISTOGRAM (DATEN, NICHT PLOT — JSON-friendly)
# ---------------------------------------------------------------------------

def histogram_data(
    proba: np.ndarray,
    bins: int = 100,
    zoom_range: tuple[float, float] = (0.38, 0.43),
) -> dict[str, Any]:
    """
    Histogramm-Daten (Bin-Edges + Counts) — keine Plots, JSON-friendly.

    Returns dict mit:
      "full_range":  edges + counts über [proba.min(), proba.max()]
      "zoom_range":  edges + counts über zoom_range (default 0.38-0.43)
    """
    if len(proba) == 0:
        return {"error": "empty array"}

    out: dict[str, Any] = {"n": int(len(proba))}

    # Full range
    counts, edges = np.histogram(proba, bins=bins)
    out["full_range"] = {
        "edges":  [float(e) for e in edges],
        "counts": [int(c) for c in counts],
    }

    # Zoom range (typischerweise 0.38-0.43 wo Cluster sind)
    z_low, z_high = zoom_range
    mask = (proba >= z_low) & (proba <= z_high)
    if mask.sum() > 0:
        z_counts, z_edges = np.histogram(proba[mask], bins=min(50, int(mask.sum() / 5) + 1))
        out["zoom_range"] = {
            "range":   [float(z_low), float(z_high)],
            "n_in_range": int(mask.sum()),
            "edges":   [float(e) for e in z_edges],
            "counts":  [int(c) for c in z_counts],
        }
    else:
        out["zoom_range"] = {
            "range":      [float(z_low), float(z_high)],
            "n_in_range": 0,
        }

    return out


# ---------------------------------------------------------------------------
# CLUSTER DETECTION (Probability-Bands)
# ---------------------------------------------------------------------------

def find_discrete_clusters(
    proba: np.ndarray,
    decimal_places: int = 4,
    min_cluster_size: int = 5,
) -> dict[str, Any]:
    """
    Detect discrete probability bands (LightGBM-Saturation-Pattern).

    Rundet proba auf N decimal places, gruppiert. Cluster = Wert mit >= min_cluster_size
    Bars. Liefert Liste der Cluster sortiert nach Frequenz.

    Returns dict mit:
      "n_total_bars":    int
      "n_clusters":      int  (Anzahl distinct bands mit >= min_cluster_size)
      "clusters":        list von dicts (value, count, pct, range_around)
      "max_cluster_pct": float (% des größten Clusters)
      "is_highly_discrete": bool (True wenn Top-3 Cluster > 50% aller Bars)
    """
    if len(proba) == 0:
        return {"error": "empty array"}

    rounded = np.round(proba, decimal_places)
    counter = Counter(rounded.tolist())
    big_clusters = [(v, c) for v, c in counter.items() if c >= min_cluster_size]
    big_clusters.sort(key=lambda x: x[1], reverse=True)

    n_total = len(proba)
    clusters = [
        {
            "value":    float(v),
            "count":    int(c),
            "pct":      float(c / n_total * 100),
        }
        for v, c in big_clusters[:20]   # Top 20 Cluster
    ]

    top3_pct = sum(c["pct"] for c in clusters[:3])

    return {
        "n_total_bars":      n_total,
        "decimal_places":    decimal_places,
        "min_cluster_size":  min_cluster_size,
        "n_clusters":        len(big_clusters),
        "clusters":          clusters,
        "top3_cluster_pct":  float(top3_pct),
        "is_highly_discrete": bool(top3_pct > 50),
    }


# ---------------------------------------------------------------------------
# CALIBRATION RELIABILITY CURVE
# ---------------------------------------------------------------------------

def calibration_curve_data(
    y_true: np.ndarray,
    proba: np.ndarray,
    n_bins: int = 10,
) -> dict[str, Any]:
    """
    Reliability-Curve-Daten: Predicted Probability vs Realized Win-Rate.

    Args:
        y_true: binary labels (0/1) — NICHT triple labels!
        proba: predicted probabilities
        n_bins: number of bins (equal-width zwischen 0 und 1)

    Returns:
        dict mit per-bin Daten — predicted_proba_mean, actual_positive_rate, n_in_bin.
        Plus "ece" (Expected Calibration Error).
    """
    if len(proba) == 0 or len(y_true) != len(proba):
        return {"error": "invalid input"}

    # Equal-width bins between min and max (oder 0/1 falls voll-range)
    edges = np.linspace(proba.min(), proba.max(), n_bins + 1)
    edges[-1] += 1e-9   # damit max-Wert in letzten Bin fällt

    rows = []
    ece_total = 0.0
    n_total = len(proba)
    for i in range(n_bins):
        mask = (proba >= edges[i]) & (proba < edges[i+1])
        n_in_bin = int(mask.sum())
        if n_in_bin == 0:
            continue
        pred_mean = float(proba[mask].mean())
        actual_rate = float(y_true[mask].mean())
        rows.append({
            "bin":                i,
            "edge_low":           float(edges[i]),
            "edge_high":          float(edges[i+1]),
            "n":                  n_in_bin,
            "pct_of_total":       float(n_in_bin / n_total * 100),
            "predicted_mean":     pred_mean,
            "actual_positive":   actual_rate,
            "calibration_gap":   float(actual_rate - pred_mean),
        })
        ece_total += (n_in_bin / n_total) * abs(actual_rate - pred_mean)

    return {
        "n_total":     n_total,
        "n_bins":      n_bins,
        "bins":        rows,
        "ece":         float(ece_total),
        "ece_interpretation": (
            "<0.05: well-calibrated, 0.05-0.10: acceptable, "
            ">0.10: poorly calibrated (model probabilities don't match reality)"
        ),
    }


# ---------------------------------------------------------------------------
# MULTI-SEED CONSISTENCY
# ---------------------------------------------------------------------------

@dataclass
class SeedRunResult:
    """Ein einzelner Trainings-Run mit fixem Seed + deterministic-Flag."""
    seed:              int
    deterministic:     bool
    proba_val_max:     float
    proba_val_q99:     float
    proba_val_q995:    float
    proba_test_max:    float
    proba_test_q99:    float
    cutoff_top1pct:    float        # = proba_val_q99
    n_test_above_q99:  int
    n_test_above_0_4070: int
    n_test_above_0_4096: int


def multi_seed_consistency(
    train_fn: Callable[..., Any],   # accepts: X_train, y_train, X_val, y_val, params → model
    predict_fn: Callable[[Any, np.ndarray], np.ndarray],   # model, X → proba
    X_train: np.ndarray, y_train: np.ndarray,
    X_val:   np.ndarray, y_val:   np.ndarray,
    X_test:  np.ndarray,
    base_params: dict,
    seeds: list[int] = (42, 1, 7),
    deterministic_options: list[bool] = (False, True),
) -> dict[str, Any]:
    """
    Trainiere Modell mit verschiedenen seeds × deterministic-Flags.
    Liefert per-Run Stats + Aggregat (mean/std).

    Returns dict mit:
      "runs":           list of SeedRunResult dicts
      "aggregates":     dict mit mean/std/cv pro Metrik
      "cutoff_drift":   float (max-min des cutoffs über alle Runs)
      "max_proba_drift": float (max-min von proba_test_max)
      "stable_enough":  bool (True wenn cutoff_drift < 0.005 UND max_proba_drift < 0.01)
    """
    runs: list[SeedRunResult] = []

    for det in deterministic_options:
        for seed in seeds:
            params = dict(base_params)
            params["seed"] = seed
            params["deterministic"] = det

            model = train_fn(X_train, y_train, X_val, y_val, params=params)
            p_val  = predict_fn(model, X_val)
            p_test = predict_fn(model, X_test)

            run = SeedRunResult(
                seed=             seed,
                deterministic=    det,
                proba_val_max=    float(p_val.max()),
                proba_val_q99=    float(np.quantile(p_val, 0.99)),
                proba_val_q995=   float(np.quantile(p_val, 0.995)),
                proba_test_max=   float(p_test.max()),
                proba_test_q99=   float(np.quantile(p_test, 0.99)),
                cutoff_top1pct=   float(np.quantile(p_val, 0.99)),
                n_test_above_q99= int((p_test >= np.quantile(p_val, 0.99)).sum()),
                n_test_above_0_4070=int((p_test >= 0.4070).sum()),
                n_test_above_0_4096=int((p_test >= 0.4096).sum()),
            )
            runs.append(run)

    # Aggregate
    cutoffs       = [r.cutoff_top1pct for r in runs]
    max_probas    = [r.proba_test_max for r in runs]
    test_q99s     = [r.proba_test_q99 for r in runs]
    n_above_0_4096 = [r.n_test_above_0_4096 for r in runs]
    n_above_0_4070 = [r.n_test_above_0_4070 for r in runs]

    aggregates = {
        "cutoff_mean":           float(np.mean(cutoffs)),
        "cutoff_std":            float(np.std(cutoffs)),
        "cutoff_cv":             float(np.std(cutoffs) / np.mean(cutoffs)) if np.mean(cutoffs) > 0 else float('nan'),
        "max_proba_mean":        float(np.mean(max_probas)),
        "max_proba_std":         float(np.std(max_probas)),
        "test_q99_mean":         float(np.mean(test_q99s)),
        "test_q99_std":          float(np.std(test_q99s)),
        "n_above_0_4096_mean":   float(np.mean(n_above_0_4096)),
        "n_above_0_4096_std":    float(np.std(n_above_0_4096)),
        "n_above_0_4070_mean":   float(np.mean(n_above_0_4070)),
        "n_above_0_4070_std":    float(np.std(n_above_0_4070)),
    }

    cutoff_drift = max(cutoffs) - min(cutoffs)
    max_proba_drift = max(max_probas) - min(max_probas)

    return {
        "n_runs":             len(runs),
        "seeds":              list(seeds),
        "deterministic_opts": list(deterministic_options),
        "runs":               [r.__dict__ for r in runs],
        "aggregates":         aggregates,
        "cutoff_drift":       float(cutoff_drift),
        "max_proba_drift":    float(max_proba_drift),
        "stable_enough":      bool(cutoff_drift < 0.005 and max_proba_drift < 0.01),
        "interpretation": (
            "stable_enough=True: cutoff variation <0.005, max-proba variation <0.01 → "
            "ANN-012-style fixed cutoff is feasible. "
            "stable_enough=False: model is too stochastic → need frequency-based "
            "calibration (top-N selection) or isotonic-calibration layer (V1.5)."
        ),
    }


# ---------------------------------------------------------------------------
# DETERMINISTIC TOGGLE DIFF
# ---------------------------------------------------------------------------

def deterministic_toggle_diff(
    proba_det_false: np.ndarray,
    proba_det_true:  np.ndarray,
) -> dict[str, Any]:
    """
    Vergleicht zwei Probability-Arrays (gleicher Seed, deterministic on vs off).

    Returns dict mit Correlation, max diff, mean abs diff, Tail-Verschiebung.
    """
    if len(proba_det_false) != len(proba_det_true):
        return {"error": "arrays must have same length"}
    if len(proba_det_false) == 0:
        return {"error": "empty array"}

    diff = proba_det_true - proba_det_false
    return {
        "n":                int(len(proba_det_false)),
        "correlation":      float(np.corrcoef(proba_det_false, proba_det_true)[0, 1]),
        "max_abs_diff":     float(np.abs(diff).max()),
        "mean_abs_diff":    float(np.abs(diff).mean()),
        "rmse":             float(np.sqrt((diff ** 2).mean())),
        "max_proba_false":  float(proba_det_false.max()),
        "max_proba_true":   float(proba_det_true.max()),
        "max_proba_shift":  float(proba_det_true.max() - proba_det_false.max()),
        "q99_false":        float(np.quantile(proba_det_false, 0.99)),
        "q99_true":         float(np.quantile(proba_det_true, 0.99)),
        "q99_shift":        float(np.quantile(proba_det_true, 0.99) - np.quantile(proba_det_false, 0.99)),
    }


# ---------------------------------------------------------------------------
# VERDICT KLASSIFIKATION
# ---------------------------------------------------------------------------

def classify_verdict(
    multi_seed_result:   dict,
    det_toggle_diff:     dict,
    cluster_result:      dict,
    calibration_result:  dict,
) -> dict[str, str]:
    """
    Klassifiziert den Probability-Distribution-Zustand in A/B/C/D.

    A) deterministic=True kaputt: hohe det-toggle-diff (RMSE > 0.01)
       → rollback to seed-only
    B) Distribution generell instabil: cutoff_drift > 0.01 ODER stable_enough=False
       → probability-tiers gefährlich, ANN-012 muss umgeschrieben werden
    C) Distribution stabil aber ultra-discrete: top3_cluster_pct > 50
       → Option A (secondary filters) ist korrekt, aber Cutoff sollte aus
         Multi-Run-Mean abgeleitet werden, nicht Single-Run
    D) Calibration komplett broken: ECE > 0.10
       → isotonic/platt calibration als V1.5 Thema

    Mehrere Kategorien können gleichzeitig zutreffen.
    """
    findings: list[str] = []
    rec: list[str] = []

    if det_toggle_diff.get("rmse", 0) > 0.01:
        findings.append("A: deterministic=True ändert das Modell signifikant (RMSE > 0.01)")
        rec.append("Rollback deterministic=False, nur seed=42 für Reproducibility")

    if not multi_seed_result.get("stable_enough", False):
        findings.append(f"B: Distribution instabil — cutoff_drift={multi_seed_result.get('cutoff_drift'):.4f}, max_proba_drift={multi_seed_result.get('max_proba_drift'):.4f}")
        rec.append("Probability-Tiers für V1 unrobust. Wechsel zu top-N-Selection oder frequency-target Cutoff")

    if cluster_result.get("is_highly_discrete", False):
        findings.append(f"C: Distribution ultra-discrete — top-3 Cluster = {cluster_result.get('top3_cluster_pct', 0):.1f}% aller Bars")
        rec.append("Cluster-Pattern bestätigt → ANN-012 Filter-Stack-Ansatz korrekt, aber Cutoff sollte multi-run-mean sein")

    if calibration_result.get("ece", 0) > 0.10:
        findings.append(f"D: Calibration broken — ECE = {calibration_result.get('ece', 0):.4f}")
        rec.append("Isotonic regression / Platt scaling als V1.5-Thema einplanen")

    if not findings:
        findings.append("✅ Distribution stabil, deterministic okay, kein Cluster-Problem, gut kalibriert")
        rec.append("Aktuelles Setup ist robust — keine Änderungen nötig")

    return {
        "findings":       findings,
        "recommendations": rec,
    }


# ---------------------------------------------------------------------------
# CLUSTER-BASED PREMIUM EXTRACTION (ANN-013 lock)
# ---------------------------------------------------------------------------

def extract_premium_cluster(
    proba: np.ndarray,
    decimal_places: int = 4,
    min_cluster_size_pct: float = 0.5,
) -> dict[str, Any]:
    """
    Extract the highest-value probability cluster that meets a minimum size threshold.

    This is the V1 Premium-Tier-Detection-Mechanik per ANN-013.
    Replaces hardcoded probability thresholds.

    Args:
        proba: probability array (typically from VAL set)
        decimal_places: rounding precision for cluster detection (4dp = standard)
        min_cluster_size_pct: minimum cluster size as % of total bars
                              (e.g. 0.5 means cluster must have >= 0.5% of bars)

    Returns:
        dict with:
            "premium_cluster_value":   float — der gelockte cutoff value
            "premium_cluster_size":    int — anzahl bars in diesem cluster
            "premium_cluster_pct":     float — % of total bars
            "premium_cluster_rank":    int — 0=highest, 1=second-highest, ...
            "all_qualifying_clusters": list[dict] — alle cluster die min_size erfüllen, sortiert nach value DESC
            "rejected_clusters":       list[dict] — cluster die zu klein waren (< min_size)
            "success":                 bool — True wenn mindestens 1 qualifizierender cluster gefunden

    Examples:
        >>> p = np.array([0.3965]*60 + [0.3993]*20 + [0.4018]*15 + [0.4096]*2)
        >>> result = extract_premium_cluster(p, min_cluster_size_pct=2.0)
        >>> result['premium_cluster_value']
        0.4018  # 0.4096 verworfen weil zu klein (nur 2% bei threshold 2%)
    """
    if len(proba) == 0:
        return {"error": "empty array", "success": False}

    n_total = len(proba)
    min_count = max(1, int(n_total * min_cluster_size_pct / 100))

    rounded = np.round(proba, decimal_places)
    counter = Counter(rounded.tolist())

    # Alle clusters (auch kleine) sortiert nach Value absteigend
    all_clusters = sorted(
        [(v, c) for v, c in counter.items()],
        key=lambda x: x[0],
        reverse=True,
    )

    qualifying: list[dict] = []
    rejected: list[dict] = []
    for v, c in all_clusters:
        info = {
            "value":     float(v),
            "count":     int(c),
            "pct":       float(c / n_total * 100),
        }
        if c >= min_count:
            qualifying.append(info)
        else:
            rejected.append(info)

    if not qualifying:
        return {
            "error":          f"no cluster with >= {min_cluster_size_pct}% size",
            "min_count_required": min_count,
            "all_clusters":   [{"value": float(v), "count": int(c)} for v, c in all_clusters[:20]],
            "success":        False,
        }

    # Highest qualifying cluster = Premium
    premium = qualifying[0]
    return {
        "premium_cluster_value":   premium["value"],
        "premium_cluster_size":    premium["count"],
        "premium_cluster_pct":     premium["pct"],
        "premium_cluster_rank":    0,
        "all_qualifying_clusters": qualifying,
        "rejected_clusters":       rejected[:10],
        "n_qualifying":            len(qualifying),
        "min_cluster_size_pct":    min_cluster_size_pct,
        "min_count_required":      min_count,
        "decimal_places":          decimal_places,
        "success":                 True,
    }


def apply_cluster_cutoff_mask(
    proba: np.ndarray,
    cluster_value: float,
    decimal_places: int = 4,
) -> np.ndarray:
    """
    Boolean mask: True where proba is at or above the cluster_value.

    Uses rounded-comparison to match the cluster-detection rounding.
    Equivalent to "this bar is in the premium-cluster or higher".
    """
    rounded = np.round(proba, decimal_places)
    return rounded >= cluster_value


def cluster_stability_test_multi_seed(
    train_fn: Callable[..., Any],
    predict_fn: Callable[[Any, np.ndarray], np.ndarray],
    X_train: np.ndarray, y_train: np.ndarray,
    X_val:   np.ndarray, y_val:   np.ndarray,
    base_params: dict,
    seeds: list[int] = (42, 1, 7),
    min_cluster_size_pct: float = 0.5,
    decimal_places: int = 4,
) -> dict[str, Any]:
    """
    Trainiere Modell mit verschiedenen seeds und extrahiere höchsten Premium-Cluster.
    Test ob der Cluster-Value stabil bleibt (mean ± std).

    Returns dict mit:
      "per_seed_results": list of {seed, premium_cluster_value, premium_cluster_pct, ...}
      "cluster_values":   list of premium-cluster values across seeds
      "value_mean":       float
      "value_std":        float
      "value_drift":      float (max - min)
      "is_stable":        bool (drift < 0.001 — ANN-013 requirement)
      "interpretation":   str
    """
    results = []
    for seed in seeds:
        params = dict(base_params)
        params["seed"] = seed
        model = train_fn(X_train, y_train, X_val, y_val, params=params)
        proba_val = predict_fn(model, X_val)
        extraction = extract_premium_cluster(
            proba_val, decimal_places=decimal_places,
            min_cluster_size_pct=min_cluster_size_pct,
        )
        results.append({
            "seed":                  seed,
            "success":               extraction.get("success", False),
            "premium_cluster_value": extraction.get("premium_cluster_value"),
            "premium_cluster_pct":   extraction.get("premium_cluster_pct"),
            "n_qualifying_clusters": extraction.get("n_qualifying", 0),
        })

    successful = [r for r in results if r["success"]]
    if not successful:
        return {
            "per_seed_results": results,
            "is_stable":        False,
            "error":            "no successful cluster extraction in any seed",
        }

    values = [r["premium_cluster_value"] for r in successful]
    drift = max(values) - min(values)

    return {
        "per_seed_results":  results,
        "cluster_values":    values,
        "value_mean":        float(np.mean(values)),
        "value_std":         float(np.std(values)),
        "value_drift":       float(drift),
        "n_runs":            len(successful),
        "is_stable":         bool(drift < 0.001),
        "interpretation": (
            f"Cluster stability: drift={drift:.4f}, std={np.std(values):.4f}. "
            f"is_stable=True wenn drift < 0.001 — ANN-013 Lock-Requirement."
        ),
    }

