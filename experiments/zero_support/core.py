"""Generalized arc consistency using only explicitly forbidden factor entries."""

from __future__ import annotations

from dataclasses import replace
import math
import time

import numpy as np

from experiments.inference import Factor, Model
from experiments.structure import simplify_model, structure_summary

VERSION = 1


def _validate(model: Model) -> None:
    if any(isinstance(q, bool) or not isinstance(q, int) or q <= 0 for q in model.domains):
        raise ValueError("Support propagation requires positive integer domains")
    for index, factor in enumerate(model.factors):
        if (len(set(factor.scope)) != len(factor.scope)
                or any(isinstance(v, bool) or not isinstance(v, int)
                       or not 0 <= v < len(model.domains) for v in factor.scope)):
            raise ValueError(f"Invalid scope in factor {index}")
        if factor.values.shape != tuple(model.domains[v] for v in factor.scope):
            raise ValueError(f"Invalid shape in factor {index}")
        if np.isnan(factor.values).any() or np.isposinf(factor.values).any():
            raise ValueError(f"Factor {index} contains an invalid log value")


def _immutable(values):
    result = np.array(values, dtype=np.float64, copy=True)
    result.flags.writeable = False
    return result


def _constraints(model: Model):
    merged = {}
    scalar_zeros = []
    for index, factor in enumerate(model.factors):
        if not factor.scope:
            if np.isneginf(factor.values).item():
                scalar_zeros.append(index)
            continue
        scope = tuple(sorted(factor.scope))
        permutation = tuple(factor.scope.index(v) for v in scope)
        support = np.logical_not(np.isneginf(factor.values)).transpose(permutation)
        if scope not in merged:
            merged[scope] = {"scope": scope, "source_factor_indices": [],
                             "support": support.copy()}
        else:
            np.logical_and(merged[scope]["support"], support, out=merged[scope]["support"])
        merged[scope]["source_factor_indices"].append(index)
    return [merged[scope] for scope in sorted(merged)], scalar_zeros


