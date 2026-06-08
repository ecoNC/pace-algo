"""Thin TV->Python capture pipe for whole-chain bit-exact checks.

PURPOSE (Block-2 prerequisite, Nico-locked 2026-06-08): the exact 1e-5 feature/signal
bit-exact needs TV-OHLCV in Python WITHOUT manual number transcription — the dead-end
that stalled Block-1(b). Workflow:

  1. Claude calls the MCP tool data_get_ohlcv(count=N) at each needed TF (e.g. 5, 60, 240).
  2. Claude saves the VERBATIM JSON result (the whole {"success":...,"bars":[...]} blob)
     via the Write tool to data/tv_capture/<SYMBOL>_<TF>.json  (structured copy, reliable).
  3. This loader parses that JSON into the canonical OHLCV DataFrame that
     core.features.compute_features expects (index open_time UTC, cols ohlcv float64),
     then runs the EXISTING feature engine — so the comparison reuses training code 1:1.

Force-multiplier: every future module's whole-chain check reuses this. Keep it THIN —
a measurement instrument, not an integration framework.

Feed note: TV (e.g. CAPITALCOM) and the training feed (Dukascopy) differ AND use different
4h-bar grids. That is fine here — the bit-exact check is FEED-CONSISTENT (TV bars feed both
the Python features and the Pine request.security reads), so it tests FORMULA parity only.

CAPTURE REQUIREMENTS (learned in smoke test — get these wrong and features go NaN/stale):
  - CONCURRENT: capture 5m/1h/4h at the same moment (same recent window) so the HTF
    shift(1)+ffill maps onto the right bars.
  - WARMUP: HTF captures need enough history BEFORE the current period — atr_percentile_100
    needs >=100 HTF bars, ema_200 needs >=200, rsi_14 needs ~60. Use count>=150 for 4h,
    >=250 for 5m (ema200). Otherwise the warmup-dependent feature is NaN at the last bar.
  - FORMING BAR: the last bar is live and ticks. For a STABLE bit-exact compare, capture
    OHLCV and read the Pine plot back-to-back, or compare at a CLOSED bar (iloc[-2]).

CLI:  python scripts/tv_capture.py GBPUSD 5          # print last-row 9 primary feats
      python scripts/tv_capture.py GBPUSD 5 --full   # full 73-feat set
"""
from __future__ import annotations
import sys, json
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))
import numpy as np
import pandas as pd
from core.features import (
    compute_features, attach_htf_context,
    compute_smc_features, compute_session_features, compute_htf_interactions,
)
from core.features.engineer import atr as atr_fn

DATA_CAP = REPO / "data" / "tv_capture"


def parse_ohlcv(obj) -> pd.DataFrame:
    """TV data_get_ohlcv result (dict | bars-list | path) -> canonical OHLCV DataFrame."""
    if isinstance(obj, (str, Path)):
        obj = json.loads(Path(obj).read_text(encoding="utf-8"))
    bars = obj["bars"] if isinstance(obj, dict) else obj
    df = pd.DataFrame(bars)
    df["open_time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("open_time").sort_index()
    df = df[["open", "high", "low", "close", "volume"]].astype("float64")
    return df


def load_capture(symbol: str, tf: str, capdir: Path = DATA_CAP) -> pd.DataFrame | None:
    p = capdir / f"{symbol}_{tf}.json"
    return parse_ohlcv(p) if p.exists() else None


def features_from_captures(symbol: str, tf_primary: str = "5", full: bool = False,
                           capdir: Path = DATA_CAP) -> pd.DataFrame:
    """Run the canonical feature engine on captured TV bars (5m primary + 1h/4h HTF).

    Mirrors model_validation_suite.build_extended exactly (minus macro, not in FEATURES_9).
    """
    raw = load_capture(symbol, tf_primary, capdir)
    if raw is None:
        raise FileNotFoundError(f"missing capture: {capdir}/{symbol}_{tf_primary}.json")
    base = compute_features(raw)
    htf_1h = load_capture(symbol, "60", capdir)
    htf_4h = load_capture(symbol, "240", capdir)
    base = attach_htf_context(
        base,
        compute_features(htf_1h) if htf_1h is not None else pd.DataFrame(),
        compute_features(htf_4h) if htf_4h is not None else pd.DataFrame(),
    )
    # Session features carry 2 of the 9 primary feats (in_ny, is_fx_market_open) -> always add.
    atr14 = atr_fn(raw["high"], raw["low"], raw["close"], 14).values
    base = pd.concat([base, compute_session_features(raw, atr14)], axis=1)
    if full:  # smc + htf interactions complete the 73-feat meta set
        ema_align = base["ema_alignment"].fillna(0).values if "ema_alignment" in base.columns else np.zeros(len(base))
        base = pd.concat([base, compute_smc_features(raw, atr14, ema_align),
                          compute_htf_interactions(base)], axis=1)
    return base


def _de(x) -> float:
    """Parse a TV data-window string ('0,50775', '−1,56387') or number -> float."""
    if isinstance(x, (int, float)):
        return float(x)
    return float(str(x).replace("−", "-").replace(" ", "").replace(" ", "").replace(",", "."))


def compare_to_pine(feats: pd.DataFrame, pine: dict, at=None, atol: float = 1e-5) -> bool:
    """Compare Python feature values vs Pine data-window plot values at one bar.

    `pine` keys = plot names = feature column names (pL_* / non-feature keys skipped).
    `at` = timestamp (str/Timestamp) or None -> last row.
    """
    row = feats.iloc[-1] if at is None else feats.loc[pd.Timestamp(at, tz="UTC")]
    print(f"bar = {row.name}   (atol={atol})")
    ok = True
    for k, pv in pine.items():
        if k not in feats.columns:
            continue
        py, pe = float(row[k]), _de(pv)
        d = abs(py - pe)
        flag = "PASS" if d <= atol else "**FAIL**"
        ok &= d <= atol
        print(f"  {k:30s} py={py:+.6f}  pine={pe:+.6f}  |diff|={d:.2e}  {flag}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "GBPUSD"
    tf = sys.argv[2] if len(sys.argv) > 2 else "5"
    full = "--full" in sys.argv
    feats = features_from_captures(sym, tf, full=full)
    cols = [c for c in ["hour_cos", "hour_sin", "rvol_20", "ema_20_dist_atr", "atr_pct",
                        "htf_4h_rsi_14", "is_fx_market_open", "in_ny", "htf_4h_atr_percentile_100"]
            if c in feats.columns]
    print(f"{sym} {tf}m  rows={len(feats)}  (full={full})  last bar = {feats.index[-1]}")
    print(feats[cols].iloc[-1].to_string())
