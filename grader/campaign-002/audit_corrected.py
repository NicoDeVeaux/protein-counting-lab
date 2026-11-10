"""Verify the corrective bundle and compare only paired recorded observations."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "grader/campaign-002"


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def quartiles(values):
    values = sorted(values)
    return {"count":len(values),"min":min(values),"median":statistics.median(values),"max":max(values)} if values else {"count":0}


def trials(path):
    return [json.loads(line) for line in (ROOT/path).read_text().splitlines()]


def cell(row):
    return tuple(row[k] for k in ["model_id","representation_id","method_id","resource_profile_id"])


def main():
    bundle_path="runs/campaign-002-amendment-001-review/bundle_manifest.json"
    bundle=read(bundle_path)
    errors=[]
    for artifact in bundle["files"]:
        p=ROOT/artifact["path"]
        if not p.is_file() or p.stat().st_size!=artifact["bytes"] or sha(artifact["path"])!=artifact["sha256"]:
            errors.append({"path":artifact["path"],"error":"missing_size_or_hash"})
    original_manifest=read("runs/campaign-002/manifest.json")
    manifest_path="runs/campaign-002-amendment-001/manifest.json"
    manifest=read(manifest_path)
    digest=sha(manifest_path)
    before=trials("runs/campaign-002/trials.jsonl")
    after=trials("runs/campaign-002-amendment-001/trials.jsonl")
    planned=read("runs/campaign-002-amendment-001/planned_trials.json")
    manifest_validator=Draft202012Validator(read("grader/campaign-002/manifest.schema.json"),format_checker=FormatChecker())
    trial_validator=Draft202012Validator(read("grader/campaign-002/trial.schema.json"),format_checker=FormatChecker())
    schema_errors=[str(e) for e in manifest_validator.iter_errors(manifest)]
    assert planned==manifest["planned_trials"]==original_manifest["planned_trials"]
    for key in ["models","references","accuracy_contracts","resource_profiles","total_wall_budget_seconds"]:
        assert manifest[key]==original_manifest[key]
    assert len(after)==len(planned)==len({r["trial_id"] for r in after})==828
    planned_map={r["trial_id"]:r for r in planned}
    profiles={r["resource_profile_id"]:r for r in manifest["resource_profiles"]}
    modelmap={m["model_id"]:m for m in manifest["models"]}
    numeric={r["model_id"]:r for r in read("grader/campaign-002/independent_numeric_audit.json")["real"]}
    native_quotas=Counter()
    native_versions=Counter()
    recomputed=[]
    posthoc=[]
    grouped=defaultdict(Counter)
    for row in after:
        schema_errors.extend(row["trial_id"]+" "+e.message for e in trial_validator.iter_errors(row))
        plan=planned_map[row["trial_id"]]
        assert all(row[k]==plan[k] for k in ["model_id","representation_id","method_id","resource_profile_id","accuracy_contract_id","repeat"])
        assert row["manifest_sha256"]==digest
        assert row==read("runs/campaign-002-amendment-001/raw/"+row["trial_id"]+".trial.json")
        profile=profiles[row["resource_profile_id"]]
        assert all(row["memory"][k]==profile[k] for k in ["table_cap_bytes","rss_ceiling_bytes","rss_enforcement"])
        grouped[(modelmap[row["model_id"]]["cohort"],row["method_id"],row["resource_profile_id"])][row["status"]]+=1
        if row["status"]=="planned_skip":
            assert row["started_at_utc"] is None
            continue
        monitor=row["monitor"]
        assert monitor["sampling_errors"]==0
        assert row["memory"]["rss_peak_bytes"]==monitor["sampled_peak_rss_bytes"]
        assert row["timing"]["wall_seconds"]==monitor["wall_seconds"]
        raw=read(row["output"]["artifact"]["path"]) if row["output"]["artifact"] else None
        if row["status"]=="timeout":
            assert monitor["termination_reason"]=="timeout"
            assert monitor["limit_trigger_seconds"]>=profile["wall_timeout_seconds"]
        if row["status"] in ["success","unverified_accuracy"]:
            assert monitor["sampled_peak_rss_bytes"]<=profile["rss_ceiling_bytes"]
            assert row["memory"]["worker_reported_lifetime_peak_rss_bytes"]<=profile["rss_ceiling_bytes"]
            assert monitor["termination_reason"] is None
            if row["method_id"]=="pyagrum":
                native_quotas[raw["metrics"].get("native_memory_mebibytes")]+=1
                native_versions[raw["metrics"].get("package_version")]+=1
                assert raw["adapter_version"]==2
                assert raw["metrics"]["native_memory_mebibytes"]==1024
            ref=manifest["references"].get(row["model_id"])
            if row["status"]=="success":
                with localcontext() as ctx:
                    ctx.prec=110
                    expected=Decimal(ref["log_z"]) if isinstance(ref["log_z"],str) else Decimal.from_float(ref["log_z"])
                    error=float(abs(Decimal.from_float(row["output"]["log_z"])-expected))
                metrics=raw.get("metrics",{})
                abs_offsets=abs(metrics.get("scalar_log_offset",0.))+math.fsum(abs(f.get("log_offset",0.)) for f in metrics.get("factor_conversion",[]))
                threshold=1e-8+64*sys.float_info.epsilon*max(1.,abs(float(expected)),abs_offsets)
                assert error<=threshold
                assert error==row["validation"]["absolute_log_error"]
                recomputed.append(error)
            else:
                assert ref is None
            if row["model_id"] in numeric:
                with localcontext() as ctx:
                    ctx.prec=110
                    error=abs(Decimal.from_float(row["output"]["log_z"])-Decimal(numeric[row["model_id"]]["log_z"]))
                assert error<Decimal("1e-8")
                posthoc.append({"trial_id":row["trial_id"],"model_id":row["model_id"],"absolute_log_error":str(error)})
    old={r["trial_id"]:r for r in before}
    transitions=Counter((old[r["trial_id"]]["status"],r["status"]) for r in after)
    changed=[{"trial_id":r["trial_id"],"model_id":r["model_id"],"representation":r["representation_id"],"method":r["method_id"],"profile":r["resource_profile_id"],"repeat":r["repeat"],"original_status":old[r["trial_id"]]["status"],"corrected_status":r["status"],"wall_seconds":r["timing"]["wall_seconds"],"cpu_seconds":r["timing"]["cpu_seconds"]} for r in after if old[r["trial_id"]]["status"]!=r["status"]]
    cells=defaultdict(list)
    for row in after:
        if row["status"] in ["success","unverified_accuracy"]:
            cells[cell(row)].append(row)
    dispersion=[]
    for key,rs in cells.items():
        walls=[r["timing"]["wall_seconds"] for r in rs]
        kernels=[r["timing"]["phases"]["inference_kernel"] for r in rs if r["timing"]["phases"]["inference_kernel"] is not None]
        dispersion.append({"model_id":key[0],"representation":key[1],"method":key[2],"profile":key[3],"completed_repeats":len(rs),
            "wall":quartiles(walls),"wall_max_min_ratio":max(walls)/min(walls),"kernel":quartiles(kernels),
            "kernel_max_min_ratio":max(kernels)/min(kernels) if kernels and min(kernels)>0 else None})
    same_impl=[]
    for row in after:
        o=old[row["trial_id"]]
        if row["method_id"] in ["ve","batch"] and row["status"] in ["success","unverified_accuracy"] and o["status"]==row["status"]:
            same_impl.append({"trial_id":row["trial_id"],"quartile":min(3,int(row["trial_id"])*4//828),
                "wall_ratio":row["timing"]["wall_seconds"]/o["timing"]["wall_seconds"],
                "cpu_ratio":row["timing"]["cpu_seconds"]/o["timing"]["cpu_seconds"],
                "kernel_ratio":row["timing"]["phases"]["inference_kernel"]/o["timing"]["phases"]["inference_kernel"]})
    timeblocks=[{"schedule_quartile":q,**{metric:quartiles([r[metric] for r in same_impl if r["quartile"]==q]) for metric in ["wall_ratio","cpu_ratio","kernel_ratio"]}} for q in range(4)]
    full=[r for r in dispersion if r["completed_repeats"]==3]
    result={"recorded_at_utc":datetime.now(timezone.utc).isoformat(),"bundle_path":bundle_path,"bundle_sha256":sha(bundle_path),"bundle_files":len(bundle["files"]),"bundle_bytes":sum(x["bytes"] for x in bundle["files"]),
        "integrity_errors":errors,"schema_errors":schema_errors,"manifest_sha256":digest,"planned_rows":len(planned),"observed_rows":len(after),
        "models_references_accuracy_resources_total_budget_and_trial_matrix_unchanged":True,
        "manifest_freeze_at":manifest["frozen_at_utc"],"earliest_trial_start":min(r["started_at_utc"] for r in after if r["started_at_utc"]),
        "native_completed_quota_counts":dict(native_quotas),"native_completed_version_counts":dict(native_versions),
        "status_counts":dict(Counter(r["status"] for r in after)),"status_transitions":[{"from":a,"to":b,"count":n} for (a,b),n in transitions.items()],"changed_status_rows":changed,
        "max_error_against_frozen_refs":max(recomputed),"frozen_ref_successes_recompared":len(recomputed),"posthoc_high_precision_trial_checks":posthoc,
        "status_by_cohort_method_profile":[{"cohort":a,"method":b,"profile":c,"counts":dict(n)} for (a,b,c),n in sorted(grouped.items())],
        "corrected_repeat_dispersion":dispersion,
        "dispersion_summary":{"completed_cells":len(dispersion),"full_three_repeat_cells":len(full),"partial_repeat_cells":len(dispersion)-len(full),"wall_max_min_ratio":quartiles([r["wall_max_min_ratio"] for r in full]),"wall_ratio_gt2":sum(r["wall_max_min_ratio"]>2 for r in full),"wall_ratio_gt5":sum(r["wall_max_min_ratio"]>5 for r in full),"kernel_max_min_ratio":quartiles([r["kernel_max_min_ratio"] for r in full if r["kernel_max_min_ratio"] is not None])},
        "unchanged_custom_methods_corrected_over_original_by_schedule_quartile":timeblocks,
        "interpretation":"The complete rerun is a disclosed adaptive correction after original outcomes and outcome-selected diagnostics. Its values and resource policies are matched, but timing stationarity must be judged from recorded dispersion; the root reports no competing agent computation, without archived system telemetry proving a cause. Original and corrected records remain separate."}
    (OUT/"corrected_audit.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:result[k] for k in ["bundle_files","integrity_errors","schema_errors","planned_rows","observed_rows","status_counts","status_transitions","changed_status_rows","dispersion_summary","unchanged_custom_methods_corrected_over_original_by_schedule_quartile"]},indent=2))


if __name__=="__main__":
    main()
