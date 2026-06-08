"""Verify the Pine _pf_pctrank100 algorithm is bit-exact to the training definition.

Training (source of truth, engineer.py:165):
    atr.rolling(100, min_periods=100).rank(pct=True)   # method='average'

Pine _pf_pctrank100 (core/export/pine_features.py) reimplemented here 1:1:
    over the trailing 100-bar window INCLUDING current bar, requiring 100 non-na obs:
        average_rank = less + (eq + 1) / 2     # eq includes self
        result       = average_rank / 100.0

This closes Block-1 bit-exact risk (a): htf_*_atr_percentile_100.
Run: python scripts/verify_pctrank_pine_parity.py
"""
import numpy as np
import pandas as pd


def pine_pctrank100(values: np.ndarray) -> np.ndarray:
    """Bar-by-bar reimplementation of the Pine _pf_pctrank100 function."""
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(n):
        if i < 99:
            continue
        window = values[i - 99 : i + 1]  # 100 bars incl. self
        cur = values[i]
        if np.isnan(cur) or np.isnan(window).any():  # needs 100 non-na (min_periods=100)
            continue
        less = float(np.sum(window < cur))
        eq = float(np.sum(window == cur))  # includes self
        out[i] = (less + (eq + 1.0) / 2.0) / 100.0
    return out


def main() -> None:
    rng = np.random.default_rng(42)
    cases = {
        "continuous_floats": rng.normal(0.0010, 0.0003, 5000),
        "with_warmup_na": np.concatenate([np.full(13, np.nan), rng.normal(1, 0.5, 4987)]),
        "with_ties": rng.integers(0, 20, 5000).astype(float),  # forces tie handling
    }
    all_ok = True
    for name, arr in cases.items():
        s = pd.Series(arr)
        pandas_ref = s.rolling(100, min_periods=100).rank(pct=True).to_numpy()
        pine = pine_pctrank100(arr)
        both = ~np.isnan(pandas_ref) & ~np.isnan(pine)
        # also require the na-masks to agree (warmup behaviour)
        mask_match = np.array_equal(np.isnan(pandas_ref), np.isnan(pine))
        max_diff = float(np.max(np.abs(pandas_ref[both] - pine[both]))) if both.any() else 0.0
        ok = mask_match and max_diff < 1e-12
        all_ok &= ok
        print(f"[{name:18s}] n_compared={both.sum():5d}  max_abs_diff={max_diff:.2e}  "
              f"na_mask_match={mask_match}  -> {'PASS' if ok else 'FAIL'}")
    print()
    print("RESULT:", "PASS — Pine _pf_pctrank100 == training definition" if all_ok else "FAIL")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
