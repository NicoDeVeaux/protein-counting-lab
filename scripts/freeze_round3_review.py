"""Seal all campaign003 attempts and unchanged prior evidence for its grader."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = ROOT / "runs/campaign-003-amendment-003"
    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    assert summary["planned_trials"] == summary["recorded_trials"] == 324
    assert not summary["missing_trial_ids"] and not summary["unexpected_trial_ids"]
    old_path = ROOT / "runs/campaign-002-amendment-001-review/bundle_manifest.json"
    old = json.loads(old_path.read_text())
    files = {old_path, Path(__file__).resolve()}
    for item in old["files"] + manifest["file_inventory"]:
        assert digest(ROOT / item["path"]) == item["sha256"], item["path"]
        files.add(ROOT / item["path"])
    for directory in ["prepared/campaign-003", "runs/campaign-003", "runs/campaign-003-amendment-002",
                      "runs/campaign-003-schema-diagnostic", "runs/campaign-003-amendment-003",
                      "grader/campaign-003"]:
        files.update(path for path in (ROOT / directory).rglob("*") if path.is_file())
    audit_path = ROOT / "grader/campaign-002/audit_manifest.json"
    audit = json.loads(audit_path.read_text())
    for item in audit["files"]:
        assert digest(ROOT / item["path"]) == item["sha256"]
        files.add(ROOT / item["path"])
    files.add(audit_path)
    files.add(ROOT / "grader/campaign-002/audit_manifest.sha256")
    review = ROOT / "runs/campaign-003-review"
    review.mkdir()
    claims = {
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_manifest_sha256": digest(run / "manifest.json"),
        "preparation_manifest_sha256": digest(ROOT / "prepared/campaign-003/preparation_manifest.json"),
        "status_counts": summary["status_counts"],
        "claims": [
            {"id": "cohort", "statement": "All six unchanged published CPD targets and six separately labeled synthetic controls, two representations, three methods and three repeats retain all324rows. Proteins use bothprofiles; controlshighonly."},
            {"id": "same_target", "statement": "The treated arm deletes only unsupported original-domain values from exact negative-infinity support constraints, with aligned duplicate-scope masks ANDed. Numeric factor values remain copied and unmerged; exact postrestriction algebra is the same implementation as baseline. Local consistency is not global support enumeration."},
            {"id": "charged_cost", "statement": "Both arms coldload the same original JSON and perform transformations inside the common row watchdog. Propagation/algebra/hash cost is not free. Wall/CPU phases and valid-result serialization sidecars retain their stated scope; immutable solver internal CPU subphases are not separately observable."},
            {"id": "prospectivity", "statement": "Adaptive003 followup: preparationmanifest froze code/models/references/budgets/completeplan before static preparation. Final executionmanifest preceded all measurements. Two metadata/schema freezes failed with zero measuredtrials and are retained. Numbered amendments disclose sequencing and format corrections; no numerical implementation, model, resource, reference or trialplan changed."},
            {"id": "numerics", "statement": "1FYN reference, formerly posthoc in002, is prospective in003. Otherfiveproteins still have no adequate reference if an output completes. Hardzero/control proofs require independent checks. Numerical agreement alone is not an oracle or interval certificate."},
            {"id": "scope", "statement": "Evaluate local feasibility, representation sizes, cold costs, memory and negative results. No ETH implementation, novel constraint algorithm, biological affinity improvement, general solver superiority or guaranteed RSS ceiling is claimed. Large domain-product reduction does not by itself make the remaining counting problem tractable."}],
        "requested_review": "Independently audit freeze chronology/amendments and unchanged plan; replay support deletions/mappings and exact algebra without importing the experiment; validate numerical controls/reference-covered cases; check all rawrows/resources/phase scopes and drift. Identify useful outcomes or reasons to stop without requiring a favorable result."}
    path = review / "claims.json"
    path.write_text(json.dumps(claims, indent=2) + "\n")
    files.add(path)
    bundle = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "All003attempts, preparation, final measurements and phase1grader criteria, with immutable002evidence. Later independent audits/plots/reports are separate.",
        "files": [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path)} for path in sorted(files)]}
    path = review / "bundle_manifest.json"
    path.write_text(json.dumps(bundle, indent=2) + "\n")
    (review / "bundle_manifest.sha256").write_text(digest(path) + "  bundle_manifest.json\n")
    print(json.dumps({"bundle": str(path.relative_to(ROOT)), "sha256_prefix": digest(path)[:6], "files": len(files)}))


if __name__ == "__main__":
    main()
