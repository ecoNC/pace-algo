"""
Market State Engine — guarantees: NO lookahead, deterministic, valid states.

The no-lookahead test is the critical one: it proves the state at bar t does
NOT depend on any future bar (the #1 non-negotiable).
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from core.state.market_state import classify_market_state, STATES, TRADEABLE_STATES


def _synthetic(n=1200, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    # random-walk close with regime shifts so we hit trend + range + vol changes
    steps = rng.normal(0, 1.0, n)
    steps[300:500] += 1.2          # trend up
    steps[700:900] -= 1.2          # trend down
    steps[900:1000] *= 4.0         # vol expansion
    close = 100 + np.cumsum(steps) * 0.01
    high = close + np.abs(rng.normal(0, 0.02, n))
    low = close - np.abs(rng.normal(0, 0.02, n))
    o = pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                      "volume": rng.integers(1, 100, n)}, index=idx)
    return o


def test_no_lookahead():
    """State at bar t must equal state computed on the full series, for any t.
    i.e. truncating the future does not change a past classification."""
    o = _synthetic()
    full = classify_market_state(o)
    # check several cut points well past warmup
    for cut in (300, 600, 900, 1100):
        prefix = classify_market_state(o.iloc[:cut + 1])
        # the LAST row of the prefix must match row `cut` of the full run
        for col in ("state", "trend_regime", "vol_regime", "ema_align", "in_ny"):
            a = prefix[col].iloc[-1]
            b = full[col].iloc[cut]
            if isinstance(a, float) and np.isnan(a) and np.isnan(b):
                continue
            assert a == b, f"LOOKAHEAD at t={cut} col={col}: prefix={a} full={b}"


def test_deterministic():
    o = _synthetic(seed=3)
    a = classify_market_state(o)
    b = classify_market_state(o)
    pd.testing.assert_frame_equal(a, b)


def test_valid_states_and_tradeable():
    o = _synthetic(seed=5)
    st = classify_market_state(o)
    assert set(st["state"].unique()).issubset(set(STATES))
    # tradeable iff state in tradeable set
    assert (st["tradeable"] == st["state"].isin(TRADEABLE_STATES)).all()


def test_session_flags():
    idx = pd.to_datetime(["2024-01-02 14:00", "2024-01-02 09:00", "2024-01-02 02:00"], utc=True)
    o = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}, index=idx)
    st = classify_market_state(o)
    assert st["in_ny"].tolist() == [True, False, False]
    assert st["in_london"].tolist() == [True, True, False]
    assert st["session"].tolist() == ["NY", "LONDON", "ASIA"]


def test_warmup_is_quiet():
    o = _synthetic(seed=7)
    st = classify_market_state(o)
    # first bars (before ATR/ADX/EMA200 warmup) must be non-tradeable QUIET
    assert (st["state"].iloc[:50] == "QUIET").all()
    assert not st["tradeable"].iloc[:50].any()


if __name__ == "__main__":
    test_no_lookahead()
    test_deterministic()
    test_valid_states_and_tradeable()
    test_session_flags()
    test_warmup_is_quiet()
    print("All market_state tests passed.")
