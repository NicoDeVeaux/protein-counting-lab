"""Independently check raw score ledgers, primary decisions and contextual statistics."""

import hashlib
import itertools
import json
import math
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent


def read(path):
    return json.loads((ROOT / path).read_text())


def lines(path):
    return [json.loads(row) for row in (ROOT / path).read_text().splitlines()]


def error(actual, expected):
    return abs(Decimal.from_float(actual) - Decimal(expected))


def direction(value, tolerance):
    return "positive" if value > tolerance else "negative" if value < -tolerance else "unresolved"


def centered_ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        for position in order[i:j]:
            result[position] = i + j - len(values)
        i = j
    assert sum(result) == 0
    return result


def correlation(x, y):
    x, y = centered_ranks(x), centered_ranks(y)
    denominator = sum(v * v for v in x) * sum(v * v for v in y)
    return sum(a * b for a, b in zip(x, y)) / math.sqrt(denominator) if denominator else None


def interval(values):
    ordered = sorted(value for value in values if value is not None)

    def quantile(q):
        index = (len(ordered) - 1) * q
        low = math.floor(index)
        high = math.ceil(index)
        return ordered[low] + (ordered[high] - ordered[low]) * (index - low)

    return {"percentile_95": [quantile(.025), quantile(.975)] if ordered else None,
            "defined_resamples": len(ordered), "undefined_resamples": len(values) - len(ordered)}


