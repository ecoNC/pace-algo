"""
Phase 12d: DIPBUY>EMA200 TRUE OUT-OF-SAMPLE — 2015-2021 holdout.

The rule was formed on 2022-2026 data (phase12/12b/12c). 2015-2021 is 7 UNSEEN years
incl. 2015-08 flash crash, 2018 Q4, 2020 COVID crash, 2021 melt-up. If the pooled
daily DIPBUY (close < EMA20 - 1*ATR, close > EMA200, SL 2*ATR, hold 10, exit EMA20)
is positive there per-year, the anomaly is real — module candidate confirmed.

Fetches native 1d data 2015-2026 (small) into data/processed_v2/{SYM}_1d.parquet,
then evaluates per-year on BOTH windows (overlap 2022-26 = consistency check vs the
4h-resampled result).

Run: python scripts/phase12d_dipbuy_holdout.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import numpy as np
import pandas as pd

from core.data.dukascopy_fetcher import fetch_dukascopy_ohlcv
from core.features.engineer import ema, atr as atr_fn
from phase12_indices_swing import trade_R, pf_wr

SYMBOLS = ["SPX500", "NAS100", "US30", "US2000", "GER40", "UK100", "FRA40", "EUSTX50", "JPN225", "HKG33"]
START = datetime(2015, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 5, 31, tzinfo=timezone.utc)
DATA = REPO / "data" / "processed_v2"


def get_daily(sym):
    p = DATA / f"{sym}_1d.parquet"
    if p.exists():
        return pd.read_parquet(p)
    print(f"  fetching {sym} 1d 2015-2026...", end="", flush=True)
    df = fetch_dukascopy_ohlcv(sym, "1d", START, END)
    if df.empty:
        print(" EMPTY"); return None
    df.to_parquet(p)
    print(f" OK {len(df):,} {df.index[0].date()}..{df.index[-1].date()}")
    return df


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    OUT = REPO / "results" / "model_validation" / f"phase12d_dip_holdout_{stamp}"; OUT.mkdir(parents=True, exist_ok=True)
    trades = []
    psym = {}
    for sym in SYMBOLS:
        d = get_daily(sym)
        if d is None or len(d) < 500: continue
        a = atr_fn(d["high"], d["low"], d["close"], 14).values
        e20 = ema(d["close"], 20).values
        e200 = ema(d["close"], 200).values
        c = d["close"].values
        with np.errstate(invalid="ignore"):
            sig = (c < e20 - 1.0 * a) & (c > e200)
        tr = trade_R(d, sig, +1)
        trades.extend(tr)
        ho = [(ts, r - 0.02) for ts, r in tr if ts.year <= 2021]
        psym[sym] = (pf_wr(ho) or {}).get("pf")
    res = {"per_year": {}, "holdout_2015_2021": {}, "formation_2022_2026": {},
           "per_symbol_holdout_pf": psym}
    for cost in (0.02, 0.05):
        net = [(ts, r - cost) for ts, r in trades]
        yr = {}
        for y in range(2015, 2027):
            yr[str(y)] = (pf_wr([(ts, r) for ts, r in net if ts.year == y]) or {}).get("pf")
        res["per_year"][str(cost)] = yr
        ho = pf_wr([(ts, r) for ts, r in net if ts.year <= 2021]) or {}
        fo = pf_wr([(ts, r) for ts, r in net if ts.year >= 2022]) or {}
        res["holdout_2015_2021"][str(cost)] = ho
        res["formation_2022_2026"][str(cost)] = fo
        yl = " ".join(f"{y}:{yr[str(y)]}" for y in range(2015, 2027))
        print(f"\ncost={cost}")
        print(f"  HOLDOUT 2015-21: PF {ho.get('pf')}  WR {ho.get('wr')}  n={ho.get('n')}")
        print(f"  formation 22-26: PF {fo.get('pf')}  WR {fo.get('wr')}  n={fo.get('n')}")
        print(f"  per-year: {yl}")
    hold_years = [res["per_year"]["0.02"][str(y)] for y in range(2015, 2022)]
    pos = [p for p in hold_years if p and p > 1]
    verdict = dict(holdout_pf=res["holdout_2015_2021"]["0.02"].get("pf"),
                   holdout_years_pos=f"{len(pos)}/{len([p for p in hold_years if p])}",
                   bar_pass=bool(res["holdout_2015_2021"]["0.02"].get("pf", 0) and
                                 res["holdout_2015_2021"]["0.02"]["pf"] >= 1.2 and len(pos) >= 5))
    res["verdict"] = verdict
    (OUT / "dip_holdout.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(f"\nVERDICT: {json.dumps(verdict)}")
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
