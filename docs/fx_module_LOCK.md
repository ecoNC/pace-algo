# PaceAlgo — FX Module LOCK (2026-06-01)

**STATUS: LOCKED.** First validated AI module. Robustness verified (`phase7_fx_lock.py`,
spec: `results/model_validation/phase7_fx_lock_*/fx_lock.json`). Pine export pending
(after crypto module per Nico). Commit family: phase3 `9c3a386` → phase4 `615464d` → this.

---

## Spec (frozen)

| Component | Value |
|---|---|
| Long universe | GBPUSD, USDJPY, USDCAD, NZDUSD, USDCHF |
| Short universe | **USDCHF only** (other shorts thin/decaying — see phase3_short_robustness) |
| Primary ranker | LGBM, **50 trees**, depth 3, 9 features (long-9), long & short |
| Features (9) | hour_cos, hour_sin, rvol_20, ema_20_dist_atr, atr_pct, htf_4h_rsi_14, is_fx_market_open, in_ny, htf_4h_atr_percentile_100 |
| Meta re-rank | secondary LGBM (50t, full-73 features) on the primary's generous candidates |
| Gate | `in_ny` (13–22 UTC) **and** vol_tradeable (state ∉ {QUIET, SHOCK}) |
| Selection | POOLED proba threshold across pairs+dirs, calibrated on validation for **top-10/day** |
| Sizing | proba-tercile 0.5 / 1.0 / 1.5× (optional "Aggressive" mode) |
| Execution | R = 1.5 (TP 1.5·ATR / SL 1.0·ATR, 24-bar time barrier), entry next-bar-open, one position |
| Timeframe | 5m |

---

## Robustness (walk-forward, 20 folds 2024–2026, net, multi-seed)

| Spread | net PF | WR | trades/day | % folds >1 | worst fold | median fold | PF 2024/2025/2026 |
|---|---|---|---|---|---|---|---|
| **0.3 pip (ECN)** | 1.66 | 0.51 | 9.3 | 90% | 0.96 | 1.60 | 1.31 / 2.10 / 1.83 |
| **0.5 pip (ECN)** | 1.51 | 0.51 | 9.3 | 80% | 0.88 | 1.45 | 1.18 / 1.92 / 1.66 |
| 1.0 pip (retail) | 1.18 | 0.51 | 9.3 | 60% | 0.69 | 1.15 | 0.91 / 1.53 / 1.31 |

**Verdict: real & robust at ECN spreads (0.3–0.5 pip)** — all years positive, ≥80% folds
positive, worst fold only −12%, 2026 strong. **Conditional**: at retail 1.0 pip it is
marginal (60% folds, 2024 negative) — do not promise retail-spread performance.

Non-edge sizing core (no sizing) = PF ~1.30 @0.5pip; sizing lifts to ~1.51 at higher
variance. Sizing is an optional capital mode, not the robustness base.

---

## Why we trust it (methodology)

- Walk-forward rolling quarters (each test quarter unseen), multi-seed.
- Net of spread + next-bar-open (gross numbers banned).
- Per-year positive, per-pair long edge broad (all 5 pairs >1.34); short curated to the
  one robust pair (USDCHF).
- No lookahead: POOLED threshold + meta candidate cut calibrated on validation only.
- Edge mechanism understood: ML selection within the NY-gated population; meta removes
  conditional false positives. Not a black-box backtest fit.

## Honest limitations

- Thin edge (PF 1.3 core), **ECN-dependent**. Not a money-printer.
- FX-majors + NY-session specific (does not generalize — see phase5/6).
- Pine cost: primary+meta = 4 cascades @50t ≈ 88% of ops budget (fits).

---

## Pine-Export — KANONISCHE Selektions-Ketten-Spec (Block 2, encoded 2026-06-08)

Abgeleitet 1:1 aus `scripts/fx_production_train.py` (+ `phase3_v1_config.build_cands`,
`phase3_selection_compare.calib_thr`, `phase4_ensemble_sizing.tier_size`). Block 2 baut
GENAU das; die Python-Whole-Chain-Referenz nutzt dieselben fixen Snapshot-Werte.

### Ketten-Reihenfolge (pro Bar, beide Richtungen)
1. **Hard-Gate zuerst:** `in_ny AND tradeable` — sonst kein Kandidat.
2. **gen-Gate VOR meta (Prefilter):** Long-Kandidat wenn `primary_long ≥ gen_long`;
   Short-Kandidat (NUR USDCHF) wenn `primary_short ≥ gen_short`.
3. **meta = Ranking-Score:** für gen-Passer ist der Score die Meta-Proba (meL/meS, 73-Feat);
   Nicht-Passer effektiv ausgeschlossen (−1e9).
