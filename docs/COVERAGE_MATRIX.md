# PaceAlgo — Coverage-Matrix (verbindliches Produkt-Artefakt)

**Zweck:** Pro Asset/TF der verbindliche Status. Router (ANN-009) UND Marketing richten sich
NACH dieser Tabelle — nie umgekehrt. Dies ist die Launch-Glaubwürdigkeits-Grundlage (Daten, kein Bauchgefühl).
**Version:** 2026-06-03 (finalisiert nach H-EXIT / H-REGIME / Router-Sweeps; harte Signifikanz-Regel eingeführt).

## Stati + HARTE Status-Regel (Nico-locked 2026-06-03)

- **`Edge-Validated`** — NUR wenn ALLE drei gelten: (1) **OOS**-Beleg (nie In-Sample),
  (2) **OOS-PF ≥ 1.3**, (3) **n ausreichend für Signifikanz: n ≥ ~30 UND Bootstrap-CI-Untergrenze > 1.0.**
  → Ein hübscher Daily-PF auf n<30 ist KEIN Edge — er wird **Tool-Only**, egal wie schön die Zahl.
- **`Tool-Only`** — Tier-A läuft sauber, aber kein validierter Edge-Anspruch (PF≈1.0 ODER n zu dünn).
- **`WAIT`** — das Tool empfiehlt aktiv Nicht-Traden (Regime-Gate still / PF<1).

## ⭐ EIN-BLICK-ZUSAMMENFASSUNG

**Rule-Core (Tier A, Live-Pine) über die Benchmark-Suite:** **0 Edge-Validated · 11 Tool-Only · 4 WAIT**
(15/16 Zellen gemessen 2026-06-03; JPN225 D = CAPITALCOM-Feed n/a). 3 Kandidaten für formalen
Walk-Forward geflaggt (GOLD 4h, SILVER 1h, ETH 1h — gut, aber Full-Hist bzw. Ein-Fenster-OOS).
→ **Der Live-Regel-Core trägt NIRGENDS einen MULTI-JAHR-validierten Edge.** Das ist KEIN Defekt — es ist
die Marke (TOOL ≠ EDGE): Tier A ist die ehrliche universelle Utility, nicht die Edge-Quelle.

**Validierte Edge-Coverage des Produkts = die 3 Forschungs-Module (Tier B):** **3 Edge-Validated**
(FX-NY ML · INDEX-DIPBUY · METAL-TREND_L exp.) · 1 Klasse geschlossen (Crypto direktional).
→ Der verkaufbare *Edge* liegt in Tier B, NICHT im Pine-Rule-Core.

## Rule-Core (Tier A, Live-Pine `pace_algo_v1.pine`, Capped/Balanced/Intraday/RR 1.2)

Gemessen 2026-06-03 (Off/Baseline = Live-Config). Intraday = echter OOS ab 2026-01-01;
Daily/4h = Full-History (OOS-Block dort 2–4 Trades = nicht messbar). **Harte Regel angewandt.**

