"""Preserve stored log-factor values as exact binary rationals during simplification."""

from dataclasses import replace
from fractions import Fraction
import itertools
import math

import numpy as np

from experiments.inference import Factor, Model


def exact_additive_split(values):
    if not np.isfinite(values).all():
        return None
    left = values[:, 0].copy()
    right = values[0, :] - values[0, 0]
    if not np.array_equal(left[:, None] + right[None, :], values):
        return None
    origin = Fraction(float(values[0, 0]))
    for j, value in enumerate(right):
        if Fraction(float(value)) != Fraction(float(values[0, j])) - origin:
            return None
    for i, j in itertools.product(range(values.shape[0]), range(values.shape[1])):
        if Fraction(float(left[i])) + Fraction(float(right[j])) != Fraction(float(values[i, j])):
            return None
    return left, right


def simplify_model(model):
    factors, transformations = [], []
    for index, factor in enumerate(model.factors):
        values = factor.values
        kind = None
        replacements = [factor]
        if values.size and np.all(values == values.flat[0]) and factor.scope:
            replacements = [Factor((), np.asarray(float(values.flat[0])))]
            kind = "constant_factor"
        elif len(factor.scope) == 2:
            left, right = factor.scope
            if np.all(values == values[0:1, :]):
                replacements = [Factor((right,), values[0, :].copy())]
                kind = "independent_of_first_axis"
            elif np.all(values == values[:, 0:1]):
                replacements = [Factor((left,), values[:, 0].copy())]
                kind = "independent_of_second_axis"
            else:
                split = exact_additive_split(values)
                if split is not None:
                    replacements = [Factor((left,), split[0]), Factor((right,), split[1])]
                    kind = "exact_binary_rational_additive_split"
        factors.extend(replacements)
        if kind:
            transformations.append({"source_factor_index": index, "kind": kind,
                                    "old_scope": list(factor.scope),
                                    "new_scopes": [list(f.scope) for f in replacements]})
    metadata = dict(model.metadata)
    metadata["scope_simplification"] = {
        "version": 1, "semantics": "exact equality of stored log weights as binary rationals; no tolerance-based edge deletion",
        "transformations": transformations,
        "domain_policy": "All original variables and domain cardinalities retained, including newly isolated variables.",
    }
    return replace(model, factors=tuple(factors), metadata=metadata), transformations


def structure_summary(model):
    neighbors = {v: set() for v in range(len(model.domains))}
    edges = set()
    for factor in model.factors:
        for a, b in itertools.combinations(factor.scope, 2):
            a, b = min(a, b), max(a, b)
            edges.add((a, b))
            neighbors[a].add(b)
            neighbors[b].add(a)
    isolated = sum(not adjacent for adjacent in neighbors.values())
    visited, components = set(), 0
    for variable in neighbors:
        if variable in visited:
            continue
        components += 1
        stack = [variable]
        while stack:
            current = stack.pop()
            if current not in visited:
                visited.add(current)
                stack.extend(neighbors[current] - visited)
    ordering, width, peak, steps = [], 0, 1, []
    while neighbors:
        def score(v):
            adjacent = neighbors[v]
            fill = sum(b not in neighbors[a] for a, b in itertools.combinations(adjacent, 2))
            log_size = sum(math.log(model.domains[x]) for x in adjacent | {v})
            return fill, log_size, v
        variable = min(neighbors, key=score)
        adjacent = neighbors.pop(variable)
        entries = math.prod(model.domains[v] for v in adjacent | {variable})
        width = max(width, len(adjacent))
        peak = max(peak, entries)
        steps.append({"variable": variable, "join_entries": str(entries), "neighbors": sorted(adjacent)})
        for other in adjacent:
            neighbors[other].discard(variable)
            neighbors[other].update(adjacent - {other})
        ordering.append(variable)
    return {"variables": len(model.domains), "domains": list(model.domains),
            "configuration_count": str(math.prod(model.domains)), "factor_count": len(model.factors),
            "factor_entries": sum(f.values.size for f in model.factors),
            "represented_pair_edges": len(edges), "connected_components": components,
            "isolated_variables": isolated, "min_fill_order": ordering,
            "predicted_induced_width": width, "predicted_peak_table_entries": str(peak),
            "predicted_peak_table_bytes_float64": str(8 * peak), "steps": steps,
            "prediction_scope": "One deterministic represented-scope min-fill ordering; not minimum treewidth or total process memory."}


def model_to_dict(model):
    def safe(value):
        if isinstance(value, list):
            return [safe(v) for v in value]
        return None if isinstance(value, float) and value == -math.inf else value
    return {"schema_version": 1, "model_id": model.model_id, "kind": model.kind,
            "log_base": "e", "domains": list(model.domains),
            "factors": [{"scope": list(f.scope), "log_values": safe(f.values.tolist())} for f in model.factors],
            "metadata": dict(model.metadata)}
