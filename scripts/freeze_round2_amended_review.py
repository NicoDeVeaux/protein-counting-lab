"""Seal both measured runs and the disclosed correction for independent review."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = ROOT / "runs/campaign-002-amendment-001"
    review = ROOT / "runs/campaign-002-amendment-001-review"
    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    original_bundle = ROOT / "runs/campaign-002-review/bundle_manifest.json"
    original = json.loads(original_bundle.read_text())
    assert summary["planned_trials"] == summary["recorded_trials"] == 828
    assert not summary["missing_trial_ids"] and not summary["unexpected_trial_ids"]
    files = {ROOT / item["path"] for item in manifest["file_inventory"]}
    for item in manifest["file_inventory"]:
        assert digest(ROOT / item["path"]) == item["sha256"], item["path"]
    for item in original["files"]:
        assert digest(ROOT / item["path"]) == item["sha256"], item["path"]
        files.add(ROOT / item["path"])
    files.add(original_bundle)
    files.add(ROOT / "runs/campaign-002-review/bundle_manifest.sha256")
    files.add(Path(__file__).resolve())
    files.update(path for path in run.rglob("*") if path.is_file())
    files.update(path for path in (ROOT / "runs/campaign-002-amendment-001-freeze-attempt-001").rglob("*") if path.is_file())
    review.mkdir()
    claims = {
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "corrected_execution_manifest_sha256": digest(run / "manifest.json"),
        "original_review_bundle_sha256": digest(original_bundle),
        "observed_corrected_status_counts": summary["status_counts"],
        "claims": [
            {"id": "disclosed_correction", "statement": "The full 828-row matrix was rerun after correcting a native scheduler unit defect from 1 MiB to 1024 MiB. Original outcomes and selected diagnostics informed this adaptive amendment; both runs and the premeasurement schema rejection are retained."},
            {"id": "matched_targets", "statement": "All original trial identities, model bytes, conditioning, references, external resource profiles, repetitions, and schedule are unchanged. Only the established adapter's native quota and version change."},
            {"id": "comparator_scope", "statement": "The comparator is pinned pyagrum3.3.2 Shafer-Shenoy inference with an adapter reconstructing log Z through conditional marginals. Costs include all queries. It is not a comparison against a native single-query partition-sum API or every established counting solver."},
            {"id": "published_scope", "statement": "The six new protein models are fixed-AA, single-state numerical beta=1 partition sums. They retain complete interactions among nontrivial variables after exact simplification. They do not establish sparse protein graph coverage or affinity prediction."},
            {"id": "numerics", "statement": "Finite output without an adequate independent reference remains unverified_accuracy. Binary64 agreement is not an interval certificate. Conversion rejection is an adapter limitation, not proof that the target is unsolvable."},
            {"id": "timing_scope", "statement": "Subprocess wall times and internal phases are recorded separately. preparation_seconds excludes derived artifact serialization; one_off_wall_plus_algebra_seconds is not complete raw-source-to-answer latency. Three repeats provide descriptive local measurements, not broad scaling laws."},
            {"id": "interpretation", "statement": "No ETH implementation, novel inference algorithm, improved biological prediction, or general solver superiority is claimed. The grader should identify useful local regimes, obstructions, and stop conditions regardless of which method wins."},
        ],
        "requested_review": "Independently verify integrity, target/row/resource identity, numeric and source semantics, changes in failure status, and defensible usefulness. Compare both runs without replacing inconvenient originals. State numerical and dataset limits prominently.",
    }
    claim_path = review / "claims.json"
    claim_path.write_text(json.dumps(claims, indent=2) + "\n")
    files.add(claim_path)
    bundle = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Corrected full matrix, retained original bundle and disclosed diagnostics/premeasurement correction; independent reports are separate.",
              "files": [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path)} for path in sorted(files)]}
    path = review / "bundle_manifest.json"
    path.write_text(json.dumps(bundle, indent=2) + "\n")
    (review / "bundle_manifest.sha256").write_text(digest(path) + "  bundle_manifest.json\n")
    print(json.dumps({"bundle": str(path.relative_to(ROOT)), "sha256_prefix": digest(path)[:6], "files": len(files)}))


if __name__ == "__main__":
    main()
