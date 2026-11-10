"""Verify the reviewed bundle and seal the complete independent audit."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).parent


def record(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size}


def main():
    out = DIRECTORY / "AUDIT_SEAL.json"
    assert not out.exists()
    bundle_path = ROOT / "runs/campaign-005-review/bundle_manifest.json"
    bundle = json.loads(bundle_path.read_text())
    for entry in bundle["files"]:
        actual = record(ROOT / entry["path"])
        assert actual["sha256"] == entry["sha256"] and actual["bytes"] == entry["bytes"], entry["path"]
    bundle_hash = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    assert bundle_path.with_name("bundle_manifest.sha256").read_text().split()[0] == bundle_hash
    entries = [record(path) for path in sorted(DIRECTORY.iterdir())
               if path.is_file() and not path.name.startswith("AUDIT_SEAL")]
    result = {"campaign": "005", "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
              "bundle": {"path": str(bundle_path.relative_to(ROOT)), "sha256": bundle_hash,
                         "files": len(bundle["files"]), "bytes": sum(entry["bytes"] for entry in bundle["files"]),
                         "all_hashes_match": True},
              "files": entries,
              "scope": "Independent source/selection/numerical/mechanistic/contextual/resource audit; direct matched-assay gate failed. Parent narrative excluded."}
    out.write_text(json.dumps(result, indent=2) + "\n")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_name("AUDIT_SEAL.sha256").write_text(digest + "  AUDIT_SEAL.json\n")
    print(json.dumps({"seal": digest[:6], "audit_files": len(entries), "bundle": bundle_hash[:6]}))


if __name__ == "__main__":
    main()
