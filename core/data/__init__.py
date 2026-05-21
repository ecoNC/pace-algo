"""Multi-source OHLCV data fetchers (Binance, Dukascopy, Yahoo)."""

from .binance_fetcher import (
    fetch_klines,
    fetch_funding_rates,
    fetch_open_interest_hist,
    save_parquet,
    load_parquet,
)
from .yahoo_macro import fetch_yahoo, YAHOO_MACRO

__all__ = [
    "fetch_klines",
    "fetch_funding_rates",
    "fetch_open_interest_hist",
    "save_parquet",
    "load_parquet",
    "fetch_yahoo",
    "YAHOO_MACRO",
]
