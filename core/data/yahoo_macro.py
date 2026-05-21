"""
Yahoo Finance macro data fetcher (VIX, DXY, gold, BTC-Dominance proxies).

Free via yfinance. Limited to daily resolution for most macro series, which is
fine — we use these as low-frequency context features (forward-filled to 5M).
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd

# Symbol map: our normalized name -> Yahoo ticker
YAHOO_MACRO = {
    "VIX": "^VIX",        # Equity fear index
    "DXY": "DX-Y.NYB",    # US Dollar Index
    "TNX": "^TNX",        # 10-Year Treasury yield
    "GOLD": "GC=F",       # Gold futures
}


def fetch_yahoo(symbols: Iterable[str], start: datetime, end: datetime,
                 interval: str = "1d") -> pd.DataFrame:
    """
    Fetch macro time series from Yahoo Finance.

    Args:
        symbols: list of our normalized names (e.g. ["VIX", "DXY"])
        start, end: UTC datetime
        interval: "1d" (recommended for macro) or "1h", "5m" (limited history)

    Returns:
        DataFrame indexed by timestamp (UTC) with columns named after our symbols
        (e.g. "VIX_close", "DXY_close").
    """
    try:
        import yfinance as yf
    except ImportError as e:
        raise ImportError("yfinance not installed. Run: pip install yfinance") from e

    yahoo_tickers = {s: YAHOO_MACRO[s] for s in symbols if s in YAHOO_MACRO}
    if not yahoo_tickers:
        raise ValueError(f"No known Yahoo tickers in {list(symbols)}")

    frames: list[pd.DataFrame] = []
    for our_name, yh_ticker in yahoo_tickers.items():
        ticker = yf.Ticker(yh_ticker)
        df = ticker.history(start=start.strftime("%Y-%m-%d"),
                             end=end.strftime("%Y-%m-%d"),
                             interval=interval, auto_adjust=False)
        if df.empty:
            continue
        df.index = pd.to_datetime(df.index, utc=True)
        sub = df[["Close"]].rename(columns={"Close": f"{our_name}_close"})
        frames.append(sub)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, axis=1).sort_index()
    return out
