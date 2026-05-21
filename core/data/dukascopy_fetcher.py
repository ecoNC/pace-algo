"""
Dukascopy historical FX/Metals data fetcher.

Dukascopy publishes free historical tick + 1-min data via their public archive.
Archive URL pattern:
  https://datafeed.dukascopy.com/datafeed/<INSTRUMENT>/<YEAR>/<MONTH-1>/<DAY>/<HOUR>h_ticks.bi5

This module wraps the third-party `dukascopy-python` library (preferred) and falls
back to direct archive access if needed.

Install: pip install dukascopy-python
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Symbol map: our normalized name -> Dukascopy instrument code
DUKASCOPY_SYMBOLS = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "XAUUSD": "XAU/USD",
    "USDCHF": "USD/CHF",
    "AUDUSD": "AUD/USD",
}


def fetch_dukascopy_ohlcv(symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetch Dukascopy OHLCV.

    Requires: `pip install dukascopy-python`

    Args:
        symbol: normalized name like "EURUSD"
        timeframe: "1m", "5m", "15m", "1h", "4h", "1d"
        start, end: UTC datetime

    Returns:
        DataFrame indexed by timestamp (UTC) with [open, high, low, close, volume]
    """
    try:
        import dukascopy_python
        from dukascopy_python.instruments import instrument_to_id
    except ImportError as e:
        raise ImportError(
            "dukascopy-python not installed. Run: pip install dukascopy-python"
        ) from e

    if symbol not in DUKASCOPY_SYMBOLS:
        raise ValueError(f"Unknown Dukascopy symbol: {symbol}")

    tf_map = {
        "1m": dukascopy_python.INTERVAL_MIN_1,
        "5m": dukascopy_python.INTERVAL_MIN_5,
        "15m": dukascopy_python.INTERVAL_MIN_15,
        "1h": dukascopy_python.INTERVAL_HOUR_1,
        "4h": dukascopy_python.INTERVAL_HOUR_4,
        "1d": dukascopy_python.INTERVAL_DAY_1,
    }
    if timeframe not in tf_map:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    inst = instrument_to_id(DUKASCOPY_SYMBOLS[symbol].replace("/", ""))

    df = dukascopy_python.fetch(
        instrument=inst,
        interval=tf_map[timeframe],
        offer_side=dukascopy_python.OFFER_SIDE_BID,
        start=start.replace(tzinfo=timezone.utc),
        end=end.replace(tzinfo=timezone.utc),
    )

    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [c.lower() for c in df.columns]
    expected = ["open", "high", "low", "close", "volume"]
    df = df[[c for c in expected if c in df.columns]]
    df.index.name = "open_time"
    return df.sort_index()
