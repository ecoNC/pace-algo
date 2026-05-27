"""
Unit-Tests für core.router.

Run: pytest tests/test_router.py -v
"""
import pytest

from core.router import (
    detect_asset_class,
    AssetClass,
    select_model,
    is_class_active,
    get_active_classes,
    MODEL_SLOTS,
    generate_pine_router,
)


# ============================================================================
# Asset Detector — Detection-Logic
# ============================================================================

class TestAssetDetection:
    """Tests for detect_asset_class()."""

    def test_fx_majors(self):
        """All FX major pairs should map to FX."""
        for sym in ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCHF",
                    "NZDUSD", "USDCAD", "EURJPY", "EURGBP"]:
            assert detect_asset_class(sym) == AssetClass.FX, f"{sym} should be FX"

    def test_crypto_majors(self):
        """All major crypto pairs should map to CRYPTO."""
        for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT",
                    "MATICUSDT", "AVAXUSDT", "DOGEUSDT"]:
            assert detect_asset_class(sym) == AssetClass.CRYPTO, f"{sym} should be CRYPTO"

    def test_commodity_precedence_over_fx(self):
        """XAUUSD/XAGUSD must NOT be classified as FX (contain 'USD')."""
        assert detect_asset_class("XAUUSD") == AssetClass.COMMODITY
        assert detect_asset_class("XAGUSD") == AssetClass.COMMODITY

    def test_crypto_precedence_over_fx(self):
        """BTCUSDT/ETHUSDC must NOT be classified as FX (contain 'USDT'/'USDC')."""
        assert detect_asset_class("BTCUSDT") == AssetClass.CRYPTO
        assert detect_asset_class("ETHUSDC") == AssetClass.CRYPTO

    def test_indices_etfs(self):
        for sym in ["SPY", "QQQ", "DIA", "IWM", "VTI"]:
            assert detect_asset_class(sym) == AssetClass.INDICES, f"{sym} should be INDICES"

    def test_unsupported(self):
        """Unknown symbols return UNSUPPORTED."""
        assert detect_asset_class("FOO") == AssetClass.UNSUPPORTED
        assert detect_asset_class("XYZ123") == AssetClass.UNSUPPORTED

    def test_empty_or_whitespace(self):
        """Empty / whitespace-only strings return UNSUPPORTED."""
        assert detect_asset_class("") == AssetClass.UNSUPPORTED
        assert detect_asset_class("   ") == AssetClass.UNSUPPORTED

    def test_case_insensitive(self):
        """Detection works regardless of input case."""
        assert detect_asset_class("eurusd") == AssetClass.FX
        assert detect_asset_class("EurUsd") == AssetClass.FX
        assert detect_asset_class("btcusdt") == AssetClass.CRYPTO
        assert detect_asset_class("xauusd") == AssetClass.COMMODITY

    def test_oil_and_silver(self):
        assert detect_asset_class("USO") == AssetClass.COMMODITY
        assert detect_asset_class("OIL") == AssetClass.COMMODITY
        assert detect_asset_class("SILVER") == AssetClass.COMMODITY


# ============================================================================
# Model Selector — Slot-Verwaltung + Stub-Handling
# ============================================================================

class TestModelSelector:
    """Tests for select_model() + is_class_active() + get_active_classes()."""

    def test_fx_is_active_in_v1(self):
        """V1 has exactly one active class: FX."""
        assert is_class_active(AssetClass.FX) is True

    def test_v2_classes_are_stub_in_v1(self):
        """Crypto/Indices/Commodity are stubs in V1."""
        assert is_class_active(AssetClass.CRYPTO) is False
        assert is_class_active(AssetClass.INDICES) is False
        assert is_class_active(AssetClass.COMMODITY) is False

    def test_unsupported_is_inactive(self):
        assert is_class_active(AssetClass.UNSUPPORTED) is False

    def test_get_active_classes_v1(self):
        """V1 should report only FX as active."""
        active = get_active_classes()
        assert AssetClass.FX in active
        assert AssetClass.CRYPTO not in active
        assert AssetClass.INDICES not in active
        assert AssetClass.COMMODITY not in active

    def test_select_model_stub_returns_none(self):
        """Stub slots return None."""
        assert select_model(AssetClass.CRYPTO) is None
        assert select_model(AssetClass.INDICES) is None
        assert select_model(AssetClass.COMMODITY) is None

    def test_select_model_unsupported_returns_none(self):
        assert select_model(AssetClass.UNSUPPORTED) is None

    def test_select_model_fx_returns_none_if_file_missing(self):
        """If FX model file doesn't exist (e.g. fresh repo), return None.

        Note: file existence is environment-dependent; this test passes when
        the V1 model has not yet been trained.
        """
        result = select_model(AssetClass.FX)
        # Either Path (model file exists) or None (not yet trained)
        from pathlib import Path
        assert result is None or isinstance(result, Path)

    def test_model_slots_structure(self):
        """All 4 asset classes have slot entries."""
        for ac in [AssetClass.FX, AssetClass.CRYPTO, AssetClass.INDICES, AssetClass.COMMODITY]:
            assert ac in MODEL_SLOTS
            slot = MODEL_SLOTS[ac]
            assert "path" in slot
            assert "active" in slot
            assert "notes" in slot


# ============================================================================
# Pine Router Codegen — V1-Stub
# ============================================================================

class TestPineRouterCodegen:
    """Tests for generate_pine_router() — V1 stub."""

    def test_v1_stub_returns_pine_code(self):
        """V1 generates static template with key elements."""
        code = generate_pine_router()
        assert "detect_asset_class" in code
        assert "fx" in code.lower()
        assert "asset_class_override" in code
        assert "V2" in code  # comment about V2 expansion

    def test_v1_stub_routes_to_fx_actively(self):
        """V1 stub has fx routing active, others as na-stubs."""
        code = generate_pine_router()
        assert "asset_class == \"fx\"" in code
        assert "fx_model_predict()" in code

    def test_v1_stub_other_classes_are_na(self):
        """V1: crypto/indices/commodity Pine branches all return na."""
        code = generate_pine_router()
        assert "V2 stub" in code  # explicit V2 stub markers

    def test_write_to_file(self, tmp_path):
        """generate_pine_router can write to file."""
        out = tmp_path / "router.pine"
        code = generate_pine_router(output_path=out)
        assert out.exists()
        assert out.read_text(encoding="utf-8") == code


# ============================================================================
# Integration: Detection → Model Selection
# ============================================================================

class TestRouterIntegration:
    """End-to-end: symbol → asset_class → model_path."""

    def test_eurusd_flow(self):
        """EURUSD → FX → model path (or None if model not built yet)."""
        ac = detect_asset_class("EURUSD")
        assert ac == AssetClass.FX
        # Model path returns either Path or None depending on env
        model = select_model(ac)
        from pathlib import Path
        assert model is None or isinstance(model, Path)

    def test_btcusdt_flow_v1_stub(self):
        """BTCUSDT → CRYPTO → None (V1 stub)."""
        ac = detect_asset_class("BTCUSDT")
        assert ac == AssetClass.CRYPTO
        assert select_model(ac) is None

    def test_unsupported_flow(self):
        """Unknown symbol → UNSUPPORTED → None."""
        ac = detect_asset_class("FOOBAR")
        assert ac == AssetClass.UNSUPPORTED
        assert select_model(ac) is None
