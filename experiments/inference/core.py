"""Log-domain sum-product inference; none of these methods implements ETH."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import heapq
import itertools
import json
import math
from pathlib import Path
import time
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True)
class Factor:
    scope: tuple[int, ...]
    values: np.ndarray = field(compare=False, repr=False)


@dataclass(frozen=True)
class Model:
    domains: tuple[int, ...]
    factors: tuple[Factor, ...]
    model_id: str = "unnamed"
    kind: str = "unspecified"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    source_sha256: str | None = None

    @property
    def n_states(self) -> int:
        return math.prod(self.domains)


class InferenceLimit(RuntimeError):
    def __init__(self, reason: str, metrics: dict[str, Any]):
        super().__init__(reason)
        self.reason = reason
        self.metrics = metrics


def _log_number(value: Any) -> float:
    if value is None or value == "-inf":
        return -math.inf
    if isinstance(value, bool):
        raise ValueError("Boolean values are not log weights")
    result = float(value)
    if math.isnan(result) or result == math.inf:
        raise ValueError("Log weights must be finite or negative infinity")
    return result


def _convert_values(values: Any) -> np.ndarray:
    raw = np.asarray(values, dtype=object)
    converted = np.fromiter((_log_number(v) for v in raw.flat), dtype=np.float64, count=raw.size)
    return converted.reshape(raw.shape)


def model_from_dict(data: Mapping[str, Any], *, allow_higher_arity: bool = False) -> Model:
    if data.get("schema_version", 1) != 1:
        raise ValueError("Unsupported schema_version")
    if data.get("log_base", "e") not in ("e", "natural"):
        raise ValueError("Expected natural-log weights; convert log-base conventions explicitly")
    domains_raw = data["domains"]
    if not isinstance(domains_raw, list):
        raise ValueError("domains must be a list")
    if any(isinstance(d, bool) or not isinstance(d, int) or d <= 0 for d in domains_raw):
        raise ValueError("Domain sizes must be positive integers")
    domains = tuple(domains_raw)
    factors = []
    for index, raw in enumerate(data.get("factors", [])):
        raw_scope = raw["scope"]
        if not isinstance(raw_scope, list) or any(
            isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < len(domains)
            for v in raw_scope
        ):
            raise ValueError(f"Factor {index}: scope indices must address domains")
        scope = tuple(raw_scope)
        if len(set(scope)) != len(scope):
            raise ValueError(f"Factor {index}: duplicate variable in scope")
        if len(scope) > 2 and not allow_higher_arity:
            raise ValueError(f"Factor {index}: higher-arity factor needs explicit opt-in")
        shape = tuple(domains[v] for v in scope)
        values = _convert_values(raw["log_values"])
        if values.size != math.prod(shape):
            raise ValueError(f"Factor {index}: expected {shape}, received {values.shape}")
        if values.ndim > 1 and values.shape != shape:
            raise ValueError(f"Factor {index}: nested shape {values.shape} != {shape}")
        values = values.reshape(shape)
        values.flags.writeable = False
        factors.append(Factor(scope, values))
    if "constant_log_weight" in data:
        value = np.asarray(_log_number(data["constant_log_weight"]), dtype=np.float64)
        value.flags.writeable = False
        factors.append(Factor((), value))
    return Model(
        domains, tuple(factors), str(data.get("model_id", "unnamed")),
        str(data.get("kind", "unspecified")), dict(data.get("metadata", {})),
    )


def load_model(path: str | Path, *, allow_higher_arity: bool = False) -> Model:
    blob = Path(path).read_bytes()
    model = model_from_dict(json.loads(blob), allow_higher_arity=allow_higher_arity)
    return Model(
        model.domains, model.factors, model.model_id, model.kind, model.metadata,
        hashlib.sha256(blob).hexdigest(),
    )


def condition_model(model: Model, fixed: Mapping[int, int]) -> Model:
    for var, value in fixed.items():
        if isinstance(var, bool) or not isinstance(var, int) or not 0 <= var < len(model.domains):
            raise ValueError("Invalid conditioned variable")
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < model.domains[var]:
            raise ValueError("Invalid conditioned value")
    remaining = [v for v in range(len(model.domains)) if v not in fixed]
    reindex = {old: new for new, old in enumerate(remaining)}
    factors = []
    for factor in model.factors:
        selector = tuple(fixed[v] if v in fixed else slice(None) for v in factor.scope)
        values = np.array(factor.values[selector], dtype=np.float64, copy=True)
        values.flags.writeable = False
        factors.append(Factor(tuple(reindex[v] for v in factor.scope if v not in fixed), values))
    metadata = dict(model.metadata)
    metadata["conditioning"] = {str(v): value for v, value in sorted(fixed.items())}
    metadata["remaining_original_variables"] = remaining
    return Model(
        tuple(model.domains[v] for v in remaining), tuple(factors), model.model_id,
        model.kind, metadata, model.source_sha256,
    )


def _logsumexp(values: np.ndarray, axis: int | None = None) -> float | np.ndarray:
    if axis is None:
        return float(np.logaddexp.reduce(np.asarray(values).ravel(), initial=-math.inf))
    return np.logaddexp.reduce(values, axis=axis)


def _order(model: Model, strategy: str | list[int] | tuple[int, ...]) -> list[int]:
    count = len(model.domains)
    if not isinstance(strategy, str):
        order = list(strategy)
        if (len(order) != count or set(order) != set(range(count))
                or any(isinstance(v, bool) or not isinstance(v, int) for v in order)):
            raise ValueError("Elimination order must be a permutation of all variables")
        return order
    if strategy == "natural":
        return list(range(count))
    if strategy not in ("min-fill", "min-weight"):
        raise ValueError("Unknown ordering strategy")
    neighbors = {v: set() for v in range(count)}
    for factor in model.factors:
        for left, right in itertools.combinations(factor.scope, 2):
            neighbors[left].add(right)
            neighbors[right].add(left)
    result = []
    while neighbors:
        def score(v: int) -> tuple[float, float, int]:
            adjacent = neighbors[v]
            fill = sum(b not in neighbors[a] for a, b in itertools.combinations(adjacent, 2))
            size = sum(math.log(model.domains[w]) for w in adjacent | {v})
            return (fill, size, v) if strategy == "min-fill" else (size, fill, v)
        variable = min(neighbors, key=score)
        adjacent = neighbors.pop(variable)
        for other in adjacent:
            neighbors[other].discard(variable)
            neighbors[other].update(adjacent - {other})
        result.append(variable)
    return result


def _aligned(factor: Factor, target: tuple[int, ...], domains: tuple[int, ...]) -> np.ndarray:
    if not factor.scope:
        return factor.values
    position = {v: axis for axis, v in enumerate(target)}
    permutation = sorted(range(len(factor.scope)), key=lambda axis: position[factor.scope[axis]])
    values = factor.values.transpose(permutation)
    shape = tuple(domains[v] if v in factor.scope else 1 for v in target)
    return values.reshape(shape)


def variable_elimination(
    model: Model, *, order: str | list[int] | tuple[int, ...] = "min-fill",
    max_table_bytes: int = 64 * 1024 * 1024, time_limit_seconds: float | None = None,
) -> dict[str, Any]:
    if max_table_bytes <= 0:
        raise ValueError("max_table_bytes must be positive")
    start = time.perf_counter()
    ordering = _order(model, order)
    factors = list(model.factors)
    input_ids = {id(f.values) for f in model.factors}
    input_bytes = sum(f.values.nbytes for f in model.factors)
    stats: dict[str, Any] = {
        "order": ordering, "ordering_strategy": order if isinstance(order, str) else "explicit",
        "max_table_bytes_limit": max_table_bytes, "input_factor_bytes": input_bytes,
        "peak_table_bytes": 0, "estimated_peak_live_array_bytes": input_bytes,
        "induced_width": 0, "eliminated_variables": 0, "isolated_variables": 0,
        "logical_entry_operations": 0, "steps": [],
    }
    if any(f.values.nbytes > max_table_bytes for f in factors):
        stats["elapsed_seconds"] = time.perf_counter() - start
        raise InferenceLimit("input_factor_exceeds_table_limit", stats)
    for variable in ordering:
        if time_limit_seconds is not None and time.perf_counter() - start >= time_limit_seconds:
            stats["elapsed_seconds"] = time.perf_counter() - start
            raise InferenceLimit("time_limit", stats)
        bucket = [f for f in factors if variable in f.scope]
        remaining = [f for f in factors if variable not in f.scope]
        if not bucket:
            remaining.append(Factor((), np.asarray(math.log(model.domains[variable]))))
            stats["isolated_variables"] += 1
            stats["eliminated_variables"] += 1
            factors = remaining
            continue
        scope = tuple(sorted(set().union(*(set(f.scope) for f in bucket))))
        shape = tuple(model.domains[v] for v in scope)
        entries = math.prod(shape)
        table_bytes = entries * np.dtype(np.float64).itemsize
        stats["induced_width"] = max(stats["induced_width"], len(scope) - 1)
        if table_bytes > max_table_bytes:
            stats.update({"blocked_variable": variable, "blocked_table_bytes": table_bytes,
                          "elapsed_seconds": time.perf_counter() - start})
            raise InferenceLimit("intermediate_table_limit", stats)
        joint = np.zeros(shape, dtype=np.float64)
        for factor in bucket:
            np.add(joint, _aligned(factor, scope, model.domains), out=joint)
        reduced = np.asarray(_logsumexp(joint, axis=scope.index(variable)))
        if np.isnan(reduced).any() or np.isposinf(reduced).any():
            raise ArithmeticError("Non-finite arithmetic overflow during elimination")
        live_bytes = input_bytes + sum(f.values.nbytes for f in factors if id(f.values) not in input_ids)
        stats["estimated_peak_live_array_bytes"] = max(
            stats["estimated_peak_live_array_bytes"], live_bytes + joint.nbytes + reduced.nbytes,
        )
        stats["peak_table_bytes"] = max(stats["peak_table_bytes"], table_bytes)
        stats["logical_entry_operations"] += entries * (len(bucket) + 1)
        stats["steps"].append({"variable": variable, "scope": list(scope), "entries": entries})
        remaining.append(Factor(tuple(v for v in scope if v != variable), reduced))
        factors = remaining
        stats["eliminated_variables"] += 1
    log_z = sum(float(f.values) for f in factors)
    if math.isnan(log_z) or log_z == math.inf:
        raise ArithmeticError("Non-finite arithmetic overflow in final log partition")
    stats["elapsed_seconds"] = time.perf_counter() - start
    return {"status": "complete", "method": "variable_elimination", "log_z": log_z,
            "arithmetic": "float64_log_domain_not_interval_certified", "metrics": stats}


def brute_force(
    model: Model, *, max_states: int = 1_000_000, time_limit_seconds: float | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    stats: dict[str, Any] = {"state_count": str(model.n_states), "states_evaluated": 0}
    if model.n_states > max_states:
        stats["elapsed_seconds"] = time.perf_counter() - start
        raise InferenceLimit("state_limit", stats)
    log_z = -math.inf
    for assignment in itertools.product(*(range(d) for d in model.domains)):
        if stats["states_evaluated"] % 1024 == 0 and time_limit_seconds is not None:
            if time.perf_counter() - start >= time_limit_seconds:
                stats["elapsed_seconds"] = time.perf_counter() - start
                raise InferenceLimit("time_limit", stats)
        log_weight = sum(float(f.values[tuple(assignment[v] for v in f.scope)]) for f in model.factors)
        if math.isnan(log_weight) or log_weight == math.inf:
            raise ArithmeticError("Non-finite arithmetic overflow during enumeration")
        log_z = float(np.logaddexp(log_z, log_weight))
        stats["states_evaluated"] += 1
    stats["elapsed_seconds"] = time.perf_counter() - start
    return {"status": "complete", "method": "brute_force", "log_z": log_z,
            "arithmetic": "float64_log_domain_not_interval_certified", "metrics": stats}


def batched_brute_force(
    model: Model, *, max_states: int = 1_000_000, batch_states: int = 65_536,
    max_batch_bytes: int = 64 * 1024 * 1024,
    time_limit_seconds: float | None = None,
) -> dict[str, Any]:
    """Enumerate mixed-radix assignments in bounded NumPy chunks, without elimination."""
    if batch_states <= 0 or max_batch_bytes <= 0 or max_states <= 0:
        raise ValueError("Batch sizes and state limits must be positive")
    start = time.perf_counter()
    bytes_per_state = np.dtype(np.int64).itemsize * (len(model.domains) + 3)
    actual_batch = min(batch_states, max_batch_bytes // bytes_per_state)
    stats: dict[str, Any] = {
        "state_count": str(model.n_states), "states_evaluated": 0, "batches": 0,
        "batch_states_requested": batch_states, "batch_states_effective": actual_batch,
        "max_batch_bytes_limit": max_batch_bytes, "estimated_peak_batch_array_bytes": 0,
        "input_factor_bytes": sum(f.values.nbytes for f in model.factors),
    }
    if model.n_states > max_states:
        stats["elapsed_seconds"] = time.perf_counter() - start
        raise InferenceLimit("state_limit", stats)
    if model.n_states > np.iinfo(np.int64).max:
        stats["elapsed_seconds"] = time.perf_counter() - start
        raise InferenceLimit("integer_index_limit", stats)
    if actual_batch < 1:
        stats["elapsed_seconds"] = time.perf_counter() - start
        raise InferenceLimit("batch_array_limit", stats)
    log_z = -math.inf
    for first in range(0, model.n_states, actual_batch):
        if time_limit_seconds is not None and time.perf_counter() - start >= time_limit_seconds:
            stats["elapsed_seconds"] = time.perf_counter() - start
            raise InferenceLimit("time_limit", stats)
        stop = min(model.n_states, first + actual_batch)
        flat_indices = np.arange(first, stop, dtype=np.int64)
        coordinates = np.unravel_index(flat_indices, model.domains) if model.domains else ()
        weights = np.zeros(stop - first, dtype=np.float64)
        for factor in model.factors:
            selector = tuple(coordinates[v] for v in factor.scope)
            np.add(weights, factor.values[selector], out=weights)
        if np.isnan(weights).any() or np.isposinf(weights).any():
            raise ArithmeticError("Non-finite arithmetic overflow during batched enumeration")
        log_z = float(np.logaddexp(log_z, _logsumexp(weights)))
        stats["states_evaluated"] += stop - first
        stats["batches"] += 1
        stats["estimated_peak_batch_array_bytes"] = max(
            stats["estimated_peak_batch_array_bytes"], bytes_per_state * (stop - first),
        )
    stats["elapsed_seconds"] = time.perf_counter() - start
    return {"status": "complete", "method": "batched_brute_force", "log_z": log_z,
            "arithmetic": "float64_log_domain_not_interval_certified", "metrics": stats}


def bounded_mass(
    model: Model, *, epsilon: float = 0.1, max_nodes: int = 100_000,
    max_frontier_nodes: int = 100_000, time_limit_seconds: float | None = None,
    check_interval: int = 64,
) -> dict[str, Any]:
    """Best-first prefix enumeration with a combinatorial omitted-mass bound."""
    if not 0 <= epsilon < 1:
        raise ValueError("epsilon must lie in [0, 1)")
    if max_nodes <= 0 or max_frontier_nodes <= 0 or check_interval <= 0:
        raise ValueError("Node limits and check_interval must be positive")
    start = time.perf_counter()
    incidence = [sum(v in f.scope for f in model.factors) for v in range(len(model.domains))]
    order = sorted(range(len(model.domains)), key=lambda v: (-incidence[v], model.domains[v], v))
    position = {v: index for index, v in enumerate(order)}
    remaining_log_count = [0.0] * (len(order) + 1)
    for index in range(len(order) - 1, -1, -1):
        remaining_log_count[index] = remaining_log_count[index + 1] + math.log(model.domains[order[index]])
    stats: dict[str, Any] = {"order": order, "nodes_popped": 0, "nodes_expanded": 0,
                            "complete_assignments_evaluated": 0, "factor_bound_evaluations": 0,
                            "peak_frontier_nodes": 0, "epsilon_requested": epsilon,
                            "max_nodes": max_nodes, "max_frontier_nodes": max_frontier_nodes,
                            "check_interval": check_interval}

    def bound(prefix: tuple[int, ...]) -> float:
        weight = remaining_log_count[len(prefix)]
        for factor in model.factors:
            selector = tuple(prefix[position[v]] if position[v] < len(prefix) else slice(None)
                             for v in factor.scope)
            weight += float(np.max(factor.values[selector]))
            stats["factor_bound_evaluations"] += 1
        if math.isnan(weight) or weight == math.inf:
            raise ArithmeticError("Non-finite arithmetic overflow during prefix bounding")
        return weight

    def mass_bounds() -> tuple[float, float, float]:
        residual = _logsumexp(np.asarray([-item[0] for item in frontier], dtype=np.float64))
        upper = float(np.logaddexp(log_lower, residual))
        relative = 0.0 if residual == -math.inf else (1.0 if log_lower == -math.inf else math.exp(residual - upper))
        return residual, upper, relative

    root_bound = bound(())
    frontier = [(-root_bound, 0, ())] if root_bound != -math.inf else []
    serial = itertools.count(1)
    log_lower = -math.inf
    reason = "exact"
    while frontier:
        stats["peak_frontier_nodes"] = max(stats["peak_frontier_nodes"], len(frontier))
        if stats["nodes_popped"] >= max_nodes:
            reason = "node_limit"
            break
        if time_limit_seconds is not None and time.perf_counter() - start >= time_limit_seconds:
            reason = "time_limit"
            break
        if stats["nodes_popped"] % check_interval == 0 and log_lower != -math.inf:
            _, _, relative = mass_bounds()
            if relative <= epsilon:
                reason = "epsilon_reached"
                break
        item = heapq.heappop(frontier)
        log_bound, _, prefix = -item[0], item[1], item[2]
        if len(prefix) == len(order):
            log_lower = float(np.logaddexp(log_lower, log_bound))
            stats["complete_assignments_evaluated"] += 1
            stats["nodes_popped"] += 1
            continue
        children = []
        variable = order[len(prefix)]
        for value in range(model.domains[variable]):
            child = prefix + (value,)
            child_bound = bound(child)
            if child_bound != -math.inf:
                children.append((-child_bound, next(serial), child))
        if len(frontier) + len(children) > max_frontier_nodes:
            heapq.heappush(frontier, item)
            reason = "frontier_limit"
            break
        for child in children:
            heapq.heappush(frontier, child)
        stats["nodes_expanded"] += 1
        stats["nodes_popped"] += 1
    residual, log_upper, relative = mass_bounds()
    if reason in ("node_limit", "frontier_limit", "time_limit") and relative <= epsilon:
        reason = "epsilon_reached_at_limit"
    stats.update({"elapsed_seconds": time.perf_counter() - start, "frontier_nodes": len(frontier)})
    return {
        "status": reason, "method": "bounded_mass", "log_z_lower": log_lower,
        "log_z_upper": log_upper, "log_residual_mass_upper": residual,
        "relative_omitted_mass_upper": relative, "epsilon_met": relative <= epsilon,
        "arithmetic": "combinatorial_bound_float64_not_interval_certified", "metrics": stats,
    }


def log_kstar(log_complex: float, log_protein: float, log_ligand: float) -> float:
    values = [log_complex, log_protein, log_ligand]
    if any(math.isnan(v) or v == math.inf for v in values):
        raise ValueError("Invalid log partition function")
    if log_protein == -math.inf or log_ligand == -math.inf:
        raise ValueError("K* is undefined for a zero unbound partition function")
    return log_complex - log_protein - log_ligand
