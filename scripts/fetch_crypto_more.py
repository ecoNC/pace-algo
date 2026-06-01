"""Fetch more crypto coins (XRP/LTC/BCH/ADA) 2022-2026 -> data/processed_v2/ for the
phase8 crypto-module push (more data + cross-sectional). Run: py -3 scripts/fetch_crypto_more.py"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.data.dukascopy_fetcher import fetch_dukascopy_ohlcv

OUT = Path(__file__).parent.parent / "data" / "processed_v2"
SYMBOLS = ["XRPUSD", "LTCUSD", "BCHUSD", "ADAUSD"]
TFS = ["5m", "1h", "4h"]
START = datetime(2022, 1, 1, tzinfo=timezone.utc); END = datetime(2026, 5, 31, tzinfo=timezone.utc)


def main():
    tot = len(SYMBOLS) * len(TFS); done = 0; err = []
    for s in SYMBOLS:
        for tf in TFS:
            p = OUT / f"{s}_{tf}.parquet"; done += 1; pre = f"[{done:2d}/{tot}] {s} {tf:3s}"
            if p.exists():
                import pandas as pd
                print(f"{pre} skip ({len(pd.read_parquet(p)):,})"); continue
            print(f"{pre} fetching...", end="", flush=True)
            try:
                df = fetch_dukascopy_ohlcv(s, tf, START, END)
                if df.empty:
                    print(" EMPTY"); err.append(f"{s} {tf}"); continue
                df.to_parquet(p)
                print(f" OK {len(df):,} {df.index[0].date()}..{df.index[-1].date()}")
            except Exception as e:
                print(f" ERR {e}"); err.append(f"{s} {tf}: {e}")
    print("done" if not err else f"errors: {err}")


if __name__ == "__main__":
    main()
