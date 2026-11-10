"""Normalize descriptive algebra labels into the inherited schema enum only."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import jsonschema

from scripts.bind_round3_amendment import ROOT, artifact


def structural_diff(before, after, path=()):
    missing = {"__absent__": True}
    if isinstance(before, dict) and isinstance(after, dict):
        return [change for key in sorted(before.keys() | after.keys())
                for change in structural_diff(before.get(key, missing), after.get(key, missing), path+(key,))]
    if isinstance(before, list) and isinstance(after, list):
        return [change for index in range(max(len(before), len(after)))
                for change in structural_diff(before[index] if index < len(before) else missing,
                    after[index] if index < len(after) else missing, path+(index,))]
    return [] if before == after else [{"path": list(path), "before": before, "after": after}]


def bind():
    directory = ROOT / "prepared/campaign-003"
    amendment = ROOT / "grader/campaign-003/AMENDMENT-003.json"
    assert amendment.exists()
    old = json.loads((directory / "catalog.amendment-002.json").read_text())
    catalog = deepcopy(old)
    labels = []
    for model in catalog["models"]:
        for rep in model["representations"]:
            proof = json.loads((ROOT / rep["evidence"][0]["path"]).read_text())
            changes = proof["pipeline"]["algebra_transformations"]
            kinds = {change["kind"] for change in changes}
            if not kinds:
                label = "unchanged"
            elif kinds <= {"constant_factor", "independent_of_first_axis", "independent_of_second_axis"}:
                label = "exact_constant_scope"
            elif kinds == {"exact_binary_rational_additive_split"}:
                label = "exact_separable"
            else:
                assert kinds <= {"constant_factor", "independent_of_first_axis", "independent_of_second_axis", "exact_binary_rational_additive_split"}
                label = "multiple_exact"
            rep["simplification_description"] = rep["simplification"]
            rep["simplification"] = label
            labels.append({"model_id": model["model_id"], "arm": rep["representation_id"], "label": label})
    catalog["format_amendment"] = artifact(amendment)
    catalog["source_inventory"].append({"source_id": "campaign003-format-amendment003",
        "provenance": "Complete premeasurement schema diagnostic; enum-only algebra label correction; all original catalogs and partial freezes retained.",
        "files": [artifact(ROOT / name) for name in ["grader/campaign-003/AMENDMENT-003.json",
            "scripts/bind_round3_enum.py", "scripts/execute_round3_v3.py", "scripts/diagnose_round3_schema.py",
            "runs/campaign-003-amendment-002/freeze_failure.json",
            "runs/campaign-003-schema-diagnostic/candidate.json", "runs/campaign-003-schema-diagnostic/all-schema-errors.json"]]})
    catalog["exposure_ledger"].append({"event": "format-only-amendment003", "exposure": "Second zero-trial freeze rejection; all24errors are the same inherited algebra enum. Complete candidate checked before a measured launch.", "effect_on_selection": "None; no algorithm/preparation/plan/resource/reference change.", "artifact": artifact(amendment)})
    def projection(value):
        value = deepcopy(value)
        for model in value["models"]:
            for rep in model["representations"]:
                rep.pop("simplification", None)
                rep.pop("simplification_description", None)
        for key in ["source_inventory", "exposure_ledger", "format_amendment"]:
            value.pop(key, None)
        return value
    assert projection(catalog) == projection(old)
    plan = json.loads((directory / "preparation_manifest.json").read_text())
    for item in plan["implementation_inventory"]:
        assert artifact(ROOT / item["path"]) == item
    path = directory / "catalog.amendment-003.json"
    with path.open("x") as stream:
        stream.write(json.dumps(catalog, indent=2, allow_nan=False) + "\n")
    candidate = json.loads((ROOT / "runs/campaign-003-schema-diagnostic/candidate.json").read_text())
    candidate.update({"models": catalog["models"], "source_inventory": catalog["source_inventory"],
        "exposure_ledger": catalog["exposure_ledger"], "catalog": artifact(path),
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "premeasurement_attestation": "Complete corrected schema fixture only; no measured worker is launched by this diagnostic."})
    schema = json.loads((ROOT / "grader/campaign-003/manifest.schema.json").read_text())
    errors = list(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).iter_errors(candidate))
    assert not errors, [error.message for error in errors]
    fixture = directory / "complete-corrected-schema-fixture.json"
    with fixture.open("x") as stream:
        stream.write(json.dumps(candidate, indent=2) + "\n")
    report = {"validated_at_utc": datetime.now(timezone.utc).isoformat(), "timed_trials": 0,
        "original_catalog": artifact(directory / "catalog.json"), "previous_catalog": artifact(directory / "catalog.amendment-002.json"),
        "replacement_catalog": artifact(path), "preparation_manifest": artifact(directory / "preparation_manifest.json"),
        "complete_schema_fixture": artifact(fixture), "full_schema_errors": 0,
        "wrapper": artifact(ROOT / "scripts/execute_round3_v3.py"),
        "retained_errors": [artifact(ROOT / name) for name in ["runs/campaign-003/freeze_failure.json", "runs/campaign-003-amendment-002/freeze_failure.json"]],
        "unchanged": "All catalog values except declared enum/description and provenance/exposure metadata; all frozen implementation files, original/prepared model bytes, references, resources, and324trialplan.",
        "proof_kind_mapping": {"no transformations": "unchanged", "only constant_factor/independent_of_first_axis/independent_of_second_axis": "exact_constant_scope",
            "only exact_binary_rational_additive_split": "exact_separable", "mixture of the preceding exact kinds": "multiple_exact", "any unknown kind": "reject"},
        "complete_structural_diff": structural_diff(old, catalog), "labels": labels}
    report_path = directory / "binding-amendment-003.json"
    with report_path.open("x") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    with (directory / "binding-amendment-003.sha256").open("x") as stream:
        stream.write(artifact(report_path)["sha256"] + "  binding-amendment-003.json\n")
    print(json.dumps({"complete_manifest_schema_errors": 0, "catalog": str(path.relative_to(ROOT)), "timed_workers": 0}), flush=True)


def verify_binding():
    from scripts.campaign_round3 import catalog_artifacts

    directory = ROOT / "prepared/campaign-003"
    report = json.loads((directory / "binding-amendment-003.json").read_text())
    list(catalog_artifacts(report))
    catalog = json.loads((directory / "catalog.amendment-003.json").read_text())
    list(catalog_artifacts(catalog))
    plan = json.loads((directory / "preparation_manifest.json").read_text())
    for item in plan["implementation_inventory"]:
        assert artifact(ROOT / item["path"]) == item
    fixture = json.loads((directory / "complete-corrected-schema-fixture.json").read_text())
    schema = json.loads((ROOT / "grader/campaign-003/manifest.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(fixture)


if __name__ == "__main__":
    bind()
