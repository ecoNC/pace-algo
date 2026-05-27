"""
Wiederverwendbare TF-Evaluation-Pipeline (Router-kompatibel).

Designed um pro Asset-Klasse identisch ausgeführt zu werden:
  - V1: NB14 nutzt es für FX-Modell
  - V2: gleiche Pipeline für Crypto-Spezialmodell, Indices-Modell, Commodity-Modell
  - Eingang: asset_class (Router.AssetClass) + symbol-pool + TFs
  - Ausgang: einheitliches dict mit Quant- + Produkt-Metriken pro TF

Eckdaten (gelocked durch ANN-009 + ANN-010):
  - Pipeline ist klassen-AGNOSTISCH; Features werden klassen-neutral berechnet
  - Trainings-Pool / Hold-Out kommen vom Caller (per asset_class konfiguriert)
  - Quality-Anchor-Check wird am Ende per TF aufgerufen
  - Produkt-Metriken werden parallel zu Quant-Metriken berechnet
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd

from ..router.asset_detector import AssetClass


# ---------------------------------------------------------------------------
# CONFIG OBJECT
# ---------------------------------------------------------------------------

@dataclass
class TFEvalConfig:
    """
    Eingabe-Konfiguration für die TF-Evaluation-Pipeline.

    Alles was sich zwischen Asset-Klassen ändert, lebt hier — der eigentliche
    Eval-Code unten ist klassen-agnostisch.
    """
    asset_class:        AssetClass
    train_symbols:      list[str]
    holdout_symbols:    list[str]
    timeframes:         list[str]
    feature_cols:       list[str]
    R:                  float = 1.5
    random_seed:        int = 42
    tier_percentiles:   dict[str, float] = field(default_factory=lambda: {
        "standard": 0.90,  # top 10%
        "high":     0.97,  # top 3%
        "premium":  0.99,  # top 1%
    })
    # Per-TF tier-Override (e.g. {"1h": {"premium": 0.97}} um H5 zu testen)
    tier_overrides:     dict[str, dict[str, float]] = field(default_factory=dict)

    def cutoff_for(self, tf: str, tier: str) -> float:
        """Tier-percentile inklusive Per-TF-Override."""
        if tf in self.tier_overrides and tier in self.tier_overrides[tf]:
            return self.tier_overrides[tf][tier]
        return self.tier_percentiles[tier]


@dataclass
class TFEvalResult:
    """
    Ergebnis pro (asset_class, TF, run).

    Container-Pattern damit Notebooks einfach iterieren + serialisieren.
    """
    asset_class:           str
    tf:                    str
    n_train_symbols:       int
    n_holdout_symbols:     int
    n_train_rows:          int
    n_val_rows:            int
    n_test_rows:           int
    # Cutoffs aus VAL
    cutoffs:               dict[str, float] = field(default_factory=dict)
    # Quant-Metriken
    quant_premium:         dict[str, float] = field(default_factory=dict)
    quant_high:            dict[str, float] = field(default_factory=dict)
    quant_standard:        dict[str, float] = field(default_factory=dict)
    # Hold-Out-Metriken
    holdout_premium:       dict[str, float] = field(default_factory=dict)
    holdout_per_symbol:    dict[str, dict] = field(default_factory=dict)
    # Yearly Stability
    yearly_pf:             dict[int, float] = field(default_factory=dict)
    stability_cv:          float = 0.0
    # Produkt-Metriken
    product_premium:       dict = field(default_factory=dict)
    product_high:          dict = field(default_factory=dict)
    product_thresholds_check: dict = field(default_factory=dict)
    # Pine-UX
    pine_ux:               dict = field(default_factory=dict)
    # SHAP
    shap_top:              list[tuple[str, float]] = field(default_factory=list)
    # Quality-Anchor
    quality_anchor:        dict = field(default_factory=dict)
    # Diagnostik
    notes:                 list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "asset_class":        self.asset_class,
            "tf":                 self.tf,
            "n_train_symbols":    self.n_train_symbols,
            "n_holdout_symbols":  self.n_holdout_symbols,
            "n_train_rows":       self.n_train_rows,
            "n_val_rows":         self.n_val_rows,
            "n_test_rows":        self.n_test_rows,
            "cutoffs":            self.cutoffs,
            "quant_premium":      self.quant_premium,
            "quant_high":         self.quant_high,
            "quant_standard":     self.quant_standard,
            "holdout_premium":    self.holdout_premium,
            "holdout_per_symbol": self.holdout_per_symbol,
            "yearly_pf":          {str(k): v for k, v in self.yearly_pf.items()},
            "stability_cv":       self.stability_cv,
            "product_premium":    _sanitize(self.product_premium),
            "product_high":       _sanitize(self.product_high),
            "product_thresholds_check": self.product_thresholds_check,
            "pine_ux":            self.pine_ux,
            "shap_top":           [(n, float(v)) for n, v in self.shap_top],
            "quality_anchor":     _sanitize(self.quality_anchor),
            "notes":              self.notes,
        }


def _sanitize(d):
    """JSON-safe (remove numpy scalars)."""
    if isinstance(d, dict):
        return {k: _sanitize(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_sanitize(v) for v in d]
    if isinstance(d, (np.floating, np.integer)):
        return float(d)
    return d


# ---------------------------------------------------------------------------
# DECISION ENGINE (TF-Selection für ein Asset-Class-Modell)
# ---------------------------------------------------------------------------

def decide_tf_setup(
    per_tf_results: dict[str, TFEvalResult],
    phase_c_thresholds: dict,
) -> dict:
    """
    Aus per-TF-Ergebnissen die Produktentscheidungen ableiten.

    Returns dict mit:
      - default_tf:          str           — empfohlener Default-TF
      - supported_tfs:       list[str]     — alle TFs die V1 unterstützt
      - profile_map:         dict          — Conservative/Balanced/Aggressive → TF
      - alert_strategy:      dict          — Welcher Tier triggert Alert pro TF
      - h1_pass / h2_pass / h3_pass: bool
      - explanation:         list[str]     — menschenlesbare Begründung
    """
    explanation = []
    h_scores = {}

    # --- H1: 5m als Default ---
    tf5 = per_tf_results.get("5m")
    h1_pass = False
    if tf5 is not None:
        holdout_pf = tf5.holdout_premium.get("profit_factor", 0)
        cv = tf5.stability_cv
        max_dd = tf5.quant_premium.get("max_drawdown", 1.0)
        trades_per_day = tf5.product_premium.get("signals_per_day_per_symbol", 0)
        h1_pass = (
            holdout_pf >= phase_c_thresholds["h1_min_premium_pf_holdout"]
            and cv <= phase_c_thresholds["h1_max_stability_cv"]
            and max_dd <= phase_c_thresholds["h1_max_drawdown"]
            and trades_per_day >= phase_c_thresholds["h1_min_trades_per_day"]
        )
        explanation.append(
            f"H1 (5m=Default): holdout_pf={holdout_pf:.2f}, cv={cv:.3f}, "
            f"mdd={max_dd:.3f}, sigs/day={trades_per_day:.2f} → {'PASS' if h1_pass else 'FAIL'}"
        )
    h_scores["h1"] = h1_pass

    # --- H2: 15m als Conservative ---
    tf15 = per_tf_results.get("15m")
    h2_pass = False
    if tf15 is not None:
        pf = tf15.quant_premium.get("profit_factor", 0)
        cv = tf15.stability_cv
        trades_per_day = tf15.product_premium.get("signals_per_day_per_symbol", 0)
        h2_pass = (
            pf >= phase_c_thresholds["h2_min_premium_pf"]
            and cv <= phase_c_thresholds["h2_max_stability_cv"]
            and trades_per_day >= phase_c_thresholds["h2_min_trades_per_day"]
        )
        explanation.append(
            f"H2 (15m=Conservative): pf={pf:.2f}, cv={cv:.3f}, "
            f"sigs/day={trades_per_day:.2f} → {'PASS' if h2_pass else 'FAIL'}"
        )
    h_scores["h2"] = h2_pass

    # --- H3: 30m/1h ausschließen ---
    h3_pass = True   # default: exclude (= H3-Hypothese ist "exclude")
    for tf_name in ("30m", "1h"):
        tf_res = per_tf_results.get(tf_name)
        if tf_res is None:
            continue
        pf = tf_res.quant_premium.get("profit_factor", 0)
        if pf >= phase_c_thresholds["h3_exclude_threshold_pf"]:
            h3_pass = False   # ein höherer TF performt doch → ausschließen wäre falsch
            explanation.append(f"H3 broken: {tf_name} pf={pf:.2f} >= {phase_c_thresholds['h3_exclude_threshold_pf']}")
    explanation.append(f"H3 (exclude 30m/1h): {'PASS' if h3_pass else 'FAIL'}")
    h_scores["h3"] = h3_pass

    # --- Produkt-Verdict: Welche TFs überleben Produkt-Schwellen ---
    product_ok = {tf: (r.product_thresholds_check.get("verdict", "?") in ("product_grade_A", "product_grade_B"))
                  for tf, r in per_tf_results.items()}

    # --- Default + supported TFs ---
    if h1_pass and product_ok.get("5m", False):
        default_tf = "5m"
    elif h2_pass and product_ok.get("15m", False):
        default_tf = "15m"
    else:
        # Fallback: bester Premium-PF mit grade A/B
        candidates = [(tf, r) for tf, r in per_tf_results.items() if product_ok.get(tf, False)]
        if candidates:
            best = max(candidates, key=lambda x: x[1].quant_premium.get("profit_factor", 0))
            default_tf = best[0]
        else:
            default_tf = "5m"  # last resort
            explanation.append("WARNING: kein TF erreicht Produkt-Grade B+ — Default-TF Fallback 5m")

    supported_tfs = [tf for tf, ok in product_ok.items() if ok]
    if not supported_tfs:
        supported_tfs = [default_tf]

    # --- Profile-Mapping ---
    # Aggressive = niedrigster TF aus supported_tfs
    # Conservative = höchster TF aus supported_tfs der Quant-Schwellen erfüllt
    # Balanced = default_tf
    tf_order = ["5m", "15m", "30m", "1h", "4h"]
    sup_ordered = [t for t in tf_order if t in supported_tfs]
    aggressive = sup_ordered[0] if sup_ordered else default_tf
    conservative = sup_ordered[-1] if len(sup_ordered) >= 2 else default_tf
    balanced = default_tf

    profile_map = {
        "Aggressive":   aggressive,
        "Balanced":     balanced,
        "Conservative": conservative,
    }

    # --- Alert-Strategie: nur Premium-Tier alert per default ---
    alert_strategy = {
        tf: {"alert_on_tier": "premium",
             "expected_alerts_per_day": per_tf_results[tf].product_premium.get("signals_per_day_per_symbol", 0)}
        for tf in supported_tfs
    }

    return {
        "default_tf":      default_tf,
        "supported_tfs":   supported_tfs,
        "profile_map":     profile_map,
        "alert_strategy":  alert_strategy,
        "h1_pass":         h1_pass,
        "h2_pass":         h2_pass,
        "h3_pass":         h3_pass,
        "product_ok":      product_ok,
        "explanation":     explanation,
    }
