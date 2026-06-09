# PaceAlgo — Module Registry (Source of Truth: was funktioniert wo)

**Zweck (Nico-Direktive 2026-06-02):** Pro Klasse/Asset/TF festhalten, was den Anforderungen
entspricht (Modul), was dünn ist, was durchgefallen ist — und welcher Lösungsansatz für die
Durchgefallenen als Nächstes dran ist. Wird bei jedem Klassen-Test aktualisiert.

**Bar für ein Modul:** net PF ≥ 1.3 · all-years-positive · Walk-Forward robust (≥80% Folds
positiv) · netto (Spread/Fees + next-bar-open) · kein Leak · Pine-bit-exact vor Ship.

---

## ✅ MODULE (bestanden, gelockt)

| Modul | Universum | TF | Long | Short | Kennzahlen | Quelle |
|---|---|---|---|---|---|---|
| **FX-NY** (ML) | GBPUSD, USDJPY, USDCAD, NZDUSD, USDCHF | 5m | ✅ alle 5 | ✅ nur USDCHF | PF 1.51 (sized), WR 0.51, 9.3/Tag, 80% Folds+, alle Jahre+ (net, ECN 0.5pip) · **✅ Edge-Validated (live) 2026-06-09** (3 Live-Gates zu; OOS-Reval per-Symbol alle 5 ≥1.3: USDCAD 2.57/NZDUSD 2.25/USDJPY 1.86/USDCHF 1.63/GBPUSD 1.43) | `fx_module_LOCK.md`, phase7, `COVERAGE_MATRIX.md` |
| **INDEX-DIPBUY** (deterministisch) | 10 Indices (SPX→HangSeng) | Daily | ✅ | ❌ (strukturell tot) | Holdout 15–21: PF 1.63/WR 74% · Formation 22–26: PF 1.32 · 36/36 Grid+ · 9/11 Jahre+ | `index_dipbuy_LOCK.md`, phase12 — **Nico-approved 2026-06-02** |
| **METAL-TREND_L** (deterministisch, **EXPERIMENTAL-Label**) | XAUUSD, XAGUSD | Daily | ✅ | ❌ (tot, 0.84–0.86) | Grid 27/27+ (Median 1.42, Min 1.16) · Hälften 15–20: 1.70 / 21–26: 1.27 · 9/11 Jahre+ | phase13/13b — **Nico-approved 2026-06-02 als Experimental** (dünn: 2 Symbole, ~14 Trades/Jahr, kein formales Holdout) |

**🏛️ Ship-Architektur (Nico-locked 2026-06-09):** Jedes Modul = **eigener Standalone-Indikator** (NICHT
als Toggle im `pace_algo_v1`-Monolith — empirisch falsifiziert: Merge Core+FX = 102% Ops, Pine rechnet
alles jeden Bar). `pace_algo_v1` = leichtes Tier-A-Tool; FX/INDEX/METAL je eigener fokussierter Indikator;
„Routing" = Supported-Markets-Onboarding. Details: `fx_module_LOCK.md` §ARCHITEKTUR-UPDATE-2026-06-09.

## 🟡 DÜNNE PULSE (real, aber unter der Bar — nicht shippen, beobachten)

| Kandidat | Universum | TF | Kennzahlen | Limitierung | Nächster Hebel |
|---|---|---|---|---|---|
| Metal high-R intraday | XAUUSD, XAGUSD | 15m, R=3 | PF 1.07 @0.05ATR, alle Jahre+ (1.02/1.08/1.22) | dünn, nur bei Niedrigkosten | superseded durch METAL-TREND_L-Kandidat (Daily, 🟢 oben) |
| Metal DIPBUY | XAUUSD, XAGUSD | Daily | PF 1.03 | transferiert NICHT von Indices — Klassen-Wahrheit erneut bestätigt | geschlossen (phase13) |

## 🟢 KANDIDAT VALIDIERT

*(leer — METAL-TREND_L am 2026-06-02 als Experimental-Modul angenommen, siehe ✅. Spec:
frischer Close>EMA50-Cross bei steigender EMA50 → long, SL 2·ATR, Hold 20d.)*

## ❌ DURCHGEFALLEN (geschlossen — NICHT re-litigieren ohne NEUE Informationsbasis)

