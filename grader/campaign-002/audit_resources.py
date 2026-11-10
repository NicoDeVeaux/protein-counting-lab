"""Check outcomes, conversion rejection, resource scopes and the quota confound."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

from audit_semantics import factors

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "grader/campaign-002"


def read(path):
    return json.loads((ROOT / path).read_text())


def conversion(data):
    grouped = {}
    constants = []
    for scope, array in factors(data):
        if not scope:
            constants.append(float(array))
            continue
        order = tuple(sorted(scope))
        values = array.transpose([scope.index(v) for v in order])
        grouped[order] = values.copy() if order not in grouped else grouped[order] + values
    if -math.inf in constants or any(np.isneginf(a).all() for a in grouped.values()):
        return {"classification": "exact_zero_factor"}
    roundtrip = 0.
    for scope, array in sorted(grouped.items()):
        finite = array[np.isfinite(array)]
        maximum = float(max(finite))
        shifted = [float(x)-maximum for x in finite]
        linear = [math.exp(x) for x in shifted]
        zeros = sum(x == 0 for x in linear)
        if zeros:
            return {"classification": "conversion_underflow", "scope": list(scope), "positive_entries_lost": zeros,
                    "min_shifted_log": min(shifted), "span": maximum-float(min(finite))}
        roundtrip += max(abs(math.log(w)-v) for v, w in zip(shifted, linear))
    return {"classification": "conversion_accuracy_limit" if roundtrip > 1e-9 else "representable",
            "scalar_exp_log_roundtrip_diagnostic": roundtrip}


def main():
    manifest = read("runs/campaign-002/manifest.json")
    trials = [json.loads(line) for line in (ROOT / "runs/campaign-002/trials.jsonl").read_text().splitlines()]
    profiles = {x["resource_profile_id"]: x for x in manifest["resource_profiles"]}
    models = {x["model_id"]: x for x in manifest["models"]}
    errors = []
    rows = []
    conversion_checks = {}
    counts = Counter()
    numerical_deltas = []
    quota_confounded = []
    for trial in trials:
        profile = profiles[trial["resource_profile_id"]]
        for key in ["table_cap_bytes", "rss_ceiling_bytes", "rss_enforcement"]:
            assert trial["memory"][key] == profile[key]
        rep = next(x for x in models[trial["model_id"]]["representations"] if x["representation_id"] == trial["representation_id"])
        if trial["status"] == "planned_skip":
            domains = rep["structure"]["domain_cardinalities"]
            assert trial["method_id"] == "batch" and math.prod(domains) > 20_000_000
            assert trial["started_at_utc"] is None
            counts["static_batch_state_cap_skips"] += 1
            continue
        raw_path = trial["output"]["artifact"]
        raw = read(raw_path["path"]) if raw_path else None
        monitor = trial["monitor"]
        assert monitor["sampling_errors"] == 0
        assert trial["memory"]["rss_peak_bytes"] == monitor["sampled_peak_rss_bytes"]
        assert trial["timing"]["wall_seconds"] == monitor["wall_seconds"]
        if trial["status"] == "timeout":
            assert monitor["termination_reason"] == "timeout"
            assert monitor["limit_trigger_seconds"] >= profile["wall_timeout_seconds"]
            assert trial["timing"]["right_censored"]
            counts["external_timeouts"] += 1
        elif trial["status"] == "predicted_table_cap":
            metric = raw["metrics"]
            if trial["method_id"] == "ve":
                assert raw["status"] == "intermediate_table_limit"
                assert metric["blocked_table_bytes"] > profile["table_cap_bytes"]
                counts["custom_per_join_policy_rejections"] += 1
            else:
                assert raw["status"] == "wrapper_preflight_clique_limit"
                assert metric["preflight_max_clique_table_bytes"] > profile["table_cap_bytes"]
                counts["native_wrapper_preflight_policy_rejections"] += 1
        elif trial["status"] == "unsupported_conversion":
            key = trial["model_id"] + "/" + trial["representation_id"]
            if key not in conversion_checks:
                conversion_checks[key] = conversion(read(rep["files"][0]["path"]))
            assert conversion_checks[key]["classification"] == raw["status"]
            counts[raw["status"]] += 1
        elif trial["status"] == "invalid_output":
            assert trial["method_id"] == "pyagrum"
            assert raw["status"] == "adapter_error"
            assert "std::bad_alloc" in raw["exception_message"]
            quota_confounded.append({"trial_id": trial["trial_id"], "model_id": trial["model_id"],
                "profile": trial["resource_profile_id"], "recorded_status": trial["status"],
                "exception": raw["exception_message"], "sampled_peak_rss_bytes": trial["memory"]["rss_peak_bytes"],
                "rss_ceiling_bytes": profile["rss_ceiling_bytes"],
                "audit_interpretation": "Native scheduler allocation exception under an unintended 1 MiB scheduler quota. Not evidence of host-RAM exhaustion or the declared RSS limit."})
        elif trial["status"] in ["success", "unverified_accuracy"]:
            value = trial["output"]["log_z"]
            ref = manifest["references"].get(trial["model_id"])
            if trial["status"] == "unverified_accuracy":
                assert ref is None
            else:
                assert ref is not None
                if value == "-Infinity":
                    assert ref["log_z"] == "-Infinity"
                else:
                    with localcontext() as ctx:
                        ctx.prec = 110
                        target = Decimal(ref["log_z"]) if isinstance(ref["log_z"], str) else Decimal.from_float(ref["log_z"])
                        delta = float(abs(Decimal.from_float(value)-target))
                    offsets = raw.get("metrics", {})
                    sum_abs_offsets = abs(offsets.get("scalar_log_offset", 0.)) + math.fsum(abs(f.get("log_offset",0.)) for f in offsets.get("factor_conversion",[]))
                    threshold = 1e-8 + 64*sys.float_info.epsilon*max(1., abs(float(target)), sum_abs_offsets)
                    assert delta <= threshold
                    assert delta == trial["validation"]["absolute_log_error"]
                    assert threshold == trial["validation"]["acceptance_threshold"]
                    numerical_deltas.append(delta)
        else:
            errors.append({"trial_id": trial["trial_id"], "error": "Unhandled status"})
        if trial["status"] in ["success", "unverified_accuracy"]:
            assert monitor["sampled_peak_rss_bytes"] <= profile["rss_ceiling_bytes"]
            worker_peak = trial["memory"]["worker_reported_lifetime_peak_rss_bytes"]
            assert worker_peak <= profile["rss_ceiling_bytes"]
        rows.append({"trial_id": trial["trial_id"], "status": trial["status"]})
    diagnostics_path = "experiments/established/diagnostics/results-authorized/all_results.json"
    diagnostics = read(diagnostics_path)
    diag_rows = []
    for observation in diagnostics["observations"]:
        d = observation["diagnostic"]
        result = d["result"]
        diag_rows.append({"model_id": observation["model_id"], "variant": observation["variant"],
            "status": result["status"], "log_z": result.get("log_z"), "message": result.get("message"),
            "peak_rss_bytes": d["peak_rss_bytes"], "termination_reason": observation["monitor"]["termination_reason"],
            "quota_events": [x for x in d["events"] if x["phase"] == "setMaxMemory"]})
    result = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(), "errors": errors,
        "trial_checks": len(trials), "counts": dict(counts),
        "references_recompared": len(numerical_deltas), "max_absolute_log_error_against_frozen_references": max(numerical_deltas),
        "conversion_checks": conversion_checks,
        "quota_confounded_original_rows": quota_confounded,
        "quota_source_evidence": read("grader/campaign-002/primary_sources/provenance.json"),
        "quota_source_finding": "Official 3.3.2 ScheduledInference forwards megabytes; Scheduler multiplies by 1048576. Original adapter passes 1 in both profiles, so its scheduler budget is 1 MiB, despite the gigabytes variable/metadata/doc label. This is separate from wrapper clique-table and RSS ceilings.",
        "authorized_posthoc_diagnostics": {"path": diagnostics_path, "sha256": hashlib.sha256((ROOT/diagnostics_path).read_bytes()).hexdigest(),
            "status": "Outcome-selected causal diagnosis, not replacement campaign measurements or a confirmatory speed comparison.", "rows": diag_rows},
        "rss_limit_scope": "External watchdog is sampled 10 ms process-tree RSS with no instantaneous guarantee. Worker lifetime high-water adjudicates completed trials. No original trial was classified rss_limit. All monitoring samples report zero access errors. The preserved nonmeasurement controls test completion, timeout and sampled RSS termination.",
        "timing_limitations": "Offline acquisition/conversion and artifact serialization are excluded. Stored preparation_seconds times model load, static analyses and exact reduction before artifact writing; one_off_wall_plus_algebra_seconds is not a full raw-source-to-result time. Original native timings also carry the 1 MiB scheduler-policy confound. No broad performance conclusion here."}
    (OUT / "original_resource_audit.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k: result[k] for k in ["errors", "trial_checks", "counts", "references_recompared", "max_absolute_log_error_against_frozen_references", "quota_source_finding"]}, indent=2))
    print("Diagnostic status counts:", dict(Counter((x["variant"],x["status"]) for x in diag_rows)))


if __name__ == "__main__":
    main()
