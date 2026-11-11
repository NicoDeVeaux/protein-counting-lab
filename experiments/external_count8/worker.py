"""One cold invocation of a frozen external probability-ordering query."""

import argparse
from dataclasses import asdict
from fractions import Fraction
from itertools import product
import json
from math import prod
from pathlib import Path
import time

from experiments.certified_rank6.core import Factor, PartitionBounds, RatioBounds, certificate_gt
from experiments.partition_certificate7.core import model_payload
from .baseline import count_query
from .cnf import parse_dimacs, to_model
from .lean_native import check_certificates


MAX_EXPANSIONS = 4096
BATCH = 16
TABLE_CAP = 262144
SEARCH_SECONDS = 8.0


class TableCap(Exception):
    pass


def limited_ve(model):
    factors = list(model.factors)
    remaining = set(range(model.n))
    maximum = 1
    operations = 0
    while remaining:
        def cost(variable):
            return len({v for f in factors if variable in f.scope for v in f.scope})
        variable = min(remaining, key=lambda v: (cost(v), v))
        selected = [f for f in factors if variable in f.scope]
        scope = tuple(sorted({v for f in selected for v in f.scope} - {variable}))
        entries = 1 << len(scope)
        if entries > TABLE_CAP:
            raise TableCap(entries)
        maximum = max(maximum, entries)
        values = []
        for assignment in product((0, 1), repeat=len(scope)):
            env = dict(zip(scope, assignment))
            value = 0
            for bit in (0, 1):
                env[variable] = bit
                value += prod(f.value(env) for f in selected)
                operations += len(selected)
            values.append(value)
        factors = [f for f in factors if variable not in f.scope]
        factors.append(Factor(scope, tuple(values)))
        remaining.remove(variable)
    return prod(f.values[0] for f in factors), maximum, operations


def exact_direction(counts, variables):
    left = int(counts[0]) * (1 << variables[1])
    right = int(counts[1]) * (1 << variables[0])
    return "A" if left > right else "B" if left < right else "equal"


def bound_direction(producers, models):
    ratios = [RatioBounds(p.lower, p.upper, 1 << m.n, 1 << m.n)
              for p, m in zip(producers, models)]
    if certificate_gt(ratios[0], ratios[1]):
        return "A"
    if certificate_gt(ratios[1], ratios[0]):
        return "B"
    if all(p.lower == p.upper for p in producers):
        return exact_direction([p.lower for p in producers], [m.n for m in models])
    return None


def export_state(model, producer, splits):
    def cut(prefix=()):
        if prefix not in splits:
            return 0
        return [cut(prefix + (0,)), cut(prefix + (1,))]
    return {**model_payload(model), "cut": cut(),
            "lower": producer.lower, "upper": producer.upper}


def cut_nodes(tree):
    return 1 if tree == 0 else 1 + cut_nodes(tree[0]) + cut_nodes(tree[1])


def certified(models, executable, started):
    prepare = time.perf_counter()
    producers = [PartitionBounds(model) for model in models]
    splits = [set(), set()]
    preprocessing_seconds = time.perf_counter() - prepare
    root_exact = all(p.lower == p.upper for p in producers)
    expansions = 0
    search = time.perf_counter()
    direction = bound_direction(producers, models)
    while direction is None and expansions < MAX_EXPANSIONS:
        if time.perf_counter() - started >= SEARCH_SECONDS:
            break
        eligible = [i for i, p in enumerate(producers) if p.heap]
        if not eligible:
            break
        i = max(eligible, key=lambda index: Fraction(
            producers[index].upper - producers[index].lower, 1 << models[index].n))
        producer = producers[i]
        for _ in range(min(BATCH, MAX_EXPANSIONS - expansions)):
            if not producer.heap:
                break
            prefix = producer.heap[0][1]
            if producer.refine(1) != 1:
                raise AssertionError("one recorded split must refine one prefix")
            splits[i].add(prefix)
            expansions += 1
        direction = bound_direction(producers, models)
    search_seconds = time.perf_counter() - search
    certificate_start = time.perf_counter()
    certificates = [export_state(m, p, s) for m, p, s in zip(models, producers, splits)]
    payload = "".join(json.dumps(c, separators=(",", ":"), allow_nan=False) + "\n"
                      for c in certificates)
    generation_seconds = time.perf_counter() - certificate_start
    check_start = time.perf_counter()
    replies = check_certificates(executable, list(zip(models, certificates)), timeout=2.0)
    checking_seconds = time.perf_counter() - check_start
    if any(reply.status != "accepted" for reply in replies):
        raise AssertionError("producer certificate rejected: " + str(replies))
    # The decision is emitted only after both actual model enclosures are checked.
    direction = bound_direction(producers, models)
    return {"status": "solved" if direction is not None else "unresolved",
            "direction": direction, "expansions": expansions,
            "expansions_per_model": [p.expansions for p in producers],
            "bounds": [[str(p.lower), str(p.upper)] for p in producers],
            "root_exact": root_exact,
            "certificate_nodes": sum(cut_nodes(c["cut"]) for c in certificates),
            "certificate_bytes": len(payload.encode()),
            "certificate_generation_seconds": generation_seconds,
            "checking_seconds": checking_seconds,
            "preprocessing_seconds": preprocessing_seconds,
            "search_seconds": search_seconds,
            "accepted_certificates": [asdict(reply) for reply in replies],
            "certificates": certificates}


def solve(method, paths, ganak, checker):
    started = time.perf_counter()
    inputs = [parse_dimacs(Path(path).read_text("ascii")) for path in paths]
    variables = [cnf.n for cnf in inputs]
    if method == "ganak":
        result = count_query(ganak, paths, timeout_seconds=9.8)
        if result["status"] == "exact":
            result.update(status="solved", direction=exact_direction(result["counts"], variables))
    else:
        models = [to_model(cnf) for cnf in inputs]
        if method == "certified":
            result = certified(models, checker, started)
        elif method == "ve":
            counts, maxima, operations = [], [], []
            try:
                for model in models:
                    count, maximum, used = limited_ve(model)
                    counts.append(str(count)); maxima.append(maximum); operations.append(used)
            except TableCap as error:
                result = {"status": "table_cap", "direction": None,
                          "counts": counts, "requested_table_entries": error.args[0]}
            else:
                result = {"status": "solved", "counts": counts,
                          "direction": exact_direction(counts, variables),
                          "maximum_table_entries": maxima, "multiplications": operations}
        else:
            raise ValueError("unknown method")
    result.update(method=method, variables=variables,
                  worker_seconds=time.perf_counter() - started)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("certified", "ganak", "ve"), required=True)
    parser.add_argument("--inputs", nargs=2, required=True)
    parser.add_argument("--ganak", required=True)
    parser.add_argument("--checker", required=True)
    args = parser.parse_args()
    print(json.dumps(solve(args.method, args.inputs, args.ganak, args.checker), separators=(",", ":")))


if __name__ == "__main__":
    main()
