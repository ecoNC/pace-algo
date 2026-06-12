# Benchmark Run — H-TIMESTOP (ANN-027, Hypothese 3/3, letzte)

**Datum:** 2026-06-10 (UTC) · **Workstation:** arbeits-pc · **Status:** SPEC GELOCKT (N normalisiert, k=2) — Probe gebaut, Sweep nach TV-Paste

## Hypothese — wörtlich aus ANN-027 zitiert (keine Umdeutung)

> **H-TIMESTOP — Zeit-Stop (neue Achse: tote Trades schneiden)**
> - **Achse:** Trades, die nach **N Bars** weder TP1 noch strukturellen Fortschritt zeigen, zu Markt
>   schließen. Orthogonal zu allen getesteten preis-basierten Exits.
> - **These:** senkt Loss-Größe + Hängepartien (Feel-Faktor). Prior moderat.

Schwelle **N ist in ANN-027 offen** → 3 threshold-saubere Kandidaten unten, **EINER wird gelockt**,
kein Grid.

## Spec — ✅ GELOCKT 2026-06-10: N **normalisiert** je Punkt (k=2 fix, einziger Parameter)

**Zeit-Stop-Regel:** an jedem confirmed Bar mit offener Position: wenn `bar_index − entryBar ≥ N_punkt`
**UND TP1 noch nicht erreicht** (`tp1Hit == false`) → Position **zu Markt** (current close) schließen.
Ist TP1 erreicht (Runner aktiv = Fortschritt da), greift der Zeit-Stop NICHT.

**N_punkt = round( 2 × Median-Bars-bis-TP1 der Baseline-TP1-Gewinner DIESES Punkts ).**
Rohe Bar-Zahlen wären über die Suite ungleiche ökonomische Horizonte (N=24 = 2 h auf 5m, ~5 Wo auf
Daily) → die 16 Punkte testeten nicht dieselbe Hypothese. Normalisierung macht „N" überall zur
**selben Intervention** (= erst dadurch ist der TF-agnostik-Bonus valide).

**k = 2 der einzige freie Parameter, vorab fix, Begründung rein mechanistisch:** k=1 köpft normal
reifende Trades (am Median); k=3 feuert zu selten; k=2 = „doppelt so lange wie ein typischer Gewinner,
ohne TP1" = ehrliche „steckt fest"-Definition. **Das 2× ersetzt die „struktureller-Fortschritt"-
Klausel** aus dem ANN-027-Wortlaut (großzügiger Horizont = Nachsicht ggü. normalen Trades) → bleibt
EIN Parameter; die Fortschritts-Klausel ist konservativ aufgeschoben (mögliche Zukunfts-Verfeinerung).

**Guard 1 (kein Outcome-Fitting):** Median ausschließlich aus Baseline-Trades, unabhängig vom
Time-Stop-PnL. **Guard 2 (Stabilität):** ein Punkt braucht **≥ 10 Baseline-TP1-Gewinner**, sonst ist
N nicht stabil ableitbar → Punkt **nicht-verwertbar** (Starvation-Klasse), nicht raten.

**Implementierung (1 Pass, kausal):** Probe führt einen **laufenden Median** der bisherigen
Baseline-Gewinner-Dauern (`array.median`) und aktiviert den Time-Stop erst ab ≥10 Gewinnern (vorher
inaktiv = konservativ, kein Look-ahead). Der finale Voll-Sample-N_punkt + Gewinnerzahl werden je
Punkt gedruckt (Normalisierung nachprüfbar).

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
