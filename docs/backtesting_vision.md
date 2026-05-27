# Backtesting Vision — User-facing Product Design

**Locked Rules (HANDOFF 12.3):**
- Universal first (PF 1.6 auf 8 Asset-Klassen schlägt PF 2.0 auf 2)
- User sieht NIE Probabilities — nur BUY/SELL + optionale Tier-Badge
- Anti-Curve-Fitting: keine free Parameter, alle Slider statistisch validiert
- Honest Backtest: was der User auf dem Chart sieht IST der Backtest, kein Cherry-Picking

---

## Was der User sehen wird

### Live-Signale (immer sichtbar)

- **BUY/SELL Label** an der Kerze mit Entry-Bestätigung
- **Entry-Line** (Pine `line.new`) bei Entry-Preis
- **TP-Box** bei Target (1.5R per default)
- **SL-Box** bei Stop-Loss (1.0R per default)
- **Tier-Badge** für Premium-Signale (top 1% confidence)

### Historische Visualisierung

- **Vergangene Trades als Boxes** auf dem Chart (Pine `box.new`, max 500 Boxes)
- Grüne Box = gewonnener Trade, rote Box = verlorener Trade
- User kann visuell verifizieren: "war's wirklich profitabel auf meinem Chart in 2024?"

### Backtest-Dashboard (Pine `table.new`)

Zeigt für das aktuelle Chart/TF:
- **PF** (Profit Factor)
- **WR** (Win Rate, ehrlich nicht aufgeblasen)
- **Avg R** (Average Return per Trade in R-Multiples)
- **MDD** (Max Drawdown)
- **Trade Count**
- **Period** (von wann bis wann)

---

## Profile-System (statt freier Parameter)

Drei vordefinierte Profile — der User wählt eines, keine freien Slider:

| Profil | Tier-Threshold | Trades/Tag (Schätzung) | Zielgruppe |
|---|---|---|---|
| **Conservative** | Premium only (~1%) | ~3/Symbol | Risk-averse, niedrige Frequenz |
| **Balanced** | High (~3%) | ~8/Symbol | Default, mittlere Frequenz |
| **Aggressive** | Standard (~10%) | ~27/Symbol | High-frequency, mehr Trades |

**Warum keine freien Slider?** Curve-Fitting-Schutz. Ein User der "Threshold 0.42 statt 0.40" probiert und damit bessere PF auf seinem Chart bekommt, optimiert sich in Noise. Wir geben ihm validierte Stufen, keine Freistil-Parameter.

---

## Limitierte sichere Parameter

Was der User ÄNDERN kann (kontrolliert):
- Profil-Switch (Conservative/Balanced/Aggressive)
- TP/SL-R-Multiple (z.B. 1.5R/1.0R → 2.0R/1.0R, aber nur diskrete Stufen 1.0/1.5/2.0/2.5)
- Long-only vs Long+Short
- Session-Filter ein/aus (London/NY/Asia)

Was der User NICHT ändern kann:
- Feature-Set
- Modell-Threshold (außer via Profil)
- Tier-Cutoffs (VAL-derived, gelockt)
- Modell-Architektur

---

## Asset-/TF-spezifische Fine-Tuning

**Phase D (NB15)** entscheidet, ob asset-spezifische Kalibrierung sinnvoll ist. Falls ja, läuft das transparent:
- User sieht: "PaceAlgo erkennt: aktuelles Symbol = Crypto. Tier-Cutoffs wurden für Crypto-Cluster kalibriert."
- Aber: keine "drehen Sie an diesem Slider"-Option. Der User SIEHT die Anpassung, kann sie nicht overriden.

---

## Backend V2 Erweiterungen (nicht V1)

Wenn Backend aktiv ist:
- **Continuous Backtest**: Live-update der Dashboard-Zahlen mit jedem neuen Trade
- **Cross-Symbol Aggregation**: User-Account zeigt PF/WR über alle Charts, die der User öffnet
- **Trade-Journal**: jeder vom User reale getätigte Trade wird annotiert mit "PaceAlgo agreed/disagreed"
- **Profile-Tuning**: ML retrainiert User-spezifisch (mit Opt-In)

V1-Backtest ist statisch auf das aktuelle Chart-Window. V2 bringt die Live-Komponente.

---

## Honesty-Constraints (HANDOFF 12.3.17)

- ❌ Keine Marketing-Behauptung "85% Win Rate" — Premium-WR liegt aktuell ~55–57%
- ❌ Keine Cherry-Picked Screenshots in Marketing
- ❌ Keine "guaranteed signals"-Sprache
- ✅ Backtest-Zahlen, die der User auf seinem Chart sieht, MÜSSEN matchen mit dem was wir in Marketing zeigen
- ✅ Tier-System ist transparent dokumentiert (Premium = top 1% Confidence)
