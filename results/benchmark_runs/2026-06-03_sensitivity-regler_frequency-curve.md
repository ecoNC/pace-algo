# Benchmark-Run — Sensitivity-Regler: Frequenz/Qualitäts-Kurve

**Datum:** 2026-06-03 (Heim-PC, TV 3.2.0, CDP). Commit `5c9df11`.
**Zweck:** Verifizieren, dass der neue `sens`-Regler (a) bei 0 die Baseline reproduziert,
(b) die Trade-Frequenz MONOTON steuert, (c) den Frequenz/Qualität-Tradeoff ehrlich abbildet.
**Setup:** Balanced/Intraday/RR1.2, Full-History. `sens` skaliert ADX-Schwelle (−2/Stufe),
baseMult (−0.2/Stufe), fastLen (−1/Stufe) zusammen. + = lockerer/mehr, − = strenger/weniger.

## Kurve A — GBPUSD 1h (Chop-Chart, ADX-Trend aber marginal)

| sens | Trades | Net PF | WR | Total R | Verdict |
|---|---|---|---|---|---|
| −2 | 60  | **1.29** | 56.7% | 7.5  | Conservative |
| −1 | 78  | 1.17 | 53.8% | 6.0  | Conservative |
| 0  | 96  | 0.97 | 50.0% | −1.5 | WAIT |
| +1 | 120 | 0.71 | 42.5% | −20.3| WAIT |
| +2 | 133 | 0.69 | 42.1% | −24.2| WAIT |

→ Auf Chop: **strenger = besser.** Mehr Signale zerstören PF (0.69 @ 133t). Optimum bei sens −2.

## Kurve B — NAS100 1h (sauberer Trend, MTF Bull-Konsensus)

| sens | Trades | Net PF | WR | Total R | Verdict |
|---|---|---|---|---|---|
| −2 | 61  | 0.92 | 50.8% | −2.5 | WAIT |
| 0  | 109 | 1.25 | 56.9% | 11.8 | Balanced |
| +2 | 160 | **1.27** | 56.9% | **18.7** | Balanced |

→ Auf sauberem Trend: **lockerer = besser.** Mehr Signale halten den PF (1.27) und vervielfachen
den Gesamtprofit (Total R 11.8 → 18.7). Optimum bei sens +2. **Genau gegenläufig zu GBPUSD.**

## Befunde

1. **Korrektheit:** sens=0 reproduziert exakt die Baseline (GBPUSD .97/96t, NAS100 1.25/109t). ✓
2. **Monotonie:** Trade-Zahl steigt streng mit sens (GBP 60→78→96→120→133; NAS 61→109→160). ✓
   Der Regler tut genau, was er soll — eine sauber steuerbare Frequenz-Achse.
3. **Frequenz/Qualität-Tradeoff bestätigt, ABER regime-abhängig:** das OPTIMALE sens ist NICHT
   global — Chop will streng (−2), Trend will locker (+2). Kein „mehr Signale = mehr Profit" und
   kein „weniger = besser"; es hängt vom Regime ab. **Genau deshalb ist es eine User-Achse, kein
   fixer Wert** (roadmap §5, gelockt) — und kein Edge-Claim.
4. **Verdict-Kopplung wirkt mit:** das Recommended-Panel flippt mit dem gemessenen PF (GBPUSD −2 →
   Conservative tradeable; NAS100 −2 → WAIT). Der User sieht direkt, welche Sensitivity auf dem
   Chart trägt.

## Implikation / Follow-up

Die Regime-Abhängigkeit des optimalen `sens` ist dasselbe Trend/Chop-Signal wie H-REGIME — aber
hier **als User-Achse exponiert statt auto-geroutet**, was das Validierungs-Problem von H-REGIME
umgeht (kein PF-Versprechen, nur Frequenz-Steuerung). **Natürlicher Follow-up:** das Recommended-
Panel schlägt eine Sensitivity vor (Trend → +, Chop → −) — reines UX-Guidance, kein Edge. Nicht
als nächstes nötig; notiert.

Default bleibt sens=0. Regler ist live-tauglich (verifiziert, kompiliert, monoton).
