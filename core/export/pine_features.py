"""Pine v6 code snippets per V1 feature — registry-based lookup.

NB15c picks the subset that the production booster actually references
(via extract_feature_usage) and only emits Pine code for those — Path B
of Build 2: minimal, data-driven, no dead-feature surface area.

Anti-Look-Ahead Discipline (ANN-018):
- All HTF (1h) reads use barmerge.lookahead_off + [1] shift
- Lower-TF features computed on closed bars only
- No high/low references in signal logic — only close-derived inputs

Source-of-Truth: core/features/engineer.py + core/features/htf_interaction.py
(these Pine snippets are line-by-line transliterations of those modules)
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Pre-computed indicators emitted ONCE per Pine file before any feature line
# ---------------------------------------------------------------------------

HELPERS_HEADER = """// === Pre-computed indicators (V1 feature engine) ===
_atr14         = ta.atr(14)
_safe_atr      = _atr14 > 0.0 ? _atr14 : na
_ema20         = ta.ema(close, 20)
_ema50         = ta.ema(close, 50)
_ema200        = ta.ema(close, 200)
_rsi14         = ta.rsi(close, 14)
// Pine v6: ta.adx() reported "not found" in some environments — use ta.dmi() instead
[_diPlus_local, _diMinus_local, _adx14] = ta.dmi(14, 14)
_swing_hi_20   = ta.highest(high, 20)
_swing_lo_20   = ta.lowest(low, 20)
_vol_sma20     = ta.sma(volume, 20)
_vol_std50     = ta.stdev(volume, 50)
_log_ret       = nz(math.log(close / close[1]), 0.0)
_ema_alignment = _ema20 > _ema50 and _ema50 > _ema200 ? 1.0 :
                 _ema20 < _ema50 and _ema50 < _ema200 ? -1.0 : 0.0
_macd_fast     = ta.ema(close, 12)
_macd_slow     = ta.ema(close, 26)
_macd_line     = _macd_fast - _macd_slow
_macd_signal   = ta.ema(_macd_line, 9)
_macd_hist     = _macd_line - _macd_signal
_macd_hist_atr = _macd_hist / _safe_atr
_atr_pct_rank  = ta.percentrank(_atr14, 100) / 100.0
// --- Session/time + Vol-Expansion helpers ---
_hour_utc      = hour(time, "UTC")
_min_utc       = minute(time, "UTC")
_frac_hour     = _hour_utc + _min_utc / 60.0
_dow_utc       = dayofweek(time, "UTC")
_atr_avg_50    = ta.sma(_atr14, 50)
_vol_ratio     = _atr_avg_50 > 0.0 ? _atr14 / _atr_avg_50 : 1.0
"""


# ---------------------------------------------------------------------------
# HTF (1h) context — pulled via request.security with lookahead_off + [1] shift
# IMPORTANT: each request.security call counts against Pine's 40-call budget
# ---------------------------------------------------------------------------

HTF_HEADER = """// === HTF (1h) context — anti-look-ahead via [1] shift ===
// Pine v6 disallows complex inline expressions in request.security() —
// we wrap each HTF computation in a helper function (standard pattern).
_pf_htf_rsi() =>
    ta.rsi(close, 14)

_pf_htf_atr_pct() =>
    ta.percentrank(ta.atr(14), 100) / 100.0

_pf_htf_ema_align() =>
    _e20 = ta.ema(close, 20)
    _e50 = ta.ema(close, 50)
    _e200 = ta.ema(close, 200)
    _e20 > _e50 and _e50 > _e200 ? 1.0 : _e20 < _e50 and _e50 < _e200 ? -1.0 : 0.0

_htf_1h_rsi14_raw     = request.security(syminfo.tickerid, "60", _pf_htf_rsi()[1],       barmerge.gaps_off, barmerge.lookahead_off)
_htf_1h_atr_pct_raw   = request.security(syminfo.tickerid, "60", _pf_htf_atr_pct()[1],   barmerge.gaps_off, barmerge.lookahead_off)
_htf_1h_ema_align_raw = request.security(syminfo.tickerid, "60", _pf_htf_ema_align()[1], barmerge.gaps_off, barmerge.lookahead_off)

