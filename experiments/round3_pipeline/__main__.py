"""Run every arm from original JSON so pruning costs stay inside the watchdog."""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import resource
import signal
import sys
import time

from experiments.inference import InferenceLimit, batched_brute_force, load_model, variable_elimination
from .core import prepare_model


class PreprocessingTimeLimit(TimeoutError):
    pass


def preprocessing_timeout(signum, frame):
    raise PreprocessingTimeLimit("Cold propagation/algebra/fingerprint time budget exceeded")


def safe_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return "-inf" if value == -math.inf else "invalid_nonfinite"
    if isinstance(value, dict):
        return {key: safe_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [safe_json(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--representation", choices=["simplified", "propagated"], required=True)
    parser.add_argument("--method", choices=["ve", "batch", "pyagrum"], required=True)
    parser.add_argument("--expected-target-sha256")
    parser.add_argument("--max-table-bytes", type=int, default=128 * 1024**2)
    parser.add_argument("--max-states", type=int, default=20_000_000)
    parser.add_argument("--batch-states", type=int, default=65_536)
    parser.add_argument("--time-limit-seconds", type=float, default=20)
    parser.add_argument("--preprocessing-limit-seconds", type=float, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    cpu_started = time.process_time()
    record = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
              "method": args.method, "pipeline_version": 1,
              "pipeline": {"representation": args.representation}}
    inference_started = None
    inference_cpu_started = None
    try:
        phase = time.perf_counter()
        cpu_phase = time.process_time()
        original = load_model(args.model, allow_higher_arity=True)
        loading_seconds = time.perf_counter() - phase
        loading_cpu_seconds = time.process_time() - cpu_phase
        record.update({"model_id": original.model_id, "model_sha256": original.source_sha256,
                       "loading_seconds": loading_seconds, "input_state_count": str(original.n_states)})
        previous_handler = signal.signal(signal.SIGALRM, preprocessing_timeout)
        signal.setitimer(signal.ITIMER_REAL, args.preprocessing_limit_seconds)
        try:
            prepared, pipeline = prepare_model(original, args.representation)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
        pipeline["load_seconds"] = loading_seconds
        pipeline["load_cpu_seconds"] = loading_cpu_seconds
        record.update({"pipeline": pipeline, "state_count": str(prepared.n_states),
                       "variables": len(prepared.domains), "factors": len(prepared.factors)})
        if args.expected_target_sha256 and pipeline["target_sha256"] != args.expected_target_sha256:
            record.update({"status": "target_fingerprint_mismatch",
                           "expected_target_sha256": args.expected_target_sha256})
        else:
            remaining = args.time_limit_seconds - (time.perf_counter() - started)
            if remaining <= 0:
                raise InferenceLimit("time_limit", {"elapsed_seconds": 0.0, "stage": "cold_preparation"})
            inference_started = time.perf_counter()
            inference_cpu_started = time.process_time()
            if args.method == "ve":
                result = variable_elimination(prepared, order="min-fill", max_table_bytes=args.max_table_bytes,
                                              time_limit_seconds=remaining)
            elif args.method == "batch":
                result = batched_brute_force(prepared, max_states=args.max_states, batch_states=args.batch_states,
                                             max_batch_bytes=args.max_table_bytes, time_limit_seconds=remaining)
            else:
                from experiments.established_v2 import run_pyagrum

                result = run_pyagrum(prepared, max_table_bytes=args.max_table_bytes)
            record.update(result)
    except InferenceLimit as error:
        record.update({"status": error.reason, "metrics": error.metrics})
    except PreprocessingTimeLimit as error:
        record.update({"status": "preprocessing_time_limit", "exception_message": str(error)})
    except ArithmeticError as error:
        record.update({"status": "numerical_failure", "exception": type(error).__name__, "exception_message": str(error)})
    except Exception as error:
        record.update({"status": "pipeline_error", "exception": type(error).__name__, "exception_message": str(error)})
    inference_seconds = time.perf_counter() - inference_started if inference_started is not None else 0.0
    record["pipeline"]["inference_seconds"] = inference_seconds
    record["pipeline"]["inference_cpu_seconds"] = time.process_time() - inference_cpu_started if inference_cpu_started is not None else 0.0
    record["pipeline"]["cold_total_seconds"] = time.perf_counter() - started
    record["pipeline"]["cold_total_cpu_seconds"] = time.process_time() - cpu_started
    record["pipeline"]["preprocessing_limit_seconds"] = args.preprocessing_limit_seconds
    record["pipeline"]["preprocessing_limit_scope"] = "SIGALRM around propagation/algebra/target fingerprint; signal can be deferred inside native code. Whole-process outer watchdog also remains active. Original JSON load is inside the outer limit, outside this phase timer."
    record["pipeline"]["inference_cpu_scope"] = "Aggregate method CPU including ordering and native conversion/ingestion where applicable. CPU subdivision inside unchanged legacy kernels is unavailable; their wall phases are retained."
    record["pipeline"]["cost_scope"] = "Original JSON load, exact support propagation when selected, exact algebra, target fingerprint, and inference; fresh-process startup and output additionally included by external wall clock."
    metrics = record.get("metrics", {})
    record["kernel_elapsed_seconds"] = metrics.get("kernel_elapsed_seconds", metrics.get("elapsed_seconds"))
    for field in ("conversion_seconds", "dependency_import_seconds", "preprocessing_seconds"):
        record[field] = metrics.get(field)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    record["process_peak_rss_bytes"] = int(rss if sys.platform == "darwin" else rss * 1024)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    timing_path = Path(str(args.output) + ".timing.json")
    record["pipeline"]["serialization_timing_sidecar"] = str(timing_path)
    phase = time.perf_counter()
    cpu_phase = time.process_time()
    output = json.dumps(safe_json(record), indent=2, allow_nan=False) + "\n"
    with args.output.open("x") as stream:
        stream.write(output)
    serialization = {"serialization_seconds": time.perf_counter() - phase,
                     "serialization_cpu_seconds": time.process_time() - cpu_phase,
                     "cold_total_through_result_seconds": time.perf_counter() - started,
                     "cold_total_through_result_cpu_seconds": time.process_time() - cpu_started,
                     "scope": "Encode and write the valid final result JSON; sidecar creation and stdout duplication are additional outer-watchdog costs. No fsync guarantee."}
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    serialization["process_peak_rss_bytes_after_result"] = int(rss if sys.platform == "darwin" else rss * 1024)
    serialization["rss_scope"] = "Worker lifetime through valid result JSON encoding/write; later sidecar creation/stdout covered by outer sampler only."
    with timing_path.open("x") as stream:
        stream.write(json.dumps(serialization, indent=2) + "\n")
    print(output, end="")


if __name__ == "__main__":
    main()
