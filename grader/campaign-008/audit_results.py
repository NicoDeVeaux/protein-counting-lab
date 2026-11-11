#!/usr/bin/env python3
"""Audit every external result, retained certificate and continuation criterion."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from itertools import product

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.external_count8.cnf import to_model, parse_dimacs as implementation_parse
from experiments.external_count8.lean_native import check_certificates
from oracle import expected_factor_tables, interval_order, parse_dimacs, probability_order

METHODS = ("certified", "ganak", "ve")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def integer(value):
    assert isinstance(value, str) and value.isascii() and value.isdecimal()
    return int(value)


def ganak_count(member):
    assert member["status"] == "exact" and member["returncode"] == 0
    lines = member["stdout"].splitlines()
    counts = [line.split()[-1] for line in lines if line.startswith("c s exact arb int ")]
    assert len(counts) == 1
    assert [line for line in lines if line.startswith("c s type ")] == ["c s type mc"]
    assert [line for line in lines if line.startswith("c s pac guarantees ")] == [
        "c s pac guarantees epsilon: 0 delta: 0"]
    count = integer(counts[0])
    assert integer(member["count"]) == count
    statuses = [line for line in lines if line.startswith("s ")]
    assert statuses == ["s UNSATISFIABLE" if count == 0 else "s SATISFIABLE"]
    return count


def inspect_tree(tree, allowed):
    assert type(tree) is list
    if len(tree) == 2 and tree[0] == "c":
        assert type(tree[1]) is int and tree[1] >= 0
    else:
        assert len(tree) == 4 and tree[0] == "b"
        assert type(tree[1]) is int and tree[1] in allowed
        inspect_tree(tree[2], allowed)
        inspect_tree(tree[3], allowed)


def tree_value(tree, assigned):
    if tree[0] == "c":
        return tree[1]
    return tree_value(tree[2 + assigned[tree[1]]], assigned)


def check_decision_tree_translation(target, payload):
    tables = expected_factor_tables(target)
    assert len(tables) == len(payload["factors"])
    checked = 0
    for (scope, values), tree in zip(tables, payload["factors"]):
        inspect_tree(tree, set(scope))
        for bits, expected in zip(product((0, 1), repeat=len(scope)), values):
            assert tree_value(tree, dict(zip(scope, bits))) == expected
            checked += 1
    return checked


def audit(results, inputs, private, checker):
    saved_seal = json.loads((results / "SOURCE_SEAL.json").read_text())
    current_seal = json.loads((ROOT / "experiments/external_count8/SOURCE_SEAL.json").read_text())
    assert saved_seal == current_seal
    for name, expected in saved_seal["files"].items():
        assert sha((ROOT / name).read_bytes()) == expected, name
    assert sha(checker.read_bytes()) == saved_seal["checker_binary_sha256"]
    cohort = json.loads((ROOT / "experiments/external_count8/COHORT.json").read_text())
    sources = {row["member"]: row for row in cohort["selected"]}
    targets, models = {}, {}
    for name, row in sources.items():
        data = (inputs / row["local_filename"]).read_bytes()
        assert sha(data) == row["sha256"]
        target = targets[name] = parse_dimacs(data.decode("ascii"))
        model = models[name] = to_model(implementation_parse(data.decode("ascii")))
        assert model.n == target.n
        assert tuple((f.scope, f.values) for f in model.key[1]) == expected_factor_tables(target)
    records = json.loads((results / "RAW_RESULTS.json").read_text())
    assert len(records) == 54
    expected_keys = {(f"Q{i:02d}", method, rep) for i in range(1, 7)
                     for method in METHODS for rep in range(3)}
    assert {(r["query"], r["method"], r["repetition"]) for r in records} == expected_keys
    assert len(expected_keys) == len(records)
    groups = {}
    known = {}
    certified_records = []
    requests = []
    certified_intervals = certificates = tree_checks = 0
    for record in records:
        query = int(record["query"][1:])
        pair = cohort["queries"][query - 1]
        assert record["inputs"] == pair
        groups.setdefault((record["query"], record["method"]), []).append(record)
        if record["status"] == "not_run_campaign_cap":
            assert record.get("direction") is None
            continue
        assert math.isfinite(record["seconds"]) and record["seconds"] >= 0
        if "worker_seconds" in record:
            assert 0 <= record["worker_seconds"] <= record["seconds"]
        if record["method"] == "ganak":
            counts = []
            for name, member in zip(pair, record.get("members", [])):
                if member["status"] == "exact":
                    count = ganak_count(member)
                    counts.append(count)
                    assert 0 <= count <= 1 << targets[name].n
                    if name in known:
                        assert known[name] == count, "conflicting exact reference counts"
                    known[name] = count
            if record["status"] == "solved":
                assert len(counts) == 2
                assert list(map(integer, record["counts"])) == counts
        elif record["method"] == "ve":
            for name, value in zip(pair, record.get("counts", [])):
                count = integer(value)
                assert 0 <= count <= 1 << targets[name].n
                if name in known:
                    assert known[name] == count, "VE/reference disagreement"
                known[name] = count
            if record["status"] == "solved":
                assert len(record["counts"]) == 2
                assert all(v <= 262144 for v in record["maximum_table_entries"])
        elif record["method"] == "certified" and record["status"] in ("solved", "unresolved"):
            assert record["expansions"] <= 4096
            assert sum(record["expansions_per_model"]) == record["expansions"]
            filename = record["certificate_file"]
            assert Path(filename).name == filename
            data = (private / filename).read_bytes()
            assert sha(data) == record["certificate_sha256"]
            assert len(data) == record["certificate_bytes"]
            lines = data.decode("ascii").splitlines()
            assert len(lines) == 2
            payloads = list(map(json.loads, lines))
            for name, payload, bounds, accepted in zip(pair, payloads, record["bounds"],
                                                       record["accepted_certificates"]):
                assert payload["n"] == targets[name].n
                tree_checks += check_decision_tree_translation(targets[name], payload)
                assert [str(payload["lower"]), str(payload["upper"])] == bounds
                assert accepted == {"status": "accepted", "lower": payload["lower"],
                                    "upper": payload["upper"]}
                requests.append((models[name], payload))
                certificates += 1
            lo_a, hi_a = map(integer, record["bounds"][0])
            lo_b, hi_b = map(integer, record["bounds"][1])
            direction = interval_order(lo_a, hi_a, targets[pair[0]].n,
                                       lo_b, hi_b, targets[pair[1]].n)
            wanted = None if direction == "unresolved" else "equal" if direction == "tie" else direction
            assert record["direction"] == wanted
            assert (record["status"] == "solved") == (wanted is not None)
            certified_records.append(record)
    replies = check_certificates(checker, requests, timeout=120)
    assert len(replies) == certificates and all(r.status == "accepted" for r in replies)
    for record in records:
        if record["status"] != "solved":
            continue
        pair = record["inputs"]
        if all(name in known for name in pair):
            expected = probability_order(known[pair[0]], targets[pair[0]].n,
                                         known[pair[1]], targets[pair[1]].n)
            assert record["direction"] == ("equal" if expected == "tie" else expected)
    for record in certified_records:
        for name, bounds in zip(record["inputs"], record["bounds"]):
            if name in known:
                low, high = map(integer, bounds)
                assert low <= known[name] <= high, "certified interval/reference disagreement"
                certified_intervals += 1
    rows = list(csv.DictReader((results / "RESULTS.csv").open(newline="")))
    assert len(rows) == 18
    for row in rows:
        group = groups[row["query"], row["method"]]
        times = [r["seconds"] for r in group if "seconds" in r]
        expected = statistics.median(times) if len(times) == 3 else None
        assert (float(row["median_seconds"]) if row["median_seconds"] else None) == expected
        outcomes = {(r["status"], r.get("direction")) for r in group}
        assert row["status"] == (next(iter(outcomes))[0] if len(outcomes) == 1 else "mixed_outcomes")
        expected_direction = next(iter(outcomes))[1] if len(outcomes) == 1 else None
        assert row["direction"] == (expected_direction or "")
        for field in ("checking_seconds", "search_seconds", "preprocessing_seconds",
                      "certificate_generation_seconds"):
            values = [r[field] for r in group if field in r]
            expected_stage = statistics.median(values) if len(values) == 3 else None
            assert (float(row[field]) if row[field] else None) == expected_stage
        for field in ("expansions", "certificate_nodes", "certificate_bytes"):
            assert (int(row[field]) if row[field] else None) == group[0].get(field)
        assert row["root_exact"] == (str(group[0]["root_exact"]) if "root_exact" in group[0] else "")
    passed = []
    for index in range(1, 7):
        label = f"Q{index:02d}"
        group = groups[label, "certified"]
        if not all(r["status"] == "solved" and r["direction"] in ("A", "B")
                   and not r["root_exact"] for r in group):
            continue
        pair = cohort["queries"][index - 1]
        if not all(name in known for name in pair):
            continue
        exact = [groups[label, method] for method in ("ganak", "ve")
                 if all(r["status"] == "solved" for r in groups[label, method])]
        if exact and statistics.median(r["seconds"] for r in group) <= min(
                statistics.median(r["seconds"] for r in baseline) for baseline in exact) / 2:
            passed.append(label)
    return {"raw_records": len(records), "summary_rows": len(rows),
            "exact_reference_instances": len(known), "native_certificates_rechecked": certificates,
            "source_tree_assignment_checks": tree_checks,
            "reference_enclosure_checks": certified_intervals, "gate_pass_queries": passed,
            "continuation_gate": "pass" if len(passed) >= 2 else "fail", "audit": "pass"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("private", type=Path)
    parser.add_argument("checker", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.results, args.inputs, args.private, args.checker)))


if __name__ == "__main__":
    main()
