"""Independently audit frozen bytes, raw-factor sums, and schedule gates."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import re
import statistics
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "grader"
EXPOSED = set()


def read(relative):
    EXPOSED.add(str(relative))
    return (ROOT / relative).read_bytes()


def load(relative):
    return json.loads(read(relative))


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def raw_parse(blob):
    tokens = blob.decode().split()
    assert tokens[0] == "MARKOV"
    n = int(tokens[1])
    dims = list(map(int, tokens[2:n + 2]))
    position = n + 2
    count = int(tokens[position])
    position += 1
    scopes = []
    for _ in range(count):
        arity = int(tokens[position])
        scopes.append(list(map(int, tokens[position + 1:position + 1 + arity])))
        position += 1 + arity
    tables = []
    for scope in scopes:
        size = int(tokens[position])
        position += 1
        assert size == math.prod(dims[v] for v in scope)
        values = np.array(tokens[position:position + size], dtype=np.longdouble)
        position += size
        assert np.all(np.isfinite(values)) and np.all(values >= 0)
        tables.append(values.reshape(tuple(dims[v] for v in scope)))
    assert position == len(tokens)
    return dims, scopes, tables


def metadata(text, key):
    start = re.search(r"^" + re.escape(key) + r"\s*$", text, re.M).end()
    return json.JSONDecoder().raw_decode(text[start:].lstrip())[0]


def raw_sum(dims, factors):
    total_states = math.prod(dims)
    total = np.longdouble(0)
    for first in range(0, total_states, 32768):
        ids = np.arange(first, min(total_states, first + 32768), dtype=np.int64)
        coords = np.unravel_index(ids, tuple(dims))
        weights = np.ones(len(ids), dtype=np.longdouble)
        for scope, table in factors:
            weights *= table[tuple(coords[v] for v in scope)]
        total += np.sum(weights, dtype=np.longdouble)
    assert np.isfinite(total) and total > 0
    return float(np.log(total)), str(total)


def value(x):
    return -math.inf if x == "-inf" else float(x)


def main():
    bundle_path = "runs/review-001/bundle_manifest.json"
    bundle_bytes = read(bundle_path)
    expected = read("runs/review-001/bundle_manifest.sha256").decode().split()[0]
    assert digest(bundle_bytes) == expected
    bundle = json.loads(bundle_bytes)
    integrity = []
    for item in bundle["files"]:
        blob = read(item["path"])
        integrity.append({"path": item["path"], "match": len(blob) == item["bytes"] and digest(blob) == item["sha256"]})
    assert all(i["match"] for i in integrity)
    rubric_hash = digest(read("grader/rubric.json"))
    assert rubric_hash == read("grader/rubric.sha256").decode().split()[0]
    manifest = load("runs/campaign-001/manifest.json")
    trials = [json.loads(line) for line in read("runs/campaign-001/trials.jsonl").decode().splitlines()]
    assert len({r["trial_id"] for r in trials}) == len(trials) == len(manifest["trials"])
    planned = {r["trial_id"]: r for r in manifest["trials"]}
    for row in trials:
        p = planned[row["trial_id"]]
        assert all(row[k] == p[k] for k in ["model_id", "method", "repeat"])
        assert row["epsilon"] == p.get("epsilon")
        assert row["result_sha256"] == digest(read(row["result_path"]))
        assert row["result"] == load(row["result_path"])
    assert manifest["rubric_sha256"] == rubric_hash
    assert min(r["started_at"] for r in trials) > manifest["frozen_at"]
    cohort = load("data/uai23_manifest.json")
    refs, conversion = {}, []
    for case in cohort["cases"]:
        source = read(case["local_path"])
        assert digest(source) == case["sha256"]
        assert hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest() == case["git_blob_sha"]
        with zipfile.ZipFile(io.BytesIO(source)) as archive:
            assert archive.testzip() is None
            uai_name = next(n for n in archive.namelist() if n.endswith(".uai"))
            dims, scopes, tables = raw_parse(archive.read(uai_name))
            query = list(map(int, archive.read(uai_name + ".query").split()))
            assert query[0] == len(query) - 1
            selectors = set(query[1:])
            summary = archive.read("uai_conversion_summary.txt").decode()
            state_maps = metadata(summary, "residue_id_to_conformationVariable_id")
        coverage = []
        conformations = [set(map(int, state.values())) for state in state_maps]
        assert set.union(*conformations).isdisjoint(selectors)
        assert selectors | set.union(*conformations) == set(range(len(dims)))
        assert all(not (a & b) for i, a in enumerate(conformations) for b in conformations[i + 1:])
        for state_index, state in enumerate(case["states"]):
            model = load(state["path"])
            old_vars = list(map(int, state_maps[state_index].values()))
            old_set = set(old_vars)
            indexes = [i for i, scope in enumerate(scopes) if old_set.intersection(scope)]
            assert indexes == model["metadata"]["source_factor_indices"]
            coverage.extend(indexes)
            allowed = {}
            for var in old_vars:
                keep = []
                for rotamer in range(dims[var]):
                    valid = True
                    for i in indexes:
                        scope = scopes[i]
                        if set(scope).intersection(selectors) and set(scope) - selectors == {var}:
                            loc = tuple(rotamer if v == var else 0 for v in scope)
                            valid &= tables[i][loc] > 0
                    if valid:
                        keep.append(rotamer)
                allowed[var] = keep
            assert allowed == {int(k): v for k, v in model["metadata"]["source_domain_indices"].items()}
            assert model["domains"] == [len(allowed[v]) for v in old_vars]
            independent = []
            max_error = 0.0
            entry_count = zero_count = 0
            for j, i in enumerate(indexes):
                scope = scopes[i]
                assert set(scope) <= old_set | selectors
                active = [v for v in scope if v in old_set]
                shape = tuple(len(allowed[v]) for v in active)
                source_table = np.empty(shape, dtype=np.longdouble)
                for flat, original in enumerate(itertools.product(*(allowed[v] for v in active))):
                    assignment = dict(zip(active, original))
                    loc = tuple(assignment[v] if v in assignment else 0 for v in scope)
                    source_table.flat[flat] = tables[i][loc]
                derived = model["factors"][j]
                assert derived["scope"] == [old_vars.index(v) for v in active]
                expected_logs = [None if x == 0 else math.log(float(x)) for x in source_table.flat]
                assert [x is None for x in expected_logs] == [x is None for x in derived["log_values"]]
                errors = [abs(a - b) for a, b in zip(expected_logs, derived["log_values"]) if a is not None]
                max_error = max(max_error, max(errors, default=0))
                entry_count += source_table.size
                zero_count += int(np.sum(source_table == 0))
                independent.append((derived["scope"], source_table))
            assert len(indexes) == len(model["factors"])
            assert model["constant_log_weight"] == 0
            ref, raw_z = raw_sum(model["domains"], independent)
            refs[model["model_id"]] = ref
            conversion.append({"model_id": model["model_id"], "state": model["metadata"]["state"], "states": math.prod(model["domains"]), "entries_checked": int(entry_count), "zeros_checked": int(zero_count), "max_log_conversion_error": max_error, "raw_longdouble_log_z": ref, "raw_longdouble_z": raw_z})
        assert sorted(coverage) == list(range(len(scopes)))
    exact, bounds, timing = [], [], defaultdict(lambda: defaultdict(list))
    for row in trials:
        result, mid = row["result"], row["model_id"]
        assert result["model_id"] == mid
        ref = refs[mid]
        tol = 1e-8 + 1e-12 * abs(ref)
        timing[row["method"]][mid].append((result["kernel_elapsed_seconds"], row["subprocess_wall_seconds"]))
        if row["method"] != "bounded":
            estimate = value(result["log_z"])
            exact.append({"trial_id": row["trial_id"], "model_id": mid, "method": row["method"], "difference": estimate - ref, "within_tolerance": abs(estimate - ref) <= tol})
        else:
            lo, hi = value(result["log_z_lower"]), value(result["log_z_upper"])
            residual = value(result["log_residual_mass_upper"])
            implied = 0.0 if residual == -math.inf else math.exp(residual - hi)
            bounds.append({"trial_id": row["trial_id"], "model_id": mid, "epsilon": row["epsilon"], "status": result["status"], "strict_contains_raw_reference": lo <= ref <= hi, "within_tolerance_contains": lo - tol <= ref <= hi + tol, "lower_minus_reference": lo - ref, "upper_minus_reference": hi - ref, "relative_bound_formula_error": implied - result["relative_omitted_mass_upper"], "epsilon_met": result["epsilon_met"], "leaves": result["metrics"]["complete_assignments_evaluated"]})
    median = {method: {mid: {"kernel": statistics.median(x[0] for x in vals), "wall": statistics.median(x[1] for x in vals)} for mid, vals in models.items()} for method, models in timing.items()}
    ratios = []
    for mid in refs:
        ratios.append({"model_id": mid, "batch_over_eliminate_kernel": median["batch"][mid]["kernel"] / median["eliminate"][mid]["kernel"], "batch_over_eliminate_wall": median["batch"][mid]["wall"] / median["eliminate"][mid]["wall"]})
    schedule = load("runs/eth-schedule-001/results.json")
    schedule_manifest = load("runs/eth-schedule-001/manifest.json")
    schedule_checks = []
    for beta in schedule_manifest["betas"]:
        first = None
        certificates = []
        for nu in range(1, 100):
            low, high = max(5, 2 ** (nu - 1) + 1), 2 ** nu
            found = None
            for t in range(math.isqrt(max(0, low - 1)) + 1, math.isqrt(high - 1) + 2):
                candidate = max(low, (t - 1) ** 2 + 1, 4 * nu ** 4, 768 * nu * (beta + 3) * t)
                if (beta + 3) * t >= 32 and candidate <= min(high, t * t):
                    found = candidate
                    break
            certificates.append({"nu": nu, "lambda_low": low, "lambda_high": high, "first_candidate": found})
            if found is not None:
                first = found
                break
        reported = next(x for x in schedule["first_all_necessary_gates"] if x["beta"] == beta)
        assert first == reported["lambda"]
        root = math.isqrt(first)
        params = {"lambda": first, "nu": (first - 1).bit_length(), "beta": beta, "r": root // ((first - 1).bit_length() ** 2), "Q": first // (128 * (first - 1).bit_length()), "R": (beta + 3) * (root + (root * root != first))}
        assert all(params[k] == reported[k] for k in params)
        schedule_checks.append({"parameters": params, "matches_reported": True, "independent_square_root_block_certificate": certificates})
    for obs in schedule["observations"]:
        n = int(obs.get("N", obs.get("n", 0)))
        if n == 0:
            continue
        lam = (n - 1).bit_length()
        nu = (lam - 1).bit_length()
        root = math.isqrt(lam)
        assert obs["lambda"] == lam and obs["nu"] == nu
        assert obs["r"] == root // (nu * nu)
        assert obs["Q"] == lam // (128 * nu)
        assert obs["R"] == (obs["beta"] + 3) * (root + (root * root != lam))
    first_r = next(max(5, 2 ** (nu - 1) + 1, 4 * nu ** 4) for nu in range(1, 100) if max(5, 2 ** (nu - 1) + 1, 4 * nu ** 4) <= 2 ** nu)
    assert first_r == schedule["first_r_gate"]["lambda"]
    status = Counter(r["result"]["status"] for r in trials)
    save("audit_results.json", {"recorded_at_utc": datetime.now(timezone.utc).isoformat(), "bundle_sha256": expected, "bundle_files_verified": len(integrity), "bundle_bytes_verified": sum(i["bytes"] for i in bundle["files"]), "rubric_sha256": rubric_hash, "trials_verified": len(trials), "trial_statuses": dict(status), "source_conversion": conversion, "independent_exact_checks": exact, "independent_bound_checks": bounds, "timing_medians": median, "timing_ratios": ratios, "schedule": schedule_checks, "first_r_gate_lambda": first_r, "exposed_paths": sorted(EXPOSED), "arithmetic": {"numpy": np.__version__, "longdouble_bits": int(np.finfo(np.longdouble).nmant), "note": "On this Apple platform longdouble may equal float64; inspect this field. Raw-factor product/sum is independent but not an interval certificate."}})
    print(json.dumps({"bundle_files_verified": len(integrity), "trials": len(trials), "models": len(refs), "entries_checked": sum(x["entries_checked"] for x in conversion), "exact_checks": len(exact), "exact_failures": sum(not x["within_tolerance"] for x in exact), "bounds": len(bounds), "bounds_outside_tolerance": sum(not x["within_tolerance_contains"] for x in bounds), "bounds_not_strictly_containing": sum(not x["strict_contains_raw_reference"] for x in bounds), "longdouble_mantissa": int(np.finfo(np.longdouble).nmant), "first_r_gate_lambda": first_r, "first_all_gates": [x["parameters"] for x in schedule_checks]}))


if __name__ == "__main__":
    main()
