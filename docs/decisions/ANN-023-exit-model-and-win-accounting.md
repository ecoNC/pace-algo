# ANN-023 — Exit-Modell & Win-Zählweise (Integritäts-Lock)

**Status:** ACCEPTED (Nico, 2026-06-02)
**Kontext:** V1-Core iter3 (Multi-TP-Build + Benchmark-Sweep) und CEO-Vorgaben vom
2026-06-02. Es geht um die Entscheidung mit echten Tradeoffs und Integritäts-Stakes:
wie Exits funktionieren und was als „Win" zählt.

## Entscheidungen

1. **TP1 ≥ 1R, niemals enger.** Sub-1R-Token-Targets sind Win-Rate-Inflation
   (HANDOFF §15, verworfener Trick) und bleiben verboten — auch nicht als Option.
2. **Win-Definition = Netto-R des GESAMTEN Trades > 0.** Ein Trade, der TP1 trifft und
   auf Break-Even ausläuft (+0.5R netto), ist ein echter Win. Ein BE-Exit ohne TP1
   existiert nicht (BE-Stop entsteht erst durch TP1).
3. **Multi-TP+BE ist ein VARIANZ-/UX-FEATURE, kein Performance-Gewinn.** Empirischer
   Beleg (iter3-Sweep): WR überall +3 bis +4.4pp, aber PF nicht breit gestiegen
   (US500 1.15→1.14 · GOLD 1.27 flat, kleinerer DD · BTC 1h 1.01→**0.85** ⚠️).
   Per Disziplin-Regel (Promotion nur bei breitem PF-Anstieg) ist Multi-TP daher:
   - **TOGGLE** (Single-TP vs. Multi-TP), kein Zwang
   - **Crypto: default Single-TP** (BE-Whipsaw kostet dort messbar PF)
   - Marketing-Sprache: „Risk-Management / sanftere Equity-Kurve", NIE „mehr Profit"
4. **PF / Erwartungswert (R) ist die Primärmetrik.** Das Backtest-Panel führt mit
   Net PF, zeigt Outcomes GESPLITTET (TP2 / Trail / BE / Loss); WR ist nachgeordnet.
   PF gegen WR tauschen ist ausschließlich CEO-Call (IMPROVEMENT_PROTOCOL).
5. **Hebel-Entkopplung** (Stop = strukturelle Invalidierung; Hebel = Positionsgröße)
   ist KEIN eigener ADR — gelockt in roadmap §5 (CEO-Entscheidung: unstrittig korrekt).

## Konsequenzen

- Pine: `useMTP`-Input bleibt; Klassen-Router (Tier B) setzt den Crypto-Default auf
  Single-TP, sobald der Router steht; bis dahin dokumentiert die COVERAGE_MATRIX den
  empfohlenen Modus pro Asset.
- Benchmark-Suite misst Crypto-Punkte in beiden Modi, solange der Default abweicht.
- Nächste Exit-Hypothese (Stufe 1 abschließen): „Trailing-Runner statt TP2-Cap"
  (Trail-Outcomes ~0 im Sweep = Runner gedeckelt = PF-Potenzial verschenkt) — läuft
  als EINE Hypothese durch die Suite, PF breit als Schiedsrichter.
