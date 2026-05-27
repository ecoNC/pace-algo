# `core/router/` — Multi-Model Routing Layer

**Locked by:** [ANN-009 Multi-Model Router Architecture](../../docs/decisions/ANN-009-multi-model-router-architecture.md)
**Pine-Side:** [docs/pine_router_design.md](../../docs/pine_router_design.md)

## Was hier lebt

Die Python-Seite des asset-aware Router-Layers. Pine-Code spiegelt diese Logik (siehe pine_router_codegen.py).

| Datei | Zweck | V1/V2 Status |
|---|---|---|
| `asset_detector.py` | Symbol → Asset-Klasse Mapping | ✅ V1 fertig |
| `model_selector.py` | Asset-Klasse → Modell-File-Pfad (oder None) | ✅ V1 fertig (Stub-fähig) |
| `pine_router_codegen.py` | Pine-Code-Template-Generator | 🟡 V1 Stub, V2 vollständig |

## Usage

```python
from core.router import detect_asset_class, select_model, AssetClass

# Asset-Klasse aus Symbol ableiten
asset_class = detect_asset_class("EURUSD")    # AssetClass.FX
asset_class = detect_asset_class("BTCUSDT")   # AssetClass.CRYPTO
asset_class = detect_asset_class("XAUUSD")    # AssetClass.COMMODITY

# Modell für Klasse holen (None wenn Slot stub oder File fehlt)
model_path = select_model(AssetClass.FX)      # PosixPath('.../fx_lgbm_v1.txt')
model_path = select_model(AssetClass.CRYPTO)  # None (V1 stub)

# Welche Klassen sind in V1 aktiv?
from core.router import get_active_classes
get_active_classes()                          # {AssetClass.FX}
```

## Design-Prinzipien

1. **Konservativ:** Wenn Detection unklar → `UNSUPPORTED`, lieber explizit fail als falsches Modell routen
2. **Reihenfolge-kritisch:** Commodity vor Crypto vor FX (XAUUSD/BTCUSDT enthalten "USD")
3. **Stub-fähig:** Inaktive Slots returnen None — Caller handhabt UI-State
4. **Quality-Gate getrennt:** select_model prüft nur Existenz, nicht Modell-Qualität — das macht der Build-Pipeline (ANN-010)

## V1 → V2 Migration

Wenn Crypto-Modell trainiert + Quality-Anchor bestanden ist:

1. Modell-File nach `artifacts/models/crypto/crypto_lgbm_v1.txt` legen
2. In `model_selector.py` `MODEL_SLOTS[AssetClass.CRYPTO]["active"] = True` setzen
3. Pine-Codegen re-runnen → `crypto_model_predict()` wird befüllt
4. **Kein Refactor an asset_detector.py oder model_selector.py nötig**

Das ist exakt der Punkt vom Router-Skelett-V1: V2 fügt Modelle hinzu, ohne Architektur-Änderungen.

## Tests

Siehe `tests/test_router.py` für Unit-Tests der Detection-Logic.

## Bekannte Limitierungen

- **CFD-Detection:** EURUSD-CFD vs EURUSD-Forex hat gleiches Symbol — wir routen beide zu `fx`. In Pine-Side via `syminfo.type` zu differenzieren wenn nötig.
- **Exotische FX:** ZAR/MXN/SGD sind in den Regeln, aber nicht in V1-Training. Werden zu `fx` geroutet → `fx_model` produziert Signale aber Quality unbekannt.
- **Multi-Asset-Pairs:** z.B. BTC/ETH (ohne USDT-Quote) würde von Crypto-Regel erfasst — okay, da Crypto-Klasse korrekt.
