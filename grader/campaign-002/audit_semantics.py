"""Audit stored representation, exact reductions and raw CPD selected entries."""

from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import itertools
import json
import lzma
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "grader/campaign-002"


def read(path):
    return json.loads((ROOT / path).read_text())


def factors(data):
    domains = data["domains"]
    result = []
    for factor in data["factors"]:
        scope = tuple(factor["scope"])
        a = np.asarray(factor["log_values"], dtype=object)
        v = np.array([-math.inf if x is None else float(x) for x in a.flat])
        result.append((scope, v.reshape(tuple(domains[i] for i in scope))))
    if "constant_log_weight" in data:
        v = data["constant_log_weight"]
        result.append(((), np.asarray(-math.inf if v is None else float(v))))
    return result


def identity(original, reduced, proof):
    source = factors(original)
    changes = {t["source_factor_index"]: t for t in proof["transformations"]}
    expected = []
    exact_entries = 0
    for index, (scope, values) in enumerate(source):
        if index not in changes:
            expected.append((scope, values))
            continue
        t = changes[index]
        kind = t["kind"]
        assert list(scope) == t["old_scope"]
        if kind == "constant_factor":
            assert np.all(values == values.flat[0])
            replacement = [((), np.asarray(values.flat[0]))]
        elif kind == "independent_of_first_axis":
            assert np.all(values == values[0, :])
            replacement = [((scope[1],), values[0, :])]
        elif kind == "independent_of_second_axis":
            assert np.all(values == values[:, :1])
            replacement = [((scope[0],), values[:, 0])]
        elif kind == "exact_binary_rational_additive_split":
            left = values[:, 0]
            origin = Fraction(float(values[0, 0]))
            right_exact = [Fraction(float(v)) - origin for v in values[0, :]]
            right = np.asarray([float(x) for x in right_exact])
            assert all(Fraction(float(v)) == e for v, e in zip(right, right_exact))
            for i, j in np.ndindex(values.shape):
                assert Fraction(float(left[i])) + right_exact[j] == Fraction(float(values[i, j]))
            replacement = [((scope[0],), left), ((scope[1],), right)]
        else:
            raise AssertionError(kind)
        exact_entries += values.size
        assert [list(s) for s, _ in replacement] == t["new_scopes"]
        expected.extend(replacement)
    assert original["domains"] == reduced["domains"]
    actual = factors(reduced)
    assert len(expected) == len(actual)
    assert all(s == a and np.array_equal(x, y) for (s, x), (a, y) in zip(expected, actual))
    return {"transformed_factors": len(changes), "entries_checked": exact_entries,
            "kinds": dict(Counter(t["kind"] for t in changes.values())), "domains_preserved": True}


def structure(data, stored):
    domains = data["domains"]
    fs = factors(data)
    edges = set(e for s, _ in fs for e in itertools.combinations(sorted(s), 2))
    graph = {i: set() for i in range(len(domains))}
    for a, b in edges:
        graph[a].add(b)
        graph[b].add(a)
    groups = []
    unseen = set(graph)
    while unseen:
        stack = [unseen.pop()]
        group = set(stack)
        while stack:
            i = stack.pop()
            for j in graph[i] & unseen:
                unseen.remove(j)
                group.add(j)
                stack.append(j)
        groups.append(group)
    max_arity = max((len(s) for s, _ in fs), default=0)
    cls = "high_order" if max_arity > 2 else ("edgeless" if not edges else ("pairwise_forest" if len(edges) == len(domains)-len(groups) else "pairwise_cyclic"))
    assert stored["graph_class"] == cls
    assert stored["primal_edges"] == len(edges)
    assert stored["components"] == len(groups)
    assert stored["domain_cardinalities"] == domains
    assert stored["factor_scopes"] == [list(s) for s, _ in fs]
    assert stored["factor_entries"] == [x.size for _, x in fs]
    peak, width = 1, 0
    for variable in stored["elimination_order"]:
        adjacent = graph.pop(variable)
        width = max(width, len(adjacent))
        peak = max(peak, math.prod(domains[i] for i in adjacent | {variable}))
        for a in adjacent:
            graph[a].discard(variable)
            graph[a].update(adjacent - {a})
    assert not graph
    assert width == stored["induced_width"]
    assert peak == stored["predicted_largest_intermediate_entries"]
    assert peak*8 == stored["predicted_largest_intermediate_bytes"]
    assert 2*peak*8 + sum(x.nbytes for _, x in fs) == stored["predicted_workspace_bytes"]
    assert stored["primal_density"] == (len(edges)*2/(len(domains)*(len(domains)-1)) if len(domains)>1 else 0)
    return {"variables": len(domains), "max_domain": max(domains, default=1), "edges": len(edges),
            "components": len(groups), "induced_width": width, "largest_table_bytes": peak*8,
            "nontrivial_variables": sum(d > 1 for d in domains), "joint_configurations": str(math.prod(domains)),
            "graph_class": cls, "factor_entries": sum(x.size for _, x in fs)}


