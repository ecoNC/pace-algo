# Benchmark Run — H-TIMESTOP (ANN-027, Hypothese 3/3, letzte)

**Datum:** 2026-06-10 (UTC) · **Workstation:** arbeits-pc · **Status:** PRE-REGISTRATION — Spec-N-Lock ausstehend, Sweep wartet auf CEO-Lock

## Hypothese — wörtlich aus ANN-027 zitiert (keine Umdeutung)

> **H-TIMESTOP — Zeit-Stop (neue Achse: tote Trades schneiden)**
> - **Achse:** Trades, die nach **N Bars** weder TP1 noch strukturellen Fortschritt zeigen, zu Markt
>   schließen. Orthogonal zu allen getesteten preis-basierten Exits.
> - **These:** senkt Loss-Größe + Hängepartien (Feel-Faktor). Prior moderat.

Schwelle **N ist in ANN-027 offen** → 3 threshold-saubere Kandidaten unten, **EINER wird gelockt**,
kein Grid.

## Spec (Definition fix, nur N offen) — ⚠ N-LOCK AUSSTEHEND

**Zeit-Stop-Regel:** an jedem confirmed Bar mit offener Position: wenn `bar_index − entryBar ≥ N`
**UND TP1 noch nicht erreicht** (`tp1Hit == false`) → Position **zu Markt** (current close) schließen,
realisiertes R buchen. Ist TP1 bereits erreicht (Runner aktiv = struktureller Fortschritt da), greift
der Zeit-Stop NICHT — normaler Trail/TP2/BE managt weiter.

„Struktureller Fortschritt" = TP1 (1R) erreicht. Bewusst an den bestehenden TP1-Marker gebunden
(kein zweiter Tuning-Parameter). **N ist der EINZIGE Parameter, vorab fix, kein Nachtunen.**

### N-Kandidaten (einer zu locken) — N in Bars (TF-relativ, kein Per-Asset-Fit)

| Kandidat | N | Charakter | real (5m / 1h / 4h / D) |
|---|---|---|---|
| A | 12 | aggressiv — schneidet früh | 1 h / 12 h / 2 T / 12 T |
| B | 24 | moderat | 2 h / 24 h / 4 T / 24 T |
| C | 36 | locker — nur echte Hängepartien | 3 h / 36 h / 6 T / 36 T |

Bars als Einheit ist die natürliche, fit-freie Wahl für einen bar-basierten Indikator (TF-relativ).

## Methode — gepaarter A/B (KEINE Partition — Trades ändern sich)

**Wichtig (methodische Korrektur vorab):** H-SESSION/H-TRIGGER waren Partitionen (Trade-Menge fix,
Wiring trivial). Ein Zeit-Stop **verändert Exits** → und damit, in einem **One-Position-System**,
potenziell auch die **Entry-Menge**: ein früher Zeit-Stop macht das System früher flat → es kann ein
Signal nehmen, das die Baseline (noch im Trade) übersprungen hätte. **Die Invariante „Entries exakt
identisch" hält daher NICHT exakt** — Entry-Divergenz ist hier ein **echtes Verhalten**, kein Bug.

**Korrigierter Wiring-/Sanity-Check:**
- Entry-Delta zwischen Baseline und Time-Stop wird **gemessen und reportet**, nicht auf 0 gezwungen.
- **Klein (≲ 5–10 %)** = erwartet, A/B bleibt valide (PF-Differenz primär exit-getrieben).
- **Groß** = Effekt vermischt Exit- mit Entry-Selektion → Flag + Vorsicht in der Interpretation.

**Probe (Dual-Engine in EINEM Lauf, kein Input-Toggle):**
`deploy_pine/experiments/pace_algo_v1_HTIMESTOP_probe.pine` — Engine byte-identisch als Baseline
(bestehende Akkumulatoren = „OHNE"), PLUS eine zweite, unabhängige Positions-State-Machine `ts*`,
die dieselben Entry-Signale nimmt (eigener Flat-State), dieselbe Multi-TP-Exit-Logik fährt **plus**
den Zeit-Stop = „MIT". Beide Varianten aus einem Read/Asset (kein 11×2-Toggle-Friction).
Read-only „H-TIMESTOP"-Tabelle: je Variante PF / Entries(n) / WR / AvgR / MaxDD + #zeitgestoppte
Trades + Ø-Loss-R + Ø-Dauer(Bars).

## Fenster & Scope

statsFrom = **2025-01-01** (steht in TV). **Alle 16 Suite-Punkte testbar** — Zeit-Stop ist
TF-agnostisch, KEINE Intraday-Restriktion (anders als H-SESSION/H-TRIGGER) → auch die 5 Daily-Punkte
zählen. Weniger Starvation-Risiko. Max 2 Runden, Runde 2 (Full-History) nur bei Starvation, FINAL.

## Keep-Kriterium GRÜN (alle müssen erfüllt sein) — pre-registriert

- **(a) Breite:** je Klasse ≥ 2 verwertbare Punkte (n ≥ 12), **Mehrzahl PF(mit) − PF(ohne) > 0**.
- **(b) Kein Einzelpunkt-Hebel:** stärksten Lift-Punkt rausrechnen → Richtung hält je Klasse.
- **(c) Mechanismus-Kontrolle (entscheidend):** der PF-Lift muss **primär aus verkürzten Verlierern**
  kommen — Ø-Loss-R UND/ODER Ø-Trade-Dauer der Verlierer sinkt MIT Zeit-Stop. Kommt der Lift aus
  zufällig „geretteten" Gewinnern oder ohne Loss-Verkürzung → **Rauschen, nicht der Mechanismus** →
  kein GRÜN. Entry-Delta muss klein sein (sonst Exit/Entry-Vermischung).
- **Promotion-Gate** unverändert: ≥ +0.05 PF Klassen-Median-Lift, keine Klassen-Regression.

## Pivot-Messlatte (Besonderheit H-TIMESTOP)

Zeit-Stop kostet **keine Signal-Frequenz** (Entries ~unverändert) → als **einziges der drei** ein
echter **Default-Kandidat**, falls GRÜN (nicht nur Toggle/Grade-Faktor). **DD-Effekt mitreporten**
(verkürzte Verlierer sollten MaxDD senken — starkes Pivot-Argument, falls bestätigt).

## Scorecard (statsFrom=2025-01-01, N=<gelockt>) — AUSSTEHEND

| Klasse | Asset/TF | PF ohne | PF mit | n ohne | n mit | WR ohne | WR mit | MaxDD ohne | MaxDD mit | #TS | Ø-Loss ohne→mit | PF-Lift | Verwertbar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FX | EURUSD 5m | | | | | | | | | | | | |
| FX | GBPUSD 1h | | | | | | | | | | | | |
| FX | USDJPY 4h | | | | | | | | | | | | |
| FX | USDCAD D | | | | | | | | | | | | |
| Index | US500 D | | | | | | | | | | | | |
| Index | NAS100 4h | | | | | | | | | | | | |
| Index | GER40 1h | | | | | | | | | | | | |
| Index | JPN225 D | | | | | | | | | | | | |
| Metal | GOLD D | | | | | | | | | | | | |
| Metal | GOLD 4h | | | | | | | | | | | | |
| Metal | SILVER D | | | | | | | | | | | | |
| Metal | SILVER 1h | | | | | | | | | | | | |
| Crypto | BTC 1h | | | | | | | | | | | | |
| Crypto | BTC 4h | | | | | | | | | | | | |
| Crypto | ETH 1h | | | | | | | | | | | | |
| Crypto | SOL 4h | | | | | | | | | | | | |

## Verdikt — AUSSTEHEND
