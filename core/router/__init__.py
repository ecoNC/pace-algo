"""
core.router — Asset-aware Multi-Model Routing Layer.

Locked by ANN-009 (Multi-Model Router Architecture).
Pine-side spiegelt diese Logic in pace_algo_v{X.Y}.pine.

Public API:
    detect_asset_class(symbol)   -> "fx" | "crypto" | "commodity" | "indices" | "unsupported"
    select_model(asset_class)    -> Path | None
    get_active_classes()         -> set[str]
    generate_pine_router(...)    -> str   (V2 — stub in V1)
"""
from .asset_detector import (
    detect_asset_class,
    AssetClass,
    ASSET_DETECTION_RULES,
)
from .model_selector import (
    select_model,
    get_active_classes,
    is_class_active,
    MODEL_SLOTS,
)
from .pine_router_codegen import generate_pine_router  # stub for V2

__all__ = [
    "detect_asset_class",
    "AssetClass",
    "ASSET_DETECTION_RULES",
    "select_model",
    "get_active_classes",
    "is_class_active",
    "MODEL_SLOTS",
    "generate_pine_router",
]
