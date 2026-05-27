"""
Quality-Anchor-Check (ANN-010).

Operationalisiert die Quality-Anchor-Schwellen aus core.config.QUALITY_ANCHOR.
Jedes neue Modell durchläuft diesen Check vor Deployment-Freigabe.

Verwendung:
    >>> from core.analysis.quality_check import check_quality_anchor
    >>> metrics = {
    ...     "premium_pf_mean_oos":       2.49,
    ...     "premium_pf_holdout_mean":   2.51,
    ...     "min_pf_per_symbol":         2.1,
    ...     "stability_cv":              0.145,
    ...     "min_pf_per_year":           1.31,
    ...     "min_trades_per_year_tier":  120,
    ...     "premium_wr":                0.57,
    ... }
    >>> passed, severity, details = check_quality_anchor(metrics, asset_class="fx")
    >>> passed, severity
    (True, "passed")

Severity-Stufen:
  - "passed"           — alle strict + 2/3 soft → auto-deploy
  - "soft_only"        — alle strict, < 2/3 soft → deploy mit Marketing-Korrektur
  - "missing_1_strict" — 1 strict fail → explizite Nico-Approval nötig
  - "blocked"          — >= 2 strict fails → Re-Research, kein Deploy
"""
from __future__ import annotations

from typing import Optional

from ..config import QUALITY_ANCHOR


REQUIRED_STRICT_KEYS = [
    "premium_pf_mean_oos",
    "premium_pf_holdout_mean",
    "min_pf_per_symbol",
    "stability_cv",
    "min_pf_per_year",
    "min_trades_per_year_tier",
]


def check_quality_anchor(
    metrics: dict,
    asset_class: str = "fx",
    pine_budget_ok: bool = True,
) -> tuple[bool, str, dict]:
    """
    Prüft Modell-Metriken gegen ANN-010-Schwellen.

    Args:
        metrics: dict mit den Modell-Metriken (siehe REQUIRED_STRICT_KEYS).
        asset_class: "fx" | "crypto" | "indices" | "commodity"
                     Wird nur für Logging/Reports verwendet — gleiche Schwellen.
        pine_budget_ok: ob das Modell den Pine-Budget-Check bestanden hat.
                        Strict-Pflicht (ANN-010).

    Returns:
        (passed: bool, severity: str, details: dict)
        passed = True falls severity in ("passed", "soft_only") — also deploybar.
    """
    strict_cfg = QUALITY_ANCHOR["strict"]
    soft_cfg = QUALITY_ANCHOR["soft_reference"]
    actions = QUALITY_ANCHOR["deployment_action"]

    strict_results: dict[str, bool] = {}

    # --- Strict checks ---
    strict_results["premium_pf_oos"]      = metrics.get("premium_pf_mean_oos", 0)    >= strict_cfg["min_premium_pf_oos"]
    strict_results["premium_pf_holdout"]  = metrics.get("premium_pf_holdout_mean", 0) >= strict_cfg["min_premium_pf_holdout"]
    strict_results["min_pf_per_symbol"]   = metrics.get("min_pf_per_symbol", 0)      >= strict_cfg["min_pf_per_symbol"]
    strict_results["stability_cv"]        = metrics.get("stability_cv", 1e9)         <= strict_cfg["max_stability_cv"]
    strict_results["min_pf_per_year"]     = metrics.get("min_pf_per_year", 0)        >= strict_cfg["min_pf_per_year"]
    strict_results["trades_per_year"]     = metrics.get("min_trades_per_year_tier", 0) >= strict_cfg["min_trades_per_year_tier"]
    strict_results["pine_budget"]         = bool(pine_budget_ok)

    n_strict_fail = sum(1 for v in strict_results.values() if not v)

    # --- Soft checks ---
    soft_results: dict[str, bool] = {}
    if "premium_pf_mean_oos" in metrics:
        soft_results["matches_fx_anchor"] = metrics["premium_pf_mean_oos"] >= soft_cfg["fx_premium_pf_anchor"]
    if "premium_wr" in metrics:
        soft_results["wr_target"] = metrics["premium_wr"] >= soft_cfg["premium_wr_target"]
    if "shap_top_consistent" in metrics:
        soft_results["shap_consistent"] = bool(metrics["shap_top_consistent"])

    n_soft_pass = sum(1 for v in soft_results.values() if v)
    n_soft_total = len(soft_results)

    # --- Severity ---
    if n_strict_fail >= 2:
        severity = "blocked"
        action = actions["missing_2plus"]
    elif n_strict_fail == 1:
        severity = "missing_1_strict"
        action = actions["missing_1_strict"]
    elif n_soft_total > 0 and n_soft_pass >= max(2, n_soft_total - 1):
        severity = "passed"
        action = actions["all_strict_passed"]
    else:
        severity = "soft_only"
        action = "deploy with marketing transparency"

    passed = severity in ("passed", "soft_only")

    details = {
        "asset_class":       asset_class,
        "severity":          severity,
        "action":            action,
        "strict_results":    strict_results,
        "strict_failed":     [k for k, v in strict_results.items() if not v],
        "soft_results":      soft_results,
        "soft_passed_count": n_soft_pass,
        "soft_total":        n_soft_total,
        "metrics_input":     metrics,
    }
    return passed, severity, details


def format_quality_report(details: dict) -> str:
    """Menschenlesbare Ausgabe für Notebooks."""
    lines = []
    sev = details["severity"]
    icon = {"passed": "✅", "soft_only": "✅", "missing_1_strict": "⚠️", "blocked": "❌"}.get(sev, "?")
    lines.append(f"{icon} Quality Anchor: {sev.upper()} ({details['asset_class']})")
    lines.append(f"   Action: {details['action']}")
    lines.append("")
    lines.append("   Strict checks:")
    for k, v in details["strict_results"].items():
        sym = "✓" if v else "✗"
        lines.append(f"     {sym} {k}")
    if details["soft_results"]:
        lines.append("")
        lines.append(f"   Soft checks ({details['soft_passed_count']}/{details['soft_total']} passed):")
        for k, v in details["soft_results"].items():
            sym = "✓" if v else "·"
            lines.append(f"     {sym} {k}")
    return "\n".join(lines)
