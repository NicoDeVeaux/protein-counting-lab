"""Freeze, execute, and summarize the initial local inference campaign."""

from __future__ import annotations

import argparse
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
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def freeze(run_dir):
    if run_dir.exists():
        raise FileExistsError(run_dir)
    data_path = ROOT / "data/uai23_manifest.json"
    cohort = json.loads(data_path.read_text())
    rubric = ROOT / "grader/rubric.json"
    expected_rubric = (ROOT / "grader/rubric.sha256").read_text().split()[0]
    assert digest(rubric) == expected_rubric
    inputs, trials = [], []
    for case in cohort["cases"]:
        inputs.append({"path": case["local_path"], "sha256": case["sha256"]})
        for model in case["states"]:
            assert digest(ROOT / model["path"]) == model["sha256"]
            inputs.append({"path": model["path"], "sha256": model["sha256"]})
            base = {"case_id": case["case_id"], "model_id": model["model_id"],
                    "model_path": model["path"], "model_sha256": model["sha256"],
                    "configuration_count": model["configuration_count"]}
            for repeat in range(3):
                trials.append(base | {"method": "eliminate", "repeat": repeat,
                                      "args": ["--order", "min-fill", "--max-table-bytes", "268435456", "--time-limit-seconds", "30"], "hard_timeout_seconds": 35})
                trials.append(base | {"method": "batch", "repeat": repeat,
                                      "args": ["--max-states", "11000000", "--batch-states", "65536", "--max-batch-bytes", "67108864", "--time-limit-seconds", "30"], "hard_timeout_seconds": 35})
            if model["configuration_count"] <= 100000:
                trials.append(base | {"method": "brute", "repeat": 0,
                                      "args": ["--max-states", "100000", "--time-limit-seconds", "30"], "hard_timeout_seconds": 35})
            for epsilon in (0.68, 0.1, 0.01):
                trials.append(base | {"method": "bounded", "repeat": 0, "epsilon": epsilon,
                                      "args": ["--epsilon", str(epsilon), "--max-nodes", "20000", "--max-frontier-nodes", "50000", "--time-limit-seconds", "2"], "hard_timeout_seconds": 7})
    random.Random(20261106).shuffle(trials)
    for index, trial in enumerate(trials):
        trial["trial_id"] = f"{index:04d}"
    source_files = []
    for pattern in ("scripts/*.py", "experiments/**/*.py", "tests/*.py"):
        source_files.extend(ROOT.glob(pattern))
    source_files += [ROOT / "pyproject.toml", ROOT / "uv.lock", ROOT / "AGENTS.md"]
    source_snapshot = {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(source_files))}
    manifest = {"campaign_id": run_dir.name, "frozen_at": now(), "classification": "poc",
                "rubric_sha256": expected_rubric,
                "data_manifest": "data/uai23_manifest.json", "data_manifest_sha256": digest(data_path),
                "selection": cohort["selection_rule"], "source_snapshot": source_snapshot,
                "input_files": inputs, "trials": trials,
                "environment": {"python": platform.python_version(), "numpy": importlib.metadata.version("numpy"), "platform": platform.platform(),
                                "machine": platform.machine(), "logical_cpu_count": os.cpu_count(),
                                "thread_policy": "OPENBLAS/OMP/MKL/VECLIB each limited to one thread", "subprocesses": "sequential, fresh Python process per trial; no warmups"},
                "numerical_comparison": {"absolute_log_tolerance": 1e-8, "relative_log_tolerance": 1e-12,
                                         "zero_targets": "both negative infinity agree; never divide by zero"},
                "timing_scope": "CLI records loading and kernel seconds; driver records total subprocess wall time. No algorithmic novelty or superiority over established solvers is inferred from the enumeration baseline.",
                "preprocessing_timing": "Raw download, source parsing, preparation, and tests are outside timed trials. Subprocess wall time starts from a prepared JSON model, not a PDB or raw UAI archive.",
                "bounded_scope": "Conventional independent-factor best-first bound; float64 combinatorial bounds are not outward-rounded interval certificates.",
                "biological_scope": "Published discrete computational models only; no biological prediction or sequence optimization is tested."}
    write_json(run_dir / "manifest.json", manifest)
    (run_dir / "manifest.sha256").write_text(digest(run_dir / "manifest.json") + "  manifest.json\n")
    print(json.dumps({"manifest": str(run_dir / "manifest.json"), "trials": len(trials), "models": sum(len(c["states"]) for c in cohort["cases"])}))


