# Benchmark Run — H-TIMESTOP (ANN-027, Hypothese 3/3, letzte)

**Datum:** 2026-06-10 (UTC) · **Workstation:** arbeits-pc · **Status:** ABGESCHLOSSEN (1 Runde, N normalisiert) — **Verdikt: WAIT (kein breites GRÜN; Metal scheitert (a), nur Index räumt Gate) — aber stärkste der 3 Achsen: realer, DD-senkender, no-cost Effekt auf Index/FX. ANN-027-Queue erschöpft.**

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

## Scorecard (statsFrom=2025-01-01, N normalisiert je Punkt) — ABGESCHLOSSEN

Wiring: ts ist eigene Engine (Entry-Delta wird reportet, nicht auf 0 gezwungen). „Verwertbar" =
OOS-n ≥ 12. Hinweis: N-Median wird über die ganze geladene History gezogen (strukturell stabiler);
Verwertbarkeit nach OOS-n. PF-Lift = PF(mit) − PF(ohne). DD/AvgLossR/Dauer = Mechanismus-Kontrolle.

| Klasse | Asset/TF | N | PF o→m | Lift | WR o→m | n o→m (Δ) | MaxDD o→m | AvgLossR o→m | Dur o→m | #TS | Verwertbar |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FX | EURUSD 5m | 12 | 1.08→1.12 | **+0.04** | 51.5→48.7 | 68→78 (+10) | 9.0→8.5 | 1.00→0.84 | 11.0→6.6 | 10 | ✅ |
| FX | GBPUSD 1h | 10 | 0.95→0.97 | **+0.02** | 50.5→48.2 | 101→110 (+9) | 9.6→9.5 | 1.00→0.81 | 8.7→5.7 | 26 | ✅ |
| FX | USDJPY 4h | 16 | 0.83→0.88 | **+0.05** | 48.0→48.0 | 25→25 (0) | 6.5→6.0 | 1.00→0.96 | 9.9→8.3 | 4 | ✅ |
| FX | USDCAD D | 8 | 0.87→2.43 | +1.57 | — | 7→7 (0) | 2.0→1.1 | — | — | 2 | ❌ n=7 |
| Index | US500 D | 12 | 1.10→1.38 | +0.28 | — | 10→10 (0) | 3.0→2.0 | — | — | 2 | ❌ n=10 |
| Index | NAS100 4h | 12 | 1.17→**1.75** | **+0.58** | 55.6→59.3 | 27→27 (0) | 4.7→3.0 | 1.00→0.68 | 14.0→9.2 | 8 | ✅ |
| Index | GER40 1h | 10 | 0.83→**1.08** | **+0.25** | 47.4→52.0 | 95→100 (+5) | **19.1→10.2** | 1.00→0.79 | 11.1→6.9 | 25 | ✅ |
| Index | JPN225 D | — | — | — | — | — | — | — | — | — | ❌ N/A (kein Render) |
| Metal | GOLD D | 14 | 2.20→4.25 | +2.05 | — | 6→6 (0) | 1.0→1.0 | — | — | 2 | ❌ n=6 |
| Metal | GOLD 4h | 12 | 1.30→1.26 | **−0.04** | 57.1→56.0 | 49→50 (+1) | 4.0→4.4 | 1.00→0.98 | 7.0→6.3 | 3 | ✅ |
| Metal | SILVER D | 6 | 2.70→6.34 | +3.64 | — | 4→5 (+1) | 1.0→0.3 | — | — | 4 | ❌ n=4 |
| Metal | SILVER 1h | 12 | 1.18→1.13 | **−0.04** | 55.1→54.7 | 107→117 (+10) | 12.2→14.6 | 1.00→0.89 | 13.1→9.7 | 20 | ✅ |
| Crypto | BTC 1h | 10 | 0.96→0.95 | −0.01 | 51.8→48.9 | 166→190 (+24) | 12.3→10.8 | 1.00→0.81 | 12.2→6.9 | 47 | ✅ (Δ groß) |
| Crypto | BTC 4h | 16 | 0.80→0.72 | −0.08 | 46.3→41.8 | 54→55 (+1) | 7.5→8.7 | 1.00→0.90 | 8.7→7.0 | 8 | ✅ |
| Crypto | ETH 1h | 10 | 0.97→1.02 | +0.05 | 50.6→50.6 | 156→178 (+22) | 10.6→9.6 | 1.00→0.80 | 13.2→8.7 | 51 | ✅ (Δ groß) |
| Crypto | SOL 4h | 8 | 1.03→1.10 | +0.06 | 50.8→49.3 | 59→73 (+14) | 6.6→7.8 | 1.00→0.80 | 8.7→5.5 | 16 | ✅ (Δ groß) |

