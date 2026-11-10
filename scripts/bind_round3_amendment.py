"""Correct inherited catalog field formatting without rerunning preparation."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def artifact(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def selection_rule():
    return {"rule": "All six unchanged campaign002 CPD targets, both arms and low/high profiles; all six predeclared synthetic controls, both arms and high profile. No outcome selection.",
        "baseline_42_mapping": artifact(ROOT / "prepared/campaign-002/baseline42_mapping.json"),
        "baseline_42_mapping_scope": "Inherited schema provenance field only; the 42 baseline models are not measured in003.",
        "coverage_gaps": ["No sparse larger published protein family", "No binding ensemble or biological affinity prediction", "No independent frozen numerical oracle for five larger proteins"],
        "intended_cells": [{"cohort": "published_protein_extension", "models": 6,
                            "arms": ["simplified", "propagated"], "profiles": ["low", "high"]},
                           {"cohort": "synthetic_measured", "models": 6,
                            "arms": ["simplified", "propagated"], "profiles": ["high"]}]}


def bind():
    directory = ROOT / "prepared/campaign-003"
    amendment = ROOT / "grader/campaign-003/AMENDMENT-002.json"
    assert amendment.exists()
    old = json.loads((directory / "catalog.json").read_text())
    catalog = deepcopy(old)
    catalog["selection_rule"] = selection_rule()
    schema = json.loads((ROOT / "grader/campaign-003/manifest.schema.json").read_text())
    jsonschema.validate(catalog["selection_rule"], {"$defs": schema["$defs"], **schema["properties"]["selection_rule"]})
    catalog["format_amendment"] = artifact(amendment)
    catalog["source_inventory"].append({"source_id": "campaign003-format-amendment002",
        "provenance": "Preserved zero-trial manifest schema rejection and format-only binding correction; no preprocessing, method, target, reference, resource or schedule change.",
        "files": [artifact(ROOT / name) for name in ["grader/campaign-003/AMENDMENT-002.json",
            "runs/campaign-003/freeze_failure.json", "scripts/bind_round3_amendment.py",
            "scripts/execute_round3_v2.py", "tests/test_round3_binding.py",
            "prepared/campaign-003/binding-tests.txt"]]})
    catalog["exposure_ledger"].append({"event": "format-only-amendment002",
        "exposure": "All24staticpreparations completed; inherited selection_rule schema rejected before any measured trial. Algorithms and original prepared artifacts remain frozen.",
        "effect_on_selection": "None; unchanged all12models324rows, references, implementations and budgets.",
        "artifact": artifact(amendment)})
    for key in ["models", "references", "preparation_manifest", "preparation_ledger"]:
        assert catalog[key] == old[key]
    output = directory / "catalog.amendment-002.json"
    with output.open("x") as stream:
        stream.write(json.dumps(catalog, indent=2, allow_nan=False) + "\n")
    report = {"bound_at_utc": datetime.now(timezone.utc).isoformat(), "original_catalog": artifact(directory / "catalog.json"),
        "corrected_catalog": artifact(output), "amendment": artifact(amendment),
        "retained_error": artifact(ROOT / "runs/campaign-003/freeze_failure.json"),
        "replacement_wrapper": artifact(ROOT / "scripts/execute_round3_v2.py"),
        "unchanged": ["models/targets", "references", "preparation manifest", "all24staticresults", "algorithms", "full324trialplan", "resourcebudgets"]}
    with (directory / "binding-amendment-002.json").open("x") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"catalog": str(output.relative_to(ROOT)), "sha256_prefix": artifact(output)["sha256"][:6]}), flush=True)


def validate_binding(run_dir):
    directory = ROOT / "prepared/campaign-003"
    old = json.loads((directory / "catalog.json").read_text())
    corrected = json.loads((directory / "catalog.amendment-002.json").read_text())
    permitted = {"selection_rule", "source_inventory", "exposure_ledger", "format_amendment"}
    assert {key:value for key,value in old.items() if key not in permitted} == {
        key:value for key,value in corrected.items() if key not in permitted}
    plan = json.loads((directory / "preparation_manifest.json").read_text())
    manifest = json.loads((run_dir / "manifest.json").read_text())
    schema = json.loads((ROOT / "grader/campaign-003/manifest.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(manifest)
    for key in ["references", "planned_trials", "resource_profiles", "total_wall_budget_seconds", "preprocessing_limit_seconds"]:
        assert manifest[key] == plan[key], key
    verified = 0
    for item in plan["implementation_inventory"]:
        assert artifact(ROOT / item["path"]) == item, item["path"]
        verified += 1
    for model in old["models"]:
        assert artifact(ROOT / model["pipeline_input"]["path"]) == model["pipeline_input"]
        for rep in model["representations"]:
            for item in rep["files"] + rep["evidence"]:
                assert artifact(ROOT / item["path"]) == item, item["path"]
                verified += 1
    assert not (run_dir / "trials.jsonl").exists()
    report = {"validated_at_utc": datetime.now(timezone.utc).isoformat(), "timed_trials_so_far": 0,
        "original_catalog": artifact(directory / "catalog.json"), "replacement_catalog": artifact(directory / "catalog.amendment-002.json"),
        "error": artifact(ROOT / "runs/campaign-003/freeze_failure.json"),
        "replacement_wrapper": artifact(ROOT / "scripts/execute_round3_v2.py"),
        "complete_candidate_manifest": artifact(run_dir / "manifest.json"),
        "full_manifest_schema": "passed unchanged003schema with format checks",
        "unchanged": ["all catalog fields except disclosed format/provenance/exposure fields", "all model/derived/proof bytes", "references", "full324rowplan", "resourceprofiles", "totalbudget", "preprocessinglimit", "frozenimplementationinventory"],
        "verified_implementation_and_derived_artifacts": verified}
    path = run_dir / "correction-validation.json"
    with path.open("x") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    with (run_dir / "correction-validation.sha256").open("x") as stream:
        stream.write(artifact(path)["sha256"] + "  correction-validation.json\n")
    print(json.dumps({"complete_manifest_schema": "passed", "prospective_contracts_and_bytes": "unchanged", "timed_trials": 0}), flush=True)


if __name__ == "__main__":
    bind()
