"""
KuCoin OHLCV fetcher — primary Crypto data source.

Used because Binance (api.binance.com + fapi.binance.com) is geo-blocked
from US-region servers (e.g. Google Colab). KuCoin's public REST API is
accessible from US/EU/Asia and provides ~5+ years of historical OHLCV
for BTC/ETH/SOL on USDT pairs.

Free API, no key required for historical public OHLCV.
Rate limit: ~30 requests/sec per IP (well above our use).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

KUCOIN_REST = "https://api.kucoin.com"
KLINE_LIMIT = 1500  # KuCoin max per request

# KuCoin uses different timeframe strings than Binance
TIMEFRAME_KUCOIN = {
    "1m":  "1min",
    "5m":  "5min",
    "15m": "15min",
    "30m": "30min",
    "1h":  "1hour",
    "4h":  "4hour",
    "1d":  "1day",
    "1w":  "1week",
}

TIMEFRAME_SECONDS = {
    "1m":  60,
    "5m":  300,
    "15m": 900,
    "30m": 1800,
    "1h":  3600,
    "4h":  14400,
    "1d":  86400,
    "1w":  604800,
}


def _to_kucoin_symbol(symbol: str) -> str:
    """
    Translate internal symbol (e.g. 'BTCUSDT') to KuCoin format (e.g. 'BTC-USDT').

    Our config keeps Binance-style names; this function adapts on the fly.
    """
    # Common quote currencies to detect
    for quote in ("USDT", "USDC", "USD", "EUR", "BTC", "ETH"):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            base = symbol[: -len(quote)]
            return f"{base}-{quote}"
    raise ValueError(f"Cannot parse KuCoin symbol from: {symbol}")


def _ts_sec(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def fetch_klines(symbol: str, timeframe: str, start: datetime, end: datetime,
                  pause_sec: float = 0.15) -> pd.DataFrame:
    """
    Fetch OHLCV from KuCoin.

    Args:
        symbol: internal Binance-style name like 'BTCUSDT' (will be translated)
        timeframe: '5m', '15m', '1h', '4h', '1d'
        start, end: UTC datetime
        pause_sec: politeness delay between requests

    Returns:
        DataFrame indexed by open_time (UTC) with columns
        [open, high, low, close, volume, turnover]
        Compatible with binance_fetcher output (extra cols stripped).
    """
    if timeframe not in TIMEFRAME_KUCOIN:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    kucoin_symbol = _to_kucoin_symbol(symbol)
    kucoin_tf = TIMEFRAME_KUCOIN[timeframe]
    tf_sec = TIMEFRAME_SECONDS[timeframe]

    start_sec = _ts_sec(start)
    end_sec = _ts_sec(end)

    # KuCoin returns data DESCENDING (newest first), max KLINE_LIMIT per call.
    # We page BACKWARD from end → start.
    all_rows: list[list] = []
    cursor_end = end_sec

    while cursor_end > start_sec:
        # Compute window start so we get at most KLINE_LIMIT candles
        window_start = max(start_sec, cursor_end - tf_sec * KLINE_LIMIT)
        params = {
            "symbol": kucoin_symbol,
            "type": kucoin_tf,
            "startAt": window_start,
            "endAt": cursor_end,
        }
        r = requests.get(f"{KUCOIN_REST}/api/v1/market/candles", params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        if payload.get("code") != "200000":
            raise RuntimeError(f"KuCoin error: {payload}")
        batch = payload.get("data", [])
        if not batch:
            break
        all_rows.extend(batch)
        # Find oldest timestamp in batch → use as next cursor_end
        oldest_ts = int(batch[-1][0])  # last row is oldest (descending order)
        next_cursor = oldest_ts - 1
        if next_cursor >= cursor_end:
            break  # safety: no progress
        cursor_end = next_cursor
        if cursor_end <= start_sec:
            break
        time.sleep(pause_sec)

    if not all_rows:
        return pd.DataFrame()

    # Parse: [time, open, close, high, low, volume, turnover]
    df = pd.DataFrame(all_rows, columns=["time", "open", "close", "high", "low", "volume", "turnover"])
    df["time"] = pd.to_datetime(df["time"].astype(int), unit="s", utc=True)
    for c in ["open", "high", "low", "close", "volume", "turnover"]:
        df[c] = pd.to_numeric(df[c])
    df = df.set_index("time").sort_index()
    df = df.rename_axis("open_time")
    # Reorder columns to match binance_fetcher convention (open, high, low, close, volume, ...)
    df = df[["open", "high", "low", "close", "volume", "turnover"]]
    df = df[~df.index.duplicated(keep="first")]
    # Filter to exact requested window (handle both naive and aware datetimes)
    start_ts = pd.Timestamp(start).tz_convert("UTC") if pd.Timestamp(start).tz is not None else pd.Timestamp(start).tz_localize("UTC")
    end_ts = pd.Timestamp(end).tz_convert("UTC") if pd.Timestamp(end).tz is not None else pd.Timestamp(end).tz_localize("UTC")
    df = df.loc[(df.index >= start_ts) & (df.index <= end_ts)]
    return df


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    """Save DataFrame to compressed Parquet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, compression="zstd")


def load_parquet(path: Path) -> pd.DataFrame:
    """Load DataFrame from Parquet."""
    return pd.read_parquet(Path(path))
