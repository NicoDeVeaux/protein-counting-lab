"""Freeze the disclosed adapter correction without changing original evidence."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def artifact(name):
    path = ROOT / name
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def create(name, value):
    with (ROOT / name).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    catalog = json.loads((ROOT / "prepared/campaign-002/catalog.json").read_text())
    proof_names = [
        "grader/campaign-002/primary_sources/provenance.json",
        "grader/campaign-002/primary_sources/scheduledInference_inl.h",
        "grader/campaign-002/primary_sources/scheduler_inl.h",
        "experiments/established/diagnostics/results-authorized/diagnostic_plan.json",
        "experiments/established/diagnostics/results-authorized/all_results.json",
        "experiments/established_v2/README.md",
        "experiments/established_v2/source_proof.json",
        "experiments/established_v2/pyagrum_adapter.py",
        "tests/test_established_pyagrum_v2.py",
        "tests/test_driver_round2_v2.py",
        "prepared/campaign-002/amendment-001-tests.txt",
    ]
    proof = [artifact(name) for name in proof_names]
    timestamp = datetime.now(timezone.utc).isoformat()
    amendment = {
        "schema_version": 1,
        "amendment_id": "campaign-002-amendment-001",
        "frozen_at_utc": timestamp,
        "kind": "adaptive_corrective_full_matrix_rerun",
        "original_execution_manifest": artifact("runs/campaign-002/manifest.json"),
        "original_review_bundle": artifact("runs/campaign-002-review/bundle_manifest.json"),
        "original_catalog": artifact("prepared/campaign-002/catalog.json"),
        "exposure": "All original campaign002 outcomes, 15 allocation exceptions, their independent source-unit audit, and 16 outcome-selected bounded quota diagnostics are known. This is a disclosed correction, not an unseen preregistration.",
        "defect": "Adapter version1 follows a misleading Python docstring and passes 1 to setMaxMemory. Pinned C++ implements the argument in MiB, imposing a 1 MiB native workspace quota instead of the intended 1 GiB. Its allocation exceptions do not demonstrate failure at the external RSS ceiling.",
        "correction": {
            "adapter_module": "experiments.established_v2",
            "adapter_version": 2,
            "native_memory_mebibytes": 1024,
            "scope": "Native scheduler workspace quota above both unchanged external RSS ceilings; external watchdog remains authoritative.",
            "unchanged": ["all model bytes and targets", "stored-log numeric semantics", "source conversion and exact reductions", "all reference values and accuracy rules", "all 828 trial identities and schedule", "three fresh repeats", "low/high external time/table/RSS profiles", "single numerical thread", "900-second campaign budget", "20,000,000-state enumeration guard", "custom VE and batch implementations"],
        },
        "diagnostic_scope": "The bounded diagnostics were selected from failed outcomes. They establish the unit defect and test the correction; they are retained separately and do not replace any original trial.",
        "execution_rule": "Repeat every original planned row for all three methods. Preserve both runs, including all failures and unverified results. No failure-only replacement or outcome-based target selection.",
        "proof_artifacts": proof,
        "limitations": ["The established adapter reconstructs log Z using conditional marginal queries, not a native one-query partition-sum API.", "The correction does not remove binary64 linear-weight conversion limitations.", "No ETH implementation, new algorithm, physical affinity, or biological prediction claim."],
    }
    name = "prepared/campaign-002/amendment-001.json"
    create(name, amendment)
    catalog["amended_at_utc"] = timestamp
    catalog["amendment"] = artifact(name)
    catalog["source_inventory"] += proof + [catalog["amendment"]]
    catalog["exposure_ledger"].append({
        "event": "adaptive-native-memory-unit-correction",
        "exposure": amendment["exposure"],
        "effect_on_selection": "No change to selection or targets; full original matrix repeated with version2 adapter and corrected native quota.",
        "artifact": catalog["amendment"],
    })
    assert catalog["models"] == json.loads((ROOT / "prepared/campaign-002/catalog.json").read_text())["models"]
    create("prepared/campaign-002/amended_catalog.json", catalog)
    print(json.dumps({"amendment": name, "sha256_prefix": catalog["amendment"]["sha256"][:6]}))


if __name__ == "__main__":
    main()
