"""Recover a normalizer through pyagrum's exact conditional marginals."""

from __future__ import annotations

import importlib.metadata
import math
import time
from typing import Any

import numpy as np

from experiments.inference import Model

PACKAGE_VERSION = "3.3.2"
ADAPTER_VERSION = 1
MAX_TOTAL_LOG_ROUNDTRIP_ERROR = 1e-9


def _base_result(status: str, metrics: dict, **extra) -> dict[str, Any]:
    return {"status": status, "method": "pyagrum_conditional_normalizer",
            "adapter_version": ADAPTER_VERSION,
            "arithmetic": "float64_linear_inference_with_log_offsets_not_interval_certified",
            "metrics": metrics, **extra}


def run_pyagrum(model: Model, *, max_table_bytes: int = 128 * 1024 * 1024) -> dict[str, Any]:
    if max_table_bytes <= 0:
        raise ValueError("max_table_bytes must be positive")
    started = time.perf_counter()
    metrics: dict[str, Any] = {
        "max_table_bytes_limit": max_table_bytes, "solver_threads": 1,
        "conditional_queries": 0, "dependency_import_seconds": 0.0,
        "conversion_seconds": 0.0, "preprocessing_seconds": 0.0,
        "kernel_elapsed_seconds": 0.0,
        "normalization": "merge identical scopes in log domain, then subtract each factor maximum; no positive entry may become zero",
        "max_total_log_roundtrip_error_allowed": MAX_TOTAL_LOG_ROUNDTRIP_ERROR,
        "numerical_guarantee": "No outward-rounded interval certificate; exp/log roundtrip errors are diagnostics, not rigorous bounds.",
        "package_distribution_version": importlib.metadata.version("pyagrum"),
    }
    if metrics["package_distribution_version"] != PACKAGE_VERSION:
        return _base_result("unsupported_package_version", metrics)
    converting = time.perf_counter()
    constants: list[float] = []
    groups: dict[tuple[int, ...], np.ndarray] = {}
    for factor in model.factors:
        if not factor.scope:
            constants.append(float(factor.values))
            continue
        scope = tuple(sorted(factor.scope))
        axes = [factor.scope.index(v) for v in scope]
        values = np.asarray(factor.values.transpose(axes), dtype=np.float64)
        if scope not in groups:
            groups[scope] = values.copy()
        else:
            finite_inputs = np.isfinite(groups[scope]) & np.isfinite(values)
            with np.errstate(over="ignore", invalid="ignore"):
                combined = groups[scope] + values
            if np.any(finite_inputs & ~np.isfinite(combined)):
                metrics["conversion_seconds"] = time.perf_counter() - converting
                return _base_result("conversion_overflow", metrics)
            groups[scope] = combined
        if np.isnan(groups[scope]).any() or np.isposinf(groups[scope]).any():
            metrics["conversion_seconds"] = time.perf_counter() - converting
            return _base_result("conversion_overflow", metrics)
    if -math.inf in constants or any(np.isneginf(values).all() for values in groups.values()):
        metrics.update({"conversion_seconds": time.perf_counter() - converting,
                        "elapsed_seconds": time.perf_counter() - started,
                        "zero_partition_reason": "A scalar or merged factor is identically zero."})
        return _base_result("complete", metrics, log_z=-math.inf)
    scalar_offset = math.fsum(constants)
    if not math.isfinite(scalar_offset):
        return _base_result("conversion_overflow", metrics)
    offsets = [scalar_offset]
    normalized: dict[tuple[int, ...], np.ndarray] = {}
    factor_diagnostics = []
    total_roundtrip = 0.0
    total_min_log_weight = 0.0
    for scope, log_values in sorted(groups.items()):
        finite = np.isfinite(log_values)
        maximum = float(log_values[finite].max())
        shifted = log_values - maximum
        with np.errstate(under="ignore"):
            weights = np.exp(shifted)
        newly_zero = int(np.count_nonzero(finite & (weights == 0)))
        if newly_zero:
            metrics.update({"conversion_seconds": time.perf_counter() - converting,
                            "failed_factor_scope": list(scope), "new_zero_entries": newly_zero,
                            "failed_factor_log_span": maximum - float(log_values[finite].min())})
            return _base_result("conversion_underflow", metrics)
        roundtrip = float(np.max(np.abs(np.log(weights[finite]) - shifted[finite])))
        total_roundtrip += roundtrip
        total_min_log_weight += float(shifted[finite].min())
        offsets.append(maximum)
        normalized[scope] = weights
        factor_diagnostics.append({"scope": list(scope), "entries": weights.size,
                                   "log_offset": maximum, "positive_entries": int(finite.sum()),
                                   "max_abs_log_roundtrip_error": roundtrip})
    metrics.update({"scalar_log_offset": scalar_offset,
                    "removed_log_offset": math.fsum(offsets),
                    "total_log_roundtrip_error_diagnostic": total_roundtrip,
                    "factor_conversion": factor_diagnostics,
                    "sum_minimum_positive_normalized_log_weight": total_min_log_weight})
    if total_roundtrip > MAX_TOTAL_LOG_ROUNDTRIP_ERROR:
        metrics["conversion_seconds"] = time.perf_counter() - converting
        return _base_result("conversion_accuracy_limit", metrics)
    for variable, domain in enumerate(model.domains):
        if not any(variable in scope for scope in normalized):
            normalized[(variable,)] = np.ones(domain, dtype=np.float64)
    metrics["conversion_seconds"] = time.perf_counter() - converting
    if not model.domains:
        metrics["elapsed_seconds"] = time.perf_counter() - started
        return _base_result("complete", metrics, log_z=scalar_offset)

    importing = time.perf_counter()
    import pyagrum as gum
    metrics["dependency_import_seconds"] = time.perf_counter() - importing
    metrics["package_version"] = gum.__version__
    metrics["package_distribution_version"] = importlib.metadata.version("pyagrum")
    if gum.__version__ != PACKAGE_VERSION:
        return _base_result("unsupported_package_version", metrics)
    preprocessing = time.perf_counter()
    mrf = gum.MarkovRandomField()
    nodes = [mrf.add(gum.LabelizedVariable(f"x{v}", "", q))
             for v, q in enumerate(model.domains)]
    for scope, weights in sorted(normalized.items()):
        potential = mrf.addFactor([nodes[v] for v in scope])
        actual_names = [v.name() for v in potential.variablesSequence()]
        actual_scope = [int(name[1:]) for name in actual_names]
        axes = [scope.index(v) for v in actual_scope]
        potential.fillWith(weights.transpose(axes).ravel(order="F").tolist())
    preflight_tree = gum.JunctionTreeGenerator().junctionTree(mrf)
    predicted_cliques = [sorted(preflight_tree.clique(node)) for node in sorted(preflight_tree.nodes())]
    predicted_entries = [math.prod(model.domains[v] for v in clique) for clique in predicted_cliques]
    metrics.update({"preflight_generator_cliques": predicted_cliques,
                    "preflight_max_clique_table_bytes": 8 * max(predicted_entries, default=1),
                    "resource_scope": "Wrapper preflight uses pyagrum JunctionTreeGenerator before creating the inference engine. This is not a process RSS ceiling or a claim about all temporary allocations; parent must enforce process memory/time externally."})
    if metrics["preflight_max_clique_table_bytes"] > max_table_bytes:
        metrics.update({"preprocessing_seconds": time.perf_counter() - preprocessing,
                        "elapsed_seconds": time.perf_counter() - started})
        return _base_result("wrapper_preflight_clique_limit", metrics)
    engine = gum.ShaferShenoyMRFInference(mrf)
    engine.setNumberOfThreads(1)
    # The 3.3.2 binding accepts only integer GB despite documenting a float.
    scheduler_gb = max(1, math.ceil(max_table_bytes / 1_000_000_000))
    engine.setMaxMemory(scheduler_gb)
    tree = engine.junctionTree()
    cliques = [sorted(tree.clique(node)) for node in sorted(tree.nodes())]
    entries = [math.prod(model.domains[v] for v in clique) for clique in cliques]
    metrics.update({"junction_tree_cliques": cliques,
                    "junction_tree_max_clique_entries": max(entries, default=1),
                    "junction_tree_sum_clique_entries": sum(entries),
                    "junction_tree_width": max((len(c)-1 for c in cliques), default=0),
                    "estimated_peak_clique_table_bytes": 8 * max(entries, default=1),
                    "estimated_sum_clique_table_bytes": 8 * sum(entries),
                    "engine_scheduler_memory_gigabytes": scheduler_gb,
                    "preprocessing_seconds": time.perf_counter() - preprocessing})
    if metrics["estimated_peak_clique_table_bytes"] > max_table_bytes:
        metrics["elapsed_seconds"] = time.perf_counter() - started
        return _base_result("postconstruction_clique_limit", metrics)

    computing = time.perf_counter()
    selected: list[int] = []
    conditional_logs: list[float] = []
    try:
        for variable, node in enumerate(nodes):
            engine.makeInference()
            probabilities = np.asarray(engine.posterior(node).toarray(), dtype=float).ravel()
            if not np.isfinite(probabilities).all() or np.any(probabilities < 0):
                raise ArithmeticError("Nonfinite or negative conditional probabilities")
            mass = math.fsum(float(v) for v in probabilities)
            if mass <= 0 or abs(mass - 1) > 1e-9:
                raise ArithmeticError("Conditional posterior is not normalized")
            value = int(np.argmax(probabilities))
            probability = float(probabilities[value])
            if probability <= 0:
                raise ArithmeticError("No positive posterior entry")
            selected.append(value)
            conditional_logs.append(math.log(probability))
            metrics["conditional_queries"] += 1
            if variable + 1 < len(nodes):
                engine.addEvidence(node, value)
    except gum.IncompatibleEvidence as error:
        metrics["kernel_elapsed_seconds"] = time.perf_counter() - computing
        metrics["elapsed_seconds"] = time.perf_counter() - started
        metrics["exception"] = type(error).__name__
        # In the safe-product regime each feasible assignment has normal positive mass.
        if total_min_log_weight >= math.log(np.finfo(np.float64).tiny):
            return _base_result("complete", metrics, log_z=-math.inf,
                                zero_partition_reason="Incompatible evidence in safe positive-product regime")
        return _base_result("numerical_failure_or_zero_support", metrics)
    except (ArithmeticError, RuntimeError) as error:
        metrics["kernel_elapsed_seconds"] = time.perf_counter() - computing
        metrics["elapsed_seconds"] = time.perf_counter() - started
        metrics["exception"] = type(error).__name__
        metrics["exception_message"] = str(error)
        return _base_result("numerical_failure", metrics)
    original_log_weight = math.fsum(float(factor.values[tuple(selected[v] for v in factor.scope)])
                                    for factor in model.factors)
    if not math.isfinite(original_log_weight):
        metrics["kernel_elapsed_seconds"] = time.perf_counter() - computing
        metrics["elapsed_seconds"] = time.perf_counter() - started
        return _base_result("numerical_failure", metrics,
                            reason="Selected assignment has zero original model weight")
    conditional_log_probability = math.fsum(conditional_logs)
    normalized_log_weight = math.fsum(math.log(float(values[tuple(selected[v] for v in scope)]))
                                      for scope, values in normalized.items())
    reconstructed_weight = normalized_log_weight + metrics["removed_log_offset"]
    log_z = reconstructed_weight - conditional_log_probability
    metrics.update({"selected_assignment": selected,
                    "conditional_log_probability": conditional_log_probability,
                    "original_assignment_log_weight": original_log_weight,
                    "normalized_assignment_log_weight": normalized_log_weight,
                    "offset_reconstruction_delta": reconstructed_weight - original_log_weight,
                    "original_weight_identity_log_z": original_log_weight - conditional_log_probability,
                    "kernel_elapsed_seconds": time.perf_counter() - computing,
                    "elapsed_seconds": time.perf_counter() - started})
    if not math.isfinite(log_z):
        return _base_result("numerical_failure", metrics)
    return _base_result("complete", metrics, log_z=log_z)
