"""Convert a harness-persisted data_get_ohlcv tool-result file into a clean tv_capture JSON.
Breaks the transcription wall: large MCP results are auto-saved to disk; read them programmatically.

Usage: py -3 scripts/_tv_persisted_to_capture.py <persisted_file> <SYMBOL> <TF>
"""
import sys, json
from pathlib import Path
REPO = Path(__file__).parent.parent
src, sym, tf = sys.argv[1], sys.argv[2], sys.argv[3]
raw = json.loads(Path(src).read_text(encoding="utf-8"))
# persisted format: [{"type":"text","text":"<inner json>"}]  OR already the inner dict
if isinstance(raw, list):
    inner = json.loads(raw[0]["text"])
elif isinstance(raw, dict) and "bars" in raw:
    inner = raw
else:
    inner = json.loads(raw["text"]) if "text" in raw else raw
bars = inner["bars"]
out = REPO / "data" / "tv_capture" / f"{sym}_{tf}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"bars": bars}), encoding="utf-8")
times = [b["time"] for b in bars]
print(f"{sym}_{tf}: {len(bars)} bars  window=[{min(times)},{max(times)}]  -> {out}")
