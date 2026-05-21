"""Multi-source OHLCV data fetchers (KuCoin, Dukascopy, Yahoo).

Primary crypto source: KuCoin (Binance is geo-blocked from US-region Colab).
The `fetch_klines` name is exported from KuCoin for drop-in use.
Binance fetcher kept for completeness in case it's usable from non-US IPs
(e.g. monthly local pull from EU).
"""

from .kucoin_fetcher import (
    fetch_klines,
    save_parquet,
    load_parquet,
)
from .binance_fetcher import (
    fetch_klines as fetch_klines_binance,
    fetch_funding_rates,
    fetch_open_interest_hist,
)
from .yahoo_macro import fetch_yahoo, YAHOO_MACRO

__all__ = [
    "fetch_klines",                # KuCoin (primary)
    "fetch_klines_binance",        # Binance (fallback, US-blocked)
    "fetch_funding_rates",         # Binance only — US-blocked
    "fetch_open_interest_hist",    # Binance only — US-blocked
    "save_parquet",
    "load_parquet",
    "fetch_yahoo",
    "YAHOO_MACRO",
]
