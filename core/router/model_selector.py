"""
Model Selector — wählt das richtige Modell-File für eine Asset-Klasse.

Locked by ANN-009. V1: nur fx-Slot aktiv. V2: alle 4.

Design-Prinzip: Stub-fähig. Wenn ein Modell-File nicht existiert (V1-Stub),
gibt select_model None zurück — Caller muss explizit handhaben (z.B. UI
"Coming Soon"-Badge). Kein silent fallback.

Quality-Anchor (ANN-010): Bevor ein Modell aktiv wird, muss es das
quality_check.py-Modul bestanden haben. select_model prüft das NICHT zur
Laufzeit (zu teuer), nur ob das File existiert — die Quality-Gate-Logik
lebt im Build-Pipeline (NB-Auto-Push).
"""
from __future__ import annotations

from pathlib import Path

from .asset_detector import AssetClass


# V1-V3 Modell-Slot-Definition. Pfade relativ zu PROJECT_ROOT.
# active=True heißt: in V1 deployment-fähig.
MODEL_SLOTS: dict[AssetClass, dict] = {
    AssetClass.FX: {
        "path":   "artifacts/models/fx/fx_lgbm_v1.txt",
        "active": True,
        "notes":  "V1 Sieger — NB13 belegt Premium-PF 2.49 mean (5m, 5 FX-Symbole)",
    },
    AssetClass.CRYPTO: {
        "path":   "artifacts/models/crypto/crypto_lgbm_v1.txt",
        "active": False,
        "notes":  "V2-Slot — NB13 zeigte FX-trained Modell random auf Crypto. Crypto-Spezialmodell muss in NB13c trainiert + Quality-Anchor bestehen",
    },
    AssetClass.INDICES: {
        "path":   "artifacts/models/indices/indices_lgbm_v1.txt",
        "active": False,
        "notes":  "V2-Slot — braucht Polygon-Fetcher + NB13b Indices-Cross-Asset-Test",
    },
    AssetClass.COMMODITY: {
        "path":   "artifacts/models/commodity/commodity_lgbm_v1.txt",
        "active": False,
        "notes":  "V2-Slot — Gold Phase 1 random (ANN-003). Vielleicht Silber/Oil dazu",
    },
}


def is_class_active(asset_class: AssetClass) -> bool:
    """True if the model slot for this asset class is V1-deployment-ready."""
    if asset_class == AssetClass.UNSUPPORTED:
        return False
    return MODEL_SLOTS.get(asset_class, {}).get("active", False)


def get_active_classes() -> set[AssetClass]:
    """Return all asset classes that have V1-active models."""
    return {ac for ac, cfg in MODEL_SLOTS.items() if cfg.get("active", False)}


def select_model(
    asset_class: AssetClass,
    project_root: Path | str | None = None,
) -> Path | None:
    """
    Select the model file path for a given asset class.

    Returns None if:
    - asset_class is UNSUPPORTED
    - the slot is not active in current version (V1-Stub)
    - the model file does not exist on disk

    Args:
        asset_class: AssetClass enum value
        project_root: optional root for resolving relative paths.
                      Defaults to detecting from this file's location.

    Returns:
        Path to model file, or None if no model available.

    Examples:
        >>> select_model(AssetClass.FX)  # if file exists
        PosixPath('/.../artifacts/models/fx/fx_lgbm_v1.txt')
        >>> select_model(AssetClass.CRYPTO)  # V1 stub
        None
    """
    if asset_class == AssetClass.UNSUPPORTED:
        return None

    slot = MODEL_SLOTS.get(asset_class)
    if not slot or not slot.get("active", False):
        return None

    if project_root is None:
        # Resolve from this file's location: core/router/model_selector.py
        # → project root is two parents up
        project_root = Path(__file__).resolve().parent.parent.parent
    else:
        project_root = Path(project_root)

    model_path = project_root / slot["path"]
    if not model_path.exists():
        return None

    return model_path
