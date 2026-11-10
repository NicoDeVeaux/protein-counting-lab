"""Preserve and correct an inventory schema error before any measured trial."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def artifact(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    run = ROOT / "runs/campaign-002-amendment-001"
    assert not (run / "manifest.json").exists()
    assert not (run / "trials.jsonl").exists()
    attempt = ROOT / "runs/campaign-002-amendment-001-freeze-attempt-001"
    assert not attempt.exists()
    run.rename(attempt)
    catalog_path = ROOT / "prepared/campaign-002/amended_catalog.json"
    failed_path = ROOT / "prepared/campaign-002/amended_catalog.before-schema-correction.json"
    assert not failed_path.exists()
    catalog_path.rename(failed_path)
    catalog = json.loads(failed_path.read_text())
    original = json.loads((ROOT / "prepared/campaign-002/catalog.json").read_text())
    added = catalog["source_inventory"][len(original["source_inventory"]):]
    correction_path = ROOT / "prepared/campaign-002/preflight-correction-001.json"
    correction = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "manifest schema validation; zero trials started; no execution manifest written",
        "failed_catalog": artifact(failed_path),
        "retained_partial_freeze_directory": str(attempt.relative_to(ROOT)),
        "error": "jsonschema.ValidationError: 'source_id' is a required property in source_inventory[3]",
        "cause": "New proof artifacts were appended directly to a source-record array requiring source_id, provenance, and files.",
        "correction": "Wrap the same unchanged proof artifacts in a named source inventory record. Targets, references, trial matrix, resource budgets, amendment, and all artifact bytes are unchanged.",
    }
    write(correction_path, correction)
    write(attempt / "freeze_failure.json", correction)
    catalog["source_inventory"] = original["source_inventory"] + [{
        "source_id": "campaign002-adapter-amendment001",
        "provenance": "Disclosed posthoc unit correction, bounded diagnostics, and premeasurement validation; all original sources and outcomes retained.",
        "files": added + [artifact(correction_path)],
    }]
    catalog["exposure_ledger"].append({
        "event": "premeasurement-manifest-schema-correction",
        "exposure": "Manifest schema rejection only; zero corrected trials started.",
        "effect_on_selection": "Inventory structure correction with no target, reference, resource, or trial selection change.",
        "artifact": artifact(correction_path),
    })
    schema = json.loads((ROOT / "grader/campaign-002/manifest.schema.json").read_text())
    jsonschema.validate(catalog["source_inventory"], {"$defs": schema["$defs"], **schema["properties"]["source_inventory"]})
    assert catalog["models"] == original["models"]
    assert catalog["references"] == original["references"]
    write(catalog_path, catalog)
    print(json.dumps({"source_inventory_schema": "passed", "original_targets_and_references": "unchanged", "corrected_trial_count": 0}))


if __name__ == "__main__":
    main()
