"""Archive the public source used for the parameter experiment."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).parent / "source"
root.mkdir(parents=True, exist_ok=True)
url = "https://raw.githubusercontent.com/openai/math/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/main_full_version.tex"
target = root / "main_full_version.tex"
if not target.exists():
    with urllib.request.urlopen(url, timeout=45) as response:
        blob = response.read(1_000_001)
    if len(blob) > 1_000_000:
        raise ValueError("source size exceeded bound")
    text = blob.decode("utf-8")
    if "label{lem:incidence-parameters}" not in text:
        raise ValueError("expected source lemma missing")
    target.write_bytes(blob)
blob = target.read_bytes()
meta = {"url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
        "lemma": "incidence-parameters", "scope": "literal Section 4 parameter schedule"}
(root / "provenance.json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps(meta))
