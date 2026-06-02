# PaceAlgo — Claude Context

Du arbeitest an **PaceAlgo**: einem ML-getriebenen TradingView-Indikator (Pine Script v6).
Lies zuerst `HANDOFF.md` vollständig — das ist die Single Source of Truth.

## Kurzüberblick

- **Ziel:** Universelles TradingView-TOOL + validierte Edge-Module pro Klasse — $39–499/mo SaaS (TOOL ≠ EDGE)
- **V1 (RESOLVED 2026-06-02):** regelbasierter selektiver Trend-Core, Pine-nativ — `deploy_pine/pace_algo_v1.pine` (ADX-Gate + HTF + Pullback-Entry, Profile, MTF-Dashboard, Backtest- + Recommended-Panel)
- **ML = geparkter V1.5-Overlay** (NB15c/pine_codegen-Kette PARKED; Archiv: `pace_algo_v1_ml_export_PARKED.pine`)
- **Modul-Landkarte:** `docs/module_registry.md` — ✅ FX-NY (PF 1.51) · ✅ INDEX-DIPBUY (Holdout PF 1.63) · 🟢 METAL-TREND_L · ❌ Crypto direktional
- **Aktueller Stand:** V1-Core in TV validieren (Heim-PC, trendend vs. rangebound), dann Feintuning mit Nico — kein per-Asset-Curve-Fit

## Workstations

- **Arbeits-PC:** `C:\Users\nico.flotz\Downloads\pace-algo\`
- **Heim-PC:** `C:\Users\ecoar\pace-algo\` ← du bist hier

## TradingView MCP (Heim-PC)

TradingView **muss mit CDP gestartet werden** damit du Chart-Zugriff hast:

```powershell
Stop-Process -Name "TradingView" -ErrorAction SilentlyContinue
Start-Process "C:\Program Files\WindowsApps\TradingView.Desktop_3.1.0.7818_x64__n534cwy3pjxzj\TradingView.exe" -ArgumentList "--remote-debugging-port=9222"
```

Oder: Desktop-Verknüpfung **"TradingView (CDP)"** doppelklicken.

Danach `tv_health_check` aufrufen um Verbindung zu bestätigen.

## Boot-Sequenz

```powershell
cd C:\Users\ecoar\pace-algo
git pull origin main
# Dann HANDOFF.md lesen — Section 0, 16, 19, 20
```

## Wichtigste Locked Rules

- Quality before speed — kein Timeline-Druck
- Kein Feature ohne ≥+0.05 PF OOS Lift
- Walk-forward Validation, kein Data Leakage
- VAL-Cutoffs only (q90/q97/q99) — nie Holdout anfassen
- Bit-exact Pine Validation vor jedem Deploy

## Nächste offene Aufgabe

**`deploy_pine/pace_algo_v1.pine` (Regel-Core v6) in TradingView testen** (nur Heim-PC — TV
Desktop fehlt auf Arbeits-PC): (a) trendendes Asset → saubere Pullback-Entries, WR ~45–55%,
PF >1.2; (b) rangebound Asset → wenige/keine Signale (Regime-Gate schweigt = GEWOLLT).
Dazu Skaleninvarianz, Non-Repaint, Box-Verhalten. Zahlen in HANDOFF §19 dokumentieren.
