#!/usr/bin/env python3
"""Drive the compiled Lean construction checker with independent controls."""

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.certified_rank6.fixtures import make_case
from experiments.partition_certificate7.core import build_certificate
from experiments.partition_certificate7.verify import LeanVerifier
from audit import inspect, source_model
from oracle import (Table, Target, deterministic_targets, full_cut, partial_cut,
                    seeded_targets, wire_certificate)


def main():
    tiny = deterministic_targets() + list(seeded_targets())
    independent, actual, bound_requests = [], [], []
    for name, target in tiny:
        model = source_model(target)
        for cut in (0, full_cut(target.n), *(partial_cut(target.n, i) for i in (1, 3, 7))):
            independent.append(wire_certificate(target, cut))
        for budget in (0, 1, 3, 7, (1 << target.n) - 1):
            certificate = build_certificate(model, budget)
            inspect(target, model, certificate)
            actual.append(certificate)
            bound_requests.append((model, certificate))
    for case in ("concentrated8", "shared12", "independent_dense8"):
        for model in make_case(case)[0].models:
            target = Target(model.n, model.factors)
            for budget in (0, 1, 16):
                certificate = build_certificate(model, budget)
                inspect(target, model, certificate)
                actual.append(certificate)
                bound_requests.append((model, certificate))

    good = {"n": 1, "factors": [["b", 0, ["c", 1], ["c", 3]]],
            "cut": [0, 0], "lower": 4, "upper": 4}
    controls = []
    def changed(name, key, value):
        record = deepcopy(good)
        record[key] = value
        controls.append((name, record))

    for name, value in (("negative_n", -1), ("fractional_n", 0.5), ("bool_n", True)):
        changed(name, "n", value)
    for name, value in (("negative_weight", ["c", -1]),
                        ("fractional_weight", ["c", 0.5]),
                        ("bool_weight", ["c", True]),
                        ("negative_index", ["b", -1, ["c", 1], ["c", 3]]),
                        ("fractional_index", ["b", 0.5, ["c", 1], ["c", 3]]),
                        ("out_of_range_index", ["b", 1, ["c", 1], ["c", 3]]),
                        ("missing_factor_child", ["b", 0, ["c", 1]]),
                        ("extra_factor_child", ["b", 0, ["c", 1], ["c", 3], ["c", 8]]),
                        ("extra_constant_field", ["c", 1, 2]),
                        ("wrong_factor_tag", ["x", 1])):
        changed(name, "factors", [value])
    for name, value in (("missing_cut_child", [0]), ("extra_cut_child", [0, 0, 0]),
                        ("depth_overflow", [[0, 0], 0]), ("nonzero_leaf", 1),
                        ("bool_leaf", False), ("fractional_leaf", 0.5),
                        ("string_leaf", "0")):
        changed(name, "cut", value)
    for name, key, value in (("forged_lower", "lower", 5),
                             ("forged_upper", "upper", 5),
                             ("negative_lower", "lower", -1),
                             ("fractional_upper", "upper", 4.5),
                             ("bool_upper", "upper", True)):
        changed(name, key, value)
    omitted = deepcopy(good)
    omitted.pop("cut")
    controls.extend((("missing_key", omitted), ("extra_key", dict(good, extra=1))))

    wrong_model = deepcopy(good)
    wrong_model["factors"] = [["b", 0, ["c", 2], ["c", 3]]]
    wrong_model["lower"] = wrong_model["upper"] = 5
    model = source_model(Target(1, (Table((0,), (1, 3)),)))
    raw_invalid = ["", "{", json.dumps(good)[:-1], json.dumps(good) + " trailing",
                   json.dumps(good) + " {}", "[]", "null"]

    with LeanVerifier() as verifier:
        valid_results = verifier.raw_batch(independent + actual)
        assert len(valid_results) == len(independent) + len(actual)
        for certificate, result in zip(independent + actual, valid_results):
            assert result.status == "accepted", (certificate, result)
            assert (result.lower, result.upper) == (certificate["lower"], certificate["upper"])
        bound_results = verifier.verify_batch(bound_requests)
        assert all(result.status == "accepted" for result in bound_results)
        rejected_results = verifier.raw_batch(record for _, record in controls)
        for (name, _), result in zip(controls, rejected_results):
            assert result.status in ("invalid", "rejected"), (name, result)
        assert all(result.status == "invalid" for result in verifier.raw_lines(raw_invalid))
        assert verifier.raw_batch([wrong_model])[0].status == "accepted"
        assert verifier.verify_batch([(model, wrong_model)])[0].status == "binding_mismatch"
        # Supplemental structural guard: this checks a root bound over 2^1000 states.
        huge = {"n": 1000, "factors": [], "cut": 0, "lower": 1 << 1000, "upper": 1 << 1000}
        huge_result = verifier.raw_batch([huge])[0]
        assert huge_result.status == "accepted" and huge_result.lower == 1 << 1000

        # Diagnose lexical normalization without assuming all JSON parsers reject it.
        normalized = json.dumps(good).replace('"n": 1', '"n": 1.0')
        duplicate = json.dumps(good).replace('"n": 1', '"n": 0, "n": 1')
        normalization = verifier.raw_lines([normalized, duplicate])

    summary = {"independent_cut_certificates": len(independent),
               "actual_producer_certificates": len(actual),
               "bound_bridge_acceptances": len(bound_results),
               "malformed_or_forged_rejections": len(controls),
               "raw_invalid_rejections": len(raw_invalid),
               "different_model_raw": "accepted_for_its_own_target",
               "different_model_expected_binding": "binding_mismatch",
               "supplemental_root_variable_count": 1000,
               "raw_integral_decimal_status": normalization[0].status,
               "raw_duplicate_key_status": normalization[1].status,
               "audit": "pass"}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
