"""Supply the unchanged measured campaign and bounded claims to its independent grader."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
run = root / "runs/campaign-002"
review = root / "runs/campaign-002-review"
review.mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((run/"manifest.json").read_text())
summary = json.loads((run/"summary.json").read_text())
claims = {"prepared_at": datetime.now(timezone.utc).isoformat(),
    "campaign_manifest_sha256": sha(run/"manifest.json"),
    "claims": [
        {"id": "cohort", "statement": "Original42 retained plus six larger fixed-AA author protein-design models and11labeled synthetic mechanisms. Largerproteinmodelsare single-state beta=1 numerical targets, not physical binding-affinity ensembles."},
        {"id": "provenance", "statement": "Author target uses Etmp+BKB+pair, not an extra SELF term; only literal1.0E38 is mapped to hard zero. Source audits and serialized-entry checks are archived; independent grader must determine verified coverage."},
        {"id": "structure", "statement": "Recorded constant/scope/additive reductions are checked as exact identities of stored binary-rational log values, with all domains retained. Their usefulness and cost must be judged separately for published/synthetic inputs. Sparse protein coverage remains absent in the new six inputs."},
        {"id": "trial_accounting", "statement": "All828plannedrowsarepresent underfrozenresourceprofiles. Failuretypes andunverifiedaccuracyare retained; counts are trials, not independentproteins."},
        {"id": "established_comparator", "statement": "pyagrum3.3.2 adapter reconstructs logZ from nconditionalmarginals, with allquerycostsrecorded. Its conversion rejections and nativeexceptions must not be presented as universal solver/resource impossibility."},
        {"id": "native_exception_caution", "statement": "15rowscurrentlyclassifiedinvalid_output include std::bad_alloc exceptions, including smallmodels at lowobservedRSS. Their cause is unresolved at bundlefreeze; they do not establish a RAMcapacityfailure. Separate posthocdiagnostics may follow and must not replace these results."},
        {"id": "scope", "statement": "No ETHimplementation, novelinferencealgorithm, generic scalinglaw, or improvedbiologicalpredictionis claimed. Evaluate usablelocalregimes, numerical/representationobstructions, or reasons to stop."},
    ], "observed_status_counts": summary["status_counts"],
    "requested_review": "Independently check integrity, semantics/reductions, representative numerics, resource enforcement and status meanings; identify useful/interesting outcomes without assuming a preferred method must win. Native exception investigation is separate and does not alter original claims or results."}
(review/"claims.json").write_text(json.dumps(claims,indent=2)+"\n")
files = {root/i["path"] for i in manifest["file_inventory"]}
files.update(p for p in run.rglob("*") if p.is_file())
files.update(root/p for p in ["grader/REPORT.md","grader/audit_results.json","grader/spotcheck_results.json","runs/campaign-001/summary.json"])
files.add(review/"claims.json")
for item in manifest["file_inventory"]:
    assert sha(root/item["path"]) == item["sha256"], item["path"]
bundle = {"frozen_at": datetime.now(timezone.utc).isoformat(),
          "scope": "Original measured campaign002; later diagnostics/amendments/reports are separate.",
          "files": [{"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(files)]}
p=review/"bundle_manifest.json"
p.write_text(json.dumps(bundle,indent=2)+"\n")
(review/"bundle_manifest.sha256").write_text(sha(p)+"  bundle_manifest.json\n")
print(json.dumps({"bundle":str(p),"sha256_prefix":sha(p)[:6],"files":len(files)}))
