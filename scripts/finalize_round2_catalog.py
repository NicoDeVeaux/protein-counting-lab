"""Record prospective metadata corrections and the static enumeration-cap choice."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
out = root / "prepared/campaign-002"
catalog_path = out / "catalog.json"
backup = out / "catalog.before-finalization.json"
if backup.exists():
    raise FileExistsError(backup)
shutil.copyfile(catalog_path, backup)
catalog = json.loads(catalog_path.read_text())
source = json.loads((root/"data/campaign-002/cpd_manifest.json").read_text())
audits = {c["model_id"]: c for c in source["cases"]}
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for model in catalog["models"]:
    if model["model_id"] in audits:
        case = audits[model["model_id"]]
        model["conversion_checks"] = {"path": case["audit_path"], "sha256": case["audit_sha256"]}
ledger_path = root/catalog["preparation_ledger"]["path"]
shutil.copyfile(ledger_path, out/"preparation_ledger.before-finalization.json")
ledger = json.loads(ledger_path.read_text())
ledger["all_source_attempts"] = "data/campaign-002/availability_audit.json"
ledger["source_download_ledger"] = "data/campaign-002/cpd_downloads.json"
ledger_path.write_text(json.dumps(ledger,indent=2)+"\n")
catalog["preparation_ledger"]["sha256"] = sha(ledger_path)
catalog["exposure_ledger"].append({
    "event": "prospective-static-census-cap-adjustment",
    "exposure": "Static configurations: new author1FYN=15805440 and syntheticclique12=16777216; no new timed inference outcomes.",
    "effect_on_selection": "Set batch cap to20000000 from tentative11000000 before execution freeze, admitting meaningful streaming/materialized comparisons. Time/RSS profiles and900s campaign budget unchanged.",
})
catalog["reference_subset_rule"] = "All42 prior models retain historically independently checked references (20have80-digit stored-log references); ten deterministic synthetic controls have90-digit analytic/row-transfer references. The six new author models and grid8 have no adequate initial numerical oracle and remain unverified_accuracy unless a separately labeled independent later audit establishes more. No biological labels are paired."
catalog_path.write_text(json.dumps(catalog,indent=2)+"\n")
change = {"recorded_at": datetime.now(timezone.utc).isoformat(), "before_measurements": True,
          "old_catalog": {"path": str(backup.relative_to(root)), "sha256": sha(backup)},
          "new_catalog": {"path": str(catalog_path.relative_to(root)), "sha256": sha(catalog_path)},
          "changes": ["Point new models to their actual per-case conversion audit.", "Correct preparation ledger to existing availability/download ledgers.", "Record prospective20million-state cap choice and frozen reference coverage."],
          "model_bytes_changed": False}
(out/"finalization.json").write_text(json.dumps(change,indent=2)+"\n")
print(json.dumps({"catalog": str(catalog_path), "sha256_prefix": sha(catalog_path)[:6]}))
