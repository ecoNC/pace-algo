"""
Crypto v2 data pipeline: clean USDT-perp data from data.binance.vision (monthly zips).

Why: Dukascopy altcoin intraday is unusable (module_registry: 5-12% flat bars, gaps,
no real volume, no funding). Binance bulk data gives real volume + funding rates —
the class-native information basis the crypto module never had.

Fetches per symbol: 5m/1h/4h klines 2022-01..2026-05 + funding rates.
Output: data/binance/{SYM}_{tf}.parquet  +  data/binance/{SYM}_funding.parquet

Run: python scripts/fetch_binance.py
"""
from __future__ import annotations
import io, sys, zipfile
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).parent.parent / "data" / "binance"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT"]
TFS = ["5m", "1h", "4h"]
MONTHS = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)][:53]  # 2022-01..2026-05
BASE = "https://data.binance.vision/data/futures/um/monthly"

KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
         "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def _to_utc(ts: pd.Series) -> pd.DatetimeIndex:
    """Binance switched some datasets to microseconds in 2025 — normalize robustly."""
    v = ts.astype("int64")
    unit = pd.Series("ms", index=v.index)
    us = v > 10_000_000_000_000_0  # > 1e14 -> microseconds
    out = pd.to_datetime(pd.concat([v[~us], (v[us] // 1000)]).sort_index(), unit="ms", utc=True)
    return pd.DatetimeIndex(out)


def fetch_zip_csv(url: str) -> pd.DataFrame | None:
    r = requests.get(url, timeout=120)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open(z.namelist()[0]) as f:
            head = f.read(64).decode("utf-8", "ignore")
        with z.open(z.namelist()[0]) as f:
            return pd.read_csv(f, header=0 if head.lower().startswith(("open_time", "calc_time", "symbol")) else None)


def fetch_klines(sym: str, tf: str) -> None:
    out = OUT / f"{sym}_{tf}.parquet"
    if out.exists():
        print(f"  {sym} {tf}: skip ({len(pd.read_parquet(out)):,})"); return
    frames = []
    for m in MONTHS:
        df = fetch_zip_csv(f"{BASE}/klines/{sym}/{tf}/{sym}-{tf}-{m}.zip")
        if df is None: continue
        df.columns = KCOLS[:len(df.columns)]
        frames.append(df)
    if not frames:
        print(f"  {sym} {tf}: NO DATA"); return
    k = pd.concat(frames, ignore_index=True)
    k.index = _to_utc(k["open_time"])
    k = k[["open", "high", "low", "close", "volume", "quote_volume", "count", "taker_buy_volume"]].astype("float64")
    k["taker_buy_ratio"] = (k["taker_buy_volume"] / k["volume"].where(k["volume"] > 0)).astype("float32")
    k = k[~k.index.duplicated()].sort_index()
    k.to_parquet(out, compression="zstd")
    print(f"  {sym} {tf}: OK {len(k):,} {k.index[0].date()}..{k.index[-1].date()}")


def fetch_funding(sym: str) -> None:
    out = OUT / f"{sym}_funding.parquet"
    if out.exists():
        print(f"  {sym} funding: skip"); return
    frames = []
    for m in MONTHS:
        df = fetch_zip_csv(f"{BASE}/fundingRate/{sym}/{sym}-fundingRate-{m}.zip")
        if df is None: continue
        df.columns = ["calc_time", "funding_interval_hours", "funding_rate"][:len(df.columns)]
        frames.append(df)
    if not frames:
        print(f"  {sym} funding: NO DATA"); return
    f = pd.concat(frames, ignore_index=True)
    f.index = _to_utc(f["calc_time"])
    f = f[["funding_rate"]].astype("float64")
    f = f[~f.index.duplicated()].sort_index()
    f.to_parquet(out, compression="zstd")
    print(f"  {sym} funding: OK {len(f):,} rows")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for sym in SYMBOLS:
        print(f"[{sym}]")
        for tf in TFS:
            try: fetch_klines(sym, tf)
            except Exception as e: print(f"  {sym} {tf}: ERR {e}")
        try: fetch_funding(sym)
        except Exception as e: print(f"  {sym} funding: ERR {e}")
    print("done")


if __name__ == "__main__":
    main()
