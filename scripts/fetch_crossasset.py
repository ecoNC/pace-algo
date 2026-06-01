"""
Fetch cross-asset OHLCV (2022-2026) -> data/processed_v2/ for the universal-goal
generalization probe: crypto (24/7), metals, indices. Same dir/format as FX so the
existing feature pipeline (build_extended) finds the HTF parquets.

Run: py -3 scripts/fetch_crossasset.py
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.data.dukascopy_fetcher import fetch_dukascopy_ohlcv

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "processed_v2"
SYMBOLS = ["BTCUSD", "ETHUSD", "XAUUSD", "XAGUSD", "SPX500", "NAS100"]  # crypto/metals/indices
TIMEFRAMES = ["5m", "1h", "4h"]
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 5, 31, tzinfo=timezone.utc)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    total = len(SYMBOLS) * len(TIMEFRAMES); done = 0; errors = []
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            out = OUTPUT_DIR / f"{symbol}_{tf}.parquet"; done += 1
            prefix = f"[{done:2d}/{total}] {symbol} {tf:3s}"
            if out.exists():
                import pandas as pd
                print(f"{prefix}  skip ({len(pd.read_parquet(out)):,} rows)"); continue
            print(f"{prefix}  fetching...", end="", flush=True)
            try:
                df = fetch_dukascopy_ohlcv(symbol, tf, START, END)
                if df.empty:
                    print("  EMPTY"); errors.append(f"{symbol} {tf}: empty"); continue
                df.to_parquet(out)
                print(f"  OK {len(df):,} rows {df.index[0].date()}..{df.index[-1].date()} ({out.stat().st_size/1024**2:.1f}MB)")
            except Exception as e:
                print(f"  ERROR: {e}"); errors.append(f"{symbol} {tf}: {e}")
    print("-" * 50)
    for e in errors: print("  ERR", e)
    print("done" if not errors else f"{len(errors)} errors")


if __name__ == "__main__":
    main()
