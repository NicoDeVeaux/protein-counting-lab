"""Cold-pipeline test of exact hard-zero propagation under frozen local budgets."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time

import jsonschema
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.round2_watchdog import supervise
from scripts import campaign_round2_v2 as legacy

METHODS = ("ve", "batch", "pyagrum")
REPRESENTATIONS = ("simplified", "propagated")
SEED = 2026110603
MAX_STATES = 20_000_000
PREPROCESSING_LIMIT_SECONDS = 3
EXCLUDED = {".venv", "__pycache__", ".pytest_cache", ".git"}
THREAD_ENV = dict(legacy.THREAD_ENV)


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


def catalog_artifacts(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            path = (ROOT/value["path"]).resolve()
            if not path.is_relative_to(ROOT) or EXCLUDED.intersection(path.relative_to(ROOT).parts):
                raise ValueError("Catalog artifact outside allowed evidence tree: "+value["path"])
            if digest(path) != value["sha256"]:
                raise ValueError("Catalog artifact hash mismatch: "+value["path"])
            yield path
        for item in value.values():
            yield from catalog_artifacts(item)
    elif isinstance(value, list):
        for item in value:
            yield from catalog_artifacts(item)


def schema(name):
    return json.loads((ROOT/"grader/campaign-003"/(name+".schema.json")).read_text())


def validate(name, payload):
    jsonschema.Draft202012Validator(schema(name), format_checker=jsonschema.FormatChecker()).validate(payload)


def source_files():
    paths = set()
    for directory in ("experiments/inference", "experiments/structure", "experiments/zero_support",
                      "experiments/round3_pipeline", "experiments/established_v2", "experiments/round2_watchdog",
                      "prepared/campaign-003"):
        for path in (ROOT/directory).rglob("*"):
            if path.is_file() and not EXCLUDED.intersection(path.relative_to(ROOT).parts):
                paths.add(path)
    for name in ("AGENTS.md", "pyproject.toml", "uv.lock", "experiments/established/pyproject.toml",
                 "experiments/established/uv.lock", "scripts/campaign_round2_v2.py", "scripts/campaign_round3.py",
                 "scripts/execute_round3.py", "scripts/prepare_round3.py", "scripts/prepare_round2.py",
                 "tests/test_driver_round3.py", "tests/test_zero_support_round3.py", "tests/test_round3_pipeline.py",
                 "grader/campaign-003/PROTOCOL.md", "grader/campaign-003/FREEZE.json", "grader/campaign-003/FREEZE.sha256",
                 "grader/campaign-003/manifest.schema.json", "grader/campaign-003/trial.schema.json",
                 "grader/campaign-003/AMENDMENT-001.md", "grader/campaign-003/AMENDMENT-001.json",
                 "grader/campaign-003/AMENDMENT-001.sha256"):
        paths.add(ROOT/name)
    return sorted(paths)


def validate_catalog(catalog, prior=None):
    models = catalog["models"]
    if len({m["model_id"] for m in models}) != len(models):
        raise ValueError("Duplicate logical model")
    for model in models:
        if "pipeline_input" not in model:
            raise ValueError("Every trial must start from a declared original pipeline_input")
        reps = model["representations"]
        if len(reps) != 2 or {r["representation_id"] for r in reps} != set(REPRESENTATIONS):
            raise ValueError("Each model must retain both simplified and propagated representations")
        profile_sets = []
        for rep in reps:
            if not rep.get("measured", True):
                raise ValueError("Outcome-based representation exclusion is not allowed")
            target_hash = rep.get("target_sha256", "")
            if len(target_hash) != 64 or any(c not in "0123456789abcdef" for c in target_hash):
                raise ValueError("Every representation requires a canonical numeric target fingerprint")
            cards = rep["structure"]["domain_cardinalities"]
            if any(not isinstance(q, int) or q < 1 for q in cards):
                raise ValueError("Invalid prepared domain cardinality")
            profiles = rep.get("resource_profiles", ["low", "high"])
            if not profiles or len(set(profiles)) != len(profiles) or not set(profiles) <= {"low", "high"}:
                raise ValueError("Invalid resource profile selection")
            profile_sets.append(set(profiles))
        if profile_sets[0] != profile_sets[1]:
            raise ValueError("Both arms must use identical external resource profiles")
    if prior is not None:
        expected = {m["model_id"]: m for m in prior["models"] if m["cohort"] == "published_protein_extension"}
        actual = {m["model_id"]: m for m in models if m["cohort"] == "published_protein_extension"}
        if set(actual) != set(expected):
            raise ValueError("All six declared protein targets must be retained without additions or omissions")
        for key, model in actual.items():
            old = expected[key]
            original = next(r for r in old["representations"] if r["representation_id"] == "original")
            if model["pipeline_input"] != original["files"][0]:
                raise ValueError("Original protein target input changed: "+key)
            for field in ("fixed_sequence_and_conditioning", "source_semantics"):
                if model[field] != old[field]:
                    raise ValueError("Protein target semantics changed: "+key)
        for key, reference in prior.get("references", {}).items():
            if catalog.get("references", {}).get(key) != reference:
                raise ValueError("A previously frozen reference changed or disappeared: "+key)


def plan_trials(catalog_or_models):
    models = catalog_or_models["models"] if isinstance(catalog_or_models, dict) else catalog_or_models
    if len({m["model_id"] for m in models}) != len(models):
        raise ValueError("Duplicate schedule model")
    for model in models:
        reps = model["representations"]
        if len(reps) != 2 or {r["representation_id"] for r in reps} != set(REPRESENTATIONS):
            raise ValueError("Each schedule model requires both arms")
        if any(not r.get("measured", True) for r in reps):
            raise ValueError("No scheduled arm may be excluded")
        profile_lists = [r.get("resource_profiles", ["low", "high"]) for r in reps]
        profiles = [set(items) for items in profile_lists]
        if any(len(items) != len(set(items)) for items in profile_lists):
            raise ValueError("Duplicate resource profile in schedule")
        if profiles[0] != profiles[1] or not profiles[0] or not profiles[0] <= {"low", "high"}:
            raise ValueError("Schedule arms must have identical valid external profiles")
    rng = random.Random(SEED)
    planned = []
    model_map = {m["model_id"]: m for m in models}
    blocks = [(m["model_id"], profile) for m in sorted(models, key=lambda x:x["model_id"])
              for profile in sorted(m["representations"][0].get("resource_profiles", ["low", "high"]))]
    for repeat in range(3):
        round_blocks = blocks.copy()
        rng.shuffle(round_blocks)
        for model_id, profile in round_blocks:
            model = model_map[model_id]
            reps = {r["representation_id"]: r for r in model["representations"]}
            methods = list(METHODS)
            rng.shuffle(methods)
            block_id = f"r{repeat}:{model_id}:{profile}"
            for method in methods:
                arm_order = list(REPRESENTATIONS)
                rng.shuffle(arm_order)
                for arm in arm_order:
                    planned.append({"trial_id": f"{len(planned):05d}", "model_id": model_id,
                                    "representation_id": arm, "method_id": method, "resource_profile_id": profile,
                                    "accuracy_contract_id": "exact_numeric", "repeat": repeat,
                                    "schedule_index": len(planned), "block_id": block_id,
                                    "static_skip_reason": None})
    return planned


def verify_preparation_manifest(catalog, planned, profiles):
    artifact_spec = catalog.get("preparation_manifest")
    if not artifact_spec:
        raise ValueError("A frozen preparation manifest is required before static target preparation")
    list(catalog_artifacts(artifact_spec))
    document = json.loads((ROOT/artifact_spec["path"]).read_text())
    def prospective_inputs(models):
        return {model["model_id"]:{
            **{field:model.get(field) for field in ("cohort", "source_id", "pipeline_input", "fixed_sequence_and_conditioning", "source_semantics")},
            "arms":{rep["representation_id"]:{"resource_profiles":sorted(rep.get("resource_profiles", ["low", "high"])),
                                             "measured":rep.get("measured", True)} for rep in model["representations"]}}
            for model in models}
    if prospective_inputs(document["models"]) != prospective_inputs(catalog["models"]):
        raise ValueError("Prepared execution changed a prospective input, arm, or source semantics")
    if document["planned_trials"] != planned:
        raise ValueError("Prepared execution changed the predeclared full trial schedule")
    if (document["resource_profiles"] != profiles or document["total_wall_budget_seconds"] != 900
            or document["preprocessing_limit_seconds"] != PREPROCESSING_LIMIT_SECONDS):
        raise ValueError("Prepared execution changed the predeclared resource budgets")
    if document["references"] != catalog.get("references", {}):
        raise ValueError("Prepared execution changed a reference after static preparation")
    for item in document["implementation_inventory"]:
        if digest(ROOT/item["path"]) != item["sha256"]:
            raise ValueError("Implementation changed after preparation freeze: "+item["path"])
    return document


def freeze(catalog_path, run_dir):
    if run_dir.exists():
        raise FileExistsError(run_dir)
    catalog = json.loads(catalog_path.read_text())
    prior_path = ROOT/"prepared/campaign-002/amended_catalog.json"
    prior = json.loads(prior_path.read_text())
    validate_catalog(catalog, prior)
    artifacts = list(catalog_artifacts(catalog))
    protocol_path = ROOT/"grader/campaign-003/PROTOCOL.md"
    freeze_path = ROOT/"grader/campaign-003/FREEZE.json"
    freeze_doc = json.loads(freeze_path.read_text())
    assert digest(freeze_path) == (ROOT/"grader/campaign-003/FREEZE.sha256").read_text().split()[0]
    for item in freeze_doc["files"]:
        assert digest(ROOT/item["path"]) == item["sha256"], item["path"]
    control_path = ROOT/"experiments/round2_watchdog/control/result.json"
    if not json.loads(control_path.read_text())["all_passed"]:
        raise ValueError("Frozen watchdog controls did not pass")
    planned = plan_trials(catalog)
    preparation = verify_preparation_manifest(catalog, planned, legacy.resource_profiles(artifact(control_path)))
    run_dir.mkdir(parents=True)
    dependencies = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions() if d.metadata.get("Name")}
    write_json(run_dir/"dependencies.json", dependencies)
    commands = {"python": sys.executable, "driver": "scripts/campaign_round3.py", "catalog": str(catalog_path.relative_to(ROOT)),
                "worker": "python -m experiments.round3_pipeline ORIGINAL --representation simplified|propagated --method ve|batch|pyagrum ..."}
    write_json(run_dir/"commands.json", commands)
    write_json(run_dir/"planned_trials.json", planned)
    methods = []
    adapters = {"ve": ROOT/"experiments/inference/core.py", "batch": ROOT/"experiments/inference/core.py",
                "pyagrum": ROOT/"experiments/established_v2/pyagrum_adapter.py"}
    for name in METHODS:
        methods.append({"method_id": name, "implementation": "pyagrum" if name == "pyagrum" else "local NumPy harness",
                        "version": dependencies.get("pyagrum", "unknown") if name == "pyagrum" else digest(adapters[name]),
                        "established_comparator": name == "pyagrum",
                        "comparator_provenance": "Pinned established_v2 adapter, pyagrum3.3.2 with1024MiB native scheduler quota" if name == "pyagrum" else "Conventional local implementation, no new algorithm claim",
                        "algorithm": {"ve":"Log-domain min-fill variable elimination", "batch":"Vectorized exhaustive enumeration", "pyagrum":"Shafer-Shenoy exact conditional marginals reconstruct log Z"}[name],
                        "configuration": {"threads":1, "max_enumerated_states":MAX_STATES, "batch_states":65536,
                                          "adapter_version":2 if name == "pyagrum" else None,
                                          "native_memory_mebibytes":1024 if name == "pyagrum" else None},
                        "numeric_semantics":"binary64; only source hard zeros may remove support; no certified interval",
                        "adapter":artifact(adapters[name]),
                        "timing_scope":"Fresh worker includes original model load, baseline simplification or propagation plus simplification, target fingerprinting, all inference queries, and worker output. Phase timings retain separate scopes.",
                        "controls":[artifact(ROOT/name) for name in ("tests/test_zero_support_round3.py", "tests/test_round3_pipeline.py", "tests/test_driver_round3.py")]})
    manifest = {"schema_version":1, "campaign":"003", "frozen_at_utc":now(), "protocol_sha256":digest(protocol_path),
                "premeasurement_attestation":"Adaptive follow-up after campaign002 outcomes and independent1FYN reference. A compact preparation manifest froze implementations, targets, references, resources and full schedule before static target preprocessing. This final manifest only adds prepared fingerprints/counts/proofs before measurements; no novelty, ETH or biological prediction claim.",
                "exposure_ledger":catalog["exposure_ledger"], "preparation_ledger":catalog["preparation_ledger"],
                "selection_rule":catalog["selection_rule"], "source_inventory":catalog["source_inventory"],
                "models":catalog["models"], "methods":methods,
                "accuracy_contracts":[{"accuracy_contract_id":"exact_numeric", "kind":"exact_numeric",
                    "target_definition":"Same declared original stored-log partition sum after exact hard-zero support restriction and exact algebra; no finite positive term may be silently removed.",
                    "source_semantics":"Original fixed-sequence source semantics; proof and original-index maps identify transformed domains and offsets.",
                    "acceptance_rule":"Same zero-mass classification and absolute log error <=1e-8+64*eps64*max(1,abs(reference_log_z),sum_abs_restored_log_offsets).",
                    "reference_plan":"Catalog references frozen before campaign003 measurements, including previously posthoc1FYN reference; no adequate reference means unverified_accuracy.",
                    "zero_mass_rule":"-Infinity only for mathematical zero; no finite-energy threshold pruning.",
                    "strict_interval_claim":False, "certificate_plan":None}],
                "resource_profiles":legacy.resource_profiles(artifact(control_path)),
                "measurement_plan":{"repetitions":3, "fresh_process":True, "concurrency":1,
                    "schedule":artifact(run_dir/"planned_trials.json"), "seeds":[SEED],
                    "warmup":"No measured warmup; fresh worker for every trial.",
                    "cache_policy":"OS caches not flushed. Each repeat round shuffles model/profile blocks; within a block method groups shuffle and each method has adjacent randomized arm pairs. No outcome-selected windows.",
                    "phase_definitions":{"loading":"Original JSON model load inside each cold worker", "propagation":"Exact hard-zero support propagation; zero for baseline", "simplification":"Exact algebra after baseline load or propagation", "target_fingerprint":"Canonical numeric representation hash checked against frozen prepared arm", "serialization":"Valid result JSON serialization/write from worker timing sidecar; sidecar and process reap additionally included in outerwall", "conversion":"Established adapter conversion where observable", "preprocessing":"Native inference preprocessing, separate from propagation", "inference_kernel":"Immutable solver-reported kernel", "end_to_end":"Worker startup, original JSON load, transformations, hash verification, solver, output, process reaping and watchdog; raw-source acquisition excluded."},
                    "reference_subset_rule":catalog.get("reference_subset_rule", "All catalog references; missing references remain unverified."),
                    "phase_cpu_scope":"Worker CPU load, propagation, simplification, hash and aggregate inference call where reported. Immutable solver internal subphase CPU clocks are not separately observable; retain their wall clocks only.",
                    "comparison_scope":"Cold-pipeline comparison; no cached-only solver timing presented as total latency. Report drift and all censoring before any speed interpretation."},
                "planned_trials":planned, "references":catalog.get("references", {}),
                "environment":{"machine":platform.machine(), "os":platform.platform(), "cpu":platform.processor() or platform.machine(),
                    "ram_bytes":psutil.virtual_memory().total, "dependencies":artifact(run_dir/"dependencies.json"),
                    "thread_environment":THREAD_ENV, "commands":artifact(run_dir/"commands.json"),
                    "load_average_at_freeze":list(os.getloadavg())},
                "total_wall_budget_seconds":900, "preprocessing_limit_seconds":PREPROCESSING_LIMIT_SECONDS, "catalog":artifact(catalog_path),
                "schema_compatibility":{"manifest":artifact(ROOT/"grader/campaign-003/manifest.schema.json"),
                    "trial":artifact(ROOT/"grader/campaign-003/trial.schema.json"),
                    "override":"Campaign003 frozen schemas preserve002 field semantics; extra cold-pipeline and block fields allowed."},
                "original_target_catalog":artifact(prior_path), "preparation_manifest":catalog["preparation_manifest"],
                "rss_posthoc_adjudication":"Maximum worker lifetime high-water before and after valid result encoding/write above prospective threshold is rss_limit even if sampling missed it. Later stdout/sidecar creation is covered only by the external sampler. No instantaneous ceiling guarantee.",
                "budget_skip_policy":"Skip before starting if remaining total budget cannot accommodate full row timeout plus0.25s; retain every row.",
                "file_inventory":[]}
    inventory = (source_files()+artifacts+list(catalog_artifacts(preparation))+
                 [ROOT/item["path"] for item in preparation["implementation_inventory"]]+
                 [catalog_path, prior_path, run_dir/"dependencies.json", run_dir/"commands.json", run_dir/"planned_trials.json"])
    manifest["file_inventory"] = [artifact(path) for path in sorted(set(inventory))]
    validate("manifest", manifest)
    write_json(run_dir/"manifest.json", manifest)
    (run_dir/"manifest.sha256").write_text(digest(run_dir/"manifest.json")+"  manifest.json\n")
    print(json.dumps({"manifest":str(run_dir/"manifest.json"), "sha256_prefix":digest(run_dir/"manifest.json")[:6], "planned_trials":len(planned)}), flush=True)


def verify(run_dir):
    path = run_dir/"manifest.json"
    assert digest(path) == (run_dir/"manifest.sha256").read_text().split()[0]
    manifest = json.loads(path.read_text())
    validate("manifest", manifest)
    for item in manifest["file_inventory"]:
        assert digest(ROOT/item["path"]) == item["sha256"], item["path"]
    return manifest


def worker_command(python, model, rep, row, profile, output):
    return [python, "-m", "experiments.round3_pipeline", model["pipeline_input"]["path"],
            "--representation", row["representation_id"], "--method", row["method_id"],
            "--expected-target-sha256", rep["target_sha256"],
            "--max-table-bytes", str(profile["table_cap_bytes"]),
            "--max-states", str(MAX_STATES), "--time-limit-seconds", str(profile["wall_timeout_seconds"]),
            "--preprocessing-limit-seconds", str(PREPROCESSING_LIMIT_SECONDS),
            "--output", str(output)]


def run(run_dir):
    manifest = verify(run_dir)
    raw_dir = run_dir/"raw"
    raw_dir.mkdir()
    profiles = {p["resource_profile_id"]:p for p in manifest["resource_profiles"]}
    models = {m["model_id"]:m for m in manifest["models"]}
    env = {key:os.environ[key] for key in ("PATH", "TMPDIR", "LANG", "LC_ALL", "PYTHONPATH", "VIRTUAL_ENV") if key in os.environ}
    env.update(THREAD_ENV)
    python = json.loads((ROOT/manifest["environment"]["commands"]["path"]).read_text())["python"]
    started = time.perf_counter()
    manifest_sha = digest(run_dir/"manifest.json")
    for index, row in enumerate(manifest["planned_trials"]):
        model = models[row["model_id"]]
        rep = next(r for r in model["representations"] if r["representation_id"] == row["representation_id"])
        profile = profiles[row["resource_profile_id"]]
        record = legacy.base_record(row, manifest_sha, profile, rep)
        record["block_id"] = row["block_id"]
        record["pipeline_input"] = model["pipeline_input"]
        record["prepared_target_sha256"] = rep["target_sha256"]
        record["timing"]["scope"] = "Cold original JSON load, exact transformations, target verification, inference, output and reaping. Raw-source acquisition excluded."
        record["timing"]["startup_and_monitor_scope"] = "Process startup and watchdog included; all propagation/simplification charged within each trial."
        remaining = manifest["total_wall_budget_seconds"]-(time.perf_counter()-started)
        reason = row.get("static_skip_reason")
        if reason is None and remaining < profile["wall_timeout_seconds"]+.25:
            reason = "Finite total campaign wall budget cannot accommodate this trial's full timeout."
        if reason:
            record["failure_detail"] = reason
        else:
            output = raw_dir/(row["trial_id"]+".result.json")
            stdout = raw_dir/(row["trial_id"]+".stdout.txt")
            stderr = raw_dir/(row["trial_id"]+".stderr.txt")
            command = worker_command(python, model, rep, row, profile, output)
            record["system_load_average_at_start"] = list(os.getloadavg())
            monitor = supervise(command, cwd=ROOT, env=env, stdout_path=stdout, stderr_path=stderr,
                                 rss_ceiling_bytes=profile["rss_ceiling_bytes"], wall_timeout_seconds=profile["wall_timeout_seconds"])
            record.update({key:monitor[key] for key in ("started_at_utc", "finished_at_utc", "exit_code", "signal")})
            record["command"], record["monitor"] = command, monitor
            record["timing"].update({"wall_seconds":monitor["wall_seconds"], "cpu_seconds":monitor["cpu_seconds"]})
            record["timing"]["phases"]["end_to_end"] = monitor["wall_seconds"]
            record["memory"].update({"rss_baseline_bytes":monitor["rss_baseline_bytes"], "rss_peak_bytes":monitor["sampled_peak_rss_bytes"],
                "limit_trigger_seconds":monitor["limit_trigger_seconds"], "kill_seconds":monitor["kill_seconds"], "overshoot_bytes":monitor["overshoot_bytes"]})
            record["logs"] = [artifact(stdout), artifact(stderr)]
            raw = None
            if output.exists():
                record["output"]["artifact"] = artifact(output)
                try:
                    raw = json.loads(output.read_text())
                except (ValueError, OSError) as error:
                    record["failure_detail"] = "Invalid worker JSON: "+str(error)
            if monitor["termination_reason"]:
                record["status"] = monitor["termination_reason"]
                record["failure_detail"] = "External sampled process-tree RSS/time watchdog terminated this trial."
            elif monitor["exit_code"] != 0:
                record["status"], record["failure_detail"] = "signal_or_crash", "Worker exited without successful completion."
            elif raw is None:
                record["status"] = "invalid_output"
            else:
                record["raw_status"] = raw.get("status")
                record["status"] = ("timeout" if raw.get("status") == "preprocessing_time_limit" else legacy.classify_raw(raw))
                if raw.get("status") == "preprocessing_time_limit":
                    record["failure_stage"] = "preprocessing"
                record["failure_detail"] = None if raw.get("status") == "complete" else str(raw.get("status"))
                if raw.get("exception_message"):
                    record["failure_detail"] = (record["failure_detail"] or "")+": "+str(raw["exception_message"])
                metrics = raw.get("metrics", {})
                pipeline = raw.get("pipeline", {})
                record["pipeline"] = pipeline
                record["timing"]["phase_cpu_seconds"] = {
                    destination:pipeline.get(source) for source,destination in (
                        ("load_cpu_seconds", "loading"), ("propagation_cpu_seconds", "propagation"),
                        ("simplification_cpu_seconds", "simplification"), ("target_validation_cpu_seconds", "target_fingerprint"),
                        ("inference_cpu_seconds", "solver_call"), ("cold_total_cpu_seconds", "cold_total"))}
                for source, destination in (("conversion_seconds", "conversion"), ("preprocessing_seconds", "preprocessing"),
                                             ("solver_ingestion_seconds", "solver_ingestion"), ("kernel_elapsed_seconds", "inference_kernel")):
                    record["timing"]["phases"][destination] = raw.get(source, metrics.get(source))
                for source, destination in (("load_seconds", "loading"), ("propagation_seconds", "propagation"),
                                             ("simplification_seconds", "simplification"), ("target_validation_seconds", "target_fingerprint"),
                                             ("inference_seconds", "solver_call")):
                    record["timing"]["phases"][destination] = pipeline.get(source)
                sidecar_path = Path(str(output)+".timing.json")
                serialization_error = None
                if sidecar_path.exists():
                    record["serialization_timing_artifact"] = artifact(sidecar_path)
                    record["logs"].append(artifact(sidecar_path))
                    try:
                        serialization = json.loads(sidecar_path.read_text())
                        if not isinstance(serialization, dict):
                            raise ValueError("Timing sidecar must be an object")
                        for key in ("serialization_seconds", "serialization_cpu_seconds"):
                            value = serialization[key]
                            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                                raise ValueError("Invalid serialization timing: "+key)
                        post_result_peak = serialization.get("process_peak_rss_bytes_after_result")
                        if post_result_peak is not None and (not isinstance(post_result_peak, int) or post_result_peak < 0):
                            raise ValueError("Invalid post-result worker RSS high-water")
                        record["serialization_timing"] = serialization
                        record["timing"]["phases"]["serialization"] = serialization["serialization_seconds"]
                        record["timing"]["phase_cpu_seconds"]["serialization"] = serialization["serialization_cpu_seconds"]
                    except (ValueError, TypeError, KeyError, OSError) as error:
                        serialization_error = str(error)
                elif pipeline.get("serialization_timing_sidecar"):
                    serialization_error = "Declared serialization timing sidecar is absent"
                record["loading_seconds"] = raw.get("loading_seconds")
                raw_peak = raw.get("process_peak_rss_bytes")
                post_result_peak = record.get("serialization_timing", {}).get("process_peak_rss_bytes_after_result")
                worker_peak = max((value for value in (raw_peak, post_result_peak) if value is not None), default=None)
                record["memory"]["worker_reported_before_result_peak_rss_bytes"] = raw_peak
                record["memory"]["worker_reported_after_result_peak_rss_bytes"] = post_result_peak
                record["memory"]["worker_reported_lifetime_peak_rss_bytes"] = worker_peak
                record["memory"]["worker_high_water_scope"] = "Maximum reported lifetime high-water before and after valid result encoding/write. Later stdout and timing-sidecar creation are covered only by the external sampler, whose transient-peak limitations remain."
                if raw.get("status") == "complete":
                    if pipeline.get("target_sha256") != rep["target_sha256"]:
                        record["status"], record["failure_detail"] = "invalid_output", "Runtime transformed target fingerprint differs from frozen representation."
                    else:
                        try:
                            value, comparison = legacy.validate_value(raw, manifest["references"].get(row["model_id"]))
                            record["validation"] = comparison
                            record["output"].update({"log_z":"-Infinity" if value == -math.inf else value,
                                "zero_mass":value == -math.inf, "scale_offsets_restored":metrics.get("removed_log_offset")})
                            record["status"] = {"passed":"success", "failed":"wrong_answer", "unverified":"unverified_accuracy"}[comparison["status"]]
                        except (ValueError, KeyError, TypeError) as error:
                            record["status"], record["failure_detail"] = "invalid_output", str(error)
                if serialization_error is not None:
                    record["status"] = "infrastructure_error"
                    record["failure_detail"] = "Invalid worker serialization timing sidecar: "+serialization_error
                if worker_peak is not None and worker_peak > profile["rss_ceiling_bytes"]:
                    record["status"] = "rss_limit"
                    record["failure_detail"] = "Worker lifetime RSS high-water exceeds prospective threshold, even if transient sampling missed it."
                    record["memory"]["overshoot_bytes"] = max(record["memory"]["overshoot_bytes"] or 0, worker_peak-profile["rss_ceiling_bytes"])
            record["timing"]["right_censored"] = record["status"] == "timeout"
        validate("trial", record)
        write_json(raw_dir/(row["trial_id"]+".trial.json"), record)
        with (run_dir/"trials.jsonl").open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False)+"\n")
        if (index+1)%10 == 0 or index+1 == len(manifest["planned_trials"]):
            print(json.dumps({"completed":index+1, "total":len(manifest["planned_trials"]), "status":record["status"], "elapsed_seconds":time.perf_counter()-started}), flush=True)
    write_json(run_dir/"completion.json", {"finished_at_utc":now(), "manifest_sha256":manifest_sha,
        "planned_trials":len(manifest["planned_trials"]), "elapsed_seconds":time.perf_counter()-started})


def summarize(run_dir):
    manifest = verify(run_dir)
    rows = [json.loads(line) for line in (run_dir/"trials.jsonl").read_text().splitlines()]
    planned = {r["trial_id"]: r for r in manifest["planned_trials"]}
    observed = {r["trial_id"]: r for r in rows}
    if len(observed) != len(rows):
        raise ValueError("Duplicate trial ledger rows")
    identity = ("model_id", "representation_id", "method_id", "resource_profile_id", "repeat", "block_id")
    for row in rows:
        validate("trial", row)
        if row["trial_id"] not in planned or any(row[key] != planned[row["trial_id"]][key] for key in identity):
            raise ValueError("Trial identity differs from frozen schedule")
    groups, counts = defaultdict(list), defaultdict(Counter)
    cohort = {m["model_id"]:m["cohort"] for m in manifest["models"]}
    for row in rows:
        key = (row["model_id"], row["representation_id"], row["method_id"], row["resource_profile_id"])
        groups[key].append(row)
        counts[(cohort[row["model_id"]], row["representation_id"], row["method_id"], row["resource_profile_id"])][row["status"]] += 1
    cells = []
    for key, cell in sorted(groups.items()):
        completed = [r for r in cell if r["status"] in {"success", "unverified_accuracy"}]
        walls = [r["timing"]["wall_seconds"] for r in completed]
        cells.append({"model_id":key[0], "representation_id":key[1], "method_id":key[2], "resource_profile_id":key[3],
            "recorded_repeats":len(cell), "statuses":dict(Counter(r["status"] for r in cell)),
            "completed_repeats":len(completed), "validated_repeats":sum(r["status"] == "success" for r in cell),
            "completed_wall_median_seconds":statistics.median(walls) if walls else None,
            "completed_wall_min_seconds":min(walls) if walls else None, "completed_wall_max_seconds":max(walls) if walls else None,
            "completed_wall_max_over_min":max(walls)/min(walls) if len(walls)>1 and min(walls)>0 else None,
            "completed_peak_rss_max_bytes":max((r["memory"]["rss_peak_bytes"] for r in completed), default=None)})
    summary = {"summarized_at_utc":now(), "manifest_sha256":digest(run_dir/"manifest.json"),
        "planned_trials":len(planned), "recorded_trials":len(rows), "missing_trial_ids":sorted(set(planned)-set(observed)),
        "unexpected_trial_ids":sorted(set(observed)-set(planned)), "status_counts":dict(Counter(r["status"] for r in rows)),
        "stratified_counts":[{"cohort":key[0], "representation_id":key[1], "method_id":key[2], "resource_profile_id":key[3], "counts":dict(value)} for key,value in sorted(counts.items())],
        "cells":cells, "interpretation":"Descriptive cold-pipeline measurements with exact target fingerprints; failures, skips, missing references and timing drift retained. No ETH or biological improvement claim."}
    write_json(run_dir/"summary.json", summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in {"stratified_counts", "cells"}}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "run", "summarize"])
    parser.add_argument("--catalog", type=Path, default=ROOT/"prepared/campaign-003/catalog.json")
    parser.add_argument("--run-dir", type=Path, default=ROOT/"runs/campaign-003")
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.catalog.resolve(), args.run_dir.resolve())
    elif args.action == "run":
        run(args.run_dir.resolve())
    else:
        summarize(args.run_dir.resolve())


if __name__ == "__main__":
    main()
