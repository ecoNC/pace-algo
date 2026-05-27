"""
Asset-Klasse aus Symbol-String ableiten.

Python-Spiegel der Pine-Detection-Logic aus docs/pine_router_design.md §2.
Wenn diese Logik sich ändert, MUSS die Pine-Seite synchron gehalten werden
(via pine_router_codegen — V2).

Reihenfolge der Checks ist WICHTIG:
1. Commodity (Gold/Silber) ZUERST — sonst matched XAUUSD die FX-Regel
2. Crypto vor FX — sonst matched BTCUSDT die FX-Regel ("USDT" enthält "USD")
3. FX
4. Indices/Stocks/ETFs
5. Sonst: unsupported

Design-Prinzip: konservativ. Wenn unklar → "unsupported" und UI zeigt
"Symbol nicht erkannt — bitte Override setzen". Lieber explizit fail
als falsches Modell routen (Locked Rule per ANN-006 Lock 3).
"""
from __future__ import annotations

from enum import Enum
from typing import Iterable


class AssetClass(str, Enum):
    """Asset classes supported by the multi-model router (ANN-009)."""
    FX          = "fx"
    CRYPTO      = "crypto"
    COMMODITY   = "commodity"
    INDICES     = "indices"
    UNSUPPORTED = "unsupported"


# Detection rules — order matters (see module docstring).
# Each rule: (asset_class, list-of-substring-tokens-or-exact-matches)
# A symbol matches if ANY of the tokens appears in the uppercase symbol string.
ASSET_DETECTION_RULES: list[tuple[AssetClass, tuple[str, ...]]] = [
    # Commodities — must be checked BEFORE FX because XAUUSD/XAGUSD contain "USD"
    (AssetClass.COMMODITY, (
        "XAU", "XAG", "GOLD", "SILVER",
        "USO", "OIL", "WTI", "BRENT", "NATGAS",
        "XPD", "XPT",   # Palladium / Platinum
    )),

    # Crypto — must be checked BEFORE FX because *USDT / *USDC contain "USD"
    (AssetClass.CRYPTO, (
        "BTC", "ETH", "SOL", "BNB", "ADA",
        "USDT", "USDC", "BUSD", "DAI",   # stablecoin quote markers
        "MATIC", "AVAX", "DOT", "LINK", "ATOM",
        "DOGE", "SHIB", "XRP", "LTC",
    )),

    # FX — Major + Minor pairs. Tokens are 3-letter currency codes.
    (AssetClass.FX, (
        "EUR", "USD", "JPY", "GBP", "AUD", "CHF", "CAD", "NZD",
        "SEK", "NOK", "DKK", "ZAR", "MXN", "SGD", "HKD",
    )),

    # Indices / ETFs — common tickers
    (AssetClass.INDICES, (
        "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO",   # US ETFs
        "EWG", "EWJ", "EFA", "VEA",                  # Regional ETFs
        "NDX", "SPX", "DJI", "RUT", "VIX",           # Index tickers
        "DAX", "FTSE", "CAC", "NIKKEI", "HSI",       # International
    )),
]


def detect_asset_class(symbol: str) -> AssetClass:
    """
    Detect asset class from symbol string.

    Args:
        symbol: ticker symbol, e.g. "BTCUSDT", "EURUSD", "XAUUSD", "SPY".
                Case-insensitive. Whitespace stripped.

    Returns:
        AssetClass enum value. Returns UNSUPPORTED if no rule matches.

    Examples:
        >>> detect_asset_class("EURUSD")
        <AssetClass.FX: 'fx'>
        >>> detect_asset_class("BTCUSDT")
        <AssetClass.CRYPTO: 'crypto'>
        >>> detect_asset_class("XAUUSD")
        <AssetClass.COMMODITY: 'commodity'>
        >>> detect_asset_class("SPY")
        <AssetClass.INDICES: 'indices'>
        >>> detect_asset_class("FOO")
        <AssetClass.UNSUPPORTED: 'unsupported'>
    """
    if not symbol:
        return AssetClass.UNSUPPORTED
    s = symbol.strip().upper()
    if not s:
        return AssetClass.UNSUPPORTED

    for asset_class, tokens in ASSET_DETECTION_RULES:
        if any(tok in s for tok in tokens):
            return asset_class

    return AssetClass.UNSUPPORTED


def classify_batch(symbols: Iterable[str]) -> dict[str, AssetClass]:
    """Classify a batch of symbols. Useful for backtest setup."""
    return {sym: detect_asset_class(sym) for sym in symbols}