### Bewertung gegen die 3 GRÜN-Kriterien (pre-registriert)

| Krit. | Anforderung | Ergebnis |
|---|---|---|
| (a) | je Klasse FX/Index/Metal ≥2 verwertbar, Mehrzahl Lift>0 | FX ✅ (3/3 +, aber klein) · Index ✅ (2/2 stark +) · **Metal ❌ (GOLD4h −0.04, SILVER1h −0.04 → 0/2)** → **(a) NICHT erfüllt** |
| (b) | stärksten Punkt rausrechnen, Richtung hält | Index hält ohne NAS100 (GER40 +0.25 allein stark) ✅; FX 3/3 unabhängig ✅ — kein Einzelpunkt-Artefakt |
| (c) | Mechanismus: Lift aus verkürzten Verlierern | **Bestätigt wo positiv** — AvgLossR 1.00→0.68–0.84 + Dauer ↓ + (Index) MaxDD stark ↓. Wo negativ (Metal) kaum Verkürzung. ✅ Mechanismus real, kein Rauschen |

**Promotion-Gate (≥+0.05 Klassen-Median-Lift):** Index +0.415 ✅ · FX +0.04 ❌ (knapp drunter) ·
Metal −0.04 ❌ (Regression) · Crypto ~0. → **Nur Index räumt das Gate.**

**Entry-Delta-Befund:** klein/0 auf 4h+Daily (USDJPY/NAS100/GER40 sauber). **Groß auf Crypto-1h +
SILVER1m-Typ (+10…+24, bis ~24 %)** — dort vermischt der Time-Stop Exit- mit Entry-Selektion; die
positiven Crypto-Lifts sind dadurch **confounded** → als flach werten (Kontrolle bleibt flach).

## FINALES VERDIKT (N normalisiert, 1 Runde, kein 2. Fenster nötig): **WAIT — kein breites GRÜN, aber der stärkste der drei Achsen**

- **Strikte Kriterien NICHT erfüllt:** Metal scheitert (a) (0/2 positiv, leichte Regression); nur
  **Index** räumt das +0.05-Promotion-Gate, FX positiv aber sub-threshold (+0.04). Kein broad GREEN.
- **ABER — echter, mechanistisch sauberer Teil-Effekt:** Auf **trendenden Indizes** (NAS100 +0.58,
  GER40 +0.25, beide WR ↑) und **FX** (mild +) verkürzt der Zeit-Stop Verlierer wie beabsichtigt
  (AvgLossR ↓, Dauer ↓) und **senkt DD deutlich** (GER40 MaxDD **19.1→10.2**, NAS100 4.7→3.0) — bei
  **null Frequenz-Kosten** (Entries ~unverändert auf den sauberen Punkten). Crypto flach (Kontrolle
  ok), Metall neutral-bis-leicht-negativ.
- **Kein Round 2:** die ausschlaggebenden Klassen (Metal, FX) sind gut gepowert (n≥49); Daily-
  Starvation (5 Punkte n<12) würde den Metal-Fail nicht drehen. Verdikt robust.

**Empfehlung (CTO):** **Nicht als broad-v1-Default bauen** (strikte Kriterien gerissen, Lock
eingehalten). ABER von den drei Achsen der **einzige Kandidat mit realem, no-cost, DD-senkendem
Effekt** — und zwar **klassen-ungleich** (stark Index, mild FX, neutral Metal, flach Crypto). Das
rechtfertigt **keine** sofortige Umsetzung, sondern höchstens eine **eigene, neu pre-registrierte
Folge-Hypothese** „Zeit-Stop nur Index/FX, DD-fokussiert" (NICHT als H-TIMESTOP-Rebrand, kein
Goalpost-Move). Sonst sauber als WAIT verbuchen.

**ANN-027-Queue damit erschöpft** (H-SESSION moderater Qualitäts-Faktor · H-TRIGGER widerlegt ·
H-TIMESTOP WAIT/teil-positiv). Nichts in `pace_algo_v1` gebaut. Produktion unberührt.
