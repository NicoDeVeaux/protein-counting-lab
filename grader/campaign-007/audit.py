#!/usr/bin/env python3
"""Independently audit source translation and actual producer certificates."""

import argparse
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.certified_rank6.core import Factor, Model
from experiments.certified_rank6.fixtures import make_case
from experiments.partition_certificate7 import core
from oracle import (Table, Target, deterministic_targets, partition, parsed_weight,
                    seeded_targets, table_cut_bounds, weight)


def source_model(target):
    return Model(target.n, tuple(Factor(f.scope, f.values) for f in target.factors))


def leaves(cut, prefix=()):
    if cut == 0:
        yield prefix
    else:
        yield from leaves(cut[0], prefix + (0,))
        yield from leaves(cut[1], prefix + (1,))


def inspect(target, model, certificate):
    assert certificate["n"] == target.n
    prefixes = list(leaves(certificate["cut"]))
    assert all(len(prefix) <= target.n for prefix in prefixes)
    for assignment in product((0, 1), repeat=target.n):
        assert sum(assignment[:len(p)] == p for p in prefixes) == 1, "cut coverage"
        assert parsed_weight(certificate["factors"], assignment) == weight(target, assignment), \
            "source table to decision tree translation"
    endpoints = certificate["lower"], certificate["upper"]
    assert endpoints == table_cut_bounds(target, certificate["cut"]), "constructed cut bounds"
    exact = partition(target)
    assert endpoints[0] <= exact <= endpoints[1], "independent enclosure"
    if all(len(prefix) == target.n for prefix in prefixes):
        assert endpoints == (exact, exact), "fully refined cut must be exact"
    assert core.check_binding(model, certificate), "valid source binding rejected"


def binding_controls():
    model = Model(1, (Factor((0,), (1, 3)),))
    original = core.build_certificate(model, 1)
    bad = []
    for name, value in (("n", True), ("n", 1.0), ("lower", False), ("upper", 4.0),
                        ("cut", False), ("cut", 0.0), ("cut", [0]),
                        ("cut", [0, 0, 0]), ("cut", [[0, 0], 0])):
        changed = deepcopy(original)
        changed[name] = value
        bad.append(changed)
    for value in (["c", -1], ["c", True], ["c", 1.0], ["c", 0.5],
                  ["b", True, ["c", 1], ["c", 3]],
                  ["b", 1, ["c", 1], ["c", 3]],
                  ["b", 0, ["c", 1]], ["c", 1, 2]):
        changed = deepcopy(original)
        changed["factors"] = [value]
        bad.append(changed)
    changed = deepcopy(original)
    changed["factors"][0][2][1] += 1
    bad.append(changed)
    for change in (dict(original, extra=0), {k: v for k, v in original.items() if k != "cut"}):
        bad.append(change)
    assert all(not core.check_binding(model, value) for value in bad), "bad binding accepted"
    forged = deepcopy(original)
    forged["lower"] = forged["upper"] = 0
    assert core.check_binding(model, forged), "numeric validity belongs to Lean checker"
    return len(bad)


def source_mutants():
    original = (ROOT / "experiments/partition_certificate7/core.py").read_text()
    mutants = {
        "factor-row": ("factor.values[offset]", "factor.values[0]"),
        "completion-output": ("\"lower\": producer.lower, \"upper\": producer.upper",
                              "\"lower\": producer.lower // 2, \"upper\": producer.upper // 2"),
        "omitted-split": ("if prefix not in splits:", "if True:"),
    }
    target = Target(1, (Table((0,), (1, 3)),))
    model = source_model(target)
    caught = []
    for name, (before, after) in mutants.items():
        assert original.count(before) == 1, (name, "mutation target changed")
        module = types.ModuleType("mutant_" + name)
        exec(compile(original.replace(before, after), name, "exec"), module.__dict__)
        certificate = module.build_certificate(model, 1)
        try:
            inspect(target, model, certificate)
        except AssertionError:
            caught.append(name)
        else:
            raise AssertionError("independent audit missed source mutant: " + name)
    return caught


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-certificates", type=Path)
    args = parser.parse_args()
    cases = deterministic_targets() + list(seeded_targets())
    certificates = []
    targets = assignments = 0
    for name, target in cases:
        model = source_model(target)
        for budget in (0, 1, 3, 7, (1 << target.n) - 1):
            certificate = core.build_certificate(model, budget)
            inspect(target, model, certificate)
            if budget == (1 << target.n) - 1:
                assert certificate["lower"] == certificate["upper"] == partition(target)
            certificates.append(certificate)
            assignments += 1 << target.n
        targets += 1
    for case in ("concentrated8", "shared12", "independent_dense8"):
        for model in make_case(case)[0].models:
            target = Target(model.n, model.factors)
            for budget in (0, 1, 16):
                certificate = core.build_certificate(model, budget)
                inspect(target, model, certificate)
                certificates.append(certificate)
                assignments += 1 << target.n
            targets += 1
    rejected = binding_controls()
    mutants = source_mutants()
    if args.write_certificates:
        args.write_certificates.write_text("".join(json.dumps(value, separators=(",", ":"))
                                                  + "\n" for value in certificates))
    print(json.dumps({"target_cases": targets, "certificates": len(certificates),
                      "assignment_translation_checks": assignments,
                      "binding_rejections": rejected, "source_mutants_rejected": mutants,
                      "audit": "pass"}))


if __name__ == "__main__":
    main()