def verify(run_dir):
    path = run_dir / "manifest.json"
    assert digest(path) == (run_dir / "manifest.sha256").read_text().split()[0]
    manifest = json.loads(path.read_text())
    assert digest(ROOT / "grader/rubric.json") == manifest["rubric_sha256"]
    assert digest(ROOT / manifest["data_manifest"]) == manifest["data_manifest_sha256"]
    for path, expected in manifest["source_snapshot"].items():
        assert digest(ROOT / path) == expected, f"Source changed after freeze: {path}"
    for item in manifest["input_files"]:
        assert digest(ROOT / item["path"]) == item["sha256"], item["path"]
    return manifest


def run(run_dir):
    manifest = verify(run_dir)
    raw = run_dir / "raw"
    raw.mkdir()
    records = []
    env = {key: os.environ[key] for key in ("PATH", "TMPDIR", "LANG") if key in os.environ}
    env.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "VECLIB_MAXIMUM_THREADS": "1", "PYTHONHASHSEED": "0"})
    for trial in manifest["trials"]:
        trial_path = raw / (trial["trial_id"] + ".json")
        command = [sys.executable, "-m", "experiments.inference", trial["model_path"], "--method", trial["method"], *trial["args"], "--output", str(trial_path)]
        started = time.perf_counter()
        record = {"trial_id": trial["trial_id"], "model_id": trial["model_id"], "method": trial["method"],
                  "repeat": trial["repeat"], "epsilon": trial.get("epsilon"), "started_at": now(), "command": command,
                  "system_loadavg_at_start": list(os.getloadavg()) if hasattr(os, "getloadavg") else None}
        with (raw / (trial["trial_id"] + ".stdout.txt")).open("w") as stdout, (raw / (trial["trial_id"] + ".stderr.txt")).open("w") as stderr:
            try:
                process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=trial["hard_timeout_seconds"])
                record.update({"exit_code": process.returncode, "driver_status": "exited"})
            except subprocess.TimeoutExpired:
                record.update({"exit_code": None, "driver_status": "hard_timeout"})
        record["subprocess_wall_seconds"] = time.perf_counter() - started
        record["finished_at"] = now()
        if trial_path.exists():
            record["result_path"] = str(trial_path.relative_to(ROOT))
            record["result_sha256"] = digest(trial_path)
            record["result"] = json.loads(trial_path.read_text())
        records.append(record)
        with (run_dir / "trials.jsonl").open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
        if len(records) % 10 == 0 or len(records) == len(manifest["trials"]):
            print(json.dumps({"completed": len(records), "total": len(manifest["trials"]), "latest_status": record.get("result", {}).get("status", record["driver_status"])}), flush=True)
    write_json(run_dir / "completion.json", {"completed_at": now(), "trials": len(records), "manifest_sha256": digest(run_dir / "manifest.json")})


def number(value):
    return -math.inf if value == "-inf" else float(value)