def cpd_source(model, raw_path):
    first_aa = {}
    labels_by_position = {}
    unary_tokens = {}
    template = []
    with lzma.open(ROOT / raw_path, "rt", encoding="ascii") as source:
        for line in source:
            if line.startswith("Etmp"):
                template.append(line.split("=", 1)[1].strip())
            elif line.startswith("ROT::BKB"):
                _, label, token, second = line.split()
                p, aa, rot = label.rsplit("-", 2)
                first_aa.setdefault(p, aa)
                labels_by_position.setdefault(p, [])
                if aa == first_aa[p]:
                    labels_by_position[p].append(label)
                assert label not in unary_tokens
                unary_tokens[label] = token
    positions = sorted(labels_by_position, key=int)
    selected = [labels_by_position[p] for p in positions]
    assert model["metadata"]["source_position_ids"] == positions
    assert model["metadata"]["source_rotamer_labels"] == selected
    assert model["metadata"]["source_aa_assignment"] == first_aa
    assert model["domains"] == list(map(len, selected))
    assert len(template) == 1
    expected = lambda token: None if token == "1.0E38" else -float(token)
    assert model["constant_log_weight"] == expected(template[0])
    fs = {tuple(f["scope"]): list(np.asarray(f["log_values"], dtype=object).flat) for f in model["factors"]}
    lookup = {label: (i, v) for i, labels in enumerate(selected) for v, label in enumerate(labels)}
    counts = Counter()
    seen_pairs = set()
    for label, (i, v) in lookup.items():
        assert fs[(i,)][v] == expected(unary_tokens[label])
        counts["selected_BKB"] += 1
        counts["selected_BKB_sentinel"] += unary_tokens[label] == "1.0E38"
    unequal_columns = Counter()
    with lzma.open(ROOT / raw_path, "rt", encoding="ascii") as source:
        for line in source:
            if not line.strip() or line.startswith("Etmp"):
                continue
            kind, label, token, second = line.split()
            counts["source_" + kind] += 1
            unequal_columns[kind] += float(token) != float(second)
            if kind != "ROT::ROT":
                continue
            a, b = label.split("::")
            if a not in lookup or b not in lookup:
                continue
            i, vi = lookup[a]
            j, vj = lookup[b]
            if i > j:
                i, j, vi, vj = j, i, vj, vi
            coordinate = (i, j, vi, vj)
            assert coordinate not in seen_pairs
            seen_pairs.add(coordinate)
            assert fs[(i, j)][vi*model["domains"][j]+vj] == expected(token)
            counts["selected_pair"] += 1
            counts["selected_pair_sentinel"] += token == "1.0E38"
    assert len(seen_pairs) == sum(model["domains"][i]*model["domains"][j] for i, j in itertools.combinations(range(len(selected)), 2))
    assert len(fs) == len(selected)*(len(selected)+1)//2
    return {"raw_path": raw_path, "counts": dict(counts), "first_second_column_unequal_counts": dict(unequal_columns),
            "selected_domains_and_first_AA_match": True, "template_matches": True,
            "selected_entry_comparison": "Every selected source BKB/pair/template token checked against serialized data, with coordinate coverage and duplicates checked. Nonselected pair completeness relies on preserved worker source audit.",
            "target": "Stored binary64 logs from negative first-column raw energy; only exact token 1.0E38 becomes hard zero; SELF is not added."}


def main():
    manifest = read("runs/campaign-002/manifest.json")
    cpd = {x["model_id"]: x for x in read("data/campaign-002/cpd_manifest.json")["cases"]}
    rows = []
    for case in manifest["models"]:
        original = read(case["representations"][0]["files"][0]["path"])
        row = {"model_id": case["model_id"], "cohort": case["cohort"], "representations": []}
        for rep in case["representations"]:
            data = read(rep["files"][0]["path"])
            result = structure(data, rep["structure"])
            result["representation_id"] = rep["representation_id"]
            if rep["representation_id"] == "simplified":
                proof_path = "prepared/campaign-002/algebra/" + case["model_id"] + ".json"
                result["identity"] = identity(original, data, read(proof_path))
            row["representations"].append(result)
        if case["model_id"] in cpd:
            row["source"] = cpd_source(original, cpd[case["model_id"]]["source_matrix"]["local_path"])
            print(case["model_id"], "source entries checked", row["source"]["counts"]["selected_pair"], flush=True)
        rows.append(row)
    result = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(), "errors": [],
              "models_checked": len(rows), "representations_checked": sum(len(x["representations"]) for x in rows), "models": rows}
    (OUT / "original_semantics_audit.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print("All structure and serialized exact-reduction checks passed.")


if __name__ == "__main__":
    main()
