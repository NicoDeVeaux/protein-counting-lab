"""Read sealed JSON and replay conversion arithmetic without experiment imports."""

from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "runs/campaign-003-amendment-003"


def read(path):
    return json.loads(Path(path).read_text())


def artifact(path):
    path = Path(path)
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def load_factors(path):
    doc = read(path)
    factors = []
    for factor in doc["factors"]:
        scope = tuple(factor["scope"])
        raw = np.asarray(factor["log_values"], dtype=object)
        values = np.array([-math.inf if v is None or v == "-inf" else float(v)
                           for v in raw.flat], dtype=np.float64)
        factors.append((scope, values.reshape(tuple(doc["domains"][v] for v in scope))))
    if "constant_log_weight" in doc:
        value = doc["constant_log_weight"]
        factors.append(((), np.asarray(-math.inf if value is None or value == "-inf" else float(value))))
    return doc["domains"], factors


def replay_conversion(path):
    domains, factors = load_factors(path)
    merged, sources, constants = {}, {}, []
    for i, (scope, values) in enumerate(factors):
        if not scope:
            constants.append(float(values))
            continue
        ordered = tuple(sorted(scope))
        values = values.transpose([scope.index(v) for v in ordered])
        if ordered in merged:
            previous = merged[ordered]
            both_finite = np.isfinite(previous) & np.isfinite(values)
            with np.errstate(over="ignore", invalid="ignore"):
                combined = previous + values
            if np.any(both_finite & ~np.isfinite(combined)):
                return {"status": "conversion_overflow", "phase": "scope_merge"}, None
            merged[ordered] = combined
        else:
            merged[ordered] = values.copy()
        sources.setdefault(ordered, []).append(i)
        if np.isnan(merged[ordered]).any() or np.isposinf(merged[ordered]).any():
            return {"status": "conversion_overflow", "phase": "scope_merge"}, None
    if -math.inf in constants or any(np.isneginf(v).all() for v in merged.values()):
        return {"status": "exact_zero_before_native", "reason": "identically zero scalar/merged factor"}, None
    scalar = math.fsum(constants)
    if not math.isfinite(scalar):
        return {"status": "conversion_overflow", "phase": "scalar_sum"}, None
    offsets, diagnostics, normalized = [scalar], [], {}
    roundtrip_total, minimum_sum = 0.0, 0.0
    for scope in sorted(merged):
        values = merged[scope]
        finite = np.isfinite(values)
        maximum = float(values[finite].max())
        shifted = values - maximum
        with np.errstate(under="ignore"):
            linear = np.exp(shifted)
        lost = finite & (linear == 0)
        if lost.any():
            ix = tuple(int(v) for v in np.argwhere(lost)[0])
            return {"status": "conversion_underflow", "failed_factor_scope": list(scope),
                    "new_zero_entries": int(lost.sum()),
                    "failed_factor_log_span": maximum - float(values[finite].min()),
                    "finite_group_entries": int(finite.sum()), "group_entries": int(values.size),
                    "group_max_log_weight": maximum, "group_min_finite_log_weight": float(values[finite].min()),
                    "example_lost_index": list(ix), "example_lost_finite_log_weight": float(values[ix]),
                    "example_shifted_log_weight": float(shifted[ix]),
                    "source_factor_indices": sources[scope],
                    "scalar_log_offset_before_failure": scalar,
                    "previous_groups_max_total_log_roundtrip_error": roundtrip_total}, None
        error = float(np.max(np.abs(np.log(linear[finite]) - shifted[finite])))
        roundtrip_total += error
        minimum_sum += float(shifted[finite].min())
        offsets.append(maximum)
        normalized[scope] = linear
        diagnostics.append({"scope": list(scope), "entries": int(linear.size), "log_offset": maximum,
                            "positive_entries": int(finite.sum()), "max_abs_log_roundtrip_error": error})
    report = {"status": "conversion_accuracy_limit" if roundtrip_total > 1e-9 else "conversion_supported",
              "scalar_log_offset": scalar, "removed_log_offset": math.fsum(offsets),
              "total_log_roundtrip_error_diagnostic": roundtrip_total, "factor_conversion": diagnostics,
              "sum_minimum_positive_normalized_log_weight": minimum_sum,
              "all_finite_group_entries_stay_positive": True}
    for variable, domain in enumerate(domains):
        if not any(variable in scope for scope in normalized):
            normalized[(variable,)] = np.ones(domain, dtype=np.float64)
    return report, (factors, normalized)