| Asset | Klasse | TF | Fenster | PF | n | WR | MaxDD(R) | Status | Grund |
|---|---|---|---|---|---|---|---|---|---|
| EURUSD | FX | 5m | OOS 2026 | 1.21 | 61 | 54% | 5.8 | **WAIT** | Regime-Gate sagt WAIT (ADX~13 Range); PF-CI spannt 1.0 |
| GBPUSD | FX | 1h | OOS 2026 | 0.85 | 26 | 50% | 5.3 | **WAIT** | PF<1 (Verlust) + n<30 |
| BTCUSDT | Crypto | 1h | OOS 2026 | 1.04 | 56 | 50% | 7.7 | **Tool-Only** | PF≈1.0, CI spannt 1.0 |
| NAS100 | Index | 4h | Full-Hist | 1.05 | 55 | 51% | 6.0 | **Tool-Only** | PF≈1.0 |
| US500 | Index | Daily | Full-Hist | 1.38 | 18 | 56% | 4.0 | **Tool-Only** | **n<30** (PF hübsch, aber nicht signifikant) |
| NAS100 | Index | Daily | Full-Hist | 4.75 | 12 | 83% | 1.5 | **Tool-Only** | **n<30** (4.75 ist ein 12-Trade-Artefakt) |
| GER40 | Index | Daily | Full-Hist | 1.25 | 13 | 62% | 3.0 | **Tool-Only** | n<30 |
| GOLD | Metall | Daily | Full-Hist | 2.13 | 12 | 67% | 1.0 | **Tool-Only** | **n<30** (war fälschlich „Edge prelim" — korrigiert) |
| SILVER | Metall | Daily | Full-Hist | 1.50 | 10 | 60% | 2.5 | **Tool-Only** | n<30 |
| USDJPY | FX | 4h | Full-Hist | 0.86 | 48 | 46% | 7.0 | **WAIT** | PF<1 (Verlust) |
| USDCAD | FX | Daily | Full-Hist | 1.92 | 10 | 70% | 2.0 | **Tool-Only** | n<30 |
| GER40 | Index | 1h | OOS 2026 | 0.68 | 24 | 42% | 7.3 | **WAIT** | PF<1 + n<30 |
| GOLD | Metall | 4h | Full-Hist | 1.45 | 71 | 59% | 4.5 | **Tool-Only** *(Kandidat)* | n≥30 & PF≥1.3, aber Full-Hist (kein formaler OOS) |
| SILVER | Metall | 1h | OOS 2026 | 1.69 | 36 | 64% | 3.5 | **Tool-Only** *(Kandidat)* | OOS/n36/PF1.69 — aber 1 Fenster + Metall-Klasse <4 Symbole |
| BTCUSDT | Crypto | 4h | Full-Hist | 1.18 | 82 | 56% | 9.3 | **Tool-Only** | PF<1.3 |
| ETHUSDT | Crypto | 1h | OOS 2026 | 1.38 | 48 | 58% | 6.0 | **Tool-Only** *(Kandidat)* | OOS/n48/PF1.38 — aber Crypto „geschlossen" + 1 Fenster |
| SOLUSDT | Crypto | 4h | Full-Hist | 1.29 | 85 | 55% | 7.0 | **Tool-Only** | PF<1.3 |
| JPN225 | Index | Daily | — | — | — | — | — | *nicht gemessen* | CAPITALCOM-Feed lädt nicht (2× versucht) |

**Kandidaten-Vermerk:** GOLD 4h / SILVER 1h / ETH 1h erreichen n≥30 mit PF≥1.3 — aber je Full-History
ODER nur das eine trendige 2026-OOS-Fenster (kein Multi-Jahr/Walk-Forward). Pro harter Regel + Disziplin
(all-years, walk-forward, Klassen-Ebene) **noch KEIN Edge-Badge** — als Kandidaten für formale Validierung
geflaggt (Metall-Klasse hat ohnehin nur 2 Symbole → ≥4-Regel nicht erfüllbar; Crypto ist „geschlossen").

> **Korrektur-Vermerk:** Die früheren Zeilen GOLD/US500 Daily = „Edge-Validated (preliminary)"
> sind unter der harten Regel **falsch** (n=12/18 < 30) → auf **Tool-Only** korrigiert. Genau dafür
> ist die Signifikanz-Regel da: dünne Daily-PFs nicht als Edge verkaufen.

## Validierte Module (Tier B — voll OOS, Quelle: `module_registry.md`)

| Modul | Klasse | TF | Status | OOS-Beleg (n + Methode) |
|---|---|---|---|---|
| FX-NY (ML) | FX-Majors (5 long, USDCHF short) | 5m | **Edge-Validated** | Walk-Forward 20 Folds, net PF 1.51 sized, ~9 Trades/Tag (n hoch) (`fx_module_LOCK.md`) |
| INDEX-DIPBUY | Indizes (10) | Daily | **Edge-Validated** | Echtes Zeit-Holdout 2015–21: PF 1.63, WR 74% (`index_dipbuy_LOCK.md`) |
| METAL-TREND_L | Gold/Silber | Daily | **Edge-Validated (Experimental)** | 27/27 Grid, Zeit-Hälften 1.70/1.27 — ⚠️ nur 2 Symbole, n dünn (phase13b) |
| Crypto direktional | Crypto | alle | **geschlossen** | phase11a–c (beste Daten, echte Fees) → Tool-Only/WAIT |

### Pine-Export-Status (Tier B → Produkt, Stand 2026-06-08)

Die Tier-B-Module sind in der RESEARCH **Edge-Validated**, aber erst im PRODUKT wirksam, wenn sie
bit-exact nach Pine exportiert + live verifiziert sind. Bis dahin KEIN „live"-Edge-Badge im Chart.

| Modul | Research | Pine-Export | Live im Produkt |
|---|---|---|---|
| **FX-NY (ML)** | ✅ Edge-Validated | 🟡 **in Arbeit** — Cascade-Math 0.0 diff, Codegen kompiliert; Features **8/9 bit-exact** (Block-1(a) percentrank ✅ 2026-06-08; Block-1(b) htf_4h_rsi_14-Alignment offen → TV-Verif); Block 2 (Short+Meta+Selektion) ausstehend | ❌ noch nicht → bei whole-chain bit-exact + OOS-Revalidierung → „Edge-Validated (live)" |
| **INDEX-DIPBUY** | ✅ Edge-Validated | ⚪ ausstehend (deterministisch, trivial Pine-bar) | ❌ noch nicht |
| **METAL-TREND_L** | 🟢 Experimental | ⚪ ausstehend | ❌ noch nicht |

## Regime-Dimension (ANN-024 — welches Modul ist pro (Asset,TF) zuständig)

Module: `Trend-Core` (live, Tool-Only) · `MR` (Mean-Reversion, geplant) · `WAIT`.

| Asset | TF | Trend-Regime | Range-Regime | Status |
|---|---|---|---|---|
| GOLD | Daily | Trend-Core (Tool-Only) | MR *(nicht gebaut)* | Range = WAIT bis MR |
| US500 | Daily | Trend-Core (Tool-Only) | MR *(geplant)* | Range = WAIT |
| BTCUSDT | 1h | Trend-Core (Tool-Only) | MR *(geplant)* | beide ohne Edge |
| EURUSD | 5m | Trend-Core (WAIT — Chop) | **MR-Kandidat** (5m-FX viel Range) | WAIT bis MR |

→ Sobald MR-Modul + Regime-Router validiert (H-MR), wandern Range-Phasen von WAIT zu MR.

## Was das für die Ship-vs-MR-Gabel heißt

- **Verkaufbarer Edge = Tier B.** FX-NY ML ist der robusteste (hohes n, Walk-Forward). INDEX-DIPBUY
  solide (echtes Holdout). METAL-TREND_L experimentell (n dünn). Der Live-Rule-Core ist überall Tool-Only.
- **Entscheidung an Nico:** Reicht „1 starkes ML-Modul (FX) + 1 solides (Index) + Tier-A-Tool mit
  ehrlichen Labels" als launch-tragfähig → **Produkt-Polish primär, MR parallel.** Wenn zu dünn →
  **MR-Modul zuerst** (Coverage-Hebel: neue Edge-Quelle in Ranges, n-reich = validierbar).

## Pflege-Regeln

- Jede Benchmark-Suite-Runde aktualisiert diese Tabelle (Datum + Scorecard-Link).
- Status-Promotion (→ Edge-Validated) nur über das Promotion-Gate (`IMPROVEMENT_PROTOCOL.md`,
  Klassen-OOS, nie Einzel-Asset) UND die harte Signifikanz-Regel oben. **Promotion = Nicos Call.**
- Optimierung auf KLASSEN-Ebene — ein Asset bekommt nie eigene Parameter.
