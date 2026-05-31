"""
Fetch fresh FX OHLCV data (2022-2026) → data/processed_v2/

Symbols: all FX train + holdout pairs (7 symbols)
Timeframes: 5m (primary) + 1h + 4h (HTF context)
Output: data/processed_v2/{SYMBOL}_{TF}.parquet (UTC-indexed, columns: open/high/low/close/volume)

Run: py -3 scripts/fetch_v2_data.py
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data.dukascopy_fetcher import fetch_dukascopy_ohlcv

# ── Config ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "processed_v2"

# All FX symbols needed for NB14f retrain
SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
    "USDCHF", "USDCAD", "NZDUSD",
]

TIMEFRAMES = ["5m", "1h", "4h"]

START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END   = datetime(2026, 5, 31, tzinfo=timezone.utc)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output: {OUTPUT_DIR}")
    print(f"Range:  {START.date()} to {END.date()}")
    print(f"Symbols: {SYMBOLS}")
    print(f"Timeframes: {TIMEFRAMES}")
    print()

    total = len(SYMBOLS) * len(TIMEFRAMES)
    done = 0
    errors = []

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            out_path = OUTPUT_DIR / f"{symbol}_{tf}.parquet"
            done += 1
            prefix = f"[{done:2d}/{total}] {symbol} {tf:3s}"

            if out_path.exists():
                import pandas as pd
                existing = pd.read_parquet(out_path)
                print(f"{prefix}  skip  ({len(existing):,} rows cached)")
                continue

            print(f"{prefix}  fetching...", end="", flush=True)
            try:
                df = fetch_dukascopy_ohlcv(symbol, tf, START, END)
                if df.empty:
                    print(f"  EMPTY — skipping")
                    errors.append(f"{symbol} {tf}: empty response")
                    continue
                df.to_parquet(out_path)
                size_mb = out_path.stat().st_size / 1024 ** 2
                print(f"  OK  {len(df):,} rows  {df.index[0].date()} to {df.index[-1].date()}  ({size_mb:.1f} MB)")
            except Exception as exc:
                print(f"  ERROR: {exc}")
                errors.append(f"{symbol} {tf}: {exc}")

    print()
    print("-" * 60)
    parquet_files = sorted(OUTPUT_DIR.glob("*.parquet"))
    print(f"Files in {OUTPUT_DIR.name}/: {len(parquet_files)}")
    for p in parquet_files:
        print(f"  {p.name:25s}  {p.stat().st_size / 1024**2:.1f} MB")

    if errors:
        print(f"\n⚠  {len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\nAll done — no errors.")


if __name__ == "__main__":
    main()