def propagate_model(model: Model, *, simplify: bool = True) -> tuple[Model, dict]:
    """Return an exactly restricted model and a replayable hard-zero deletion ledger."""
    started = time.perf_counter()
    _validate(model)
    validation_finished = time.perf_counter()
    constraints, scalar_zeros = _constraints(model)
    active = [np.arange(q, dtype=np.int64) for q in model.domains]
    trace = []
    checks, rounds, restricted_support_entries = 0, 0, 0
    reason = ({"kind": "scalar_hard_zero", "source_factor_indices": scalar_zeros}
              if scalar_zeros else None)
    while reason is None:
        rounds += 1
        changed = False
        for constraint_index, constraint in enumerate(constraints):
            scope = constraint["scope"]
            allowed = [active[v] for v in scope]
            support = constraint["support"][np.ix_(*allowed)]
            checks += 1
            restricted_support_entries += int(support.size)
            removed = {}
            kept = {}
            for axis, variable in enumerate(scope):
                other_axes = tuple(i for i in range(len(scope)) if i != axis)
                supported = np.any(support, axis=other_axes) if other_axes else support
                supported = np.asarray(supported, dtype=bool).reshape(-1)
                missing = allowed[axis][np.logical_not(supported)]
                if missing.size:
                    removed[str(variable)] = missing.tolist()
                    kept[variable] = allowed[axis][supported]
            if not removed:
                continue
            trace.append({"round": rounds, "constraint_index": constraint_index,
                          "scope": list(scope),
                          "source_factor_indices": list(constraint["source_factor_indices"]),
                          "allowed_before": {str(v): active[v].tolist() for v in scope},
                          "removed_original_indices": removed,
                          "reason": "No tuple allowed by this merged hard-zero constraint supports the value under current domains."})
            for variable, values in kept.items():
                active[variable] = values
            changed = True
            wiped = sorted(variable for variable in kept if not active[variable].size)
            if wiped:
                reason = {"kind": "domain_wipeout", "variables": wiped,
                          "trace_event_index": len(trace) - 1,
                          "constraint_index": constraint_index}
                break
        if not changed:
            break
    propagation_finished = time.perf_counter()
    retained = [values.tolist() for values in active]
    if reason is None:
        domains = tuple(len(values) for values in active)
        factors = tuple(Factor(factor.scope, _immutable(
            factor.values[np.ix_(*(active[v] for v in factor.scope))]
            if factor.scope else factor.values)) for factor in model.factors)
        output_indices = retained
        mapping_semantics = "Output value j of variable v is input value retained_original_indices[v][j]."
        status = "arc_consistent"
    else:
        domains = tuple(1 for _ in model.domains)
        factors = (Factor((), _immutable(-math.inf)),)
        output_indices = [[0] for _ in model.domains]
        mapping_semantics = "Proven-zero target uses dummy singleton domains. Output indices are not a feasible-assignment witness; retained_original_indices records the propagation state."
        status = "proven_zero"
    metadata = dict(model.metadata)
    metadata["zero_support"] = {
        "version": VERSION, "status": status,
        "input_model_source_sha256": model.source_sha256,
        "input_domains": list(model.domains),
        "retained_original_indices": retained,
        "output_value_original_indices": output_indices,
        "mapping_semantics": mapping_semantics,
        "target_relation": "Exactly the same partition sum: every discarded input assignment has an explicit hard-zero factor; retained finite entries are copied without arithmetic.",
        "finite_weight_policy": "Every finite log value is retained. No exp, threshold, energy cutoff, or tolerance-based pruning.",
        "feasibility_policy": "Arc consistency does not imply global satisfiability.",
    }
    restricted = replace(model, domains=domains, factors=factors, metadata=metadata)
    restriction_finished = time.perf_counter()
    if simplify:
        output, algebra = simplify_model(restricted)
        output = replace(output, factors=tuple(Factor(f.scope, _immutable(f.values))
                                               for f in output.factors))
    else:
        output, algebra = restricted, []
    simplification_finished = time.perf_counter()
    before, after = structure_summary(model), structure_summary(output)
    ledger = {
        "schema_version": 1, "algorithm": "merged-scope generalized arc consistency",
        "version": VERSION, "status": status,
        "input_model_id": model.model_id, "input_model_source_sha256": model.source_sha256,
        "input_domains": list(model.domains), "output_domains": list(output.domains),
        "retained_original_indices": retained,
        "output_value_original_indices": output_indices,
        "mapping_semantics": mapping_semantics,
        "input_declared_assignments": str(math.prod(model.domains)),
        "retained_cartesian_assignments": str(math.prod(len(values) for values in active)),
        "output_declared_assignments": str(math.prod(output.domains)),
        "removed_domain_values": sum(model.domains[v] - len(active[v]) for v in range(len(active))),
        "inconsistency_proof": reason,
        "factor_restrictions": [
            {"input_factor_index": index, "scope": list(factor.scope),
             "input_shape": list(factor.values.shape),
             "original_indices_per_axis": [active[v].tolist() for v in factor.scope],
             "restricted_shape": [len(active[v]) for v in factor.scope],
             "restricted_factor_index_before_algebra": index if reason is None else None,
             "representation": "sliced_original_factor" if reason is None else "replaced_by_canonical_proven_zero",
             "stage": "support restriction before optional exact algebra"}
            for index, factor in enumerate(model.factors)
        ],
        "constraints": [{"constraint_index": i, "scope": list(c["scope"]),
                         "source_factor_indices": list(c["source_factor_indices"]),
                         "entries": int(c["support"].size),
                         "hard_zero_entries_after_scope_intersection": int(c["support"].size - np.count_nonzero(c["support"]))}
                        for i, c in enumerate(constraints)],
        "constraint_checks": checks, "fixpoint_rounds": rounds,
        "restricted_support_entries_examined": restricted_support_entries,
        "deletions": trace, "simplification_enabled": simplify,
        "algebra_transformations": algebra,
        "structure_before": before, "structure_after": after,
        "support_policy": "Only negative infinity is a hard zero. Finite values, including extreme energies, are not pruned or numerically merged.",
        "duplicate_scope_policy": "AND aligned boolean supports for identical variable scopes; original numeric factors remain separate.",
        "proof_scope": "Each deletion has no support in one merged-scope constraint under the recorded prior domains. Induction proves no removed value occurs in any globally nonzero-weight assignment. Arc consistency alone does not certify remaining assignments feasible.",
        "timing_seconds": {
            "validation": validation_finished - started,
            "support_construction_and_propagation": propagation_finished - validation_finished,
            "restriction_and_metadata": restriction_finished - propagation_finished,
            "optional_exact_simplification": simplification_finished - restriction_finished,
        },
        "timing_scope": "In-memory validation, support construction, fixed-point propagation, array restriction, optional exact algebra, structure summaries and ledger construction. Caller loading and serialization are excluded.",
    }
    ledger["elapsed_seconds"] = time.perf_counter() - started
    return output, ledger
