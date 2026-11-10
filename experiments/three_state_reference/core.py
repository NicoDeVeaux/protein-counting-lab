"""Stdlib-only source decoder and direct Decimal weighted enumeration."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import platform
import re
import resource
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Mapping


STATES = ("complex", "protein", "ligand")
SEMANTICS = ("source_binary64", "source_decimal_lexeme", "stored_binary64_log")
SUMMARY_KEYS = (
    "residues", "residues_to_id", "subunit_residue_ids",
    "residue_id_to_dissociated_subunit", "residue_aminoAcids",
    "residue_aminoAcids_to_id", "residue_id_to_conformationVariable_id",
    "residue_to_conformations", "residue_conformation_pair_to_id",
    "residue_conformation_pair_to_aminoAcid", "residue_to_maxAminoAcid_rotamers",
)


class SourceError(ValueError):
    """The archived encoding cannot establish an unambiguous target."""


class ReferenceLimit(RuntimeError):
    def __init__(self, status: str, reason: str):
        super().__init__(reason)
        self.status = status


@dataclass(frozen=True)
class ReferenceLimits:
    max_assignments: int = 1_000_000
    state_seconds: float = 60.0
    total_seconds: float = 300.0
    memory_mib: int = 512


@dataclass(frozen=True)
class RawFactor:
    source_id: int
    scope: tuple[int, ...]
    lexemes: tuple[str, ...]
    weights: tuple[float, ...]


@dataclass(frozen=True)
class RawModel:
    domains: tuple[int, ...]
    factors: tuple[RawFactor, ...]


@dataclass(frozen=True)
class Archive:
    path: str
    case_id: str
    model: RawModel
    selectors: tuple[int, ...]
    state_variables: Mapping[str, tuple[int, ...]]
    summary: dict
    source_hashes: dict


@dataclass(frozen=True)
class SlicedFactor:
    source_id: int
    scope: tuple[int, ...]
    source_indices: tuple[int, ...]
    lexemes: tuple[str, ...]
    weights: tuple[float, ...]


@dataclass(frozen=True)
class ConditionedState:
    state: str
    sequence: Mapping[int, str]
    variables: tuple[int, ...]
    domain_maps: tuple[tuple[int, ...], ...]
    factors: tuple[SlicedFactor, ...]
    proof: dict


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _tokens(text: str) -> list[str]:
    return re.sub(r"#.*", "", text).split()


def parse_uai(text: str) -> RawModel:
    tokens = iter(_tokens(text))
    try:
        if next(tokens) != "MARKOV":
            raise SourceError("only MARKOV UAI is supported")
        count = int(next(tokens))
        if count < 0:
            raise SourceError("negative variable count")
        domains = tuple(int(next(tokens)) for _ in range(count))
        if any(d <= 0 for d in domains):
            raise SourceError("domains must be positive")
        factor_count = int(next(tokens))
        if factor_count < 0:
            raise SourceError("negative factor count")
        scopes = []
        for _ in range(factor_count):
            arity = int(next(tokens))
            if arity < 0:
                raise SourceError("negative factor arity")
            scope = tuple(int(next(tokens)) for _ in range(arity))
            if len(set(scope)) != len(scope) or any(v < 0 or v >= count for v in scope):
                raise SourceError("invalid or repeated factor variable")
            scopes.append(scope)
        factors = []
        for source_id, scope in enumerate(scopes):
            size = int(next(tokens))
            if size != math.prod(domains[v] for v in scope):
                raise SourceError(f"factor {source_id}: incorrect table size")
            lexemes = tuple(next(tokens) for _ in range(size))
            weights = tuple(float(x) for x in lexemes)
            for token, weight in zip(lexemes, weights):
                exact = Decimal(token)
                if not exact.is_finite() or exact < 0 or not math.isfinite(weight) or weight < 0:
                    raise SourceError(f"factor {source_id}: expected finite nonnegative weight")
                if exact != 0 and weight == 0:
                    raise SourceError("adapter would underflow a positive source decimal")
            factors.append(RawFactor(source_id, scope, lexemes, weights))
        if next(tokens, None) is not None:
            raise SourceError("trailing UAI tokens")
        return RawModel(domains, tuple(factors))
    except (StopIteration, ValueError, ArithmeticError) as exc:
        if isinstance(exc, SourceError):
            raise
        raise SourceError(f"invalid UAI: {exc}") from exc


def parse_sum(text: str) -> dict[str, tuple[int, ...]]:
    tokens = iter(_tokens(text))
    try:
        denominator_count = int(next(tokens))
        groups = []
        for _ in range(denominator_count):
            size = int(next(tokens))
            if size < 0:
                raise SourceError("negative sum group size")
            groups.append(tuple(int(next(tokens)) for _ in range(size)))
        numerator_count = int(next(tokens))
        numerators = []
        for _ in range(numerator_count):
            size = int(next(tokens))
            if size < 0:
                raise SourceError("negative sum group size")
            numerators.append(tuple(int(next(tokens)) for _ in range(size)))
        if denominator_count != 2 or numerator_count != 1:
            raise SourceError("expected protein, ligand denominator groups and one complex group")
        if next(tokens, None) is not None:
            raise SourceError("trailing sum tokens")
        result = dict(zip(STATES, (numerators[0], groups[0], groups[1])))
        combined = tuple(v for state in STATES for v in result[state])
        if len(combined) != len(set(combined)):
            raise SourceError("sum groups overlap or repeat variables")
        return result
    except (StopIteration, ValueError) as exc:
        if isinstance(exc, SourceError):
            raise
        raise SourceError(f"invalid sum metadata: {exc}") from exc


def parse_summary(text: str) -> dict:
    decoder = json.JSONDecoder()
    result = {}
    for name in SUMMARY_KEYS:
        matches = list(re.finditer(rf"^{name}\s*$", text, re.MULTILINE))
        if len(matches) != 1:
            raise SourceError(f"expected one summary section {name}")
        try:
            result[name], _ = decoder.raw_decode(text[matches[0].end():].lstrip())
        except ValueError as exc:
            raise SourceError(f"invalid summary section {name}") from exc
    temperature = re.search(r"Using the temperature:\s*([0-9.eE+\-]+)\s*K", text)
    gas = re.search(r"Universal Gas Constant\s+([0-9.eE+\-]+)\s+kcal\s*/\s*\(mol\s*\*\s*K\)", text)
    if not temperature or not gas:
        raise SourceError("temperature or kcal gas constant missing")
    result["temperature_kelvin"] = temperature.group(1)
    result["gas_constant_kcal_per_mol_kelvin"] = gas.group(1)
    result["normalization_statement"] = (
        "No normalization after Boltzmann conversions"
        if "No normalization after Boltzmann conversions" in text else None
    )
    return result


def load_archive(path: str | Path) -> Archive:
    path = Path(path)
    with zipfile.ZipFile(path) as source:
        names = source.namelist()
        if len(names) != len(set(names)):
            raise SourceError("duplicate ZIP member name")
        uai_names = [name for name in names if name.endswith(".uai")]
        summary_names = [name for name in names if name.endswith("uai_conversion_summary.txt")]
        if len(uai_names) != 1 or len(summary_names) != 1:
            raise SourceError("expected one UAI and one conversion summary")
        uai_name, summary_name = uai_names[0], summary_names[0]
        required = (uai_name, uai_name + ".query", uai_name + ".sum", summary_name)
        contents = {name: source.read(name) for name in required}
        # The full member inventory also identifies energy/TOML evidence without interpreting it.
        hashes = {"archive_sha256": _sha(path.read_bytes()), "members": {}}
        for name in names:
            hashes["members"][name] = _sha(contents[name] if name in contents else source.read(name))
    model = parse_uai(contents[uai_name].decode())
    query = _tokens(contents[uai_name + ".query"].decode())
    try:
        selectors = tuple(int(v) for v in query[1:])
        if not query or int(query[0]) != len(selectors) or len(set(selectors)) != len(selectors):
            raise SourceError("invalid query selector count/order")
    except ValueError as exc:
        raise SourceError("invalid query metadata") from exc
    states = parse_sum(contents[uai_name + ".sum"].decode())
    if set(selectors).intersection(v for values in states.values() for v in values):
        raise SourceError("selector is also a state conformation variable")
    declared = set(selectors).union(*(set(values) for values in states.values()))
    if declared != set(range(len(model.domains))):
        raise SourceError("query/sum metadata do not cover each UAI variable exactly once")
    summary = parse_summary(contents[summary_name].decode())
    archive = Archive(str(path.resolve()), Path(uai_name).stem, model, selectors, states, summary, hashes)
    _validate_maps(archive)
    return archive


def _pair(key: str) -> tuple[int, int]:
    match = re.fullmatch(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)", key)
    if not match:
        raise SourceError(f"invalid residue/conformer pair {key!r}")
    return int(match[1]), int(match[2])


def _validate_maps(archive: Archive) -> None:
    summary = archive.summary
    expected = {str(selector) for selector in archive.selectors}
    if set(summary["residue_aminoAcids"]) != expected:
        raise SourceError("query selector IDs do not match residue AA map IDs")
    if set(summary["residues_to_id"].values()) != set(archive.selectors):
        raise SourceError("query IDs do not match residue IDs")
    for selector in archive.selectors:
        labels = summary["residue_aminoAcids"][str(selector)]
        ids = summary["residue_aminoAcids_to_id"][str(selector)]
        if len(labels) != archive.model.domains[selector] or len(set(labels)) != len(labels):
            raise SourceError("AA label count/uniqueness differs from selector domain")
        if ids != {label: i for i, label in enumerate(labels)}:
            raise SourceError("AA label IDs disagree with declared source order")
    for state_index, state in enumerate(STATES):
        var_map = summary["residue_id_to_conformationVariable_id"][state_index]
        residues = summary["subunit_residue_ids"][state_index]
        if set(map(int, var_map)) != set(residues):
            raise SourceError("state residue IDs differ from conformation map")
        if set(var_map.values()) != set(archive.state_variables[state]):
            raise SourceError("summary state variables disagree with UAI.sum")
        pairs = {_pair(key): label for key, label in summary["residue_conformation_pair_to_aminoAcid"][state_index].items()}
        expected_pairs = set()
        for residue, variable in var_map.items():
            conformers = summary["residue_to_conformations"][state_index][residue]
            if conformers != list(range(archive.model.domains[variable])):
                raise SourceError("conformer map must account for the complete source domain")
            expected_pairs.update((int(residue), c) for c in conformers)
            for c in conformers:
                label = pairs.get((int(residue), c))
                if label not in summary["residue_aminoAcids"][residue] and label != "DUMMY":
                    raise SourceError("unmapped conformer amino-acid label")
        if set(pairs) != expected_pairs:
            raise SourceError("conformer label map has absent or extra entries")


def panel_specs(archive: Archive) -> list[dict]:
    labels = archive.summary["residue_aminoAcids"]
    baseline = {}
    chosen = None
    for selector in archive.selectors:
        available = [label for label in labels[str(selector)] if label != "DUMMY"]
        if not available:
            raise SourceError(f"selector {selector} has no non-DUMMY baseline")
        baseline[selector] = available[0]
        if chosen is None and len(available) >= 2:
            chosen = selector
    if chosen is None:
        raise SourceError("no selector has two non-DUMMY amino acids")
    return [
        {"panel_index": i, "selector": chosen, "label": label,
         "sequence": {**baseline, chosen: label}}
        for i, label in enumerate(label for label in labels[str(chosen)] if label != "DUMMY")
    ]


def _ownership(archive: Archive, scalar_owners: Mapping[int, str]) -> dict[int, str]:
    selectors = set(archive.selectors)
    owners = {}
    for factor in archive.model.factors:
        conformers = set(factor.scope) - selectors
        candidates = [state for state in STATES if conformers and conformers <= set(archive.state_variables[state])]
        if len(candidates) == 1:
            owner = candidates[0]
            if factor.source_id in scalar_owners:
                raise SourceError("explicit scalar assignment used on a non-scalar state factor")
        elif not conformers and factor.source_id in scalar_owners:
            owner = scalar_owners[factor.source_id]
            if owner not in STATES:
                raise SourceError("unknown explicit scalar state owner")
        else:
            raise SourceError(f"factor {factor.source_id} is unassigned or crosses state groups")
        owners[factor.source_id] = owner
    if set(scalar_owners) - set(owners):
        raise SourceError("scalar owner references an absent factor")
    return owners


def condition_state(
    archive: Archive, sequence: Mapping[int, str], state: str,
    scalar_owners: Mapping[int, str] | None = None,
) -> ConditionedState:
    if state not in STATES:
        raise SourceError(f"unknown state {state}")
    if set(sequence) != set(archive.selectors):
        raise SourceError("sequence must fix every shared selector exactly once")
    selector_values = {}
    for selector in archive.selectors:
        labels = archive.summary["residue_aminoAcids_to_id"][str(selector)]
        if sequence[selector] == "DUMMY" or sequence[selector] not in labels:
            raise SourceError("sequence has an absent/DUMMY template")
        selector_values[selector] = labels[sequence[selector]]
    index = STATES.index(state)
    var_map = archive.summary["residue_id_to_conformationVariable_id"][index]
    reverse = {variable: int(residue) for residue, variable in var_map.items()}
    pairs = {_pair(key): label for key, label in archive.summary["residue_conformation_pair_to_aminoAcid"][index].items()}
    variables = archive.state_variables[state]
    domain_maps = tuple(
        tuple(c for c in range(archive.model.domains[v]) if pairs[(reverse[v], c)] == sequence[reverse[v]])
        for v in variables
    )
    if any(not values for values in domain_maps):
        raise SourceError("declared sequence has no mapped conformer in a present state")
    domains_by_id = dict(zip(variables, domain_maps))
    owners = _ownership(archive, scalar_owners or {})
    exclusion_witnesses = []
    for variable, retained in domains_by_id.items():
        candidates = [
            f for f in archive.model.factors
            if owners[f.source_id] == state and variable in f.scope
            and set(f.scope) <= set(selector_values) | {variable}
        ]
        for conformer in range(archive.model.domains[variable]):
            if conformer in retained:
                continue
            witness = None
            for factor in candidates:
                source_index = 0
                for v in factor.scope:
                    value = conformer if v == variable else selector_values[v]
                    source_index = source_index * archive.model.domains[v] + value
                if factor.weights[source_index] == 0:
                    witness = {"variable": variable, "removed_conformer": conformer,
                               "source_factor": factor.source_id, "source_index": source_index,
                               "source_lexeme": factor.lexemes[source_index]}
                    break
            if witness is None:
                raise SourceError("metadata domain exclusion lacks a source exact-zero witness")
            exclusion_witnesses.append(witness)
    factors = []
    for factor in archive.model.factors:
        if owners[factor.source_id] != state:
            continue
        residual = tuple(v for v in factor.scope if v not in selector_values)
        assignments = [domains_by_id[v] if v in domains_by_id else (selector_values[v],) for v in factor.scope]
        source_indices = []
        for assignment in itertools.product(*assignments):
            offset = 0
            for variable, value in zip(factor.scope, assignment):
                offset = offset * archive.model.domains[variable] + value
            source_indices.append(offset)
        indices = tuple(source_indices)
        factors.append(SlicedFactor(
            factor.source_id, residual, indices,
            tuple(factor.lexemes[i] for i in indices), tuple(factor.weights[i] for i in indices),
        ))
    evidence = {
        "state": state, "sequence": {str(k): v for k, v in sequence.items()},
        "variables": list(variables), "domain_maps": [list(v) for v in domain_maps],
        "factor_ownership": {str(k): v for k, v in owners.items()},
        "explicit_scalar_owners": {str(k): v for k, v in (scalar_owners or {}).items()},
        "metadata_exclusion_zero_witnesses": exclusion_witnesses,
        "factors": [
            {"source_id": f.source_id, "source_scope": list(archive.model.factors[f.source_id].scope),
             "scope": list(f.scope), "source_indices": list(f.source_indices),
             "lexemes": list(f.lexemes), "binary64_hex": [v.hex() for v in f.weights],
             "stored_log_hex": [math.log(v).hex() if v > 0 else None for v in f.weights]}
            for f in factors
        ],
        "retained_factor_count": len(factors), "all_source_factors_assigned_once": True,
        "table_convention": "scope order, last scope variable changes fastest",
        "domain_rule": "every source conformer whose exact metadata label equals the shared selector; no ordinal/last-conformer exclusion",
        "no_offsets_discarded": True,
    }
    proof = {**evidence, "conditioned_source_sha256": _sha(_canonical(evidence))}
    return ConditionedState(state, dict(sequence), variables, domain_maps, tuple(factors), proof)


def _rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def verify_conditioning(
    archive: Archive, sequence: Mapping[int, str], state: str, model_json: dict,
    scalar_owners: Mapping[int, str] | None = None,
) -> dict:
    """Compare a serialized unpruned target to independently indexed source entries."""
    try:
        target = condition_state(archive, sequence, state, scalar_owners)
        allowed = {"schema_version", "model_id", "kind", "log_base", "domains", "factors", "metadata"}
        if set(model_json) - allowed:
            raise SourceError("unexpected top-level target fields could contain unverified offsets")
        if model_json.get("schema_version") != 1 or model_json.get("log_base") != "e":
            raise SourceError("target schema or log base differs")
        domains = [len(values) for values in target.domain_maps]
        if model_json.get("domains") != domains:
            raise SourceError("target domain sizes differ from retained source multiplicity")
        metadata = model_json.get("metadata", {})
        expected_metadata = {
            "source_case_id": archive.case_id,
            "source_archive_sha256": archive.source_hashes["archive_sha256"],
            "state": state, "source_variable_ids": list(target.variables),
            "source_domain_indices": {str(v): list(values) for v, values in zip(target.variables, target.domain_maps)},
            "source_factor_indices": [factor.source_id for factor in target.factors],
            "source_selector_assignment": {
                str(v): archive.summary["residue_aminoAcids_to_id"][str(v)][sequence[v]]
                for v in archive.selectors
            },
            "sequence": {residue: sequence[v] for residue, v in archive.summary["residues_to_id"].items()},
        }
        uai_hashes = [value for name, value in archive.source_hashes["members"].items() if name.endswith(".uai")]
        if len(uai_hashes) != 1:
            raise SourceError("cannot identify the source UAI member hash")
        expected_metadata["source_uai_sha256"] = uai_hashes[0]
        for key, expected in expected_metadata.items():
            if metadata.get(key) != expected:
                raise SourceError(f"target metadata {key} differs from independent source decoding")
        for key, source_key in (
            ("temperature_kelvin", "temperature_kelvin"),
            ("source_gas_constant_kcal_mol_kelvin", "gas_constant_kcal_per_mol_kelvin"),
        ):
            if float(metadata.get(key, math.nan)) != float(archive.summary[source_key]):
                raise SourceError(f"target metadata {key} differs from source")
        if metadata.get("zero_target", False):
            raise SourceError("nonempty independently mapped target was replaced by a dummy zero target")
        actual_factors = model_json.get("factors", [])
        if len(actual_factors) != len(target.factors):
            raise SourceError("a source factor/scalar is missing or an extra factor was introduced")
        positions = {v: i for i, v in enumerate(target.variables)}
        checked = 0

        def flatten_table(value, shape):
            if not shape:
                if isinstance(value, list):
                    raise SourceError("scalar source entry became a non-scalar table")
                return [value]
            if not isinstance(value, list) or len(value) != shape[0]:
                raise SourceError("target table shape differs from source axis order")
            return [entry for child in value for entry in flatten_table(child, shape[1:])]

        for actual, factor in zip(actual_factors, target.factors):
            if set(actual) != {"scope", "log_values"}:
                raise SourceError("unexpected target factor fields")
            scope = [positions[v] for v in factor.scope]
            if actual["scope"] != scope:
                raise SourceError("target factor scope/order differs from original source scope")
            flat = flatten_table(actual["log_values"], [domains[v] for v in scope])
            if len(flat) != len(factor.weights):
                raise SourceError("target entry count differs from source slice")
            for value, weight in zip(flat, factor.weights):
                if weight == 0:
                    if value is not None:
                        raise SourceError("source zero was not retained as null/-Infinity")
                elif not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or float(value).hex() != math.log(weight).hex():
                    raise SourceError("positive source entry differs from its binary64 math.log value")
                checked += 1
        return {
            "status": "pass", "state": state, "checked_numeric_entries": checked,
            "checked_source_factors": len(target.factors),
            "conditioned_source_sha256": target.proof["conditioned_source_sha256"],
            "serialized_target_sha256": _sha(_canonical(model_json)),
            "checks": "source IDs, domain multiplicity, shared sequence, factor ownership/order, every numeric entry, scalars/offsets, temperature and source identities",
        }
    except (SourceError, ValueError, TypeError, KeyError) as exc:
        return {"status": "fail", "state": state, "reason": str(exc)}


def _check_limits(deadline: float, limits: ReferenceLimits) -> None:
    if time.perf_counter() >= deadline:
        raise ReferenceLimit("timeout", "reference wall cap reached")
    if _rss_bytes() > limits.memory_mib * 1024**2:
        raise ReferenceLimit("memory/resource-policy rejection", "observed lifetime high-water RSS exceeds policy")


def _enumerate_pass(target: ConditionedState, precision: int, deadline: float, limits: ReferenceLimits) -> dict:
    sizes = tuple(len(values) for values in target.domain_maps)
    cartesian = math.prod(sizes)
    positions = {v: i for i, v in enumerate(target.variables)}
    plans = []
    for factor in target.factors:
        stride = 1
        indexed = []
        for v in reversed(factor.scope):
            indexed.append((positions[v], stride))
            stride *= sizes[positions[v]]
        plans.append((factor, tuple(indexed)))
    positive = 0
    visited = 0
    cache = {}
    with localcontext() as context:
        context.prec = precision
        context.Emax = 999_999_999
        context.Emin = -999_999_999
        sums = [Decimal(0), Decimal(0), Decimal(0)]
        for assignment in itertools.product(*(range(size) for size in sizes)):
            if visited % 256 == 0:
                _check_limits(deadline, limits)
            visited += 1
            entries = []
            for factor, indexed in plans:
                offset = sum(assignment[position] * stride for position, stride in indexed)
                weight = factor.weights[offset]
                if weight == 0:
                    break
                entries.append((weight, factor.lexemes[offset]))
            else:
                positive += 1
                products = [Decimal(1), Decimal(1), Decimal(1)]
                for weight, lexeme in entries:
                    key = (weight, lexeme)
                    converted = cache.get(key)
                    if converted is None:
                        converted = (
                            Decimal.from_float(weight), Decimal(lexeme),
                            Decimal.from_float(math.log(weight)).exp(),
                        )
                        cache[key] = converted
                    for i, value in enumerate(converted):
                        products[i] *= value
                for i in range(3):
                    sums[i] += products[i]
        _check_limits(deadline, limits)
        values = {}
        for semantics, value in zip(SEMANTICS, sums):
            values[semantics] = {"Z": str(value), "logZ": str(value.ln()) if value else "-Infinity"}
        return {
            "precision": precision, "visited_assignments": visited,
            "cartesian_assignments": cartesian, "positive_assignments": positive,
            "zero_proof": "complete source-zero-aware enumeration" if positive == 0 else None,
            "values": values,
        }


def reference_state(
    target: ConditionedState, limits: ReferenceLimits = ReferenceLimits(),
    total_deadline: float | None = None,
) -> dict:
    started = time.perf_counter()
    deadline = min(started + limits.state_seconds, total_deadline if total_deadline is not None else math.inf)
    cartesian = math.prod(len(values) for values in target.domain_maps)
    result = {
        "state": target.state, "input_sha256": target.proof["conditioned_source_sha256"],
        "planned_precisions": [90, 120], "passes": [],
        "cartesian_assignments": cartesian, "limits": vars(limits),
        "numerical_evidence": "precision agreement; not directed intervals or a certificate",
    }
    try:
        if cartesian > limits.max_assignments:
            raise ReferenceLimit("memory/resource-policy rejection", "Cartesian assignment cap exceeded before enumeration")
        for precision in (90, 120):
            result["passes"].append(_enumerate_pass(target, precision, deadline, limits))
        first, second = result["passes"]
        if first["positive_assignments"] != second["positive_assignments"]:
            raise SourceError("precision passes disagree on exact support")
        deltas = {}
        with localcontext() as context:
            context.prec = 120
            for semantics in SEMANTICS:
                one, two = (Decimal(p["values"][semantics]["logZ"]) for p in (first, second))
                deltas[semantics] = str(two - one) if one.is_finite() and two.is_finite() else "0" if one == two else None
            source_log = Decimal(second["values"]["source_binary64"]["logZ"])
            conversions = {}
            for semantics in SEMANTICS[1:]:
                value = Decimal(second["values"][semantics]["logZ"])
                conversions[semantics + "_minus_source_binary64"] = (
                    str(value - source_log) if value.is_finite() and source_log.is_finite() else "0" if value == source_log else None
                )
        result.update({
            "precision_120_minus_90_logZ": deltas,
            "conversion_logZ_differences": conversions,
            "positive_assignments": second["positive_assignments"],
            "values": second["values"],
            "status": "reference-passing success" if all(v is not None and abs(Decimal(v)) <= Decimal("1e-10") for v in deltas.values()) else "completed but unverified/incorrect",
        })
    except ReferenceLimit as exc:
        result.update(status=exc.status, reason=str(exc))
    except Exception as exc:
        result.update(status="error", reason=f"{type(exc).__name__}: {exc}")
    result["elapsed_seconds"] = time.perf_counter() - started
    result["lifetime_high_water_rss_bytes"] = _rss_bytes()
    return result


def score_states(states: Mapping[str, dict], semantics: str = "source_binary64") -> dict:
    if any(states.get(state, {}).get("status") != "reference-passing success" for state in STATES):
        return {"status": "unresolved", "reason": "missing or unsuccessful constituent reference"}
    logs = {state: Decimal(states[state]["values"][semantics]["logZ"]) for state in STATES}
    if any(logs[state] == Decimal("-Infinity") for state in ("protein", "ligand")):
        return {"status": "undefined", "logKstar": None, "reason": "zero denominator; includes 0/0"}
    if logs["complex"] == Decimal("-Infinity"):
        return {"status": "zero numerator", "logKstar": "-Infinity"}
    with localcontext() as context:
        context.prec = 120
        return {"status": "finite", "logKstar": str(logs["complex"] - logs["protein"] - logs["ligand"])}


def _scores_with_precision_evidence(states: Mapping[str, dict]) -> dict:
    scores = {semantics: score_states(states, semantics) for semantics in SEMANTICS}
    if any(states[state].get("status") != "reference-passing success" for state in STATES):
        return scores
    with localcontext() as context:
        context.prec = 120
        for semantics, score in scores.items():
            passes = []
            for pass_index, precision in enumerate((90, 120)):
                pass_states = {
                    state: {"status": "reference-passing success", "values": states[state]["passes"][pass_index]["values"]}
                    for state in STATES
                }
                passes.append({"precision": precision, **score_states(pass_states, semantics)})
            score["passes"] = passes
            score["precision_120_minus_90_logKstar"] = (
                str(Decimal(passes[1]["logKstar"]) - Decimal(passes[0]["logKstar"]))
                if score["status"] == "finite" else "0" if score["status"] == "zero numerator" else None
            )
            source = scores["source_binary64"]
            score["logKstar_minus_source_binary64"] = (
                str(Decimal(score["logKstar"]) - Decimal(source["logKstar"]))
                if score["status"] == source["status"] == "finite" else "0" if score["status"] == source["status"] == "zero numerator" else None
            )
    return scores


def reference_panel(
    archive: Archive, limits: ReferenceLimits = ReferenceLimits(),
    scalar_owners: Mapping[int, str] | None = None,
    *, started_monotonic: float | None = None,
) -> dict:
    started = time.perf_counter() if started_monotonic is None else started_monotonic
    deadline = started + limits.total_seconds
    specs = panel_specs(archive)
    rows = []
    for spec in specs:
        states = {}
        for state in STATES:
            identity = {"case_id": archive.case_id, "panel_index": spec["panel_index"], "label": spec["label"], "state": state}
            try:
                _check_limits(deadline, limits)
                target = condition_state(archive, spec["sequence"], state, scalar_owners)
                row = {**identity, **reference_state(target, limits, deadline), "conditioning_proof": target.proof}
            except ReferenceLimit as exc:
                row = {**identity, "status": exc.status, "reason": str(exc), "passes": [], "elapsed_seconds": 0.0}
            except SourceError as exc:
                row = {**identity, "status": "unsupported conversion", "reason": str(exc), "passes": [], "elapsed_seconds": 0.0}
            except Exception as exc:
                row = {**identity, "status": "error", "reason": f"{type(exc).__name__}: {exc}", "passes": [], "elapsed_seconds": 0.0}
            states[state] = row
        rows.append({
            **spec, "sequence": {str(k): v for k, v in spec["sequence"].items()}, "states": states,
            "scores": _scores_with_precision_evidence(states),
        })
    return {
        "schema_version": 1, "campaign": "004", "kind": "independent_raw_source_decimal_reference",
        "created_utc": datetime.now(timezone.utc).isoformat(), "case_id": archive.case_id,
        "source_hashes": archive.source_hashes, "limits": vars(limits),
        "semantics": {
            "source_binary64": "sum of products of Decimal.from_float(float(source lexeme)); log applied after sum",
            "source_decimal_lexeme": "sum of products of Decimal(source lexeme); decimal-text diagnostic",
            "stored_binary64_log": "sum of products exp(Decimal.from_float(math.log(float(source lexeme)))); zero source entries remain exact zero",
            "physical_interpretation": "source-encoding arithmetic diagnostic; physical claims require the independent source-semantics gate",
            "zero_rule": "only source-represented exact zero can suppress an assignment",
            "numerics": "90/120 digit agreement, not outward-rounded interval certification",
        },
        "algorithm": "direct Cartesian enumeration; no support propagation or inference-kernel imports",
        "planned_panel": [{**spec, "sequence": {str(k): v for k, v in spec["sequence"].items()}} for spec in specs],
        "planned_state_rows": len(specs) * len(STATES), "rows": rows,
        "elapsed_seconds": time.perf_counter() - started,
        "environment": {"python": sys.version, "platform": platform.platform(), "decimal_module": "stdlib decimal"},
        "rss_policy": "getrusage lifetime high-water RSS checked every 256 assignments and between targets; rejection after observation, not instantaneous enforced ceiling",
        "lifetime_high_water_rss_bytes": _rss_bytes(),
    }
