"""Independently reconcile the original frozen campaign-002 bundle and rows."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "grader/campaign-002"


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    bundle_path = "runs/campaign-002-review/bundle_manifest.json"
    bundle = read(bundle_path)
    manifest_path = "runs/campaign-002/manifest.json"
    manifest = read(manifest_path)
    manifest_hash = sha(manifest_path)
    trials = [json.loads(line) for line in (ROOT / "runs/campaign-002/trials.jsonl").read_text().splitlines()]
    planned = read("runs/campaign-002/planned_trials.json")
    integrity_errors = []
    total_bytes = 0
    for artifact in bundle["files"]:
        p = ROOT / artifact["path"]
        if not p.is_file():
            integrity_errors.append({"path": artifact["path"], "error": "missing"})
            continue
        total_bytes += p.stat().st_size
        if p.stat().st_size != artifact["bytes"] or sha(artifact["path"]) != artifact["sha256"]:
            integrity_errors.append({"path": artifact["path"], "error": "size_or_hash"})
    own_freeze = read("grader/campaign-002/FREEZE.json")
    grader_errors = [x["path"] for x in own_freeze["files"] if sha(x["path"]) != x["sha256"]]
    manifest_validator = Draft202012Validator(read("grader/campaign-002/manifest.schema.json"), format_checker=FormatChecker())
    trial_validator = Draft202012Validator(read("grader/campaign-002/trial.schema.json"), format_checker=FormatChecker())
    schema_errors = {"manifest": [str(e) for e in manifest_validator.iter_errors(manifest)], "trials": []}
    for trial in trials:
        for error in trial_validator.iter_errors(trial):
            schema_errors["trials"].append({"trial_id": trial["trial_id"], "path": list(error.path), "error": error.message})
    expected = {x["trial_id"]: x for x in planned}
    observed = {x["trial_id"]: x for x in trials}
    reconciliation_errors = []
    for trial in trials:
        key = trial["trial_id"]
        if key not in expected:
            reconciliation_errors.append({"trial_id": key, "error": "unplanned"})
            continue
        for name in ["model_id", "representation_id", "method_id", "resource_profile_id", "accuracy_contract_id", "repeat"]:
            if trial[name] != expected[key][name]:
                reconciliation_errors.append({"trial_id": key, "error": "planned_identity", "field": name})
        if trial["manifest_sha256"] != manifest_hash:
            reconciliation_errors.append({"trial_id": key, "error": "manifest_hash"})
        if trial != read("runs/campaign-002/raw/" + key + ".trial.json"):
            reconciliation_errors.append({"trial_id": key, "error": "raw_row_mismatch"})
    for key in expected.keys() - observed.keys():
        reconciliation_errors.append({"trial_id": key, "error": "missing"})
    cohorts = {m["model_id"]: m["cohort"] for m in manifest["models"]}
    grouped = defaultdict(Counter)
    failures = []
    for trial in trials:
        grouped[(cohorts[trial["model_id"]], trial["method_id"], trial["resource_profile_id"])][trial["status"]] += 1
        if trial["status"] not in ["success", "unverified_accuracy"]:
            failures.append({k: trial.get(k) for k in ["trial_id", "model_id", "representation_id", "method_id", "resource_profile_id", "repeat", "status", "raw_status", "failure_detail", "exit_code"]} | {"rss_peak_bytes": trial["memory"]["rss_peak_bytes"], "wall_seconds": trial["timing"]["wall_seconds"]})
    output = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "original_bundle_interim_audit_no_broad_comparative_verdict",
        "bundle": {"path": bundle_path, "sha256": sha(bundle_path), "files": len(bundle["files"]), "bytes": total_bytes},
        "manifest_sha256": manifest_hash,
        "integrity_errors": integrity_errors,
        "grader_payload_integrity_errors": grader_errors,
        "schema_errors": schema_errors,
        "trial_counts": {"planned": len(planned), "manifest_planned": len(manifest["planned_trials"]), "observed": len(trials), "unique": len(observed), "raw_trial_files": len(list((ROOT / "runs/campaign-002/raw").glob("*.trial.json")))},
        "manifest_plan_equals_external": manifest["planned_trials"] == planned,
        "reconciliation_errors": reconciliation_errors,
        "status_counts": dict(Counter(x["status"] for x in trials)),
        "cohort_model_counts": dict(Counter(cohorts.values())),
        "status_by_cohort_method_profile": [{"cohort": k[0], "method": k[1], "profile": k[2], "counts": dict(v)} for k, v in sorted(grouped.items())],
        "earliest_trial_start": min(x["started_at_utc"] for x in trials if x["started_at_utc"]),
        "manifest_freeze_at": manifest["frozen_at_utc"],
        "failures": failures,
    }
    (OUT / "original_integrity_audit.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: output[k] for k in ["bundle", "integrity_errors", "grader_payload_integrity_errors", "trial_counts", "reconciliation_errors", "status_counts", "cohort_model_counts", "earliest_trial_start", "manifest_freeze_at"]}, indent=2))
    print("Schema error counts:", len(schema_errors["manifest"]), len(schema_errors["trials"]))


if __name__ == "__main__":
    main()
