# WS4-Regression — Benchmark-Suite v1.0, 2026-06-10

**Zweck:** Pflicht-Regression nach WS1–4 + Branding (Commits `a6ab029`…`35fe9ad`). Erwartung:
Auto-Profile ändert NUR Crypto (Balanced→Conservative); alle Nicht-Crypto-Punkte identisch zur
Baseline 2026-06-03 (COVERAGE_MATRIX Rule-Core-Tabelle) modulo Daten-Fenster-Drift (7 Tage).

**Konfig:** aktuelles Build `35fe9ad`, Defaults (Profile=Auto, Style=Intraday, RR 1.2, MTP on,
Layout Desktop). Intraday-Punkte mit `statsFrom=2026-01-01` (Baseline-Fenster repliziert —
ohne das ist n unvergleichbar, verifiziert an GBPUSD 1h: n=101@2024 vs n=30@2026). Daily/4h Default.

## Nicht-Crypto (Erwartung: identisch)

| Punkt | Baseline 06-03 PF/n/WR/DD | Jetzt 06-10 PF/n/WR/DD | Verdikt |
|---|---|---|---|
| EURUSD 5m | 1.21 / 61 / 54% / 5.8 | 0.97 / 63 / 49.2% / 9.0 | DRIFT — 5m-Fenster in 7 Tagen KOMPLETT gerollt (schwächste Vergleichbarkeit der Suite) |
| GBPUSD 1h | 0.85 / 26 / 50% / 5.3 | 0.86 / 30 / 50.0% / 4.0 | ✓ identisch (+4 = neue Handelstage) |
| USDJPY 4h | 0.86 / 48 / 46% / 7.0 | 0.89 / 52 / 48.1% / 6.5 | ✓ drift-konform |
| USDCAD D | 1.92 / 10 / 70% / 2.0 | 1.97 / 10 / 70.0% / 2.0 | ✓ identisch (n/WR/DD exakt) |
| US500 D | 1.38 / 18 / 56% / 4.0 | 1.37 / 18 / 55.6% / 4.0 | ✓ identisch |
| NAS100 4h | 1.05 / 55 / 51% / 6.0 | 0.93 / 55 / 49.1% / 6.5 | ~ Drift — n identisch, 1–2 Trade-Flips (Crash-Woche in/raus) |
| GER40 1h | 0.68 / 24 / 42% / 7.3 | 0.69 / 26 / 42.3% / 7.1 | ✓ identisch |
| JPN225 D | n/a (Feed lud nicht) | 1.74 / 14 / 64.3% / 2.0 | **NEU** — 16. Zelle erstmals gemessen (J225-Ticker); n<30 → Tool-Only |
| GOLD D | 2.13 / 12 / 67% / 1.0 | 1.90 / 12 / 66.7% / 1.0 | ✓ n/WR/DD identisch, PF = 1 Trade-Swap |
| GOLD 4h | 1.45 / 71 / 59% / 4.5 | 1.39 / 71 / 59.2% / 4.0 | ✓ n identisch |
| SILVER D | 1.50 / 10 / 60% / 2.5 | 1.35 / 10 / 60.0% / 2.5 | ✓ n/WR/DD identisch |
| SILVER 1h | 1.69 / 36 / 64% / 3.5 | 1.54 / 38 / 63.2% / 3.5 | ✓ drift-konform (bleibt stärkste Kandidaten-Zelle) |

**Nicht-Crypto-Verdikt: KEINE unerklärte Abweichung → kein Stopp.** 5 Punkte mit exakt identischem
n + nahezu identischen Stats; alle übrigen drift-erklärt (rollendes Fenster / Trade-Flips bei gleichem n).
Hätten WS1–3 die Engine berührt, würden ALLE Punkte shiften — sie tun es nicht. Engine unverändert bestätigt.

## Crypto (Erwartung: ÄNDERT sich — WS4 Auto-Profile Balanced→Conservative)

| Punkt | Baseline 06-03 (Balanced) | Jetzt 06-10 (Auto=Conservative) | Effekt |
|---|---|---|---|
| BTCUSDT 1h | 1.04 / 56 / 50% / 7.7 | 0.84 / 27 / 44.4% / 6.5 | n halbiert, PF ↓, DD ↓ |
| BTCUSDT 4h | 1.18 / 82 / 56% / 9.3 | 1.38 / 45 / 60.0% / 3.3 | **alle Achsen besser** (PF↑ WR↑ DD 9.3→3.3) |
| ETHUSDT 1h | 1.38 / 48 / 58% / 6.0 | 1.28 / 26 / 61.5% / 2.5 | WR ↑, DD ↓↓, PF leicht ↓ |
| SOLUSDT 4h | 1.29 / 85 / 55% / 7.0 | 1.03 / 37 / 51.4% / 5.9 | PF ↓, DD ↓ |

**Crypto-WS4-Bild (für den offenen CEO-Call Conservative vs Balanced):** Conservative halbiert die
Frequenz und senkt den DD auf ALLEN vier Punkten (Median-DD 7.35→4.6) — aber Median-PF sinkt leicht
(1.235→1.155), WR gemischt. Kein klarer Dominanz-Fall in eine Richtung: BTC-4h profitiert stark,
SOL-4h/BTC-1h verlieren PF. Beide Defaults lock-konform; Entscheidung = Nico (Messlatte: PF≥~1.0 breit
hält BEIDE Varianten — Balanced punktet bei „lebendig + PF-Optik", Conservative bei „ruhig + DD-Gefühl").

## Live-Verifikationen nebenbei
- **Caution-Zeile feuert korrekt in freier Wildbahn:** USDJPY 4h (PF .89/52), GBPUSD 1h (.86/30),
  GER40 1h (.69/26), BTCUSDT 1h (.84/27) — überall ≥20 Trades & PF<0.9; nirgends fälschlich.
- Verdict-Wortlaut „Trend regime active — X" / „stay out" + Auto-Profile („Conservative (recommended)"
  auf Crypto) live bestätigt.
