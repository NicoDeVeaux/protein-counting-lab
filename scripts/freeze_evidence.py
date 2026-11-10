"""Freeze files and explicit claims for independent review."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "runs/review-001"
target.mkdir()
claims = {
    "prepared_at": datetime.now(timezone.utc).isoformat(),
    "claims": [
        {"id": "artifact", "statement": "The repository contains a provenance-tracked conversion of 14 public UAI redesign cases into 42 source-first, fixed-sequence state partition queries. The source's zeros and discrete-model approximations are preserved.", "category": "validated_benchmark_artifact"},
        {"id": "correctness", "statement": "Within the prospective floating-log tolerance, independent enumeration and variable elimination agree for all 42 state models. The 126 approximate bounds contain the chosen reference values; float64 bounds are not interval certificates.", "category": "useful_measurement"},
        {"id": "small_cohort_feasibility", "statement": "This cohort is tractable with conventional inference on the recorded local hardware. Its results alone do not justify implementing a new asymptotic counting algorithm or generalize to larger/other protein models.", "category": "useful_measurement"},
        {"id": "literal_schedule", "statement": "The four necessary gates in the literal Section4 parameter schedule fail at the fixed illustrative sizes. For beta=1 their first passing lambda is 10909384704, hence the first N in that ceil-log interval is 2**10909384703+1. This is not all-hypothesis feasibility, a runtime crossover, or a lower bound on optimized variants.", "category": "eth_specific_progress"},
        {"id": "reproduction_gap", "statement": "The retrieved 2025 supplementary package supplies 63 measured affinity labels and scripts, but not prepared input PDBs, computed score tables, or energy matrices required for a direct matched-input epsilon sweep. Reconstructing inputs was not attempted.", "category": "useful_measurement"},
        {"id": "novel_speedup", "statement": "No novel counting algorithm or ETH-derived computational speedup is claimed; timing comparisons are conventional variable elimination versus the named exhaustive implementation only.", "category": "computational_improvement", "claimed": False},
        {"id": "biology", "statement": "No improvement in experimental affinity prediction is tested. The UAI models and experimental labels describe different systems and are not paired.", "category": "biological_evidence", "claimed": False},
    ],
    "requested_review": "Evaluate usefulness and scope independently, reject unsupported claims, audit source conversion and schedule minimality, and identify which next experiment the evidence supports. Do not assume a positive outcome is preferred.",
}
(target / "claims.json").write_text(json.dumps(claims, indent=2) + "\n")
files = []
for directory in ("data", "experiments", "grader", "runs/campaign-001", "runs/eth-schedule-001", "scripts", "tests"):
    for path in sorted((root / directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            files.append(path)
files += [root / p for p in ("AGENTS.md", "README.md", "pyproject.toml", "uv.lock")]
files.append(target / "claims.json")
manifest = {"frozen_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Exact local files supplied to grader before phase2; later reports/diagnostics are separate.",
            "files": [{"path": str(p.relative_to(root)), "bytes": p.stat().st_size,
                       "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(files))]}
path = target / "bundle_manifest.json"
path.write_text(json.dumps(manifest, indent=2) + "\n")
sha = hashlib.sha256(path.read_bytes()).hexdigest()
(target / "bundle_manifest.sha256").write_text(sha + "  bundle_manifest.json\n")
print(json.dumps({"bundle": str(path), "sha256_prefix": sha[:6], "files": len(manifest["files"])}))