| Was | Evidenz | Geschlossen am |
|---|---|---|
| Ein universelles Modell über alle Klassen | phase5: 0/4 Klassen ≥1.3 (Mittel PF 1.00) | 2026-06-01 |
| Per-Klasse-Modelle mit generischem Feature-Pool | phase6/6b/6c: nur FX besteht | 2026-06-01 |
| FX-Shorts jenseits USDCHF (auch unter META+Sizing) | phase10a: Short-PF 0.87–1.00, ALL5 2026-Einbruch | 2026-06-02 |
| Indices/Metals intraday (15m–1h), alle R, Heimat-Sessions | phase10d: 0/72 Konfigs | 2026-06-02 |
| Regime-Routing auf Indices/Metals | phase10e: PF ~0.95 | 2026-06-02 |
| Klassen-Features (Gap/OR/DXY/Weekend) intraday | phase10c (nach Leak-Fix): Lift −0.10/−0.22/±0 | 2026-06-02 |
| EURUSD (long wie short) | ANN-020: kein Edge | 2026-05-31 |
| **Crypto-Modul (alle Architekturen, beste Informationsbasis)** | phase11: ML auf 8 sauberen Binance-Perps, native Features liften (+0.08) aber 2026 stirbt (0.94) · phase11b: Routing bei ECHTEN Fees ~breakeven (2026 +, 24/25 flach) · phase11c: Synthese Routing×ML×native PF ≤1.03, ML zerstört den 2026-Routing-Vorteil. **v1-Puls (PF 1.11) hiermit INVALIDIERT: war mit 0.03R Fantasie-Kosten gerechnet, echte 5m-Perp-Fees ~0.7R.** Edge-Mechanismus (Selektion in Trend-Regimen) bricht im Chop-Regime 2026 strukturell — kein Selektions-, sondern ein Regime-Problem. | 2026-06-02 |

## 🔬 OFFEN / UNGETESTET (die ehrlichen verbleibenden Hebel)

| Hypothese | Warum noch offen | Status |
|---|---|---|
| Indices auf Swing-TF | — | **ERLEDIGT 2026-06-02** → DIPBUY validiert (🟢 oben); TOM seit 2024 zerfallen; Index-Shorts tot (auch im Bär-Regime, PF 0.56) |
| Cross-sektionale Formulierung (Ranking innerhalb Klasse) | Anderes Problem-Design, nie als Kern getestet (nur als Feature in phase9). Für Crypto der einzig verbliebene Pfad (Long-Stärkste/Short-Schwächste statt direktional) | pending |
| Metals Swing-TF | analog Indices | pending |
| Crypto direktional | — | **GESCHLOSSEN 2026-06-02** (siehe ❌) — nur noch via Cross-Sectional oder neuem Datentyp (OI/Liquidations) re-openbar |

## 📐 PRODUKT-ARCHITEKTUR (Nico-approved Richtung 2026-06-02)

**Ein Indikator, drei Schichten:** (1) Universeller adaptiver Kern — R-Einheiten,
symmetrisch long/short, adaptives Aktivitätsfenster, State-Engine, User-RR/Risk,
Backtest-Panel → läuft auf JEDEM Asset/TF by construction. (2) Klassen-Router
(`syminfo.type` + TF) schaltet Module zu. (3) Edge-Module pro Klasse aus diesem
Register — nur ✅-Zeilen werden als "AI Confidence" aktiviert; 🟡 höchstens als
gekennzeichnetes Experimental; ❌/🔬 laufen tool-only.

**Kein Release-Druck (Nico 2026-06-02): Produkt wird fertig gebaut wie geplant; Module
wachsen, bis die Klassen-Abdeckung steht.**

## ⚠️ DATEN-REGELN (gelernt, teuer)

- **Dukascopy Altcoin-Intraday (non-BTC/ETH): UNBRAUCHBAR** (5–12% Flat-Bars, 4–8% Gaps → Phantom-PF 5–6). Root-Cause von phase9.
- Session-Fenster-Aggregate IMMER kausal bauen (cummax/cummin, nie transform über das ganze Fenster) — OR-Lookahead-Falle aus phase10c.
- Jede Klasse braucht eine Datenquelle mit echtem Volumen + klasseneigenen Signalen (Crypto: Funding/OI; Indices: ggf. Cash-Session-Daten).
