"""
Pine Router Codegen — generiert den Asset-Detection + Routing-Layer in Pine v6.

V1-STUB. Vollständige Implementation kommt in Phase E (NB17 / Pine-Compilation).

Lock: docs/pine_router_design.md
Output-Template wird das hier generieren:
    - detect_asset_class() Pine-Funktion (mirror of asset_detector.py)
    - User-Override-Input
    - Routing-Switch zu fx_model_predict() / crypto_model_predict() / etc.
    - Tier-Engine-Cutoffs pro Modell

Bis V2 ist diese Funktion ein NotImplementedError-Stub. Sie wird vom
NB17-Pine-Compilation-Notebook aufgerufen werden.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable


_STUB_PINE_TEMPLATE = """\
// =============================================================================
// PaceAlgo Pine Router (auto-generated)
// =============================================================================
// Source: core/router/pine_router_codegen.py
// Spec:   docs/pine_router_design.md
// V1 stub — only FX model active. Other classes return na.
// =============================================================================

// --- ASSET DETECTION ---
// Spiegel der Logic in core/router/asset_detector.py
// Reihenfolge ist KRITISCH: Commodity -> Crypto -> FX -> Indices -> Unsupported
_is_commodity() =>
    s = syminfo.tickerid
    str.contains(s, "XAU") or str.contains(s, "XAG") or str.contains(s, "GOLD") or str.contains(s, "SILVER")

_is_crypto() =>
    s = syminfo.tickerid
    str.contains(s, "BTC") or str.contains(s, "ETH") or str.contains(s, "SOL") or str.contains(s, "BNB") or str.contains(s, "ADA") or str.contains(s, "USDT") or str.contains(s, "USDC")

_is_fx() =>
    s = syminfo.tickerid
    str.contains(s, "EUR") or str.contains(s, "USD") or str.contains(s, "JPY") or str.contains(s, "GBP") or str.contains(s, "AUD") or str.contains(s, "CHF")

_is_indices() =>
    s = syminfo.tickerid
    str.contains(s, "SPY") or str.contains(s, "QQQ") or str.contains(s, "DIA") or str.contains(s, "IWM") or syminfo.type == "index" or syminfo.type == "stock" or syminfo.type == "fund"

detect_asset_class() =>
    _is_commodity() ? "commodity" :
      _is_crypto()    ? "crypto"    :
      _is_fx()        ? "fx"        :
      _is_indices()   ? "indices"   :
                        "unsupported"

// --- USER OVERRIDE ---
asset_class_override = input.string("auto", "Asset Class",
                                     options=["auto", "fx", "crypto", "commodity", "indices", "off"])
asset_class = asset_class_override == "auto" ? detect_asset_class() : asset_class_override

// --- MODEL ROUTER (V1: only FX active) ---
// TODO V2: replace na-stubs with auto-generated model_predict() functions
// from core/export/pine_codegen.py for each active class.
probability = float(na)
if asset_class == "fx"
    probability := fx_model_predict()  // injected by codegen
else if asset_class == "crypto"
    probability := na  // V2 stub
else if asset_class == "indices"
    probability := na  // V2 stub
else if asset_class == "commodity"
    probability := na  // V2 stub

// --- UI BADGE for inactive classes (V1) ---
if asset_class != "fx" and asset_class != "off" and asset_class != "unsupported" and bar_index == last_bar_index
    label.new(bar_index, high, "PaceAlgo: " + asset_class + " support coming in V2",
              color=color.gray, textcolor=color.white, style=label.style_label_down)
"""


def generate_pine_router(
    active_classes: Iterable[str] | None = None,
    output_path: Path | str | None = None,
) -> str:
    """
    Generate Pine-Code for the asset-aware router layer.

    V1-STUB: returns the static template above. V2 will:
    - Read model files from core/models/{class}/
    - Read VAL-derived cutoffs from each model's config JSON
    - Generate tree-cascade Pine-Code for each active model
    - Inject into the router template

    Args:
        active_classes: subset of {"fx", "crypto", "commodity", "indices"}.
                        If None, uses MODEL_SLOTS to determine.
        output_path: if given, write template to file. Else return as string.

    Returns:
        Generated Pine code as string.

    Raises:
        NotImplementedError: V2 logic not yet built (Phase E / NB17 scope).
    """
    # V1 stub: return the static template. V2 will do real codegen.
    if active_classes is not None:
        # Future: filter the template based on active_classes.
        pass

    pine_code = _STUB_PINE_TEMPLATE

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(pine_code, encoding="utf-8")

    return pine_code


def validate_pine_router(pine_code: str) -> tuple[bool, list[str]]:
    """
    V1-STUB: would validate Pine syntax + budget compliance.

    V2 will:
    - Parse Pine code to AST (or use TradingView API)
    - Count ops/bar against pine_constraints.md budget
    - Validate request.security count ≤ 12
    - Check tree-cascade depth ≤ 3 per model

    Returns:
        (passed, list_of_issues)
    """
    raise NotImplementedError(
        "validate_pine_router not yet implemented — Phase E scope (NB17). "
        "Until then, Pine validation is manual: paste into TradingView Editor, "
        "watch for compile errors + ops/bar warning."
    )
