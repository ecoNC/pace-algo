"""
Product-orientierte Metriken für PaceAlgo Modell-Evaluation.

Klassische Quant-Metriken (PF/WR/MDD) sagen "ist das Modell statistisch gut?".
Diese Metriken sagen "wie fühlt sich das im Pine-Chart an?". Sie sind die
Brücke von Backtest-Tabelle zu User-Experience.

Verwendet ab NB14 (Multi-TF Deep Dive) und in allen späteren Produkt-Notebooks.

Design-Prinzipien (per Nico 2026-05-27):
  - Stability > maximaler PF
  - Konsistenz > Peak-Ergebnisse
  - Produktqualität > reine Quant-Optimierung
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# BARS-PER-DAY MAPPING (für TF-normalisierte Frequenz-Metriken)
# ---------------------------------------------------------------------------
# FX-Markt: 24/5 (Mo–Fr 24h) → ~120h/Woche
# Crypto-Markt: 24/7 → ~168h/Woche
# Wir nutzen 24h/Tag als Normierung (vereinfacht; FX-Trades laufen nur Mo–Fr)
TF_BARS_PER_DAY: dict[str, int] = {
    "5m":  288,   # 24 * 60 / 5
    "15m": 96,
    "30m": 48,
    "1h":  24,
    "4h":  6,
    "1d":  1,
}


# ---------------------------------------------------------------------------
# SIGNAL-FREQUENZ
# ---------------------------------------------------------------------------

def signals_per_day(
    n_signals: int,
    n_bars: int,
    tf: str,
    n_symbols: int = 1,
) -> float:
    """
    Durchschnittliche Signale pro Tag pro Symbol.

    Args:
        n_signals: Anzahl Signale im Eval-Zeitraum (alle Symbole zusammen)
        n_bars: Anzahl Bars im Eval-Zeitraum (alle Symbole zusammen)
        tf: Timeframe-String ("5m", "15m", ...)
        n_symbols: Anzahl Symbole im Pool

    Returns:
        Mittlere Signale pro Tag pro Symbol.
    """
    if n_bars == 0 or n_symbols == 0:
        return 0.0
    bars_per_day = TF_BARS_PER_DAY.get(tf, 24)
    days = n_bars / (bars_per_day * n_symbols)
    if days <= 0:
        return 0.0
    return n_signals / (days * n_symbols)


def signal_density(n_signals: int, n_bars: int) -> float:
    """Anteil aller Bars die ein Signal sind. Premium soll < 1.5% sein."""
    if n_bars == 0:
        return 0.0
    return n_signals / n_bars


# ---------------------------------------------------------------------------
# TRADE-DURATION
# ---------------------------------------------------------------------------

def trade_duration_stats(hit_bar_offsets: pd.Series | np.ndarray) -> dict[str, float]:
    """
    Statistik wie lange Trades offen sind (in Bars), aus Triple-Barrier-Labels.

    Erwartet die `hit_bar_offset`-Spalte aus core/labeling/triple_barrier.py:
      - 1..N = TP oder SL nach N Bars getroffen
      - == time_barrier_bars = Time-Barrier (oft 24)

    Returns:
        dict mit mean, median, p25, p75, min, max, share_short (< 3 bars),
        share_long (> 24 bars).
    """
    vals = np.asarray(hit_bar_offsets)
    vals = vals[~np.isnan(vals)] if vals.dtype == float else vals
    vals = vals[vals > 0]  # Filter negative/0 (kein Trade)
    if len(vals) == 0:
        return {
            "mean": 0.0, "median": 0.0,
            "p25": 0.0, "p75": 0.0,
            "min": 0.0, "max": 0.0,
            "share_short": 0.0, "share_long": 0.0,
            "n_trades": 0,
        }
    return {
        "mean":         float(np.mean(vals)),
        "median":       float(np.median(vals)),
        "p25":          float(np.percentile(vals, 25)),
        "p75":          float(np.percentile(vals, 75)),
        "min":          float(np.min(vals)),
        "max":          float(np.max(vals)),
        "share_short":  float(np.mean(vals < 3)),
        "share_long":   float(np.mean(vals > 24)),
        "n_trades":     int(len(vals)),
    }


# ---------------------------------------------------------------------------
# ALERT-FREQUENZ
# ---------------------------------------------------------------------------

def alert_frequency(
    signal_mask: np.ndarray,
    timestamps: pd.DatetimeIndex,
    granularity: str = "hour",
) -> pd.Series:
    """
    Wie verteilen sich Signale über die Zeit?

    Returns: Anzahl Signale pro Bucket (Stunde/Tag/Woche).
    """
    sig_idx = timestamps[signal_mask.astype(bool)]
    if len(sig_idx) == 0:
        return pd.Series(dtype=int)
    if granularity == "hour":
        return sig_idx.to_series().groupby(sig_idx.hour).size()
    if granularity == "weekday":
        return sig_idx.to_series().groupby(sig_idx.dayofweek).size()
    if granularity == "day":
        return sig_idx.to_series().groupby(sig_idx.date).size()
    raise ValueError(f"unknown granularity: {granularity}")


def max_burst_signals_per_hour(signal_mask: np.ndarray, timestamps: pd.DatetimeIndex) -> int:
    """Maximale Anzahl Signale die je in 1h auftraten. Indikator für Alert-Burst-Risiko."""
    sig_idx = timestamps[signal_mask.astype(bool)]
    if len(sig_idx) == 0:
        return 0
    hour_counts = sig_idx.to_series().groupby(sig_idx.floor("h")).size()
    return int(hour_counts.max())


# ---------------------------------------------------------------------------
# SESSION DEPENDENCY
# ---------------------------------------------------------------------------

# FX-Session-Windows (UTC) — match core/features/session.py
SESSIONS_UTC = {
    "asia":      (23, 8),    # 23:00 – 08:00 (wrap-around)
    "london":    (8, 17),
    "ny":        (13, 22),
    "ldn_ny_kz": (13, 17),   # Killzone
}


def _hour_in_session(hour: int, window: tuple[int, int]) -> bool:
    lo, hi = window
    if lo < hi:
        return lo <= hour < hi
    # wrap-around (e.g. 23 – 8)
    return hour >= lo or hour < hi


def session_share(signal_mask: np.ndarray, timestamps: pd.DatetimeIndex) -> dict[str, float]:
    """
    Anteil aller Signale pro Session.

    Returns: dict {session_name: share (0..1)}.
    Wenn z.B. {"ldn_ny_kz": 0.75} → 75% der Signale im LDN/NY-Killzone =
    starke Session-Abhängigkeit → schlecht für 24/5-Marketing-Story.
    """
    sig_idx = timestamps[signal_mask.astype(bool)]
    n = len(sig_idx)
    if n == 0:
        return {s: 0.0 for s in SESSIONS_UTC}
    hours = sig_idx.hour
    out = {}
    for name, window in SESSIONS_UTC.items():
        count = int(sum(_hour_in_session(int(h), window) for h in hours))
        out[name] = count / n
    return out


def session_dependency_score(session_shares: dict[str, float]) -> float:
    """
    Maximaler Session-Anteil. Hoch = schlechte Verteilung (über-konzentriert).
    Niedrig = balanciert über alle Sessions.

    Heuristik:
      < 0.40 → balanciert (Edge generalisiert über Sessions)
      0.40 – 0.65 → akzeptabel
      > 0.65 → über-abhängig von einer Session
    """
    if not session_shares:
        return 0.0
    # Asia/London/NY (Killzone excluded — ist Subset)
    primary = {k: v for k, v in session_shares.items() if k != "ldn_ny_kz"}
    if not primary:
        return 0.0
    return float(max(primary.values()))


# ---------------------------------------------------------------------------
# CHART CLEANLINESS
# ---------------------------------------------------------------------------

def chart_cleanliness(
    signal_mask: np.ndarray,
    hit_bar_offsets: np.ndarray,
    window_bars: int = 200,
) -> dict[str, float]:
    """
    Wie viele aktive (noch nicht aufgelöste) Trade-Boxen wären im sichtbaren
    Chart-Fenster gleichzeitig zu sehen?

    Approximation: Für jedes Signal sind die nächsten `hit_bar_offset` Bars
    aktiv. Wir zählen pro Position wie viele aktive Trades es gibt → max.
    """
    n = len(signal_mask)
    if n == 0:
        return {"max_overlapping": 0, "mean_overlapping": 0.0,
                "boxes_per_window": 0.0}

    active = np.zeros(n, dtype=int)
    for i in range(n):
        if not signal_mask[i]:
            continue
        offset = int(hit_bar_offsets[i]) if not np.isnan(hit_bar_offsets[i]) else 24
        end = min(n, i + offset + 1)
        active[i:end] += 1

    boxes_per_window = float(np.mean(np.convolve(
        signal_mask.astype(int),
        np.ones(window_bars, dtype=int),
        mode="valid"
    )))

    return {
        "max_overlapping":  int(active.max()),
        "mean_overlapping": float(active.mean()),
        "boxes_per_window": boxes_per_window,
    }


# ---------------------------------------------------------------------------
# PINE UX PRACTICALITY
# ---------------------------------------------------------------------------

def pine_ux_score(
    tf: str,
    n_features: int,
    n_trees: int,
    tree_depth: int,
    requests_security_count: int,
    pine_budget: dict,
) -> dict[str, float]:
    """
    Approximation der Pine-Last für diesen TF.

    Returns:
        - ops_per_bar_estimate
        - budget_utilization (0–1)
        - request_security_utilization (0–1)
        - feasibility_score (0–1) — komposit
    """
    # grobe Operations-Schätzung: features + tree-traversals + bookkeeping
    ops_features = n_features * 6          # ~6 ops pro Feature (typische Formel)
    ops_trees = n_trees * (tree_depth + 2)
    ops_overhead = 30                      # tier check, draw boxes etc.
    ops_total = ops_features + ops_trees + ops_overhead

    budget_util = ops_total / pine_budget.get("max_operations_bar", 5000)
    rs_util = requests_security_count / pine_budget.get("max_request_security", 12)
    feas = max(0.0, 1.0 - max(budget_util, rs_util))

    return {
        "tf":                              tf,
        "ops_per_bar_estimate":            int(ops_total),
        "budget_utilization":              float(budget_util),
        "request_security_utilization":    float(rs_util),
        "feasibility_score":               float(feas),
    }


# ---------------------------------------------------------------------------
# COMPOSITE
# ---------------------------------------------------------------------------

def compute_product_metrics_bundle(
    proba: np.ndarray,
    threshold: float,
    timestamps: pd.DatetimeIndex,
    hit_bar_offsets: np.ndarray,
    tf: str,
    n_symbols: int,
) -> dict[str, float | dict]:
    """
    One-shot: berechne alle Produkt-Metriken für eine (TF, Tier)-Kombo.

    Args:
        proba: Modell-Wahrscheinlichkeiten, aligned zu timestamps
        threshold: Tier-Cutoff (z.B. premium_cutoff)
        timestamps: pd.DatetimeIndex zur Position-Auflösung
        hit_bar_offsets: aus Triple-Barrier
        tf: timeframe string
        n_symbols: Anzahl Symbole im Pool (für signals/day Normalisierung)

    Returns: flat dict mit allen Produkt-Metriken.
    """
    mask = proba >= threshold
    n_signals = int(mask.sum())
    n_bars = len(proba)

    out: dict[str, float | dict] = {}
    out["signals_per_day_per_symbol"] = signals_per_day(n_signals, n_bars, tf, n_symbols)
    out["signal_density"]              = signal_density(n_signals, n_bars)
    out["max_burst_per_hour"]          = max_burst_signals_per_hour(mask, timestamps)
    out["alert_freq_hour"]             = alert_frequency(mask, timestamps, "hour").to_dict()
    out["alert_freq_weekday"]          = alert_frequency(mask, timestamps, "weekday").to_dict()
    out["session_shares"]              = session_share(mask, timestamps)
    out["session_dependency"]          = session_dependency_score(out["session_shares"])
    out["trade_duration"]              = trade_duration_stats(hit_bar_offsets[mask] if len(hit_bar_offsets) == len(mask) else hit_bar_offsets)
    out["chart_cleanliness"]           = chart_cleanliness(mask, hit_bar_offsets if len(hit_bar_offsets) == len(mask) else np.zeros(len(mask)))

    return out


def evaluate_product_thresholds(
    product_metrics: dict,
    thresholds: dict,
    tier: str = "premium",
) -> dict[str, bool | str]:
    """
    Vergleicht berechnete Produkt-Metriken gegen PRODUCT_METRIC_THRESHOLDS.

    Returns: pass/fail per Metric + Gesamt-Verdict.
    """
    checks = {}

    sigs = product_metrics.get("signals_per_day_per_symbol", 0.0)
    if tier == "premium":
        lo = thresholds["signals_per_day_premium_min"]
        hi = thresholds["signals_per_day_premium_max"]
        checks["signals_per_day_in_range"] = lo <= sigs <= hi
    elif tier == "high":
        lo = thresholds["signals_per_day_high_min"]
        hi = thresholds["signals_per_day_high_max"]
        checks["signals_per_day_in_range"] = lo <= sigs <= hi

    density = product_metrics.get("signal_density", 0.0)
    if tier == "premium":
        checks["premium_density_ok"] = density <= thresholds["premium_density_max"]

    td = product_metrics.get("trade_duration", {})
    if td and td.get("n_trades", 0) > 0:
        mean_dur = td.get("mean", 0.0)
        checks["trade_duration_in_range"] = (
            thresholds["trade_duration_min_bars"] <= mean_dur <= thresholds["trade_duration_max_bars"]
        )

    chart = product_metrics.get("chart_cleanliness", {})
    if chart:
        checks["chart_clean"] = (
            chart.get("max_overlapping", 0) <= thresholds["max_overlapping_signals"]
            and chart.get("boxes_per_window", 0) <= thresholds["max_boxes_visible_window"]
        )

    session_dep = product_metrics.get("session_dependency", 0.0)
    checks["session_balanced"] = session_dep <= thresholds["max_signal_share_single_session"]

    # Verdict
    n_pass = sum(1 for v in checks.values() if v)
    n_total = len(checks)
    if n_total == 0:
        verdict = "no_data"
    elif n_pass == n_total:
        verdict = "product_grade_A"
    elif n_pass >= n_total - 1:
        verdict = "product_grade_B"
    elif n_pass >= n_total - 2:
        verdict = "product_grade_C"
    else:
        verdict = "product_grade_F"

    return {**checks, "n_pass": n_pass, "n_total": n_total, "verdict": verdict}