4. **POOLED über Richtungen+Paare:** Long (alle Paare) + USDCHF-Short in EINE Liste,
   nach Meta-Proba absteigend, pro Bar-Row dedupliziert (höhere Meta-Proba gewinnt die Richtung).
5. **Signal feuert wenn** gepoolte Meta-Proba `≥ pooled_thr`.
6. **Sizing** auf finaler Meta-Proba: `< size_q1 → 0.5R · < size_q2 → 1.0R · sonst → 1.5R`.

### Thresholds — ALLE fix aus `artifacts/models/fx_ship_snapshot.json` (keine Laufzeit-Rekalibrierung)
`gen_long=0.49943 · gen_short=0.49643 · pooled_thr=0.49287 · size_q1=0.50753 · size_q2=0.61798`
(trees=50, seed=42, topn=10, gen_mult=3.0). `calib_thr` läuft NUR im Training → eingefroren.

### 🔒 Drei Verdrahtungs-Locks (bit-exact-grün-aber-falsch-Fallen — Nico-locked 2026-06-08)
1. **Sizing-Quantile sind FIX, nicht live.** `tier_size()` rechnet im Eval `np.quantile(sel.proba,…)`
   live über die Selektion — das ist **Look-at-all-trades / Look-ahead** und in Pine strukturell
   unmöglich. **Die fixen `size_q1/size_q2` aus dem Snapshot sind die KANONISCHE WAHRHEIT**, nicht
   das Live-`tier_size`. Pine UND die Python-Whole-Chain-Referenz nutzen die fixen Werte. ⚠️ NICHT
   später „zurückfixen" auf das Live-Quantil — das wäre eine Regression zu einer Look-ahead-Definition.
2. **`tradeable`-Gate bit-exact portieren, NICHT approximieren.** Quelle: `core/state/market_state.py`
   `classify_market_state` (ATR-Perzentil; state ∈ {QUIET,SHOCK} = nicht tradeable). Es ist Teil des
   Hard-Gates, das die Trainings-Trade-Population definiert hat (PF 1.51). Ein anderes Gate (z.B. ADX)
   → andere Trade-Menge → stiller Validitäts-Bruch, nicht nur bit-exact-Wackeln. Eigener bit-exact-Punkt.
3. **USDCHF-Short-Asymmetrie.** Short-Pfad NUR auf USDCHF (`syminfo`-Check), sonst long-only. Nicht-
   offensichtliche Asymmetrie — sichtbar dokumentiert, damit ein späterer Reviewer nicht „vereinheitlicht".

### Zwei getrennte Gates — NICHT verschmelzen
- **Tier-A-Tool:** ADX-Regime-Gate (für WAIT-Optik) — `pace_algo_v1.pine`.
- **FX-Modul (Edge):** `classify_market_state` ATR-Perzentil-`tradeable`-Gate (für Edge-Selektion).
Unterschiedlicher Zweck, unterschiedliche Logik. Im Code klar getrennt benannt halten.

### Block-2 Build-Sequenz (Nico-locked 2026-06-08 — Risiko-zuerst = Debugging-Hygiene)
Signal-Logik KOMPLETT vor Display. In dieser Reihenfolge:
1. **`classify_market_state`-`tradeable`-Port nach Pine + bit-exact ZUERST.** Das Gate definiert
   die Trade-Population → zuerst pinnen isoliert die Fehlerquelle: ab dann ist die Trade-Menge
   garantiert korrekt, jeder spätere Diff liegt eindeutig an Cascade/Sizing, nicht am Gate.
2. **4 Cascades** (Primary L/S 9-Feat + Meta L/S 73-Feat) ins Skelett.
3. **Selektions-Kette** (gen→meta→POOLED→Sizing, fixe Snapshot-Thresholds).
4. **Whole-Chain bit-exact** (siehe Regel unten).
5. **FX-Display-Modus** (Modus-Toggle im `pace_algo_v1.pine`, KEIN Routing-Layer) — erst NACHDEM
   die Signal-Kette grün ist. Display auf unverifizierter Selektion = gefährlichste Variante
   (sieht fertig aus, ist es nicht).

### Whole-Chain-Check: MENGEN-Identität VOR Wert-Identität (Nico-locked)
Beim whole-chain-Lauf ZUERST prüfen: feuern Pine und Python auf **exakt denselben Entry-Bars**
(Trade-Menge identisch)? DANN erst die Werte (Proba/Sizing pro Trade). Ein reiner Wert-Vergleich
kann grün sein, während Pine in Wahrheit eine andere (zufällig zahlengleiche) Selektion fährt.
Erst Mengen-Identität, dann Wert-Identität.