def range_stats(values):
    return {"min": min(values), "median": statistics.median(values), "max": max(values)}


def main():
    manifest = read(RUN / "manifest.json")
    rows = [json.loads(line) for line in (RUN / "trials.jsonl").read_text().splitlines()]
    models = {m["model_id"]: m for m in manifest["models"]}
    profiles = {p["resource_profile_id"]: p for p in manifest["resource_profiles"]}
    conversions, numerical = {}, {}
    for model in manifest["models"]:
        original = ROOT / model["pipeline_input"]["path"]
        original_result, _ = replay_conversion(original)
        for rep in model["representations"]:
            key = (model["model_id"], rep["representation_id"])
            path = ROOT / rep["files"][0]["path"]
            replay, matrices = replay_conversion(path)
            conversions[key] = {"model_id": key[0], "representation_id": key[1],
                                "prepared_artifact": artifact(path), "prepared_conversion": replay,
                                "original_artifact": artifact(original), "original_conversion": original_result}
            numerical[key] = matrices
    mismatches, offset_checks, zero_checks = [], [], []
    distribution_versions, imported_versions = Counter(), Counter()
    native_rows = [r for r in rows if r["method_id"] == "pyagrum"]
    for row in native_rows:
        raw = read(ROOT / row["output"]["artifact"]["path"])
        metrics = raw["metrics"]
        distribution_versions[str(metrics.get("package_distribution_version"))] += 1
        imported_versions[str(metrics.get("package_version"))] += 1
        key = (row["model_id"], row["representation_id"])
        replay = conversions[key]["prepared_conversion"]
        status = replay["status"]
        tid = row["trial_id"]
        if status.startswith("conversion_") and status != "conversion_supported":
            for name in ("failed_factor_scope", "new_zero_entries", "failed_factor_log_span"):
                if metrics.get(name) != replay.get(name):
                    mismatches.append({"trial_id": tid, "field": name, "recorded": metrics.get(name), "replayed": replay.get(name)})
            if raw["status"] != status or row["status"] != "unsupported_conversion":
                mismatches.append({"trial_id": tid, "field": "status"})
            continue
        if status == "exact_zero_before_native":
            zero_checks.append({"trial_id": tid, "kind": "zero_factor_guard", "passed": raw["status"] == "complete" and raw["log_z"] == "-inf"})
            continue
        for name in ("scalar_log_offset", "removed_log_offset", "total_log_roundtrip_error_diagnostic", "factor_conversion", "sum_minimum_positive_normalized_log_weight"):
            if metrics.get(name) != replay[name]:
                mismatches.append({"trial_id": tid, "field": name, "recorded": metrics.get(name), "replayed": replay[name]})
        if "selected_assignment" not in metrics:
            safe = replay["sum_minimum_positive_normalized_log_weight"] >= math.log(np.finfo(np.float64).tiny)
            zero_checks.append({"trial_id": tid, "kind": "native_incompatible_evidence", "safe_positive_product": safe,
                                "passed": safe and raw["log_z"] == "-inf" and metrics.get("exception") == "IncompatibleEvidence"})
            continue
        factors, normalized = numerical[key]
        selected = metrics["selected_assignment"]
        if metrics["conditional_queries"] != len(selected):
            mismatches.append({"trial_id": tid, "field": "conditional_queries"})
        original_weight = math.fsum(float(values[tuple(selected[v] for v in scope)]) for scope, values in factors)
        normalized_weight = math.fsum(math.log(float(values[tuple(selected[v] for v in scope)])) for scope, values in normalized.items())
        reconstructed = normalized_weight + replay["removed_log_offset"]
        fields = {"original_assignment_log_weight": original_weight,
                  "normalized_assignment_log_weight": normalized_weight,
                  "offset_reconstruction_delta": reconstructed - original_weight,
                  "original_weight_identity_log_z": original_weight - metrics["conditional_log_probability"]}
        for name, value in fields.items():
            if metrics.get(name) != value:
                mismatches.append({"trial_id": tid, "field": name, "recorded": metrics.get(name), "replayed": value})
        logz = reconstructed - metrics["conditional_log_probability"]
        if raw["log_z"] != logz:
            mismatches.append({"trial_id": tid, "field": "log_z"})
        offset_checks.append({"trial_id": tid, "absolute_offset_reconstruction_delta": abs(reconstructed - original_weight),
                              "log_z_reconstruction_matches": raw["log_z"] == logz,
                              "conditional_queries": metrics["conditional_queries"]})

    clock_issues, resource_issues, completed, timeouts = [], [], [], []
    all_rss = []
    for row in rows:
        tid = row["trial_id"]
        mon, mem = row["monitor"], row["memory"]
        profile = profiles[row["resource_profile_id"]]
        if row["timing"]["wall_seconds"] != mon["wall_seconds"] or row["timing"]["phases"]["end_to_end"] != mon["wall_seconds"]:
            clock_issues.append({"trial_id": tid, "check": "outer clock copied exactly"})
        if row["timing"]["cpu_seconds"] != mon["cpu_seconds"]:
            clock_issues.append({"trial_id": tid, "check": "outer CPU copied exactly"})
        if mon["sampling_errors"] or mem["rss_peak_bytes"] != mon["sampled_peak_rss_bytes"]:
            resource_issues.append({"trial_id": tid, "check": "sampler error/value"})
        dates_elapsed = (datetime.fromisoformat(row["finished_at_utc"]) - datetime.fromisoformat(row["started_at_utc"])).total_seconds()
        common = {"trial_id": tid, "sampled_peak_rss_bytes": mem["rss_peak_bytes"],
                  "rss_ceiling_bytes": profile["rss_ceiling_bytes"], "rss_samples": mon["rss_samples"],
                  "outer_wall_seconds": mon["wall_seconds"], "outer_cpu_seconds": mon["cpu_seconds"],
                  "utc_minus_monotonic_seconds": dates_elapsed - mon["wall_seconds"]}
        if row["status"] == "timeout":
            output = RUN / "raw" / (tid + ".result.json")
            sidecar = Path(str(output) + ".timing.json")
            if not (mon["termination_reason"] == "timeout" and mon["signal"] == "SIGTERM" and row["timing"]["right_censored"]):
                resource_issues.append({"trial_id": tid, "check": "timeout classification"})
            if output.exists() or sidecar.exists() or (RUN / "raw" / (tid + ".stdout.txt")).stat().st_size or (RUN / "raw" / (tid + ".stderr.txt")).stat().st_size:
                resource_issues.append({"trial_id": tid, "check": "unexpected timeout outputs"})
            common.update({"method_id": row["method_id"], "model_id": row["model_id"], "representation_id": row["representation_id"],
                           "profile": row["resource_profile_id"], "timeout_seconds": profile["wall_timeout_seconds"],
                           "trigger_seconds": mon["limit_trigger_seconds"], "kill_seconds": mon["kill_seconds"],
                           "wall_overshoot_seconds": mon["wall_seconds"] - profile["wall_timeout_seconds"],
                           "result_and_sidecar_absent": not output.exists() and not sidecar.exists()})
            timeouts.append(common)
        else:
            raw = read(ROOT / row["output"]["artifact"]["path"])
            side = read(ROOT / row["serialization_timing_artifact"]["path"])
            pipe = raw["pipeline"]
            prep_sum = sum(pipe[k] for k in ("propagation_seconds", "simplification_seconds", "target_validation_seconds"))
            charged_sum = pipe["load_seconds"] + pipe["preparation_seconds"] + pipe["inference_seconds"]
            checks = {
                "prepared subphases within preparation": prep_sum <= pipe["preparation_seconds"],
                "worker phases within worker endpoint": charged_sum <= pipe["cold_total_seconds"],
                "worker endpoint before result write endpoint": pipe["cold_total_seconds"] <= side["cold_total_through_result_seconds"],
                "serialization fits endpoint difference": side["serialization_seconds"] <= side["cold_total_through_result_seconds"] - pipe["cold_total_seconds"],
                "result write endpoint within outer endpoint": side["cold_total_through_result_seconds"] <= mon["wall_seconds"],
                "CPU endpoint ordered": pipe["cold_total_cpu_seconds"] <= side["cold_total_through_result_cpu_seconds"] <= mon["cpu_seconds"],
                "serialization copied": row["timing"]["phases"]["serialization"] == side["serialization_seconds"],
            }
            for name, passed in checks.items():
                if not passed:
                    clock_issues.append({"trial_id": tid, "check": name})
            before, after = raw["process_peak_rss_bytes"], side["process_peak_rss_bytes_after_result"]
            if after < before or mem["worker_reported_lifetime_peak_rss_bytes"] != max(before, after):
                resource_issues.append({"trial_id": tid, "check": "worker high-water propagation"})
            combined = max(mem["rss_peak_bytes"], before, after)
            if combined > profile["rss_ceiling_bytes"] and row["status"] != "rss_limit":
                resource_issues.append({"trial_id": tid, "check": "unadjudicated RSS ceiling exceedance"})
            common.update({"worker_before_result_peak_rss_bytes": before, "worker_after_result_peak_rss_bytes": after,
                           "combined_observed_peak_rss_bytes": combined, "serialization_seconds": side["serialization_seconds"],
                           "cold_before_result_seconds": pipe["cold_total_seconds"], "cold_through_result_seconds": side["cold_total_through_result_seconds"],
                           "outer_minus_through_result_seconds": mon["wall_seconds"] - side["cold_total_through_result_seconds"],
                           "preparation_seconds": pipe["preparation_seconds"],
                           "status": row["status"], "method_id": row["method_id"]})
            completed.append(common)
        all_rss.append(common)
    underflow_cells = [v for v in conversions.values() if v["prepared_conversion"]["status"] == "conversion_underflow"]
    conversion_path = OUT / "conversion_replay.json"
    conversion_path.write_text(json.dumps(list(conversions.values()), indent=2, allow_nan=False) + "\n")
    resource_path = OUT / "resource_rows.json"
    resource_path.write_text(json.dumps(all_rss, indent=2, allow_nan=False) + "\n")
    report = {
        "audit": "independent campaign003 resource and conversion read-only audit",
        "classification": "poc",
        "scope": "No timed measurement rerun; no experiment imports; independent JSON parsing, NumPy conversion replay, and raw-record/code endpoint audit. Original/prepared same-target proofs and bundle hashes are assigned to other graders.",
        "inputs": [artifact(RUN / "manifest.json"), artifact(ROOT / "runs/campaign-003-review/bundle_manifest.json"),
                   artifact(ROOT / "experiments/established_v2/pyagrum_adapter.py"), artifact(ROOT / "experiments/round3_pipeline/__main__.py"),
                   artifact(ROOT / "experiments/round2_watchdog/monitor.py"), artifact(ROOT / "scripts/campaign_round3.py")],
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__},
        "conversion": {
            "native_rows": len(native_rows), "unsupported_rows": sum(r["status"] == "unsupported_conversion" for r in native_rows),
            "reproduced_underflow_cells": len(underflow_cells),
            "unsupported_trial_ids": [r["trial_id"] for r in native_rows if r["status"] == "unsupported_conversion"],
            "replay_evidence": artifact(conversion_path),
            "underflow_cells": [{"model_id": v["model_id"], "representation_id": v["representation_id"],
                                 **{k: v["prepared_conversion"][k] for k in ("failed_factor_scope", "new_zero_entries", "failed_factor_log_span", "example_shifted_log_weight")}}
                                for v in underflow_cells],
            "record_replay_mismatches": mismatches,
            "package_evidence": {"manifest_method_version": next(m["version"] for m in manifest["methods"] if m["method_id"] == "pyagrum"),
                                 "raw_distribution_version_counts": dict(distribution_versions),
                                 "raw_imported_module_version_counts": dict(imported_versions),
                                 "explanation": "All108 native workers record installed distribution3.3.2. The21 workers reaching pyagrum import also record module3.3.2. Other87 return before native import (78 underflow,9 exact-zero guard). Manifest version unknown is inaccurate metadata and is not independent native-build identification."},
            "completed_offset_identity_checks": offset_checks, "zero_checks": zero_checks,
            "interpretation": "All finite source log entries represent positive ideal-real mass. Rejecting exp underflow preserves this contract; unsupported conversion is an adapter limitation, not evidence that exact inference is intrinsically impossible. Exp/log diagnostics are not rigorous error bounds."
        },
        "resources": {
            "monitored_rows": len(rows), "valid_result_and_sidecar_rows": len(completed), "timeout_rows": len(timeouts),
            "record_audit_issues": resource_issues, "rss_limit_rows": sum(r["status"] == "rss_limit" for r in rows),
            "sampling_errors": sum(r["monitor"]["sampling_errors"] for r in rows),
            "sample_counts": range_stats([r["monitor"]["rss_samples"] for r in rows]),
            "rows_at_most_three_samples": sum(r["monitor"]["rss_samples"] <= 3 for r in rows),
            "worker_high_water_exceeds_sampled_rows": sum(r["worker_after_result_peak_rss_bytes"] > r["sampled_peak_rss_bytes"] for r in completed),
            "serialization_increases_worker_high_water_rows": sum(r["worker_after_result_peak_rss_bytes"] > r["worker_before_result_peak_rss_bytes"] for r in completed),
            "maximum_serialization_high_water_increase_bytes": max(r["worker_after_result_peak_rss_bytes"] - r["worker_before_result_peak_rss_bytes"] for r in completed),
            "sampled_peak_max_bytes": max(r["sampled_peak_rss_bytes"] for r in all_rss),
            "worker_high_water_max_bytes": max(r["worker_after_result_peak_rss_bytes"] for r in completed),
            "combined_observed_peak_max_bytes": max(r.get("combined_observed_peak_rss_bytes", r["sampled_peak_rss_bytes"]) for r in all_rss),
            "per_row_evidence": artifact(resource_path),
            "timeouts": timeouts,
            "limits": "10ms is the requested sleep between samples, not a verified sample cadence. Tree enumeration/scheduling add latency. Process RSS sums can double-count shared pages and miss exited descendants or between-sample peaks. Worker high-water covers through result write; sidecar creation/stdout only have sampled coverage. No instantaneous RSS ceiling or exhaustive descendant history is certified."
        },
        "clocks": {
            "record_audit_issues": clock_issues,
            "completed_outer_minus_through_result_seconds": range_stats([r["outer_minus_through_result_seconds"] for r in completed]),
            "serialization_seconds": range_stats([r["serialization_seconds"] for r in completed]),
            "preparation_seconds": range_stats([r["preparation_seconds"] for r in completed]),
            "utc_minus_monotonic_seconds": range_stats([r["utc_minus_monotonic_seconds"] for r in all_rss]),
            "sum_outer_wall_seconds": sum(r["monitor"]["wall_seconds"] for r in rows),
            "campaign_elapsed_seconds": read(RUN / "completion.json")["elapsed_seconds"],
            "row_budget": "Outer perf_counter starts before Popen and ends after worker reap/log closure. Worker imports precede its internal cold clock but are charged by outer wall. Load, support propagation, simplification, target hash, all solver calls and result/stdout output are inside outer watchdog. Driver-side ingestion/hashing/validation after supervise returns is campaign overhead, not row wall.",
            "phase_limitations": "Solver_call nests conversion/preprocessing/kernel and is not additive with them. Conversion, ingestion and legacy kernel CPU subphases are unavailable; worker aggregate inference CPU includes them. Native ingestion is inside preprocessing wall. No fsync guarantee. Four killed rows have no worker phase clock/result and cannot be assigned to a precise internal stage."
        },
        "code_review": {
            "cold_reexecution": "Every row command takes the declared original pipeline_input, then redoes selected propagation, exact algebra and target fingerprint inside the worker; prepared JSON is only the independently frozen expected target, not the worker input.",
            "preprocessing_limit": "3s SIGALRM wraps propagation/algebra/fingerprint; original load is outside this phase alarm but inside outer watchdog. Native code can defer Python signals. No preprocessing_time_limit rows occurred.",
            "native_conversion_boundary": "Finite merged factors use subtract-max and np.exp; a finite entry becoming zero returns conversion_underflow before pyagrum import/MRF construction. Successful conversions restore scalar and factor offsets; all conditional makeInference queries and identity reconstruction lie inside kernel wall.",
            "native_memory_boundary": "Adapter version2 passes1024 to setMaxMemory; source_proof.json records MiB units. Native scheduling quota is not RSS enforcement; outer128/512MiB sampled thresholds plus post-result worker high-water control row classification. Source unit proof was not separately fetched from upstream in this audit.",
            "hidden_work_assessment": "No out-of-clock propagation, algebra, cached prepared-target inference, omitted conditional query, or worker-result serialization was found in the audited paths. Source acquisition and static preparation are explicitly outside measured rows. No raw event trace verifies actual sample timestamps, child history, fsync, CPU subphases, or which internal phase the killed workers reached."
        },
        "findings": [
            {"id": "R1", "severity": "qualification", "finding": "Ledger rss_peak_bytes and summary completed_peak_rss_max_bytes use sampled RSS alone. Use max(sampled, before-result worker high-water, after-result worker high-water) for observed whole-pipeline memory summaries, preserving scopes and missing timeout high-water."},
            {"id": "R2", "severity": "qualification", "finding": "10ms requested sampler interval is not an achieved cadence; no individual sample timestamps exist. Four timeouts trigger26-49ms after nominal wall limit and finish43-78ms after it. These remain right-censored whole-pipeline outcomes."},
            {"id": "R3", "severity": "qualification", "finding": "CPU phase granularity is weaker than the protocol's full phase list: conversion/ingestion/native/custom kernel CPU are only present in aggregate solver_call CPU. Wall subphases are nested and cannot be summed with solver_call."},
            {"id": "R4", "severity": "metadata", "finding": "Final manifest pyagrum method.version is unknown. All 108 raw native rows record installed distribution 3.3.2; all 21 reaching native import also record module 3.3.2. Runtime evidence repairs practical version interpretation but does not make the manifest field accurate or identify the native binary build."}
        ],
        "limitations": ["No timed reruns, native engine reruns, or experiment preprocessing imports were performed.",
                        "Replay uses the same NumPy binary64 exp primitive as the adapter, independently reconstructing its inputs and guards; it is not a second transcendental implementation or real-arithmetic certificate.",
                        "Original-to-prepared support/algebra proof correctness and numeric reference truth are reviewed separately."]
    }
    destination = OUT / "audit.json"
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(destination.relative_to(ROOT)), "native_rows": len(native_rows),
                      "underflow_rows": report["conversion"]["unsupported_rows"], "underflow_cells": len(underflow_cells),
                      "conversion_mismatches": len(mismatches), "clock_issues": len(clock_issues), "resource_issues": len(resource_issues)}))


if __name__ == "__main__":
    main()
