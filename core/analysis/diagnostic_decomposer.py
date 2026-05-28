"""
Diagnostic Decomposer — Pair-/Symbol-Inversion-Diagnose.

Klassen-agnostisch designed: nimmt proba + labels + timestamps + optional
Macro-Series und gibt confidence-scored Diagnose-Report zurück.

Verwendet ab NB15a (D.1 USDCHF Deep-Dive, ANN-016 Phase D).
Per ANN-016 Lock 2 (Replicable-Blueprint-Design) als wiederverwendbares
Modul gebaut — V2-Modelle (Crypto/Indices/Commodity) nutzen dieselbe
Diagnose-Pipeline wenn einzelne Symbole/Pairs brechen.

WICHTIG (ANN-016 Lock 5): Dieses Modul DIAGNOSTIZIERT nur — es
implementiert NIEMALS Overrides. Overrides leben in einem separaten
Modul (`core/router/pair_override_registry.py`) und brauchen alle 4
Discipline-Kriterien (statistical / structural / OOS / reproducible).
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# SESSION DEFINITIONS (UTC)
# ---------------------------------------------------------------------------
SESSIONS_UTC = {
    "asia":      (23, 8),    # 23:00 – 08:00 wrap
    "london":    (8, 17),
    "ny":        (13, 22),
    "ldn_ny_kz": (13, 17),   # Killzone overlap
    "eu_open":   (7, 9),     # EU open ramp
    "us_close":  (20, 22),   # NY close ramp
}


def _hour_in_window(hour: int, window: tuple[int, int]) -> bool:
    lo, hi = window
    if lo < hi:
        return lo <= hour < hi
    return hour >= lo or hour < hi   # wrap-around


# ---------------------------------------------------------------------------
# METRICS HELPER
# ---------------------------------------------------------------------------
def _pf_wr_n(labels_triple: np.ndarray, R: float = 1.5) -> dict:
    if len(labels_triple) == 0:
        return {"pf": 0.0, "wr": 0.0, "n": 0, "wins": 0, "losses": 0}
    wins = int((labels_triple == 1).sum())
    losses = int((labels_triple == -1).sum())
    n = wins + losses + int((labels_triple == 0).sum())
    pf = (wins * R) / losses if losses > 0 else (float("inf") if wins > 0 else 0.0)
    wr = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    return {"pf": float(pf), "wr": float(wr), "n": int(n),
            "wins": int(wins), "losses": int(losses)}


# ---------------------------------------------------------------------------
# SECTION 2 — PER-SESSION PERFORMANCE DECOMPOSITION
# ---------------------------------------------------------------------------
def per_session_metrics(
    timestamps: pd.DatetimeIndex,
    signal_mask: np.ndarray,
    labels_triple: np.ndarray,
    R: float = 1.5,
    sessions: dict | None = None,
) -> pd.DataFrame:
    """
    PF/WR/n_trades pro Session aus signal_mask.

    Args:
        timestamps: aligned zu signal_mask + labels_triple
        signal_mask: bool array (True = Signal an Bar t)
        labels_triple: -1/0/+1 (triple-barrier output)
        R: TP/SL ratio

    Returns: DataFrame mit Spalten [session, pf, wr, n, wins, losses, share_of_total]
    """
    sessions = sessions or SESSIONS_UTC
    hours = np.asarray(timestamps.hour)
    signal_mask = np.asarray(signal_mask).astype(bool)
    labels_triple = np.asarray(labels_triple)

    rows = []
    total_n = int(signal_mask.sum())
    for name, window in sessions.items():
        in_session = np.array([_hour_in_window(int(h), window) for h in hours])
        sub_mask = signal_mask & in_session
        labs = labels_triple[sub_mask]
        m = _pf_wr_n(labs, R)
        m["session"] = name
        m["share_of_total"] = (m["n"] / total_n) if total_n > 0 else 0.0
        rows.append(m)
    return pd.DataFrame(rows)[["session", "pf", "wr", "n", "wins", "losses", "share_of_total"]]


# ---------------------------------------------------------------------------
# SECTION 3 — MARGINAL CONTRIBUTION ANALYSIS (4-Kombo Filter-Ablation)
# ---------------------------------------------------------------------------
def filter_marginal_contributions(
    proba: np.ndarray,
    cluster_cutoff: float,
    timestamps: pd.DatetimeIndex,
    labels_triple: np.ndarray,
    htf_confirm_mask: np.ndarray,
    session_mask: np.ndarray,
    R: float = 1.5,
) -> pd.DataFrame:
    """
    Echte 2x2-Ablation des Filter-Stacks auf Premium-Cutoff-Basis:

    1. Base               — proba >= cluster_cutoff (kein Filter)
    2. +HTF only          — base AND htf_confirm
    3. +Session only      — base AND session
    4. +HTF + Session     — base AND htf_confirm AND session  (Full Conservative)

    Args:
        proba: model probabilities (aligned to timestamps)
        cluster_cutoff: Premium-Cluster-Cutoff (z.B. 0.40 für seed=7)
        timestamps: pd.DatetimeIndex
        labels_triple: -1/0/+1
        htf_confirm_mask: bool array — True wo HTF-Confirmation feuert
        session_mask: bool array — True wo Session-Filter (z.B. NY) erfüllt
        R: TP/SL ratio

    Returns: DataFrame mit Spalten
        [config, n, pf, wr, wins, losses, sigs_per_day_pct_of_base]
        plus delta-Spalten gegenüber Base.
    """
    proba = np.asarray(proba)
    labels_triple = np.asarray(labels_triple)
    htf = np.asarray(htf_confirm_mask).astype(bool)
    sess = np.asarray(session_mask).astype(bool)

    base_mask = proba >= cluster_cutoff

    configs = {
        "base":           base_mask,
        "base_+htf":      base_mask & htf,
        "base_+session":  base_mask & sess,
        "base_+htf_+sess": base_mask & htf & sess,
    }

    rows = []
    base_n = int(base_mask.sum())
    base_pf = _pf_wr_n(labels_triple[base_mask], R)["pf"]
    base_wr = _pf_wr_n(labels_triple[base_mask], R)["wr"]
    for name, mask in configs.items():
        labs = labels_triple[mask]
        m = _pf_wr_n(labs, R)
        m["config"] = name
        m["pct_of_base"] = (m["n"] / base_n) if base_n > 0 else 0.0
        m["pf_delta_vs_base"] = m["pf"] - base_pf
        m["wr_delta_vs_base"] = m["wr"] - base_wr
        rows.append(m)
    return pd.DataFrame(rows)[[
        "config", "n", "pf", "wr", "wins", "losses",
        "pct_of_base", "pf_delta_vs_base", "wr_delta_vs_base",
    ]]


# ---------------------------------------------------------------------------
# SECTION 4 — CONDITIONED SHAP
# ---------------------------------------------------------------------------
def conditioned_shap_extract(
    shap_values: np.ndarray,
    feature_names: list[str],
    condition_mask: np.ndarray,
    top_k: int = 15,
) -> pd.DataFrame:
    """
    SHAP-Statistik nur auf der durch `condition_mask` selektierten Subset.

    Args:
        shap_values: shape (N, F) — pre-computed SHAP values aligned to feature_names
        feature_names: list[str], length F
        condition_mask: bool array length N — True für Bars die in die Auswertung gehen
        top_k: zurückgegebene Top-Features

    Returns: DataFrame mit Spalten [feature, mean_abs_shap, mean_signed_shap, n_samples]
        sortiert nach mean_abs_shap descending.
    """
    cm = np.asarray(condition_mask).astype(bool)
    if cm.sum() == 0:
        return pd.DataFrame(columns=["feature", "mean_abs_shap", "mean_signed_shap", "n_samples"])
    sub = shap_values[cm]
    abs_mean = np.abs(sub).mean(axis=0)
    signed_mean = sub.mean(axis=0)
    df = pd.DataFrame({
        "feature": feature_names,
        "mean_abs_shap": abs_mean,
        "mean_signed_shap": signed_mean,
        "n_samples": int(cm.sum()),
    })
    return df.sort_values("mean_abs_shap", ascending=False).head(top_k).reset_index(drop=True)


def shap_delta(
    shap_a: pd.DataFrame, shap_b: pd.DataFrame,
    label_a: str = "A", label_b: str = "B",
) -> pd.DataFrame:
    """
    Vergleicht zwei SHAP-Tabellen (winning vs losing, NY vs LDN, ...).
    Returns sorted by absolute delta in mean_signed_shap (largest divergence first).
    """
    a = shap_a.set_index("feature")
    b = shap_b.set_index("feature")
    merged = a[["mean_abs_shap", "mean_signed_shap"]].join(
        b[["mean_abs_shap", "mean_signed_shap"]],
        lsuffix=f"_{label_a}", rsuffix=f"_{label_b}", how="outer",
    ).fillna(0.0)
    merged["abs_delta"]   = merged[f"mean_abs_shap_{label_a}"]    - merged[f"mean_abs_shap_{label_b}"]
    merged["signed_delta"] = merged[f"mean_signed_shap_{label_a}"] - merged[f"mean_signed_shap_{label_b}"]
    merged = merged.reset_index()
    return merged.reindex(merged["signed_delta"].abs().sort_values(ascending=False).index).reset_index(drop=True)


# ---------------------------------------------------------------------------
# SECTION 5 — VOL-REGIME CLASSIFIER (percentile-basiert)
# ---------------------------------------------------------------------------
def vol_regime_percentile(
    atr_pct_series: np.ndarray,
    low_pctile: float = 0.30,
    high_pctile: float = 0.70,
    use_rolling: bool = False,
    rolling_window: int = 500,
) -> np.ndarray:
    """
    Klassifiziert ATR-Series in 'low'/'mid'/'high' Vol-Regime.

    Args:
        atr_pct_series: numerische Series (ATR%, realized_vol_20, oder atr_percentile_100)
        low_pctile: untere Schwelle (default 30%)
        high_pctile: obere Schwelle (default 70%)
        use_rolling: wenn True, rolling-Percentile statt global. Verhindert
                     dass eine high-vol Phase in 2020 alle low-vol Phasen
                     in 2024 als "extreme" markiert.
        rolling_window: nur relevant wenn use_rolling=True

    Returns: ndarray same length, values in {'low', 'mid', 'high', 'unknown'}
    """
    s = np.asarray(atr_pct_series, dtype=float)
    n = len(s)
    out = np.full(n, "unknown", dtype=object)

    if not use_rolling:
        valid = s[~np.isnan(s)]
        if len(valid) == 0:
            return out
        lo = np.quantile(valid, low_pctile)
        hi = np.quantile(valid, high_pctile)
        out[s <= lo] = "low"
        out[(s > lo) & (s < hi)] = "mid"
        out[s >= hi] = "high"
        out[np.isnan(s)] = "unknown"
    else:
        ser = pd.Series(s)
        lo_roll = ser.rolling(rolling_window, min_periods=max(50, rolling_window // 4)).quantile(low_pctile)
        hi_roll = ser.rolling(rolling_window, min_periods=max(50, rolling_window // 4)).quantile(high_pctile)
        for i in range(n):
            if np.isnan(s[i]) or np.isnan(lo_roll.iloc[i]) or np.isnan(hi_roll.iloc[i]):
                continue
            if s[i] <= lo_roll.iloc[i]:
                out[i] = "low"
            elif s[i] >= hi_roll.iloc[i]:
                out[i] = "high"
            else:
                out[i] = "mid"
    return out


def per_regime_metrics(
    regimes: np.ndarray,
    signal_mask: np.ndarray,
    labels_triple: np.ndarray,
    R: float = 1.5,
    regime_labels: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """
    PF/WR/n pro Regime-Label. Generic — funktioniert für Vol-Regimes
    (low/mid/high), Macro-Regimes (bull/bear/sideways) oder beliebige
    andere Labels.

    Bug-Fix 2026-05-28 (NB15a): vorher hardcoded ('low', 'mid', 'high', 'unknown'),
    was DXY-Regime ('bull', 'bear', 'sideways') nie matchte → alle 0/0/0.
    Jetzt: regime_labels optional — wenn None, werden unique values aus dem
    Array verwendet.
    """
    if regime_labels is None:
        # auto-detect unique labels (sortiert für Konsistenz)
        regime_labels = tuple(sorted(set(regimes.tolist())))
    rows = []
    total_n = int(signal_mask.sum())
    for r in regime_labels:
        sub_mask = signal_mask & (regimes == r)
        labs = labels_triple[sub_mask]
        m = _pf_wr_n(labs, R)
        m["regime"] = r
        m["share_of_signals"] = (m["n"] / total_n) if total_n > 0 else 0.0
        rows.append(m)
    return pd.DataFrame(rows)[["regime", "pf", "wr", "n", "wins", "losses", "share_of_signals"]]


def filter_interaction_score(marginal_df: pd.DataFrame) -> dict:
    """
    Misst ob die HTF + Session Filter additiv oder destruktiv sind.

    Definition (per Nico-Direktive 2026-05-28):
        interaction_score = both_pf - max(htf_pf, session_pf)

    Interpretation:
        > +0.1  : additiv (Filter verstärken sich)
        -0.1 to +0.1 : neutral (Filter unabhängig)
        < -0.1  : destruktiv (Filter heben sich auf)

    Args:
        marginal_df: Output von filter_marginal_contributions() (pro Pair)

    Returns: dict mit
        - base_pf, htf_pf, session_pf, both_pf
        - max_single_pf
        - interaction_score
        - lift_vs_base   (both_pf - base_pf, der "Stack-Total-Lift")
        - verdict        ('additive' | 'neutral' | 'destructive')
    """
    by_config = marginal_df.set_index("config")
    base_pf    = float(by_config.loc["base",            "pf"]) if "base"            in by_config.index else 0.0
    htf_pf     = float(by_config.loc["base_+htf",       "pf"]) if "base_+htf"       in by_config.index else 0.0
    session_pf = float(by_config.loc["base_+session",   "pf"]) if "base_+session"   in by_config.index else 0.0
    both_pf    = float(by_config.loc["base_+htf_+sess", "pf"]) if "base_+htf_+sess" in by_config.index else 0.0

    max_single = max(htf_pf, session_pf)
    interaction = both_pf - max_single
    lift_vs_base = both_pf - base_pf

    if interaction > 0.10:
        verdict = "additive"
    elif interaction < -0.10:
        verdict = "destructive"
    else:
        verdict = "neutral"

    return {
        "base_pf":           base_pf,
        "htf_pf":            htf_pf,
        "session_pf":        session_pf,
        "both_pf":           both_pf,
        "max_single_pf":     max_single,
        "interaction_score": interaction,
        "lift_vs_base":      lift_vs_base,
        "verdict":           verdict,
    }


# ---------------------------------------------------------------------------
# SECTION 7 — MACRO REGIME ANNOTATOR (DXY / VIX / etc.)
# ---------------------------------------------------------------------------
def macro_regime_annotator(
    timestamps: pd.DatetimeIndex,
    macro_series: pd.Series,
    rolling_days: int = 20,
    bull_threshold: float = 0.02,   # +2% rolling change → bull
    bear_threshold: float = -0.02,  # -2% rolling change → bear
) -> np.ndarray:
    """
    Klassifiziert Macro-Series in 'bull'/'bear'/'sideways' basierend auf
    rolling N-day change.

    Args:
        timestamps: intraday DatetimeIndex
        macro_series: daily macro values (DXY-close, VIX-close, etc.)
                       wird auf intraday-index forward-filled
        rolling_days: window für % change calculation

    Returns: ndarray same length as timestamps in {'bull', 'bear', 'sideways', 'unknown'}
    """
    if macro_series.empty:
        return np.full(len(timestamps), "unknown", dtype=object)

    macro = macro_series.copy()
    macro.index = macro.index.normalize() if isinstance(macro.index, pd.DatetimeIndex) else macro.index
    macro = macro.groupby(macro.index).last().sort_index().ffill()
    macro_change = macro.pct_change(rolling_days)
    macro_change = macro_change.shift(1)   # anti-look-ahead — gestern's change ist Wert für heute

    # forward-fill auf intraday
    macro_ff = macro_change.reindex(timestamps.union(macro_change.index)).sort_index().ffill()
    macro_ff = macro_ff.reindex(timestamps)

    out = np.full(len(timestamps), "unknown", dtype=object)
    vals = macro_ff.values
    out[vals > bull_threshold] = "bull"
    out[vals < bear_threshold] = "bear"
    out[(vals >= bear_threshold) & (vals <= bull_threshold)] = "sideways"
    return out


# ---------------------------------------------------------------------------
# CORRELATION CHECK
# ---------------------------------------------------------------------------
def rolling_correlation(
    series_a: pd.Series,
    series_b: pd.Series,
    window: int = 100,
) -> pd.Series:
    """Rolling Pearson correlation auf gleicher Frequenz (Resampling vor Aufruf)."""
    aligned = pd.concat([series_a, series_b], axis=1, join="inner").dropna()
    if aligned.empty or len(aligned) < window:
        return pd.Series(dtype=float)
    a, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    return a.rolling(window).corr(b)


# ---------------------------------------------------------------------------
# SECTION 8 — AUTO-DIAGNOSE-ENGINE (Confidence-Scored)
# ---------------------------------------------------------------------------
def diagnose_pair_inversion(
    per_session_df: pd.DataFrame,
    marginal_df: pd.DataFrame,
    per_regime_df: pd.DataFrame,
    shap_winning_vs_losing: pd.DataFrame | None,
    per_macro_regime_df: pd.DataFrame | None = None,
) -> dict:
    """
    Bewertet konkurrierende Hypothesen für eine Pair-Inversion mit
    Confidence-Scores (0.0 – 1.0). Höhere Werte = stärkere Evidenz.

    Hypothesen:
        session_mismatch:        Edge nur in 1-2 Sessions konzentriert, in
                                  anderen invertiert
        htf_filter_interaction:  HTF-Confirm-Filter zerstört Edge spezifisch
        session_filter_inversion: NY-Session-Filter macht es schlechter
        regime_dependency:       Edge nur in einem Vol-Regime, invertiert in anderen
        macro_regime_dependency: Edge an DXY/VIX-Regime gebunden, invertiert
                                  in gegenteiliger Phase
        feature_signature_diff:  SHAP-Top-Features unterscheiden sich stark
                                  zwischen Winning und Losing
        structural_pair_issue:   "None of the above" — fundamentale Pair-Eigenheit
                                  die wir mit aktuellen Features nicht erfassen

    Confidence-Berechnung ist heuristisch (siehe Code-Kommentare). Keine
    Statistik-Inferenz — die liefert die separate Section in Notebook.

    Returns: dict mit
        - hypothesis_scores: dict[str, float]
        - top_hypothesis: str (höchster Score)
        - notes: list[str] — menschenlesbare Begründungen
    """
    scores: dict[str, float] = {}
    notes: list[str] = []

    # === session_mismatch ===
    # Session mit höchstem PF vs niedrigstem PF — wie weit auseinander?
    primary_sessions = per_session_df[per_session_df["session"].isin(["asia", "london", "ny"])].copy()
    primary_sessions = primary_sessions[primary_sessions["n"] >= 30]
    if len(primary_sessions) >= 2:
        pf_max = primary_sessions["pf"].replace([np.inf], 5.0).max()
        pf_min = primary_sessions["pf"].min()
        sigma = pf_max - pf_min
        score = min(1.0, max(0.0, (sigma - 0.5) / 1.5))   # delta 0.5 → 0, delta 2.0+ → 1.0
        # Boost wenn Min-PF unter 1.0 (echte Inversion in einer Session)
        if pf_min < 1.0:
            score = min(1.0, score + 0.2)
        scores["session_mismatch"] = round(score, 3)
        notes.append(f"session_mismatch: PF range across primary sessions = {pf_min:.2f}–{pf_max:.2f} (Δ={sigma:.2f})")

    # === htf_filter_interaction ===
    # Vergleicht base vs base_+htf — wenn HTF die Edge zerstört
    if "config" in marginal_df.columns and len(marginal_df) >= 4:
        base_pf = marginal_df[marginal_df["config"] == "base"]["pf"].values[0] if len(marginal_df[marginal_df["config"] == "base"]) else 0
        htf_pf = marginal_df[marginal_df["config"] == "base_+htf"]["pf"].values[0] if len(marginal_df[marginal_df["config"] == "base_+htf"]) else 0
        delta_htf = htf_pf - base_pf
        # negative delta = HTF macht es schlechter
        if delta_htf < -0.1:
            score = min(1.0, abs(delta_htf) / 1.0)
            scores["htf_filter_interaction"] = round(score, 3)
            notes.append(f"htf_filter_interaction: Δpf = {delta_htf:+.3f} (HTF zerstoert Edge)")
        else:
            scores["htf_filter_interaction"] = 0.0
            notes.append(f"htf_filter_interaction: Δpf = {delta_htf:+.3f} (HTF neutral oder positiv)")

        # === session_filter_inversion ===
        # base vs base_+session
        sess_pf = marginal_df[marginal_df["config"] == "base_+session"]["pf"].values[0] if len(marginal_df[marginal_df["config"] == "base_+session"]) else 0
        delta_sess = sess_pf - base_pf
        if delta_sess < -0.1:
            score = min(1.0, abs(delta_sess) / 1.0)
            scores["session_filter_inversion"] = round(score, 3)
            notes.append(f"session_filter_inversion: Δpf = {delta_sess:+.3f} (NY-Session-Filter zerstoert Edge)")
        else:
            scores["session_filter_inversion"] = 0.0
            notes.append(f"session_filter_inversion: Δpf = {delta_sess:+.3f} (Session neutral oder positiv)")

        # === destructive_filter_interaction (NEU 2026-05-28 per Nico nach NB15a) ===
        # Filter sind individuell positiv (jeder >= base+0.1) ABER zusammen NICHT
        # so gut wie der bessere einzeln. Das war exakt das USDCHF-Muster.
        both_pf = marginal_df[marginal_df["config"] == "base_+htf_+sess"]["pf"].values[0] if len(marginal_df[marginal_df["config"] == "base_+htf_+sess"]) else 0
        max_single = max(htf_pf, sess_pf)
        interaction_delta = both_pf - max_single
        individual_helps = (htf_pf > base_pf + 0.05) or (sess_pf > base_pf + 0.05)
        if individual_helps and interaction_delta < -0.05:
            # destruction = wie viel Lift wird durch Combination zerstoert
            destruction_magnitude = abs(interaction_delta)
            score = min(1.0, destruction_magnitude / 0.5)
            scores["destructive_filter_interaction"] = round(score, 3)
            notes.append(
                f"destructive_filter_interaction: Δ(both vs max(htf,sess)) = "
                f"{interaction_delta:+.3f}  "
                f"(base={base_pf:.2f} htf={htf_pf:.2f} sess={sess_pf:.2f} both={both_pf:.2f}) "
                f"→ Filter heben sich auf"
            )
        else:
            scores["destructive_filter_interaction"] = 0.0
            notes.append(
                f"destructive_filter_interaction: Δ(both vs max(htf,sess)) = "
                f"{interaction_delta:+.3f} (additiv oder neutral)"
            )

    # === regime_dependency ===
    if per_regime_df is not None and len(per_regime_df) >= 3:
        regime_filt = per_regime_df[per_regime_df["regime"].isin(["low", "mid", "high"])]
        regime_filt = regime_filt[regime_filt["n"] >= 20]
        if len(regime_filt) >= 2:
            pf_max = regime_filt["pf"].replace([np.inf], 5.0).max()
            pf_min = regime_filt["pf"].min()
            sigma = pf_max - pf_min
            score = min(1.0, max(0.0, (sigma - 0.5) / 1.5))
            if pf_min < 1.0:
                score = min(1.0, score + 0.15)
            scores["regime_dependency"] = round(score, 3)
            notes.append(f"regime_dependency: PF range across vol regimes = {pf_min:.2f}–{pf_max:.2f}")

    # === macro_regime_dependency ===
    if per_macro_regime_df is not None and len(per_macro_regime_df) >= 2:
        macro_filt = per_macro_regime_df[per_macro_regime_df["n"] >= 20]
        if len(macro_filt) >= 2:
            pf_max = macro_filt["pf"].replace([np.inf], 5.0).max()
            pf_min = macro_filt["pf"].min()
            sigma = pf_max - pf_min
            score = min(1.0, max(0.0, (sigma - 0.5) / 1.5))
            scores["macro_regime_dependency"] = round(score, 3)
            notes.append(f"macro_regime_dependency: PF range across macro regimes = {pf_min:.2f}–{pf_max:.2f}")

    # === feature_signature_diff ===
    # NB15a (2026-05-28) zeigte: Threshold 0.05 ist zu sensitiv — alle Pairs
    # erreichen Score 1.0, nicht diskriminierend. Temporär deaktiviert bis
    # bessere Calibration verfügbar (z.B. relative to baseline-pair statt
    # absolute threshold).
    if shap_winning_vs_losing is not None and len(shap_winning_vs_losing) > 0:
        top_deltas = shap_winning_vs_losing["signed_delta"].abs().head(5).sum()
        scores["feature_signature_diff"] = 0.0  # DISABLED — siehe Kommentar
        notes.append(
            f"feature_signature_diff: top-5 signed-shap deltas sum = {top_deltas:.4f} "
            f"(score DISABLED — Threshold-Calibration nicht diskriminierend zwischen Pairs)"
        )

    # === structural_pair_issue (residual) ===
    explained = sum(v for v in scores.values()) / max(1, len(scores))
    # je niedriger der Mittelwert anderer Scores, desto höher die Wahrscheinlichkeit dass
    # wir die Inversion mit den aktuellen Tests NICHT erklären können
    if explained < 0.3:
        scores["structural_pair_issue"] = round(1.0 - explained, 3)
        notes.append(f"structural_pair_issue: mean other scores = {explained:.2f} (low → residual hypothesis)")
    else:
        scores["structural_pair_issue"] = round(max(0.0, 0.3 - explained), 3)

    # === top hypothesis ===
    top = max(scores.items(), key=lambda x: x[1]) if scores else ("unknown", 0.0)
    return {
        "hypothesis_scores": scores,
        "top_hypothesis": top[0],
        "top_score": top[1],
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# OVERRIDE-DISCIPLINE PRECHECK (ANN-016 Lock 5)
# ---------------------------------------------------------------------------
def override_discipline_precheck(
    statistical_proof: bool,
    market_structure_documented: bool,
    oos_lift_pf: float,
    seeds_tested: int,
    time_periods_tested: int,
    min_oos_lift: float = 0.05,
    min_seeds: int = 3,
    min_periods: int = 2,
) -> dict:
    """
    Prüft VOR Implementation eines Per-Pair-Overrides ob alle 4 ANN-016-
    Discipline-Kriterien erfüllt sind. Returnt klare PASS/FAIL pro Kriterium.

    Diese Funktion implementiert KEINE Overrides — sie validiert nur ob
    ein vorgeschlagener Override in den Code wandern darf.

    Returns: dict mit
        - all_passed: bool
        - checks: dict[str, bool]
        - missing: list[str]
        - recommendation: str
    """
    checks = {
        "1_statistical_proof":     bool(statistical_proof),
        "2_market_structure":      bool(market_structure_documented),
        "3_oos_lift":              float(oos_lift_pf) >= min_oos_lift,
        "4_reproducible":          int(seeds_tested) >= min_seeds and int(time_periods_tested) >= min_periods,
    }
    all_passed = all(checks.values())
    missing = [k for k, v in checks.items() if not v]
    if all_passed:
        rec = "ALL_PASSED — Override darf in core/router/pair_override_registry.py"
    else:
        rec = f"BLOCKED — missing: {missing}. Override NICHT implementieren."
    return {
        "all_passed": all_passed,
        "checks": checks,
        "missing": missing,
        "recommendation": rec,
    }
