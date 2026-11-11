"""Seal and run the prospective external gate with supervised cold workers."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time

from .baseline import verify_binary


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
METHODS = ("certified", "ganak", "ve")
SOURCES = (
    "experiments/external_count8/__init__.py", "experiments/external_count8/cnf.py",
    "experiments/external_count8/select.py", "experiments/external_count8/worker.py",
    "experiments/external_count8/run.py", "experiments/external_count8/baseline.py",
    "experiments/external_count8/lean_native.py", "experiments/certified_rank6/core.py",
    "experiments/partition_certificate7/core.py", "experiments/partition_certificate7/verify.py",
    "formal/campaign-007/lean/PartitionCertificate.lean", "formal/campaign-007/lean/Main.lean",
    "formal/campaign-007/lean/lean-toolchain", "grader/campaign-008/PROTOCOL.md",
    "grader/campaign-008/AMENDMENT-001.md", "experiments/external_count8/COHORT.json",
    "experiments/external_count8/baseline-provenance.json",
    "experiments/external_count8/NATIVE_BUILD.json",
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal(ganak, checker):
    return {"files": {name: digest(ROOT / name) for name in SOURCES},
            "ganak_binary_sha256": verify_binary(ganak), "checker_binary_sha256": digest(checker)}


def clean_text(value, replacements):
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [clean_text(v, replacements) for v in value]
    if isinstance(value, dict):
        return {k: clean_text(v, replacements) for k, v in value.items()}
    return value


def invoke(command, replacements):
    start = time.perf_counter()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        return {"status": "timeout", "direction": None,
                "seconds": time.perf_counter() - start, "stdout": clean_text(stdout, replacements),
                "stderr": clean_text(stderr, replacements)}
    seconds = time.perf_counter() - start
    if process.returncode:
        return {"status": "error", "direction": None, "returncode": process.returncode,
                "seconds": seconds, "stdout": clean_text(stdout, replacements),
                "stderr": clean_text(stderr, replacements)}
    try:
        result = json.loads(stdout)
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError("worker result is not a status record")
    except ValueError:
        return {"status": "malformed_output", "direction": None, "seconds": seconds,
                "stdout": clean_text(stdout, replacements), "stderr": clean_text(stderr, replacements)}
    result["seconds"] = seconds
    if stderr:
        result["stderr"] = stderr
    return clean_text(result, replacements)


def run(args):
    expected = json.loads((HERE / "SOURCE_SEAL.json").read_text())
    if seal(args.ganak, args.checker) != expected:
        raise ValueError("source, cohort or binary changed after prospective seal")
    cohort = json.loads((HERE / "COHORT.json").read_text())
    members = {row["member"]: row for row in cohort["selected"]}
    if len(members) != 12 or len(cohort["queries"]) != 6:
        raise ValueError("frozen cohort must contain twelve inputs and six queries")
    for member in members.values():
        if digest(args.inputs / member["local_filename"]) != member["sha256"]:
            raise ValueError("input bytes differ from selected source")
    args.output.mkdir(parents=True, exist_ok=False)
    args.private.mkdir(parents=True, exist_ok=False)
    replacements = [(str(ROOT), "$REPO"), (str(args.inputs.resolve()), "$COHORT"),
                    (str(args.checker), "$CHECKER"), (str(args.ganak), "$GANAK"),
                    (str(args.checker.resolve()), "$CHECKER"),
                    (str(args.ganak.resolve()), "$GANAK"), (str(Path.home()), "$HOME")]
    records = []
    start = time.monotonic()
    for index, pair in enumerate(cohort["queries"], 1):
        for repetition in range(3):
            order = METHODS[repetition:] + METHODS[:repetition]
            for method in order:
                label = f"Q{index:02d}"
                if time.monotonic() - start >= 900:
                    result = {"status": "not_run_campaign_cap", "direction": None}
                else:
                    paths = [args.inputs / members[name]["local_filename"] for name in pair]
                    command = [sys.executable, "-B", "-m", "experiments.external_count8.worker",
                               "--method", method, "--inputs", *map(str, paths),
                               "--ganak", str(args.ganak), "--checker", str(args.checker)]
                    result = invoke(command, replacements)
                    certificates = result.pop("certificates", None)
                    if certificates is not None:
                        payload = "".join(json.dumps(c, separators=(",", ":"), allow_nan=False)
                                          + "\n" for c in certificates)
                        filename = f"{label}-rep{repetition}.cert"
                        (args.private / filename).write_text(payload)
                        result["certificate_file"] = filename
                        result["certificate_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
                result.update(query=label, inputs=pair, method=method, repetition=repetition)
                records.append(result)
                (args.output / "RAW_RESULTS.json").write_text(json.dumps(records, indent=2) + "\n")
                print(f"{label} rep={repetition} {method}: {result['status']} "
                      f"seconds={result.get('seconds', 'not_run')}", flush=True)
    columns = ("query", "method", "status", "direction", "median_seconds", "expansions",
               "certificate_nodes", "certificate_bytes", "checking_seconds", "search_seconds",
               "preprocessing_seconds", "certificate_generation_seconds", "root_exact")
    with (args.output / "RESULTS.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for index in range(1, 7):
            for method in METHODS:
                group = [r for r in records if r["query"] == f"Q{index:02d}" and r["method"] == method]
                first = group[0]
                row = {key: first.get(key) for key in columns}
                variants = {(r["status"], r.get("direction")) for r in group}
                if len(variants) != 1:
                    row["status"] = "mixed_outcomes"
                    row["direction"] = None
                values = [r["seconds"] for r in group if "seconds" in r]
                row["median_seconds"] = statistics.median(values) if len(values) == 3 else None
                for key in ("checking_seconds", "search_seconds", "preprocessing_seconds",
                            "certificate_generation_seconds"):
                    stages = [r[key] for r in group if key in r]
                    row[key] = statistics.median(stages) if len(stages) == 3 else None
                writer.writerow(row)
    (args.output / "SOURCE_SEAL.json").write_text(json.dumps(expected, indent=2) + "\n")
    print(f"rows={len(records)} campaign_seconds={time.monotonic() - start:.3f}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ganak", required=True, type=Path)
    parser.add_argument("--checker", required=True, type=Path)
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--private", type=Path)
    args = parser.parse_args()
    if args.seal:
        destination = HERE / "SOURCE_SEAL.json"
        with destination.open("x") as stream:
            stream.write(json.dumps(seal(args.ganak, args.checker), indent=2) + "\n")
        print("prospective source/cohort/binary seal written; no external counts run")
    else:
        if any(value is None for value in (args.inputs, args.output, args.private)):
            parser.error("measurement requires inputs, output and private evidence directories")
        run(args)


if __name__ == "__main__":
    main()
