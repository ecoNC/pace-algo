# PaceAlgo — Coverage-Matrix (Tier B: wo gilt was)

**Zweck:** Pro Asset/TF der verbindliche Status der Edge-Schicht. Der Router (ANN-009)
und das Marketing richten sich NACH dieser Tabelle — nie umgekehrt.
**Stati:** `Edge-Validated` (OOS belegt) · `Tool-Only` (Tier A läuft, kein Edge-Anspruch)
· `WAIT` (Tool empfiehlt aktiv Nicht-Traden).

**Integritäts-Regel:** Ein Status `Edge-Validated` setzt OUT-OF-SAMPLE-Beleg voraus —
NIE In-Sample. ⚠️ **Ehrlichkeits-Vermerk zum aktuellen Stand:** die Rule-Core-Zeilen
unten stammen aus Live-History-Sweeps (TV, sichtbare Historie, 2026-06-02) — das ist
noch KEIN formaler OOS-Split. Sie gelten als **preliminary**, bis die Benchmark-Suite
(`BENCHMARK_SUITE.md`) sie mit definiertem Split bestätigt. Die Modul-Zeilen (aus der
Forschung) sind voll OOS-validiert (Walk-Forward bzw. echtes Zeit-Holdout).

## Rule-Core (Tier A Signalpfad) — Stand 2026-06-02, iter3, Balanced/Intraday/RR 1.2

| Asset | Klasse | TF | Status | Best-Config | PF | WR | Validierung |
|---|---|---|---|---|---|---|---|
| GOLD | Metall | Daily | **Edge-Validated** *(preliminary)* | Multi-TP, RR 1.2 (Panel folgt) | 1.27 | 55.9% | Live-Sweep 2026-06-02 |
| US500 | Index | Daily | **Edge-Validated (grenzwertig)** *(preliminary)* | Multi-TP; **RR-Panel-Empfehlung beachten** (1.5 bei starkem Trend → PF zurück Richtung 1.26) | 1.14 | 52.9% | Live-Sweep 2026-06-02 |
| BTCUSDT | Crypto | 1h | **Tool-Only** | **Single-TP default** (Multi-TP schadet dort: PF 1.01→0.85, BE-Whipsaw) | 1.01 (Single) | 45.6% | Live-Sweep 2026-06-02 |
| EURUSD | FX | 5m | **WAIT** | — (Regime-Gate hält still; Restverlust strukturell, deckt ANN-020) | 0.85 | 45.8% | Live-Sweep 2026-06-02 |

## Validierte Module (Tier B Gehirne — voll OOS, Quelle: `module_registry.md`)

| Modul | Klasse | TF | Status | OOS-Beleg |
|---|---|---|---|---|
| FX-NY (ML) | FX-Majors (5 Paare long, USDCHF short) | 5m | **Edge-Validated** | Walk-Forward 20 Folds, net PF 1.51 sized (`fx_module_LOCK.md`) |
| INDEX-DIPBUY | Indizes (10) | Daily | **Edge-Validated** | Echtes Zeit-Holdout 2015–21: PF 1.63, WR 74% (`index_dipbuy_LOCK.md`) |
| METAL-TREND_L | Gold/Silber | Daily | **Edge-Validated (Experimental)** | 27/27 Grid, Zeit-Hälften 1.70/1.27 (phase13b) |
| Crypto direktional | Crypto | alle | **geschlossen** | phase11a–c (beste Daten, echte Fees) → Tool-Only/WAAIT |

## Pflege-Regeln

- Jede Benchmark-Suite-Runde aktualisiert diese Tabelle (Datum + Scorecard-Link).
- Status-Promotion (→ Edge-Validated) nur über das Promotion-Gate des
  `IMPROVEMENT_PROTOCOL.md` (Klassen-OOS, nie Einzel-Asset). **Promotion = Nicos Call.**
- Optimierung passiert auf KLASSEN-Ebene — ein Asset bekommt nie eigene Parameter.
