"""Adaptive corrective rerun of campaign 002; original evidence remains immutable."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time

import jsonschema
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.round2_watchdog import supervise, validate_controls

EXCLUDED = {".venv", "__pycache__", ".pytest_cache", ".git"}
METHODS = ("ve", "batch", "pyagrum")
THREAD_ENV = {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
              "MKL_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "PYTHONHASHSEED": "0"}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def artifact(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT/path
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}


def source_files():
    paths = set()
    for directory in ("experiments", "scripts", "tests", "data/campaign-002", "prepared/campaign-002", "data/raw/uai23"):
        for path in (ROOT/directory).rglob("*"):
            if path.is_file() and not EXCLUDED.intersection(path.relative_to(ROOT).parts):
                if directory == "experiments" and path.suffix not in {".py", ".toml", ".lock", ".json", ".md", ".txt"}:
                    continue
                paths.add(path)
    for name in ("AGENTS.md", "pyproject.toml", "uv.lock", "data/uai23_manifest.json",
                 "grader/campaign-002/PROTOCOL.md", "grader/campaign-002/FREEZE.json",
                 "grader/campaign-002/FREEZE.sha256", "grader/campaign-002/manifest.schema.json",
                 "grader/campaign-002/trial.schema.json"):
        paths.add(ROOT/name)
    return sorted(paths)


def catalog_artifacts(value):
    if isinstance(value,dict):
        if isinstance(value.get("path"),str) and isinstance(value.get("sha256"),str):
            path = (ROOT/value["path"]).resolve()
            if not path.is_relative_to(ROOT) or EXCLUDED.intersection(path.relative_to(ROOT).parts):
                raise ValueError("Catalog artifact is outside the allowed evidence tree: "+value["path"])
            if digest(path) != value["sha256"]:
                raise ValueError("Catalog artifact hash mismatch: "+value["path"])
            yield path
        for item in value.values():
            yield from catalog_artifacts(item)
    elif isinstance(value,list):
        for item in value:
            yield from catalog_artifacts(item)


def schema(name):
    return json.loads((ROOT/"grader/campaign-002"/(name+".schema.json")).read_text())


def validate(name, payload):
    jsonschema.Draft202012Validator(schema(name), format_checker=jsonschema.FormatChecker()).validate(payload)


def resource_profiles(control_artifact):
    profiles = []
    for name, table, rss, wall in (("low",16,128,10), ("high",128,512,20)):
        profiles.append({"resource_profile_id": name, "table_cap_bytes": table*1024**2,
            "allocation_accounting": "VE: each dense joined table; batch: bounded index/weight working arrays; pyagrum: its wrapper's clique-table estimate. These differ from total RSS and are not guarantees for all temporaries.",
            "wall_timeout_seconds": wall, "rss_ceiling_bytes": rss*1024**2,
            "rss_enforcement": "external_watchdog", "threads": 1, "cpu_limit": "One numerical/native thread, sequential trials; no OS CPU-time quota.",
            "rss_measurement": {"scope": "Worker plus live descendants; worker lifetime high-water also adjudicates completed trials.",
                "sampler": "psutil process-tree RSS every 0.01 seconds plus worker resource.ru_maxrss", "sample_interval_seconds": .01,
                "units": "bytes", "limitations": "Sampled peaks are lower bounds, sum RSS can double-count shared pages, short-lived descendants/transient peaks can be missed. No instantaneous ceiling guarantee. A completed worker high-water above the ceiling is a resource failure even if not sampled."},
            "watchdog_validation": control_artifact})
    return profiles


def check_corrective_matrix(catalog, planned, prior):
    if "amendment" not in catalog:
        raise ValueError("The corrective execution requires a dated, hashed amendment artifact")
    amendment = catalog["amendment"]
    if not isinstance(amendment,dict) or set(("path","sha256"))-amendment.keys():
        raise ValueError("amendment must identify its path and sha256")
    list(catalog_artifacts(amendment))
    if planned != prior["planned_trials"]:
        raise ValueError("Corrective run must repeat the full unchanged original trial matrix")
    def targets(models):
        return {(m["model_id"],r["representation_id"]): {
                    "files":r["files"], "cohort":m["cohort"],
                    "fixed_sequence_and_conditioning":m["fixed_sequence_and_conditioning"],
                    "source_semantics":m["source_semantics"], "target_relation":r["target_relation"]}
                for m in models for r in m["representations"]}
    if targets(catalog["models"]) != targets(prior["models"]):
        raise ValueError("Corrective run changed a model, representation, conditioning, or target")


def freeze(catalog_path, run_dir):
    if run_dir.exists():
        raise FileExistsError(run_dir)
    for required in ("experiments/established_v2/pyagrum_adapter.py", "tests/test_established_pyagrum_v2.py", "tests/test_driver_round2_v2.py"):
        if not (ROOT/required).exists():
            raise FileNotFoundError("Corrective adapter/control artifact missing: "+required)
    catalog = json.loads(catalog_path.read_text())
    for model in catalog["models"]:
        for rep in model["representations"]:
            for item in rep["files"]:
                assert digest(ROOT/item["path"]) == item["sha256"], item["path"]
    protocol_path = ROOT/"grader/campaign-002/PROTOCOL.md"
    freeze_doc = json.loads((ROOT/"grader/campaign-002/FREEZE.json").read_text())
    for item in freeze_doc["files"]:
        assert digest(ROOT/item["path"]) == item["sha256"]
    control_path = ROOT/"experiments/round2_watchdog/control/result.json"
    if not control_path.exists():
        raise FileNotFoundError("Run the watchdog control action before freezing")
    assert json.loads(control_path.read_text())["all_passed"]
    run_dir.mkdir(parents=True)
    dependencies = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions() if d.metadata.get("Name")}
    write_json(run_dir/"dependencies.json", dependencies)
    commands = {"python": sys.executable, "driver": "scripts/campaign_round2_v2.py", "catalog": str(catalog_path.relative_to(ROOT)),
                "custom": "python -m experiments.inference MODEL --method eliminate|batch ...",
                "established": "python -m experiments.established_v2 MODEL --max-table-bytes B ..."}
    write_json(run_dir/"commands.json", commands)
    planned = []
    for model in catalog["models"]:
        for rep in model["representations"]:
            if not rep.get("measured", True):
                continue
            profiles = rep.get("resource_profiles", ["high"] if model["cohort"] == "original_42" else ["low", "high"])
            for profile in profiles:
                for method in METHODS:
                    for repeat in range(3):
                        count = rep["structure"].get("log_joint_configurations", 0)
                        skip = "Predeclared exhaustive enumeration guard: joint configurations exceed 20,000,000." if method == "batch" and count > math.log(20_000_000)+1e-12 else None
                        planned.append({"trial_id": "", "model_id": model["model_id"], "representation_id": rep["representation_id"],
                                        "method_id": method, "resource_profile_id": profile, "accuracy_contract_id": "exact_numeric",
                                        "repeat": repeat, "schedule_index": 0, "static_skip_reason": skip})
    random.Random(2026110602).shuffle(planned)
    for i, row in enumerate(planned):
        row.update({"trial_id": f"{i:05d}", "schedule_index": i})
    prior_path = ROOT/"runs/campaign-002/manifest.json"
    prior_expected = (ROOT/"runs/campaign-002/manifest.sha256").read_text().split()[0]
    if digest(prior_path) != prior_expected:
        raise ValueError("Original execution manifest hash mismatch")
    prior = json.loads(prior_path.read_text())
    check_corrective_matrix(catalog,planned,prior)
    corrected_profiles = resource_profiles(artifact(control_path))
    if corrected_profiles != prior["resource_profiles"]:
        raise ValueError("Corrective run changed the external resource profiles")
    write_json(run_dir/"planned_trials.json", planned)
    adapters = {"ve": ROOT/"experiments/inference/core.py", "batch": ROOT/"experiments/inference/core.py",
                "pyagrum": ROOT/"experiments/established_v2/pyagrum_adapter.py"}
    methods = []
    for name in METHODS:
        methods.append({"method_id": name, "implementation": "pyagrum" if name == "pyagrum" else "local NumPy harness",
                        "version": dependencies.get("pyagrum", "unknown") if name == "pyagrum" else digest(adapters[name]),
                        "established_comparator": name == "pyagrum",
                        "comparator_provenance": "experiments/established_v2/README.md; locked pyagrum 3.3.2 source/API provenance" if name == "pyagrum" else "Local implementation; established prior algorithm, not an established package comparator.",
                        "algorithm": {"ve":"Deterministic min-fill log-domain variable elimination", "batch":"Streaming vectorized exhaustive enumeration", "pyagrum":"Shafer-Shenoy exact MRF inference; n conditional marginals recover log Z via log W - log P"}[name],
                        "configuration": ({"threads":1,"max_enumerated_states":20000000,"batch_states":65536,
                                           "adapter_version":2,"native_memory_mebibytes":1024,
                                           "native_quota_scope":"Corrected C++ scheduler limit, above the unchanged external 128/512 MiB RSS budgets; not the enforced process ceiling."}
                                          if name == "pyagrum" else {"threads":1,"max_enumerated_states":20000000,"batch_states":65536}),
                        "numeric_semantics": "binary64, no outward-rounded interval certificate; explicit log/scale handling",
                        "adapter": artifact(adapters[name]),
                        "timing_scope": "Custom VE kernel includes ordering; pyagrum separately records import/conversion/JT preparation/n conditional queries. Subprocess wall includes startup, loading, output, and monitoring.",
                        "controls": [artifact(ROOT/p) for p in ("tests/test_structure_round2.py", "tests/test_established_pyagrum_v2.py", "tests/test_round2_references.py", "tests/test_watchdog_round2.py", "tests/test_driver_round2_v2.py") if (ROOT/p).exists()]})
    manifest = {"schema_version":1,"campaign":"002","frozen_at_utc":now(),
                "protocol_sha256":digest(protocol_path),
                "premeasurement_attestation":"The original campaign002 outcomes and subsequent native-memory-unit diagnostics are known. This is an adaptive corrective amendment frozen before corrected measurements, not an unseen preregistration. The full original trial matrix, targets, external resources, seed and repetitions are repeated; the established adapter alone changes to version2 with a 1024 MiB native scheduler quota.",
                "amendment":catalog["amendment"],
                "original_execution_manifest":artifact(prior_path),
                "matrix_equality_attestation":"All planned row dictionaries match the original execution manifest exactly, in the same randomized order. Targets, conditioning and original representation file hashes also match.",
                "corrective_scope":"Full-matrix rerun, not failure-only selection. Original evidence is preserved; native scheduler units corrected without changing external budgets.",
                "exposure_ledger":catalog.get("exposure_ledger", []),
                "preparation_ledger":catalog["preparation_ledger"], "selection_rule":catalog["selection_rule"],
                "source_inventory":catalog["source_inventory"], "models":catalog["models"], "methods":methods,
                "accuracy_contracts":[{"accuracy_contract_id":"exact_numeric","kind":"exact_numeric",
                    "target_definition":"log(sum_x product_a w_a(x_scope)) for the declared stored-log target and exact representation transformations.",
                    "source_semantics":"Each model's source_semantics and exact-reduction target_relation control; no conversion may silently replace positive mass with zero.",
                    "acceptance_rule":"Same zero-mass classification and absolute log error <= 1e-8 + 64*eps64*max(1,abs(reference_log_z),sum_abs_restored_log_offsets). No strict interval claim.",
                    "reference_plan":"Frozen catalog references where provided; otherwise unverified_accuracy until an independent later check. Agreement alone does not retroactively become a prospective oracle.",
                    "zero_mass_rule":"Use -Infinity only for mathematical zero mass; numerical underflow is a failure/unsupported conversion.", "strict_interval_claim":False,"certificate_plan":None}],
                "resource_profiles":corrected_profiles,
                "measurement_plan":{"repetitions":3,"fresh_process":True,"concurrency":1,"schedule":artifact(run_dir/"planned_trials.json"),
                    "seeds":[2026110602],"warmup":"No measured warmup; each trial starts a fresh process.","cache_policy":"OS caches not flushed; one randomized schedule includes all planned rows.",
                    "phase_definitions":{"conversion":"Adapter factor conversion, where available","preprocessing":"Native JT/order preparation where available; custom VE ordering is inside its kernel","solver_ingestion":"Not separately observable unless reported; null otherwise","inference_kernel":"Adapter/core timed inference boundary","end_to_end":"Popen through reaped worker plus output/log handling; offline model preparation is separate."},
                    "reference_subset_rule":catalog.get("reference_subset_rule","Frozen catalog reference map; any missing adequate reference remains unverified.")},
                "planned_trials":planned,"references":catalog.get("references", {}),
                "environment":{"machine":platform.machine(),"os":platform.platform(),"cpu":platform.processor() or platform.machine(),
                    "ram_bytes":psutil.virtual_memory().total,"dependencies":artifact(run_dir/"dependencies.json"),"thread_environment":THREAD_ENV,
                    "commands":artifact(run_dir/"commands.json")},"total_wall_budget_seconds":900,
                "catalog":artifact(catalog_path),"rss_posthoc_adjudication":"Worker lifetime high-water above the ceiling is rss_limit even if a spike escaped sampling; retain both measurements. No instantaneous hard ceiling is claimed.",
                "budget_skip_policy":"Before each nonstatic trial, skip if remaining campaign wall budget is less than its full timeout plus0.25s; keep every planned row.",
                "file_inventory":[]}
    inventory = source_files()+list(catalog_artifacts(catalog))+[run_dir/"dependencies.json",run_dir/"commands.json",run_dir/"planned_trials.json",catalog_path]
    inventory += [ROOT/p for p in ("grader/spotcheck_results.json", "grader/audit_results.json", "runs/campaign-001/summary.json") if (ROOT/p).exists()]
    inventory += [ROOT/p for p in ("runs/campaign-002/manifest.json", "runs/campaign-002/manifest.sha256", "runs/campaign-002/completion.json", "runs/campaign-002/summary.json", "runs/campaign-002/trials.jsonl") if (ROOT/p).exists()]
    manifest["file_inventory"] = [artifact(p) for p in sorted(set(inventory))]
    validate("manifest", manifest)
    write_json(run_dir/"manifest.json", manifest)
    (run_dir/"manifest.sha256").write_text(digest(run_dir/"manifest.json")+"  manifest.json\n")
    print(json.dumps({"manifest":str(run_dir/"manifest.json"),"sha256_prefix":digest(run_dir/"manifest.json")[:6],"planned_trials":len(planned)}))


def verify(run_dir):
    path = run_dir/"manifest.json"
    assert digest(path) == (run_dir/"manifest.sha256").read_text().split()[0]
    manifest = json.loads(path.read_text())
    validate("manifest", manifest)
    for item in manifest["file_inventory"]:
        assert digest(ROOT/item["path"]) == item["sha256"], item["path"]
    return manifest


def normalized_number(value):
    if value in ("-inf", "-Infinity"):
        return -math.inf
    number = float(value)
    if math.isnan(number) or number == math.inf:
        raise ValueError("Invalid log partition value")
    return number


def classify_raw(raw):
    status = raw.get("status")
    if status == "complete":
        return "unverified_accuracy"
    if status in {"intermediate_table_limit","input_factor_exceeds_table_limit","batch_array_limit","wrapper_preflight_clique_limit","postconstruction_clique_limit"}:
        return "predicted_table_cap"
    if status in {"state_limit","integer_index_limit"}:
        return "planned_skip"
    if status == "time_limit":
        return "timeout"
    if status == "unsupported_package_version":
        return "infrastructure_error"
    if status and status.startswith("conversion_"):
        return "unsupported_conversion"
    if status in {"numerical_failure","numerical_failure_or_zero_support"}:
        return "numerical_failure"
    if raw.get("exception") == "MemoryError":
        return "allocation_error"
    return "invalid_output"


def validate_value(raw, reference):
    result = {"status":"unverified","reference_id":None,"absolute_log_error":None,"reference_uncertainty":None,
              "acceptance_threshold":None,"zero_mass_agrees":None,"strict_interval_contains_reference":None,
              "tolerance_relaxed_interval_passes":None,"detail":"No frozen adequate independent reference supplied."}
    value = normalized_number(raw["log_z"])
    if reference is None:
        return value, result
    expected = normalized_number(reference["log_z"])
    offsets = raw.get("metrics", {})
    sum_abs_offsets = abs(offsets.get("scalar_log_offset", 0.)) + math.fsum(abs(f.get("log_offset",0.)) for f in offsets.get("factor_conversion",[]))
    threshold = 1e-8 + 64*sys.float_info.epsilon*max(1., abs(expected) if math.isfinite(expected) else 1., sum_abs_offsets)
    zero_agrees = (value == -math.inf) == (expected == -math.inf)
    if math.isfinite(value) and math.isfinite(expected):
        with localcontext() as context:
            context.prec = 110
            reference_value = reference["log_z"]
            expected_decimal = Decimal(reference_value) if isinstance(reference_value,str) else Decimal.from_float(float(reference_value))
            error = float(abs(Decimal.from_float(value)-expected_decimal))
    else:
        error = 0. if value == expected else None
    passed = zero_agrees and error is not None and error <= threshold
    result.update({"status":"passed" if passed else "failed","reference_id":reference["reference_id"],
                   "absolute_log_error":error,"reference_uncertainty":reference.get("reference_uncertainty",reference.get("uncertainty",0.)),
                   "acceptance_threshold":threshold,"zero_mass_agrees":zero_agrees,
                   "detail":"Prospective floating-value check against frozen reference; not a strict real-arithmetic enclosure."})
    return value, result


def base_record(row, manifest_sha, profile, representation):
    structure = representation["structure"]
    return {"schema_version":1,**{k:row[k] for k in ("trial_id","model_id","representation_id","method_id","resource_profile_id","accuracy_contract_id","repeat")},
            "manifest_sha256":manifest_sha,"status":"planned_skip","started_at_utc":None,"finished_at_utc":None,
            "exit_code":None,"signal":None,"failure_detail":None,"retry_of":None,
            "timing":{"clock":"time.perf_counter","wall_seconds":None,"cpu_seconds":None,
                      "phases":{"conversion":None,"preprocessing":None,"solver_ingestion":None,"inference_kernel":None,"end_to_end":None},
                      "right_censored":False,"scope":"Fresh process from prepared JSON, through output and process reap. Offline raw-data preparation excluded.",
                      "startup_and_monitor_scope":"Startup, JSON loading, dependency import, and external monitoring included in wall; native/custom kernel boundaries are separately labeled."},
            "memory":{"table_cap_bytes":profile["table_cap_bytes"],"predicted_intermediate_bytes":structure["predicted_largest_intermediate_bytes"],
                      "predicted_workspace_bytes":structure["predicted_workspace_bytes"],"rss_baseline_bytes":None,"rss_peak_bytes":None,
                      "rss_ceiling_bytes":profile["rss_ceiling_bytes"],"rss_enforcement":"external_watchdog",
                      "rss_scope":profile["rss_measurement"]["scope"],"rss_source":"psutil 10ms sampled process tree plus worker lifetime high-water",
                      "sampling_interval_seconds":.01,"peak_is_sampled_lower_bound":True,"limit_trigger_seconds":None,"kill_seconds":None,"overshoot_bytes":None},
            "output":{"log_z":None,"zero_mass":None,"scale_offsets_restored":None,"interval":None,"artifact":None},
            "validation":{"status":"not_applicable","reference_id":None,"absolute_log_error":None,"reference_uncertainty":None,
                          "acceptance_threshold":None,"zero_mass_agrees":None,"strict_interval_contains_reference":None,
                          "tolerance_relaxed_interval_passes":None,"detail":"Trial not completed with a value."},"logs":[]}


def run(run_dir):
    manifest = verify(run_dir)
    raw_dir = run_dir/"raw"
    raw_dir.mkdir()
    profile_map = {p["resource_profile_id"]:p for p in manifest["resource_profiles"]}
    model_map = {m["model_id"]:m for m in manifest["models"]}
    env = {k:os.environ[k] for k in ("PATH","TMPDIR","LANG","LC_ALL","PYTHONPATH","VIRTUAL_ENV") if k in os.environ}
    env.update(THREAD_ENV)
    python = json.loads((ROOT/manifest["environment"]["commands"]["path"]).read_text())["python"]
    start = time.perf_counter()
    manifest_sha = digest(run_dir/"manifest.json")
    for index,row in enumerate(manifest["planned_trials"]):
        model = model_map[row["model_id"]]
        rep = next(r for r in model["representations"] if r["representation_id"] == row["representation_id"])
        profile = profile_map[row["resource_profile_id"]]
        record = base_record(row,manifest_sha,profile,rep)
        remaining = manifest["total_wall_budget_seconds"] - (time.perf_counter()-start)
        reason = row.get("static_skip_reason")
        if reason is None and remaining < profile["wall_timeout_seconds"]+.25:
            reason = "Finite total campaign wall budget cannot accommodate this trial's full timeout."
        if reason:
            record["failure_detail"] = reason
        else:
            output = raw_dir/(row["trial_id"]+".result.json")
            stdout = raw_dir/(row["trial_id"]+".stdout.txt")
            stderr = raw_dir/(row["trial_id"]+".stderr.txt")
            model_path = rep["files"][0]["path"]
            if row["method_id"] == "pyagrum":
                command = [python,"-m","experiments.established_v2",model_path,"--max-table-bytes",str(profile["table_cap_bytes"]),"--output",str(output)]
            else:
                method = "eliminate" if row["method_id"] == "ve" else "batch"
                command = [python,"-m","experiments.inference",model_path,"--method",method,"--max-table-bytes",str(profile["table_cap_bytes"]),
                           "--max-batch-bytes",str(profile["table_cap_bytes"]),"--max-states","20000000","--time-limit-seconds",str(profile["wall_timeout_seconds"]),"--output",str(output)]
            monitor = supervise(command,cwd=ROOT,env=env,stdout_path=stdout,stderr_path=stderr,
                                rss_ceiling_bytes=profile["rss_ceiling_bytes"],wall_timeout_seconds=profile["wall_timeout_seconds"])
            record.update({k:monitor[k] for k in ("started_at_utc","finished_at_utc","exit_code","signal")})
            record["command"] = command
            record["monitor"] = monitor
            record["timing"].update({"wall_seconds":monitor["wall_seconds"],"cpu_seconds":monitor["cpu_seconds"]})
            record["timing"]["offline_algebra_preparation_seconds"] = rep.get("preparation_seconds",0.)
            record["timing"]["one_off_wall_plus_algebra_seconds"] = monitor["wall_seconds"]+rep.get("preparation_seconds",0.)
            record["timing"]["phases"]["end_to_end"] = monitor["wall_seconds"]
            record["memory"].update({"rss_baseline_bytes":monitor["rss_baseline_bytes"],"rss_peak_bytes":monitor["sampled_peak_rss_bytes"],
                                      "limit_trigger_seconds":monitor["limit_trigger_seconds"],"kill_seconds":monitor["kill_seconds"],"overshoot_bytes":monitor["overshoot_bytes"]})
            record["logs"] = [artifact(stdout),artifact(stderr)]
            raw = None
            if output.exists():
                record["output"]["artifact"] = artifact(output)
                try:
                    raw = json.loads(output.read_text())
                except (ValueError,OSError) as error:
                    record["failure_detail"] = "Invalid worker JSON: "+str(error)
            if monitor["termination_reason"]:
                record["status"] = monitor["termination_reason"]
                record["failure_detail"] = "External sampled process-tree RSS/time watchdog terminated this trial."
            elif monitor["exit_code"] != 0:
                record["status"] = "signal_or_crash"
                record["failure_detail"] = "Worker exited without a valid successful completion."
            elif raw is None:
                record["status"] = "invalid_output"
            else:
                record["raw_status"] = raw.get("status")
                record["status"] = classify_raw(raw)
                record["failure_detail"] = None if raw.get("status") == "complete" else str(raw.get("status"))
                if raw.get("exception_message"):
                    record["failure_detail"] = (record["failure_detail"] or "")+": "+str(raw["exception_message"])
                metric = raw.get("metrics", {})
                for source,destination in (("conversion_seconds","conversion"),("preprocessing_seconds","preprocessing"),("solver_ingestion_seconds","solver_ingestion"),("kernel_elapsed_seconds","inference_kernel")):
                    record["timing"]["phases"][destination] = raw.get(source,metric.get(source))
                record["loading_seconds"] = raw.get("loading_seconds")
                worker_peak = raw.get("process_peak_rss_bytes")
                record["memory"]["worker_reported_lifetime_peak_rss_bytes"] = worker_peak
                if raw.get("status") == "complete":
                    try:
                        value,comparison = validate_value(raw,manifest["references"].get(row["model_id"]))
                        record["validation"] = comparison
                        record["output"].update({"log_z":"-Infinity" if value == -math.inf else value,"zero_mass":value == -math.inf,
                                                  "scale_offsets_restored":metric.get("removed_log_offset")})
                        record["status"] = {"passed":"success","failed":"wrong_answer","unverified":"unverified_accuracy"}[comparison["status"]]
                    except (ValueError,KeyError,TypeError) as error:
                        record["status"],record["failure_detail"] = "invalid_output",str(error)
                if worker_peak is not None and worker_peak > profile["rss_ceiling_bytes"]:
                    record["status"] = "rss_limit"
                    record["failure_detail"] = "Worker lifetime RSS high-water exceeds the prospective ceiling, even if a transient peak escaped sampling."
                    record["memory"]["overshoot_bytes"] = max(record["memory"]["overshoot_bytes"] or 0,worker_peak-profile["rss_ceiling_bytes"])
            record["timing"]["right_censored"] = record["status"] == "timeout"
        validate("trial",record)
        write_json(raw_dir/(row["trial_id"]+".trial.json"),record)
        with (run_dir/"trials.jsonl").open("a") as stream:
            stream.write(json.dumps(record,allow_nan=False)+"\n")
        if (index+1)%10 == 0 or index+1 == len(manifest["planned_trials"]):
            print(json.dumps({"completed":index+1,"total":len(manifest["planned_trials"]),"status":record["status"],"elapsed_seconds":time.perf_counter()-start}),flush=True)
    write_json(run_dir/"completion.json",{"finished_at_utc":now(),"manifest_sha256":manifest_sha,"planned_trials":len(manifest["planned_trials"]),"elapsed_seconds":time.perf_counter()-start})


def summarize(run_dir):
    manifest = verify(run_dir)
    records = [json.loads(line) for line in (run_dir/"trials.jsonl").read_text().splitlines()]
    assert len({r["trial_id"] for r in records}) == len(records)
    planned = {r["trial_id"] for r in manifest["planned_trials"]}
    recorded = {r["trial_id"] for r in records}
    model_map = {m["model_id"]:m for m in manifest["models"]}
    counts = defaultdict(Counter)
    timings = defaultdict(list)
    for row in records:
        validate("trial",row)
        model = model_map[row["model_id"]]
        rep = next(r for r in model["representations"] if r["representation_id"] == row["representation_id"])
        key = (model["cohort"],rep["structure"]["graph_class"],rep["structure"]["memory_bin"],row["method_id"],row["resource_profile_id"])
        counts[key][row["status"]] += 1
        if row["status"] == "success":
            timings[(row["model_id"],row["representation_id"],row["method_id"],row["resource_profile_id"])].append(row)
    cells = []
    for key,rows in sorted(timings.items()):
        walls = [r["timing"]["wall_seconds"] for r in rows]
        rss = [r["memory"]["rss_peak_bytes"] for r in rows]
        cells.append({"model_id":key[0],"representation_id":key[1],"method_id":key[2],"resource_profile_id":key[3],
                      "validated_repeats":len(rows),"wall_median_seconds":statistics.median(walls),"wall_min_seconds":min(walls),"wall_max_seconds":max(walls),"sampled_peak_rss_max_bytes":max(rss)})
    summary = {"summarized_at_utc":now(),"manifest_sha256":digest(run_dir/"manifest.json"),"planned_trials":len(planned),"recorded_trials":len(records),
               "missing_trial_ids":sorted(planned-recorded),"unexpected_trial_ids":sorted(recorded-planned),
               "status_counts":dict(Counter(r["status"] for r in records)),
               "stratified_counts":[{"cohort":k[0],"graph_class":k[1],"memory_bin":k[2],"method_id":k[3],"resource_profile_id":k[4],"counts":dict(v)} for k,v in sorted(counts.items())],
               "validated_timing_cells":cells,"interpretation":"Descriptive case-level measurements; unverified_accuracy is not a validated success. No ETH or biological improvement claim."}
    write_json(run_dir/"summary.json",summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in {"stratified_counts","validated_timing_cells"}},indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action",choices=["control","freeze","run","summarize"])
    parser.add_argument("--catalog",type=Path,default=ROOT/"prepared/campaign-002/amended_catalog.json")
    parser.add_argument("--run-dir",type=Path,default=ROOT/"runs/campaign-002-amendment-001")
    args = parser.parse_args()
    run_dir,catalog = args.run_dir.resolve(),args.catalog.resolve()
    if args.action == "control":
        result = validate_controls(ROOT/"experiments/round2_watchdog/control-v2")
        print(json.dumps({"all_passed":result["all_passed"],"control_path":"experiments/round2_watchdog/control-v2/result.json"}))
    elif args.action == "freeze":
        freeze(catalog,run_dir)
    elif args.action == "run":
        run(run_dir)
    else:
        summarize(run_dir)


if __name__ == "__main__":
    main()
