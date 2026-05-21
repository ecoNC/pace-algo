"""
Binance OHLCV + Funding Rate + Open Interest fetcher.

Free API, no key required for historical public data.
Rate limit: 1200 requests/min (well above our needs).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BINANCE_REST = "https://api.binance.com"
BINANCE_FAPI = "https://fapi.binance.com"  # USD-M Futures for funding/OI

KLINE_LIMIT = 1000  # Binance max per request
TIMEFRAME_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def _ts_ms(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch_klines(symbol: str, timeframe: str, start: datetime, end: datetime,
                  pause_sec: float = 0.15) -> pd.DataFrame:
    """
    Fetch OHLCV from Binance Spot.

    Args:
        symbol: e.g. "BTCUSDT"
        timeframe: "5m", "15m", "1h", "4h", "1d"
        start, end: UTC datetime
        pause_sec: politeness delay between requests

    Returns:
        DataFrame indexed by open_time (UTC) with columns
        [open, high, low, close, volume, trades, taker_buy_vol]
    """
    if timeframe not in TIMEFRAME_MS:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    tf_ms = TIMEFRAME_MS[timeframe]
    start_ms = _ts_ms(start)
    end_ms = _ts_ms(end)

    all_rows: list[list] = []
    cursor = start_ms

    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": KLINE_LIMIT,
        }
        r = requests.get(f"{BINANCE_REST}/api/v3/klines", params=params, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        all_rows.extend(batch)
        last_open = batch[-1][0]
        next_cursor = last_open + tf_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        time.sleep(pause_sec)

    if not all_rows:
        return pd.DataFrame()

    cols = ["open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "_ignore"]
    df = pd.DataFrame(all_rows, columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume", "quote_vol", "taker_buy_base"]:
        df[c] = pd.to_numeric(df[c])
    df["trades"] = pd.to_numeric(df["trades"], downcast="integer")
    df = df.set_index("open_time").sort_index()
    df = df[["open", "high", "low", "close", "volume", "trades", "taker_buy_base"]]
    df = df.rename(columns={"taker_buy_base": "taker_buy_vol"})
    df = df[~df.index.duplicated(keep="first")]
    return df


def fetch_funding_rates(symbol: str, start: datetime, end: datetime,
                          pause_sec: float = 0.2) -> pd.DataFrame:
    """
    Fetch perpetual funding rates (8h interval) from Binance USD-M Futures.

    Args:
        symbol: e.g. "BTCUSDT" (futures perp)
        start, end: UTC datetime

    Returns:
        DataFrame indexed by funding_time (UTC) with column [funding_rate]
    """
    start_ms = _ts_ms(start)
    end_ms = _ts_ms(end)

    all_rows: list[dict] = []
    cursor = start_ms

    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1000,
        }
        r = requests.get(f"{BINANCE_FAPI}/fapi/v1/fundingRate", params=params, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        all_rows.extend(batch)
        last_time = batch[-1]["fundingTime"]
        if last_time <= cursor:
            break
        cursor = last_time + 1
        time.sleep(pause_sec)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["fundingRate"] = pd.to_numeric(df["fundingRate"])
    df = df.set_index("fundingTime")[["fundingRate"]].sort_index()
    df.columns = ["funding_rate"]
    df = df[~df.index.duplicated(keep="first")]
    return df


def fetch_open_interest_hist(symbol: str, timeframe: str, start: datetime, end: datetime,
                              pause_sec: float = 0.2) -> pd.DataFrame:
    """
    Fetch historical open interest (5m/15m/30m/1h/2h/4h/6h/12h/1d) from Binance Futures.

    NOTE: Binance only provides ~30 days of OI history via this endpoint.
    For full historical OI we need to accumulate over time or use a third-party archive.

    Args:
        symbol: e.g. "BTCUSDT"
        timeframe: "5m", "15m", "1h", "4h", "1d"
        start, end: UTC datetime

    Returns:
        DataFrame indexed by timestamp (UTC) with columns
        [open_interest, open_interest_value]
    """
    valid_tf = {"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}
    if timeframe not in valid_tf:
        raise ValueError(f"Open interest only supports: {valid_tf}")

    start_ms = _ts_ms(start)
    end_ms = _ts_ms(end)

    all_rows: list[dict] = []
    cursor = start_ms

    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "period": timeframe,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 500,
        }
        r = requests.get(f"{BINANCE_FAPI}/futures/data/openInterestHist", params=params, timeout=30)
        if r.status_code == 400:
            # Out of available range — Binance returns empty for older dates
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        all_rows.extend(batch)
        last_time = batch[-1]["timestamp"]
        if last_time <= cursor:
            break
        cursor = last_time + 1
        time.sleep(pause_sec)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["sumOpenInterest"] = pd.to_numeric(df["sumOpenInterest"])
    df["sumOpenInterestValue"] = pd.to_numeric(df["sumOpenInterestValue"])
    df = df.set_index("timestamp")[["sumOpenInterest", "sumOpenInterestValue"]].sort_index()
    df.columns = ["open_interest", "open_interest_value"]
    df = df[~df.index.duplicated(keep="first")]
    return df


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    """Save DataFrame to compressed Parquet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, compression="zstd")


def load_parquet(path: Path) -> pd.DataFrame:
    """Load DataFrame from Parquet."""
    return pd.read_parquet(Path(path))
