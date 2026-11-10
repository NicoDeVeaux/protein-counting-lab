"""Measure a complete mutant panel from its original source archive."""

from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib
import math
from pathlib import Path
import resource
import signal
import sys
import time

from experiments.inference import InferenceLimit, batched_brute_force, variable_elimination
from experiments.round3_pipeline import prepare_model, target_fingerprint
from experiments.three_state_data import load_case, condition_sequence
from .core import STATES, score_ratio


def safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return "-inf" if value == -math.inf else "invalid_nonfinite"
    if isinstance(value, dict):
        return {key:safe(item) for key,item in value.items()}
    if isinstance(value, (list,tuple)):
        return [safe(item) for item in value]
    return value


def peak():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform == "darwin" else rss*1024)


def now():
    return datetime.now(timezone.utc).isoformat()


def timeout(signum, frame):
    raise TimeoutError("Source-load phase deadline")


def main():
    manifest_path, panel_id, output_path = map(str, sys.argv[1:4])
    manifest = json.loads(Path(manifest_path).read_text())
    panel = next(row for row in manifest["panels"] if row["panel_id"] == panel_id)
    science = manifest["scientific_choices"]
    root = Path(manifest["root"])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    progress = Path(str(output)+".progress.jsonl")
    if progress.exists() or output.exists():
        raise FileExistsError(output)
    started, cpu_started = time.perf_counter(), time.process_time()
    deadline = started + science["resources"]["panel_wall_seconds"]-science["resources"]["closeout_reserve_seconds"]
    record = {"panel_id": panel_id, "method": panel["method"], "arm": panel["arm"], "repeat": panel["repeat"],
              "started_at_utc": now(), "queries": [], "phase_scopes": science["phase_scopes"], "status": "running",
              "manifest_sha256":hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
              "case_id":manifest["pilot"]["case_id"], "archive_sha256":manifest["pilot"]["archive"]["sha256"]}
    source = None
    phase, cpu_phase = time.perf_counter(), time.process_time()
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, science["resources"]["source_load_seconds"])
    try:
        source = load_case(root / manifest["pilot"]["archive"]["path"])
        assert source.archive_sha256 == manifest["pilot"]["archive"]["sha256"]
        record["source_status"] = "loaded"
    except Exception as error:
        source = None
        record["source_status"] = "error"
        record["source_error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    record["source_load_seconds"] = time.perf_counter()-phase
    record["source_load_cpu_seconds"] = time.process_time()-cpu_phase
    cache = {}
    variants = {row["sequence_id"]:row for row in manifest["pilot"]["sequences"]}
    for sequence_id in panel["query_order"]:
        variant = variants[sequence_id]
        query_started, query_cpu = time.perf_counter(), time.process_time()
        query = {"sequence_id": sequence_id, "label": variant["label"], "assignment": variant["assignment"],
                 "started_at_utc": now(), "states": {}}
        if source is None or time.perf_counter() >= deadline:
            for state in STATES:
                query["states"][state] = {"status": "source_error" if source is None else "panel_budget_skip",
                    "reason":"Panel source did not load; see source_error." if source is None else "Frozen panel work deadline reached.",
                    "started_at_utc":None,"finished_at_utc":None}
        else:
            phase, cpu_phase = time.perf_counter(), time.process_time()
            try:
                models, proof = condition_sequence(source, {int(key):value for key,value in variant["assignment"].items()})
                query["conditioning_seconds"] = time.perf_counter()-phase
                query["conditioning_cpu_seconds"] = time.process_time()-cpu_phase
                for state in STATES:
                    entry = {"status": "pending", "input_state_count": str(models[state].n_states),"started_at_utc":now()}
                    query["states"][state] = entry
                    if time.perf_counter() >= deadline:
                        entry["status"] = "panel_budget_skip"
                        entry["reason"] = "Frozen panel work deadline reached before this state."
                        entry["finished_at_utc"] = now()
                        continue
                    phase, cpu_phase = time.perf_counter(), time.process_time()
                    prepared, preparation = prepare_model(models[state], panel["arm"])
                    entry["preparation_seconds"] = time.perf_counter()-phase
                    entry["preparation_cpu_seconds"] = time.process_time()-cpu_phase
                    fingerprint = preparation["target_sha256"]
                    expected = manifest["targets"][sequence_id][panel["arm"]][state]
                    entry.update({"target_sha256": fingerprint, "state_count": str(prepared.n_states),
                                  "propagation_seconds": preparation["propagation_seconds"],
                                  "simplification_seconds": preparation["simplification_seconds"]})
                    if fingerprint != expected:
                        entry["status"] = "target_fingerprint_mismatch"
                        entry["reason"] = "Runtime numerical target differs from its prospectively prepared target."
                        entry["finished_at_utc"] = now()
                        continue
                    if fingerprint in cache:
                        previous_result = cache[fingerprint]["result"]
                        entry.update({key:deepcopy(previous_result[key]) for key in ("status", "log_z", "method") if key in previous_result})
                        entry["cache_origin"] = cache[fingerprint]["origin"]
                        entry["cache_hit"] = True
                        entry["solver_call_seconds"] = entry["solver_call_cpu_seconds"] = 0.0
                        entry["finished_at_utc"] = now()
                        continue
                    phase, cpu_phase = time.perf_counter(), time.process_time()
                    try:
                        remaining = max(0.0, deadline-time.perf_counter())
                        if remaining <= 0:
                            entry["status"] = "panel_budget_skip"
                            entry["reason"] = "Frozen panel work deadline reached before inference."
                            continue
                        if panel["method"] == "ve":
                            result = variable_elimination(prepared, order="min-fill", max_table_bytes=science["resources"]["table_bytes"], time_limit_seconds=remaining)
                        else:
                            result = batched_brute_force(prepared, max_states=science["resources"]["max_states"], batch_states=65536,
                                max_batch_bytes=science["resources"]["table_bytes"], time_limit_seconds=remaining)
                        entry.update(result)
                        if result["status"] == "complete":
                            cache[fingerprint] = {"result": deepcopy(result), "origin": {"sequence_id": sequence_id, "state": state}}
                    except InferenceLimit as error:
                        entry.update({"status": error.reason, "metrics": error.metrics,"reason":"Frozen solver policy: "+error.reason})
                    except Exception as error:
                        entry.update({"status": "error", "error": {"type": type(error).__name__, "message": str(error)}})
                    finally:
                        entry["solver_call_seconds"] = time.perf_counter()-phase
                        entry["solver_call_cpu_seconds"] = time.process_time()-cpu_phase
                        entry["finished_at_utc"] = now()
            except Exception as error:
                query["conditioning_error"] = {"type": type(error).__name__, "message": str(error)}
                for state in STATES:
                    query["states"].setdefault(state, {"status": "conditioning_error"})
                    if query["states"][state]["status"] == "pending":
                        query["states"][state].update({"status":"preparation_error","error":query["conditioning_error"]})
                    query["states"][state].setdefault("started_at_utc",None)
                    query["states"][state].setdefault("finished_at_utc",now())
        logs = {state:entry["log_z"] for state,entry in query["states"].items() if entry["status"] == "complete"}
        query["score"] = score_ratio(logs)
        query["wall_seconds"] = time.perf_counter()-query_started
        query["cpu_seconds"] = time.process_time()-query_cpu
        query["worker_lifetime_peak_rss_bytes_at_query_end"] = peak()
        query["finished_at_utc"] = now()
        query = safe(query)
        with progress.open("a") as stream:
            stream.write(json.dumps(query, allow_nan=False)+"\n")
        record["queries"].append(query)
    record.update({"status": "panel_record_complete", "finished_at_utc": now(),
        "cold_worker_seconds_before_result": time.perf_counter()-started,
        "cold_worker_cpu_seconds_before_result": time.process_time()-cpu_started,
        "worker_peak_rss_before_result": peak()})
    phase, cpu_phase = time.perf_counter(), time.process_time()
    payload = json.dumps(safe(record), indent=2, allow_nan=False)+"\n"
    with output.open("x") as stream:
        stream.write(payload)
    timing = {"serialization_seconds": time.perf_counter()-phase, "serialization_cpu_seconds": time.process_time()-cpu_phase,
              "worker_peak_rss_after_result": peak(), "cold_worker_seconds_through_result": time.perf_counter()-started,
              "scope": "Through final result JSON write; timing sidecar creation and stdout later covered by outer sampler only."}
    with Path(str(output)+".timing.json").open("x") as stream:
        stream.write(json.dumps(timing, indent=2)+"\n")
    print(json.dumps({"panel_id": panel_id, "queries": len(record["queries"]), "status": record["status"]}), flush=True)


if __name__ == "__main__":
    main()
