# PaceAlgo — Claude Context

Du arbeitest an **PaceAlgo**: einem ML-getriebenen TradingView-Indikator (Pine Script v6).
Lies zuerst `HANDOFF.md` vollständig — das ist die Single Source of Truth.

## Kurzüberblick

- **Ziel:** Universeller TradingView-Indikator (FX, Crypto, Indices) — $39–499/mo SaaS
- **Modell:** LightGBM, 100 Trees, Depth 3, 27 Features — V1 Kandidat `v1b_100_noes` gesperrt
- **Pipeline:** Google Colab (NB01–NB16) → `pine_codegen.py` → `deploy_pine/pace_algo_v1.pine` → TradingView
- **Aktueller Stand:** NB15c muss mit `AUTO_PUSH=True` re-run werden um echtes Pine Script nach GitHub zu pushen

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

**NB15c in Google Colab re-run:** `AUTO_PUSH=True` setzen (Section 0) + Section 7 Bug ist gefixt.
Danach: `deploy_pine/pace_algo_v1.pine` in TradingView testen → Signale prüfen.
