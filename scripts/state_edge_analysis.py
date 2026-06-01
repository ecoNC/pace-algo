"""
State Profitability Map (V2 Phase 1) — Edge Attribution per market state.

CRITICAL layer before building setups: which states actually carry net edge,
and in which direction / session / pair? Build setups ONLY on profitable states.

Method (no ML, no setup logic — pure state edge):
  For every bar, simulate the R-based outcome of entering in the state-ALIGNED
  direction (TREND_UP->long, TREND_DOWN->short, RANGE-> both reported),
  TP 1.5*ATR / SL 1.0*ATR / 24-bar barrier, SL-first, NET of spread (1.0 pip).
  Aggregate net PF/WR per (state x session x pair), with per-year stability.

This answers: "Which market states deserve a setup at all?"

Output: results/model_validation/state_edge_<UTC>/state_edge.json
Run: python scripts/state_edge_analysis.py
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import numpy as np
import pandas as pd

from model_validation_suite import DATA_V2
from core.features.engineer import atr as atr_fn
from core.state.market_state import classify_market_state, TREND_UP, TREND_DOWN, RANGE

PAIRS = ["GBPUSD", "USDJPY", "USDCAD"]   # Tier-1 (locked scope); extensible
TB = 24
TP_R, SL_R = 1.5, 1.0
SPREAD_PIP = 1.0   # retail (hard test)


def pip_size(s): return 0.01 if s.endswith("JPY") else 0.0001


def barrier_R(o, h, l, c, atr, direction):
    """Net R per bar for entering (close-entry) in `direction`; NaN if not evaluable."""
    n = len(c); R = np.full(n, np.nan)
    for i in range(n - TB - 1):
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        entry = c[i]
        r = None
        if direction == "long":
            tp, sl = entry + TP_R * a, entry - SL_R * a
            for k in range(i + 1, i + 1 + TB):
                if l[k] <= sl: r = -SL_R; break
                if h[k] >= tp: r = TP_R; break
        else:
            tp, sl = entry - TP_R * a, entry + SL_R * a
            for k in range(i + 1, i + 1 + TB):
                if h[k] >= sl: r = -SL_R; break
                if l[k] <= tp: r = TP_R; break
        if r is None:
            r = 0.0
        R[i] = r
    return R


def pf_wr(rs):
    rs = rs[np.isfinite(rs)]
    if len(rs) < 20:
        return None
    w = int((rs > 0).sum()); gw = rs[rs > 0].sum(); gl = -rs[rs <= 0].sum()
    return dict(n=int(len(rs)), wr=round(w / len(rs), 3),
                pf=round(float(gw / gl), 3) if gl > 0 else 999.0,
                avg_R=round(float(rs.mean()), 4))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = OUT = REPO / "results" / "model_validation" / f"state_edge_{stamp}"
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []   # flat records for the map
    per_pair = {}
    for p in PAIRS:
        df = pd.read_parquet(DATA_V2 / f"{p}_5m.parquet")
        st = classify_market_state(df)
        a = atr_fn(df["high"], df["low"], df["close"], 14).values
        o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
        longR = barrier_R(o, h, l, c, a, "long")
        shortR = barrier_R(o, h, l, c, a, "short")
        spread_R = (SPREAD_PIP * pip_size(p)) / np.where(a > 0, a, np.nan)
        longR_net = longR - spread_R
        shortR_net = shortR - spread_R
        state = st["state"].values
        ny = st["in_ny"].values
        year = df.index.year.values

        # aligned direction per state
        aligned = {TREND_UP: longR_net, TREND_DOWN: shortR_net}
        pp = {}
        for s, R in aligned.items():
            for sess, mask in [("NY", ny), ("nonNY", ~ny)]:
                m = (state == s) & mask & np.isfinite(R)
                d = pf_wr(R[m])
                if d:
                    yrs = {int(y): pf_wr(R[m & (year == y)]) for y in np.unique(year[m])}
                    d["per_year_pf"] = {y: (v["pf"] if v else None) for y, v in yrs.items()}
                    pp[f"{s}/{sess}"] = d
                    rows.append(dict(pair=p, state=s, session=sess, dir=("long" if s == TREND_UP else "short"), **{k: d[k] for k in ("n", "wr", "pf", "avg_R")}))
        # RANGE: report BOTH directions (no inherent bias) — NY only
        for s, R, dname in [(RANGE, longR_net, "long"), (RANGE, shortR_net, "short")]:
            m = (state == RANGE) & ny & np.isfinite(R)
            d = pf_wr(R[m])
            if d:
                pp[f"RANGE_{dname}/NY"] = d
                rows.append(dict(pair=p, state="RANGE", session="NY", dir=dname, **{k: d[k] for k in ("n", "wr", "pf", "avg_R")}))
        per_pair[p] = pp

    # pooled Tier-1 per (state, session, dir): recompute by concatenating — approximate via mean of pair PFs weighted by n
    df_rows = pd.DataFrame(rows)
    print("=== STATE PROFITABILITY MAP (Tier-1, 5m, NET @1.0pip) ===")
    print(f"{'pair':7s} {'state':10s} {'sess':6s} {'dir':5s} {'PF':>6s} {'WR':>5s} {'avgR':>7s} {'n':>7s}")
    for _, r in df_rows.sort_values(["state", "session", "pair"]).iterrows():
        print(f"{r['pair']:7s} {r['state']:10s} {r['session']:6s} {r['dir']:5s} {r['pf']:>6.2f} {r['wr']:>5.2f} {r['avg_R']:>7.3f} {int(r['n']):>7d}")

    # pooled view: mean PF per (state,session,dir) across Tier-1, n-weighted avg_R
    print("\n=== POOLED Tier-1 (mean PF / n-weighted avgR) ===")
    pooled = {}
    for (s, sess, dr), g in df_rows.groupby(["state", "session", "dir"]):
        wavg = float((g["avg_R"] * g["n"]).sum() / g["n"].sum())
        pooled[f"{s}/{sess}/{dr}"] = dict(mean_pf=round(float(g["pf"].mean()), 2),
                                          wavg_R=round(wavg, 4), total_n=int(g["n"].sum()))
        print(f"  {s:10s} {sess:6s} {dr:5s}  mean PF {g['pf'].mean():.2f}  wavgR {wavg:+.4f}  n {int(g['n'].sum())}")

    (OUT / "state_edge.json").write_text(json.dumps(dict(per_pair=per_pair, pooled=pooled,
        params=dict(tp_R=TP_R, sl_R=SL_R, tb=TB, spread_pip=SPREAD_PIP)), indent=2, default=str), encoding="utf-8")
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
