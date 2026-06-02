# PaceAlgo — INDEX-DIPBUY Module LOCK (2026-06-02)

**STATUS: LOCKED (Nico-approved 2026-06-02).** Zweites validiertes Modul, erstes
deterministisches. Pine-Export im Rahmen der Universal-Core+Router-Architektur.
Commit-Familie: phase12 `797b13b` → phase12c/d `ef1c0ee`.

---

## Spec (frozen)

| Komponente | Wert |
|---|---|
| Klasse | Indices (Klassen-Router: `syminfo.type == "index"` bzw. CFD-Mapping) |
| Universum (validiert) | SPX500, NAS100, US30, US2000, GER40, UK100, FRA40, EUSTX50, JPN225, HKG33 |
| Timeframe | **Daily** (Signal auf Tagesschluss, Entry next open) |
| Entry (long only) | `close < EMA20 − 1.0·ATR14` **und** `close > EMA200` |
| Stop | 2.0 · ATR14 unter Entry |
| Exit | EMA20-Touch (profitabel) oder 10 Handelstage Time-Exit |
| Position | eine pro Symbol; überlappende Signale bis Exit ignoriert |
| Shorts | **KEINE** — Index-Shorts strukturell negativ (phase12: Rip-Fade PF 0.56–0.79, auch im Bär-Regime) |

## Validierung (der vollständige Gauntlet)

| Prüfung | Ergebnis |
|---|---|
| Formation 2022–2026 (gepoolt, netto 0.02 ATR) | PF 1.32–1.39, WR 72–73% |
| Parameter-Grid 36 Zellen (thr×SL×hold) | **36/36 profitabel**, Median 1.35, Min 1.14 |
| Regime-EMA 150/200/250 | flach (1.39–1.48), alle Jahre positiv |
| **Holdout 2015–2021 (7 ungesehene Jahre, native 1d)** | **PF 1.63, WR 74%, n=415** |
| Per-Jahr (11 Jahre) | 9/11 positiv; Schwachjahre 2018 (0.84), 2020 (0.87) — scharfe Korrekturen, moderate Verluste |
| Per-Symbol (Holdout+Formation) | Breite Mehrheit trägt; Träger: JPN225/FRA40/EUSTX50/US2000/SPX500 |

## Warum wir es glauben (Methodik)

- Echtes Zeit-Holdout: Regel auf 2022–26 geformt, 2015–21 nie angefasst — Holdout-PF > Formation-PF.
- Parameter-Flachheit (kein Spike-Fit), Regime-Filter-Unempfindlichkeit.
- Ökonomisch erklärbar: Panik-Dips in Bullenmärkten werden institutionell gekauft (dokumentierte Anomalie).
- Deterministisch → keine ML-Degeneracy-Risiken, bit-exact in Pine trivial, kein Ops-Budget.

## Ehrliche Grenzen (so kommunizieren)

- **Long-only.** Shorts sind auf Indices empirisch tot — das Tool zeigt sie nicht als Edge an.
- Verliert moderat in scharfen Korrekturphasen (2018/2020-Typ) — EMA200-Filter mildert, eliminiert nicht.
- ~65 Trades/Jahr über 10 Indices (~6–7 pro Index) — Swing-Charakter, kein Daytrading-Modul.
- Kosten-Annahme 0.02–0.05 ATR-Fraktion round-trip — bei Index-CFDs mit engen Spreads realistisch; bei teuren Brokern PF entsprechend niedriger (0.05-Spalte ausweisen).
