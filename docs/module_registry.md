# PaceAlgo — Module Registry (Source of Truth: was funktioniert wo)

**Zweck (Nico-Direktive 2026-06-02):** Pro Klasse/Asset/TF festhalten, was den Anforderungen
entspricht (Modul), was dünn ist, was durchgefallen ist — und welcher Lösungsansatz für die
Durchgefallenen als Nächstes dran ist. Wird bei jedem Klassen-Test aktualisiert.

**Bar für ein Modul:** net PF ≥ 1.3 · all-years-positive · Walk-Forward robust (≥80% Folds
positiv) · netto (Spread/Fees + next-bar-open) · kein Leak · Pine-bit-exact vor Ship.

---

## ✅ MODULE (bestanden, gelockt)

| Modul | Universum | TF | Long | Short | Kennzahlen (net, ECN 0.5pip) | Quelle |
|---|---|---|---|---|---|---|
| **FX-NY** | GBPUSD, USDJPY, USDCAD, NZDUSD, USDCHF | 5m | ✅ alle 5 | ✅ nur USDCHF | PF 1.51 (sized), WR 0.51, 9.3/Tag, 80% Folds+, alle Jahre+ | `fx_module_LOCK.md`, phase7 |

## 🟡 DÜNNE PULSE (real, aber unter der Bar — nicht shippen, beobachten)

| Kandidat | Universum | TF | Kennzahlen | Limitierung | Nächster Hebel |
|---|---|---|---|---|---|
| Metal high-R | XAUUSD, XAGUSD | 15m, R=3 | PF 1.07 @0.05ATR, alle Jahre+ (1.02/1.08/1.22) | dünn, nur bei Niedrigkosten | Swing-TF-Test; DXY-Kontext brachte als Feature nichts (10c) |

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
| **Indices auf Swing-TF (4h/D): Overnight-Drift, Monatswende, Dip-Buying** | Nur intraday getestet; dokumentierte Anomalien leben höher | **IN ARBEIT** |
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