def main():
    activation = read("prepared/campaign-005/ACTIVATION.json")
    for entry in activation["files"]:
        path = ROOT / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], entry["path"]
        assert path.stat().st_size == entry["bytes"]
    plan = read(activation["plan"])
    refs = lines("grader/campaign-005/reference_states.jsonl")
    reference = read("grader/campaign-005/references.json")
    states = lines("runs/campaign-005/states.jsonl")
    attempts = lines("runs/campaign-005/attempts.jsonl")
    queries = lines("runs/campaign-005/queries.jsonl")
    scheduled = [(query, slot) for query in plan["selected_unique_variants"] for slot in query["slots"]]
    assert len(states) == len(attempts) == len(refs) == len(scheduled) == 78
    maxima = {key: Decimal(0) for key in ("log_z", "minimum_energy", "gmec_log_weight", "log_effective_conformations")}
    state_rows = []
    for (query, slot), actual, attempt, oracle in zip(scheduled, states, attempts, refs, strict=True):
        for key in ("version", "state", "matrix_member", "domains", "matrix_sha256", "assignments"):
            assert actual[key] == attempt[key] == slot[key]
        assert actual["variant"] == attempt["variant"] == oracle["variant"] == query["variant"]
        assert actual["status"] == "complete" and attempt["status"] == "started" and oracle["status"] == "ok"
        assert actual["config_member"] == attempt["config_member"] == oracle["configuration"] == query["config_member"]
        assert oracle["domains"] == slot["domains"]
        ref, result = oracle["reference"], actual["result"]
        assert ref["cartesian"] == ref["finite_support"] == result["assignments"] == slot["assignments"]
        with localcontext() as context:
            context.prec = 90
            rt = Fraction.from_float(float.fromhex(activation["rt_hex"]))
            minimum = Fraction(int(ref["emin_numerator"]), int(ref["emin_denominator"]))
            gmec = -minimum / rt
            expected = {"log_z": ref["logz_decimal"], "minimum_energy": ref["emin_decimal"],
                        "gmec_log_weight": str(Decimal(gmec.numerator) / Decimal(gmec.denominator)),
                        "log_effective_conformations": ref["log_effective_decimal"]}
            errors = {key: error(result[key], value) for key, value in expected.items()}
        for key, value in errors.items():
            maxima[key] = max(maxima[key], value)
            assert value < Decimal("1e-8"), (query["variant"], key, value)
        state_rows.append({"variant": query["variant"], "version": slot["version"], "state": slot["state"],
                           "errors": {key: str(value) for key, value in errors.items()}})
    precision = reference["precision_checks"]
    assert len(precision) == 12
    grouped = {(row["version"], row["state"], row["precision"]): row["reference"] for row in precision}
    precision_difference = Decimal(0)
    for version in ("wild_type", "mutant"):
        for state in ("complex", "protein", "ligand"):
            a, b = grouped[version, state, 60], grouped[version, state, 90]
            for key in ("logz_decimal", "log_effective_decimal"):
                precision_difference = max(precision_difference, abs(Decimal(a[key]) - Decimal(b[key])))
    assert precision_difference < Decimal("1e-50")
    query_refs = {row["variant"]: row["reference"] for row in reference["query_references"]}
    query_errors, primary_rows = [], []
    mapping = {"delta_log_k_ensemble": "delta_ensemble", "delta_log_k_gmec": "delta_gmec",
               "delta_log_k_ensemble_correction": "delta_correction"}
    assert len(queries) == len(query_refs) == 13
    for actual, selected in zip(queries, plan["selected_unique_variants"], strict=True):
        assert actual["variant"] == selected["variant"] and actual["status"] == "complete"
        assert actual["score_error"] is None
        row = query_refs[actual["variant"]]
        errors = {key: error(actual["scores"][key], row[value]) for key, value in mapping.items()}
        assert all(value < Decimal("1e-7") for value in errors.values())
        query_errors.extend(errors.values())
        ensemble, gmec = Decimal(row["delta_ensemble"]), Decimal(row["delta_gmec"])
        ds = {"ensemble": direction(ensemble, Decimal("1e-7")), "gmec": direction(gmec, Decimal("1e-7"))}
        primary_rows.append({"variant": actual["variant"], "delta_ensemble": str(ensemble), "delta_gmec": str(gmec),
                             "correction": row["delta_correction"], "directions": ds,
                             "reversed": set(ds.values()) == {"positive", "negative"}})
    pairs = []
    for a, b in itertools.combinations(primary_rows, 2):
        ds = {method: direction(Decimal(a[f"delta_{method}"]) - Decimal(b[f"delta_{method}"]), Decimal("2e-7"))
              for method in ("ensemble", "gmec")}
        status = "unresolved" if "unresolved" in ds.values() else "reversed" if len(set(ds.values())) == 2 else "concordant"
        pairs.append({"variants": [a["variant"], b["variant"]], "directions": ds, "status": status})
    analysis = read("outputs/campaign-005-analysis.json")
    assert analysis["pairwise_orders"] == pairs
    assert analysis["primary"]["direction_reversals"] == sum(row["reversed"] for row in primary_rows)
    pair_counts = Counter(row["status"] for row in pairs)
    assert analysis["primary"]["pairwise_order_status"] == {
        status: pair_counts[status] for status in ("concordant", "reversed", "unresolved")
    }
    labels = read("data/campaign-005/source_discovery/kras_S2_labels.json")
    by_source = {row["source_row"]: row for row in labels["rows"]}
    contextual = []
    for row in analysis["points"]:
        source = by_source[row["source_row"]]
        for key in ("experimental_kd_um_raw", "experimental_relative_binding_percent_raw"):
            assert row[key] == source[key]
        if row["stratum"] == "Fridman-relative-binding-context":
            contextual.append(row)
    if not contextual:
        contextual = [row for row in analysis["points"] if not row["experimental_kd_um_raw"]]
    assert len(contextual) == 8
    y = [Decimal(row["experimental_relative_binding_percent_raw"]) for row in contextual]
    xs = {method: [Decimal(query_refs[row["variant"]][f"delta_{method}"]) for row in contextual]
          for method in ("ensemble", "gmec")}
    stats = {}
    rng = np.random.default_rng(2026110905)
    indexes = rng.integers(0, 8, size=(10000, 8))
    boots = {}
    for method, values in xs.items():
        rho = correlation(values, y)
        xr, yr = centered_ranks(values), centered_ranks(y)
        observed = abs(sum(a * b for a, b in zip(xr, yr)))
        count = sum(abs(sum(a * b for a, b in zip(xr, perm))) >= observed for perm in itertools.permutations(yr))
        bootstrap = [correlation([values[i] for i in idx], [y[i] for i in idx]) for idx in indexes]
        boots[method] = bootstrap
        stats[method] = {"n": 8, "spearman_rho": rho, "nominal_two_sided_permutation_p": count / math.factorial(8),
                         "permutations": math.factorial(8), "bootstrap": interval(bootstrap)}
        expected = analysis["Fridman_relative_binding_context"][method]
        assert abs(expected["spearman_rho"] - rho) < 1e-12
        assert expected["nominal_two_sided_permutation_p"] == stats[method]["nominal_two_sided_permutation_p"]
        for a, b in zip(expected["bootstrap"]["percentile_95"], stats[method]["bootstrap"]["percentile_95"], strict=True):
            assert abs(a - b) < 1e-12
    paired = [a - b if a is not None and b is not None else None for a, b in zip(boots["ensemble"], boots["gmec"])]
    stats["paired_rho_difference_bootstrap"] = interval(paired)
    expected = analysis["Fridman_relative_binding_context"]["paired_rho_difference_bootstrap"]
    assert all(abs(a - b) < 1e-12 for a, b in zip(expected["percentile_95"], stats["paired_rho_difference_bootstrap"]["percentile_95"]))
    completion = read("runs/campaign-005/completion.json")
    controller = read("runs/campaign-005-control/completion.json")
    startup = read("runs/campaign-005/startup.json")
    assert controller["returncode"] == 0 and not controller["timed_out"]
    assert completion["assignments"] == sum(row["assignments"] for row in states) == 3677224
    assert not completion["inference_cache_reuse"]
    assert startup["activation_sha256"] == controller["activation_sha256"] == reference["activation_sha256"]
    summary = {"all_frozen_inputs_rehash": True, "state_slots": 78, "query_slots": 13, "attempt_slots": 78,
               "missing_extra_retried_slots": 0, "assignments": 3677224,
               "maximum_state_errors": {key: str(value) for key, value in maxima.items()},
               "maximum_query_error": str(max(query_errors)), "smallest_case_60_90_maximum_difference": str(precision_difference),
               "maximum_reference_tail_logz_error_bound": str(max(Decimal(row["reference"]["tail_logz_error_upper_bound"]) for row in refs)),
               "direction_reversals": sum(row["reversed"] for row in primary_rows),
               "pairwise_orders": {status: pair_counts[status] for status in ("concordant", "reversed", "unresolved")},
               "correction_range": [str(min(Decimal(row["correction"]) for row in primary_rows)), str(max(Decimal(row["correction"]) for row in primary_rows))],
               "reported_batch_exponential_underflows": sum(row["result"]["batch_exp_underflows"] for row in states),
               "longdouble_mantissa_bits_observed": sorted(set(row["result"]["longdouble_mantissa_bits"] for row in states)),
               "worker_wall_seconds": completion["wall_seconds"], "controller_outer_wall_seconds": controller["wall_seconds"],
               "maximum_observed_worker_self_lifetime_peak_rss_bytes": max(row["worker_lifetime_peak_rss_bytes"] for row in states),
               "independent_reference_wall_seconds": reference["wall_seconds"],
               "biological_gate": "FAILED direct match; contextual transfer only; 5Kd rows remain unpooled and unresolved."}
    result = {"summary": summary, "state_errors": state_rows, "primary": primary_rows, "pairwise_orders": pairs,
              "independent_contextual_statistics": stats,
              "qualifications": ["No experiment scoring/analysis code imported.", "Rank implementations differ; NumPy PRNG is shared only to reproduce frozen bootstrap indices.",
                                 "All raw finite energy assignments remain positive in the mathematical target; reported floating underflows are numerical tails, not hard support zeros.",
                                 "High precision and bounded exponential tails are numerical evidence; this is not a directed-rounding interval certificate for a physical model."]}
    (OUT / "results_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