_htf_1h_rsi14        = nz(_htf_1h_rsi14_raw, 50.0)
_htf_1h_atr_pct_safe = nz(_htf_1h_atr_pct_raw, 0.5)
_htf_1h_ema_align    = nz(_htf_1h_ema_align_raw, 0.0)
"""


# ---------------------------------------------------------------------------
# Per-feature Pine expressions
# Keys MUST match feature_name from core/features/* (no aliasing)
# ---------------------------------------------------------------------------

FEATURE_REGISTRY: dict[str, str] = {
    # === Session (cyclical hour encoding) ===
    'hour_sin': 'math.sin(2.0 * math.pi * (hour(time, "UTC") + minute(time, "UTC") / 60.0) / 24.0)',
    'hour_cos': 'math.cos(2.0 * math.pi * (hour(time, "UTC") + minute(time, "UTC") / 60.0) / 24.0)',

    # === Volatility ===
    'atr_pct':             '_atr14 / close',
    'atr_percentile_100':  '_atr_pct_rank',
    'realized_vol_20':     'ta.stdev(_log_ret, 20) * math.sqrt(20)',

    # === Trend ===
    'adx_14':              '_adx14',
    'ema_20_dist_atr':     '(close - _ema20) / _safe_atr',
    'ema_20_slope_atr':    '(_ema20 - _ema20[5]) / _safe_atr',

    # === Momentum ===
    'momentum_composite':  '(_rsi14 - 50.0) / 50.0 + math.tanh(_macd_hist_atr)',

    # === Structure ===
    'dist_to_swing_high_atr': '(_swing_hi_20 - close) / _safe_atr',
    'dist_to_swing_low_atr':  '(close - _swing_lo_20) / _safe_atr',

    # === Volume ===
    'rvol_20':             'volume / nz(_vol_sma20, 1.0)',
    'volume_z_score':      '(volume - _vol_sma20) / nz(_vol_std50, 1.0)',

    # === HTF (1h) raw ===
    'htf_1h_rsi_14':              '_htf_1h_rsi14',
    'htf_1h_atr_percentile_100':  '_htf_1h_atr_pct_safe',

    # === HTF × LTF Interactions ===
    'htf_ltf_agree_bull':       '(_ema_alignment > 0.5 and _htf_1h_ema_align > 0.5) ? 1.0 : 0.0',
    'htf_ltf_agree_bear':       '(_ema_alignment < -0.5 and _htf_1h_ema_align < -0.5) ? 1.0 : 0.0',
    'htf_ltf_counter_trend':    '((_ema_alignment > 0.5 and _htf_1h_ema_align < -0.5) or (_ema_alignment < -0.5 and _htf_1h_ema_align > 0.5)) ? 1.0 : 0.0',
    'htf_ltf_alignment_score':  '_ema_alignment * _htf_1h_ema_align',
    'ltf_rsi_minus_htf_rsi':    '_rsi14 - _htf_1h_rsi14',
    'both_rsi_oversold':        '(_rsi14 < 35.0 and _htf_1h_rsi14 < 40.0) ? 1.0 : 0.0',
    'both_rsi_overbought':      '(_rsi14 > 65.0 and _htf_1h_rsi14 > 60.0) ? 1.0 : 0.0',
    'vol_pct_diff_htf':         '_atr_pct_rank - _htf_1h_atr_pct_safe',
    'both_high_vol':            '(_atr_pct_rank > 0.7 and _htf_1h_atr_pct_safe > 0.7) ? 1.0 : 0.0',
    'both_low_vol':             '(_atr_pct_rank < 0.3 and _htf_1h_atr_pct_safe < 0.3) ? 1.0 : 0.0',
    'pullback_in_bull':         '(_htf_1h_ema_align > 0.5 and _rsi14 < 45.0) ? 1.0 : 0.0',
    'pullback_in_bear':         '(_htf_1h_ema_align < -0.5 and _rsi14 > 55.0) ? 1.0 : 0.0',

    # === Session Flags (core/features/session.py) ===
    'in_asia':                  '(_hour_utc >= 23 or _hour_utc < 8) ? 1.0 : 0.0',
    'in_london':                '(_hour_utc >= 8 and _hour_utc < 17) ? 1.0 : 0.0',
    'in_ny':                    '(_hour_utc >= 13 and _hour_utc < 22) ? 1.0 : 0.0',
    'in_london_ny_killzone':    '(_hour_utc >= 13 and _hour_utc < 17) ? 1.0 : 0.0',
    'in_asia_london_overlap':   '(_hour_utc >= 8 and _hour_utc < 9) ? 1.0 : 0.0',
    'in_us_open_killzone':      '(_frac_hour >= 13.5 and _frac_hour < 15.5) ? 1.0 : 0.0',
    'in_london_open_killzone':  '(_hour_utc >= 8 and _hour_utc < 10) ? 1.0 : 0.0',
    # Pine FX charts only render bars during market hours, so this is
    # effectively always 1.0 — but emit it explicitly to match training.
    'is_fx_market_open':        '(_dow_utc == dayofweek.sunday and _hour_utc >= 22) ? 1.0 : (_dow_utc >= dayofweek.monday and _dow_utc <= dayofweek.friday) ? 1.0 : 0.0',

    # === Vol-Expansion (core/features/session.py vol_expansion_features) ===
    'vol_expansion_ratio':      '_vol_ratio',
    'vol_expanding':            '_vol_ratio > 1.2 ? 1.0 : 0.0',
    'vol_contracting':          '_vol_ratio < 0.8 ? 1.0 : 0.0',
    # ta.barssince returns na if condition has never been true — fall back to 99.
    'bars_since_vol_spike':     'math.min(99.0, nz(ta.barssince(_vol_ratio > 1.5), 99))',
}


# Features that require HTF_HEADER to be emitted (anything reading 1h state)
_HTF_DEPENDENT_PREFIXES = ('htf_', 'both_', 'pullback_')
_HTF_DEPENDENT_EXACT = {'vol_pct_diff_htf', 'ltf_rsi_minus_htf_rsi'}


def render_feature_engine(used_features: list[str]) -> dict:
    """Compose the Pine feature-engine block for the booster's referenced features.

    Soft-fail semantics (Nicos Build-2-Direktive):
    Features without a Pine snippet are AUTO-DROPPED and emitted with a
    fallback value of 0.0 — the booster's tree splits on dropped features
    will then behave as if the feature is 0 in Pine. This lets a single
    low-impact missing feature not block the entire export. The dropped
    list is surfaced in the return so the caller can log + persist it
    into snapshot.json.

    Args:
        used_features: subset of FEATURE_REGISTRY keys (from
            pine_codegen.extract_feature_usage(...)['used_features'])

    Returns:
        dict with:
        - 'helpers': always-emitted indicator pre-computations
        - 'htf':     HTF_HEADER if any HTF-dependent IMPLEMENTED feature
                     is used, else ''
        - 'features': per-feature variable definitions; dropped features
                      get a `f_<name> = 0.0  // DROPPED` line
        - 'feature_arg_list': comma-separated f_<name> args in original
                      used_features order (passes into cascade unchanged)
        - 'dropped_features': list of feature names with no Pine impl —
                      Pine output will substitute 0.0 for them. Caller
                      should log this; non-empty list means Pine predictions
                      will diverge slightly from booster.predict() for any
                      tree branch that splits on a dropped feature.
        - 'missing': DEPRECATED — always empty list (kept for backward compat,
                     legacy callers can drop the check).
    """
    implemented = [f for f in used_features if f in FEATURE_REGISTRY]
    dropped = [f for f in used_features if f not in FEATURE_REGISTRY]

    # HTF header only needed if at least one IMPLEMENTED feature reads HTF
    needs_htf = any(
        f.startswith(_HTF_DEPENDENT_PREFIXES) or f in _HTF_DEPENDENT_EXACT
        for f in implemented
    )

    feat_lines: list[str] = []
    feat_lines.append('// === V1 Features (referenced by booster) ===')
    for fname in implemented:
        snippet = FEATURE_REGISTRY[fname]
        feat_lines.append(f"f_{fname} = {snippet}")

    if dropped:
        feat_lines.append('')
        feat_lines.append('// === DROPPED (no Pine impl — fallback to 0.0) ===')
        feat_lines.append('// Booster references these; add to FEATURE_REGISTRY for full fidelity.')
        for fname in dropped:
            feat_lines.append(f"f_{fname} = 0.0  // DROPPED")

    # arg_list keeps original order — that's how the cascade signature is built
    arg_list = ", ".join(f"f_{n}" for n in used_features)

    return {
        'helpers':           HELPERS_HEADER,
        'htf':               HTF_HEADER if needs_htf else '',
        'features':          '\n'.join(feat_lines),
        'feature_arg_list':  arg_list,
        'dropped_features':  dropped,
        'missing':           [],   # deprecated — kept for legacy callers
    }


def supported_features() -> list[str]:
    """Sorted list of all feature names with a Pine implementation."""
    return sorted(FEATURE_REGISTRY.keys())