def summarize(run_dir):
    manifest = verify(run_dir)
    records = [json.loads(line) for line in (run_dir / "trials.jsonl").read_text().splitlines()]
    cohort = json.loads((ROOT / manifest["data_manifest"]).read_text())
    models, observations, failures = {}, [], []
    for record in records:
        models.setdefault(record["model_id"], []).append(record)
        if record["driver_status"] != "exited" or record.get("exit_code") != 0:
            failures.append({"trial_id": record["trial_id"], "driver_status": record["driver_status"], "exit_code": record.get("exit_code")})
    for model_id, rows in sorted(models.items()):
        by_method = {m: [r for r in rows if r["method"] == m] for m in ("eliminate", "batch", "brute", "bounded")}
        exact = {}
        timings = {}
        for method in ("eliminate", "batch", "brute"):
            completed = [r for r in by_method[method] if r.get("result", {}).get("status") == "complete"]
            if completed:
                exact[method] = number(completed[0]["result"]["log_z"])
                kernels = [r["result"]["kernel_elapsed_seconds"] for r in completed]
                timings[method] = {"count": len(completed), "kernel_median_seconds": statistics.median(kernels), "kernel_min_seconds": min(kernels), "kernel_max_seconds": max(kernels), "wall_median_seconds": statistics.median(r["subprocess_wall_seconds"] for r in completed)}
        reference = exact.get("eliminate")
        checks = {}
        for method, value in exact.items():
            if reference is not None:
                tol = 1e-8 + 1e-12 * max(abs(value), abs(reference)) if math.isfinite(reference) and math.isfinite(value) else 0.0
                checks[method] = {"agree": value == reference if not math.isfinite(value) or not math.isfinite(reference) else abs(value - reference) <= tol,
                                  "absolute_log_difference": abs(value - reference) if math.isfinite(value) and math.isfinite(reference) else None, "tolerance": tol}
        bounds = []
        for row in by_method["bounded"]:
            result = row.get("result", {})
            if "log_z_lower" not in result:
                bounds.append({"epsilon": row["epsilon"], "status": row["driver_status"], "contains_reference": None})
                continue
            lower, upper = number(result["log_z_lower"]), number(result["log_z_upper"])
            tol = 1e-8 + 1e-12 * abs(reference) if reference is not None and math.isfinite(reference) else 0.0
            bounds.append({"epsilon": row["epsilon"], "status": result["status"], "epsilon_met": result["epsilon_met"], "relative_omitted_mass_upper": result["relative_omitted_mass_upper"], "contains_reference": None if reference is None else lower - tol <= reference <= upper + tol,
                           "log_z_lower": result["log_z_lower"], "log_z_upper": result["log_z_upper"], "kernel_seconds": result["kernel_elapsed_seconds"], "leaves_evaluated": result["metrics"]["complete_assignments_evaluated"]})
        observations.append({"model_id": model_id, "log_z": {m: v if math.isfinite(v) else "-inf" for m, v in exact.items()}, "checks": checks, "timings": timings, "bounds": bounds})
    state_lookup = {o["model_id"]: o for o in observations}
    affinities = []
    for case in cohort["cases"]:
        states = [state_lookup[s["model_id"]] for s in case["states"]]
        values = [number(s["log_z"].get("eliminate", "-inf")) for s in states]
        score = values[0] - values[1] - values[2] if all(math.isfinite(v) for v in values) else None
        affinities.append({"case_id": case["case_id"], "pdb_id": case["pdb_id"], "modeled_log_kstar": score, "interpretation": "discrete source-first computational score, not measured affinity or a sequence optimum"})
    summary = {"campaign_id": manifest["campaign_id"], "summarized_at": now(), "planned_trials": len(manifest["trials"]), "recorded_trials": len(records), "models": len(observations), "cases": len(cohort["cases"]), "distinct_pdb_ids": len({c["pdb_id"] for c in cohort["cases"]}), "driver_failures": failures,
               "exact_checks": sum(len(o["checks"]) for o in observations), "exact_check_failures": sum(not c["agree"] for o in observations for c in o["checks"].values()),
               "bound_checks": sum(b["contains_reference"] is not None for o in observations for b in o["bounds"]), "bound_check_failures": sum(b["contains_reference"] is False for o in observations for b in o["bounds"]),
               "epsilon_target_met": {str(eps): sum(b.get("epsilon_met", False) for o in observations for b in o["bounds"] if b["epsilon"] == eps) for eps in (.68,.1,.01)},
               "observations": observations, "affinities": affinities}
    write_json(run_dir / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("observations", "affinities")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "run", "summarize"])
    parser.add_argument("--run-dir", type=Path, default=ROOT / "runs/campaign-001")
    args = parser.parse_args()
    {"freeze": freeze, "run": run, "summarize": summarize}[args.action](args.run_dir.resolve())
