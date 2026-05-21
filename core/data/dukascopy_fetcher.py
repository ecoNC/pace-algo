"""
Dukascopy historical FX/Metals data fetcher.

Wraps dukascopy-python 4.0+ which provides direct INSTRUMENT_* constants
(no more instrument_to_id() lookup) and a single fetch() entry point with
built-in retry and pagination.

Install: pip install dukascopy-python>=4.0
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Symbol map: our normalized name -> dukascopy_python.instruments constant name
# (kept as string lookup so the module loads even if dukascopy_python isn't installed)
DUKASCOPY_INSTRUMENT = {
    "EURUSD": "INSTRUMENT_FX_MAJORS_EUR_USD",
    "GBPUSD": "INSTRUMENT_FX_MAJORS_GBP_USD",
    "USDJPY": "INSTRUMENT_FX_MAJORS_USD_JPY",
    "USDCHF": "INSTRUMENT_FX_MAJORS_USD_CHF",
    "AUDUSD": "INSTRUMENT_FX_MAJORS_AUD_USD",
    "XAUUSD": "INSTRUMENT_FX_METALS_XAU_USD",
}


def fetch_dukascopy_ohlcv(symbol: str, timeframe: str,
                            start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetch Dukascopy OHLCV (dukascopy-python 4.0+ API).

    Args:
        symbol: normalized name like "EURUSD"
        timeframe: "1m", "5m", "15m", "1h", "4h", "1d"
        start, end: UTC datetime

    Returns:
        DataFrame indexed by timestamp (UTC) with [open, high, low, close, volume]
    """
    try:
        import dukascopy_python
        from dukascopy_python import instruments as dp_instruments
    except ImportError as e:
        raise ImportError(
            f"dukascopy-python not installed or API changed: {e}. "
            f"Run: pip install --force-reinstall dukascopy-python"
        ) from e

    if symbol not in DUKASCOPY_INSTRUMENT:
        raise ValueError(f"Unknown Dukascopy symbol: {symbol}")

    tf_map = {
        "1m":  dukascopy_python.INTERVAL_MIN_1,
        "5m":  dukascopy_python.INTERVAL_MIN_5,
        "15m": dukascopy_python.INTERVAL_MIN_15,
        "30m": dukascopy_python.INTERVAL_MIN_30,
        "1h":  dukascopy_python.INTERVAL_HOUR_1,
        "4h":  dukascopy_python.INTERVAL_HOUR_4,
        "1d":  dukascopy_python.INTERVAL_DAY_1,
    }
    if timeframe not in tf_map:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    instrument_const_name = DUKASCOPY_INSTRUMENT[symbol]
    instrument = getattr(dp_instruments, instrument_const_name, None)
    if instrument is None:
        raise RuntimeError(
            f"Instrument constant {instrument_const_name} not found in dukascopy_python.instruments. "
            f"Library API may have changed."
        )

    # Ensure UTC datetimes
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    df = dukascopy_python.fetch(
        instrument=instrument,
        interval=tf_map[timeframe],
        offer_side=dukascopy_python.OFFER_SIDE_BID,
        start=start,
        end=end,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    # Normalize column names + index
    df.columns = [c.lower() for c in df.columns]
    expected = ["open", "high", "low", "close", "volume"]
    df = df[[c for c in expected if c in df.columns]]
    df.index.name = "open_time"
    # Ensure tz-aware UTC index
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df.sort_index()
