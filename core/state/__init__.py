"""PaceAlgo V2 — deterministic, regel-basierte Trading-Engine (state-driven)."""

from .market_state import (
    classify_market_state,
    STATES,
    TREND_UP, TREND_DOWN, RANGE,
    QUIET, NORMAL, EXPANSION, SHOCK,
    DEFAULT_PARAMS,
)

__all__ = [
    "classify_market_state",
    "STATES",
    "TREND_UP", "TREND_DOWN", "RANGE",
    "QUIET", "NORMAL", "EXPANSION", "SHOCK",
    "DEFAULT_PARAMS",
]
