#!/usr/bin/env python3
"""Cold-process, bounded campaign-006 benchmark; protocol must be sealed first."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.certified_rank6.core import RankController, exact_panel
from experiments.certified_rank6.fixtures import CASE_NAMES, input_profile, make_case


METHODS = ("adaptive", "fixed", "ve", "enumeration")
SOURCES = ("experiments/certified_rank6/core.py", "experiments/certified_rank6/fixtures.py",
           "scripts/campaign6_benchmark.py", "grader/campaign-006/PROTOCOL.md",
           "grader/campaign-006/AMENDMENT-001.md")


def source_seal():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def worker(case, method):
    start = time.perf_counter_ns()
    candidates = make_case(case)
    if method in ("adaptive", "fixed"):
        result = RankController(candidates).run(method=method)
    else:
        result = exact_panel(candidates, method)
    elapsed = (time.perf_counter_ns() - start) / 1e9
    # Inventory is reported separately and excluded from algorithm timings for every method.
    result["case"] = case
    result["seconds"] = elapsed
    result["input"] = input_profile(candidates)
    return result


def run_campaign(output):
    seal = ROOT / "experiments/certified_rank6/SOURCE_SEAL.json"
    if not seal.is_file() or json.loads(seal.read_text()) != source_seal():
        raise SystemExit("seal the frozen protocol, generator and implementation before timing")
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    records, witnesses = [], []
    for case in CASE_NAMES:
        for repetition in range(3):
            methods = METHODS[repetition:] + METHODS[:repetition]
            for method in methods:
                if time.monotonic() - start > 600:
                    raise SystemExit("campaign exceeded prospective ten-minute cap")
                command = [sys.executable, "-B", str(Path(__file__).resolve()),
                           "--worker", case, method]
                try:
                    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                               timeout=30, check=True)
                    result = json.loads(completed.stdout)
                except subprocess.TimeoutExpired:
                    result = {"case": case, "method": method, "status": "timeout", "winner": None}
                except subprocess.CalledProcessError as failure:
                    raise RuntimeError(f"{case}/{method}: {failure.stderr}") from failure
                result["repetition"] = repetition
                for witness in result.pop("witnesses", []):
                    witnesses.append([case, method, repetition, *witness])
                records.append(result)
                print(f"{case} {method} rep={repetition} {result['status']} "
                      f"seconds={result.get('seconds', 'timeout')}", flush=True)
                # Preserve every completed invocation even if a later process fails.
                (output / "RAW_RESULTS.json").write_text(json.dumps(records, indent=2) + "\n")
    fields = ["case", "method", "status", "winner", "median_seconds", "expansions",
              "bound_evaluations", "unique_states", "state_uses", "certification_calls",
              "all_partitions_exact", "work", "max_endpoint_bits", "factor_entries",
              "coefficient_bits", "coefficient_bits_sum", "binary_variables_per_state", "tolerance_met"]
    fields += ["exact_leaf_evaluations", "resolved_assignments"]
    with (output / "RESULTS.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for case in CASE_NAMES:
            for method in METHODS:
                group = [r for r in records if r["case"] == case and r["method"] == method]
                if len({(r["status"], r.get("winner")) for r in group}) != 1:
                    raise AssertionError("nondeterministic status or winner")
                row = {key: group[0].get(key) for key in fields}
                row.update({key: group[0].get("input", {}).get(key)
                            for key in fields if key in group[0].get("input", {})})
                seconds = [r["seconds"] for r in group if "seconds" in r]
                row["median_seconds"] = statistics.median(seconds) if len(seconds) == 3 else None
                writer.writerow(row)
    with (output / "WITNESSES.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["case", "method", "repetition", "aNL", "aNU", "aDL", "aDU",
                         "bNL", "bNU", "bDL", "bDU"])
        writer.writerows(witnesses)
    (output / "SOURCE_SEAL.json").write_text(json.dumps(source_seal(), indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", nargs=2, metavar=("CASE", "METHOD"))
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/certified_rank6/results")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(*args.worker)))
    elif args.seal:
        destination = ROOT / "experiments/certified_rank6/SOURCE_SEAL.json"
        if destination.exists():
            raise SystemExit("refusing to replace existing prospective seal")
        destination.write_text(json.dumps(source_seal(), indent=2) + "\n")
        print("prospective source seal created; no timings run")
    else:
        run_campaign(args.output)


if __name__ == "__main__":
    main()
