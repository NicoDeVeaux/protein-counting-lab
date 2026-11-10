"""Preserve source Boltzmann weights and state groups during sequence conditioning."""

from dataclasses import dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import zipfile

import numpy as np

from experiments.inference import Factor, Model

STATES = ("complex", "protein", "ligand")
VERSION = 1


@dataclass(frozen=True)
class SourceFactor:
    scope: tuple[int, ...]
    weights: np.ndarray


@dataclass(frozen=True)
class SourceCase:
    case_id: str
    domains: tuple[int, ...]
    factors: tuple[SourceFactor, ...]
    selectors: tuple[int, ...]
    state_variables: tuple[tuple[int, ...], ...]
    metadata: dict
    archive_sha256: str
    uai_sha256: str
    summary_sha256: str
    temperature_kelvin: float
    gas_constant: float


def _named(text, name):
    match = re.search(r"^"+re.escape(name)+r"\s*$", text, re.M)
    if match is None:
        raise ValueError("Missing conversion metadata: "+name)
    return json.JSONDecoder().raw_decode(text[match.end():].lstrip())[0]


def _uai(blob):
    tokens = iter(blob.decode().split())
    if next(tokens) != "MARKOV":
        raise ValueError("Expected unnormalized MARKOV source factors")
    count = int(next(tokens))
    domains = tuple(int(next(tokens)) for _ in range(count))
    if any(q <= 0 for q in domains):
        raise ValueError("Nonpositive source domain")
    count = int(next(tokens))
    scopes = [tuple(int(next(tokens)) for _ in range(int(next(tokens)))) for _ in range(count)]
    factors = []
    for scope in scopes:
        if len(set(scope)) != len(scope) or any(v < 0 or v >= len(domains) for v in scope):
            raise ValueError("Invalid source scope")
        count = int(next(tokens))
        shape = tuple(domains[v] for v in scope)
        if count != math.prod(shape):
            raise ValueError("Source table length differs from scope shape")
        weights = np.fromiter((float(next(tokens)) for _ in range(count)), dtype=np.float64, count=count).reshape(shape)
        if np.any(weights < 0) or not np.isfinite(weights).all():
            raise ValueError("Source weights must be finite and nonnegative")
        weights.flags.writeable = False
        factors.append(SourceFactor(scope, weights))
    if next(tokens, None) is not None:
        raise ValueError("Trailing source UAI tokens")
    return domains, tuple(factors)


def _sum_groups(blob):
    text = "\n".join(line.split("#", 1)[0] for line in blob.decode().splitlines())
    tokens = iter(text.split())
    groups = []
    for _ in range(2):
        count = int(next(tokens))
        groups.append(tuple(tuple(int(next(tokens)) for _ in range(int(next(tokens)))) for _ in range(count)))
    if next(tokens, None) is not None:
        raise ValueError("Trailing .sum group tokens")
    denominator, numerator = groups
    if len(denominator) != 2 or len(numerator) != 1:
        raise ValueError("Pilot requires exactly one bound and two unbound groups")
    return (numerator[0], *denominator)


def load_case(path):
    path = Path(path)
    blob = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".uai")]
        if len(names) != 1:
            raise ValueError("Expected exactly one UAI source model")
        name = names[0]
        uai = archive.read(name)
        summary_blob = archive.read("uai_conversion_summary.txt")
        summary = summary_blob.decode()
        domains, factors = _uai(uai)
        query = [int(value) for value in archive.read(name+".query").decode().split()]
        if not query or query[0] != len(query)-1:
            raise ValueError("Malformed source query selector list")
        selectors = tuple(query[1:])
        variables = _sum_groups(archive.read(name+".sum"))
        fields = ("residues", "residues_to_id", "subunit_residue_ids", "residue_id_to_dissociated_subunit",
                  "residue_aminoAcids", "residue_aminoAcids_to_id", "residue_id_to_conformationVariable_id",
                  "residue_to_conformations", "residue_conformation_pair_to_aminoAcid")
        metadata = {field: _named(summary, field) for field in fields}
        mapped = tuple(tuple(int(value) for value in group.values())
                       for group in metadata["residue_id_to_conformationVariable_id"])
        if variables != mapped:
            raise ValueError("Author .sum groups disagree with conversion-summary state order")
        if "No normalization after Boltzmann conversions" not in summary:
            raise ValueError("Unverified source normalization convention")
        temperature = re.search(r"Using the temperature:\s*([0-9.eE+-]+)\s*K", summary)
        gas_constant = re.search(r"Universal Gas Constant\s+([0-9.eE+-]+)\s*kcal", summary)
        if temperature is None or gas_constant is None or "Objective Type: KstarMAP" not in summary:
            raise ValueError("Missing source objective, temperature or gas constant")
    sha = lambda value: hashlib.sha256(value).hexdigest()
    case = SourceCase(Path(name).stem, domains, factors, selectors, variables, metadata,
                      sha(blob), sha(uai), sha(summary_blob), float(temperature[1]), float(gas_constant[1]))
    if (not math.isfinite(case.temperature_kelvin) or case.temperature_kelvin <= 0
            or not math.isfinite(case.gas_constant) or case.gas_constant <= 0):
        raise ValueError("Source temperature and gas constant must be finite and positive")
    audit_case(case)
    return case


def _state_factor_indices(case):
    selectors = set(case.selectors)
    result = [[] for _ in STATES]
    for index, factor in enumerate(case.factors):
        touched = [state for state, variables in enumerate(case.state_variables) if set(factor.scope) & set(variables)]
        if len(touched) != 1:
            raise ValueError(f"Factor {index} is unassigned scalar/selector-only or crosses source states")
        state = touched[0]
        if not set(factor.scope) <= selectors | set(case.state_variables[state]):
            raise ValueError(f"Factor {index} has an unrecognized variable")
        result[state].append(index)
    return result


def audit_case(case):
    meta = case.metadata
    if len(meta["residues"]) != len(case.selectors) or set(case.selectors) != set(range(len(meta["residues"]))):
        raise ValueError("Source selector IDs do not identify residue metadata")
    all_variables = list(case.selectors) + [v for group in case.state_variables for v in group]
    if len(set(all_variables)) != len(all_variables) or set(all_variables) != set(range(len(case.domains))):
        raise ValueError("Source selectors/state groups are not a disjoint full variable partition")
    state_factors = _state_factor_indices(case)
    checked = 0
    last_conformers = []
    for state, group in enumerate(meta["residue_id_to_conformationVariable_id"]):
        subunit = tuple(int(residue) for residue in group)
        if tuple(meta["subunit_residue_ids"][state]) != subunit:
            raise ValueError("Subunit residue membership differs from state map")
        for residue, variable_raw in group.items():
            variable, selector = int(variable_raw), int(residue)
            names = meta["residue_aminoAcids"][residue]
            if len(names) != case.domains[selector] or len(set(names)) != len(names):
                raise ValueError("Amino-acid selector labels are missing or repeated")
            if meta["residue_aminoAcids_to_id"][residue] != {name:index for index,name in enumerate(names)}:
                raise ValueError("Amino-acid selector lookup disagrees with declared label order")
            if state and int(meta["residue_id_to_dissociated_subunit"][residue]) != state:
                raise ValueError("Residue dissociated-subunit mapping disagrees with state membership")
            declared = meta["residue_to_conformations"][state][residue]
            if declared != list(range(case.domains[variable])):
                raise ValueError("Conformation metadata does not cover exact source domain")
            labels = [meta["residue_conformation_pair_to_aminoAcid"][state][str((selector, c))]
                      for c in declared]
            if not set(labels) <= set(names):
                raise ValueError("Conformation has an unknown amino-acid label")
            constraints = [case.factors[i] for i in state_factors[state] if selector in case.factors[i].scope]
            if len(constraints) != 1 or set(constraints[0].scope) != {selector, variable}:
                raise ValueError("Expected one explicit residue/conformation selector constraint")
            constraint = constraints[0]
            for aa, name in enumerate(names):
                for conf, label in enumerate(labels):
                    coords = {selector: aa, variable: conf}
                    value = constraint.weights[tuple(coords[v] for v in constraint.scope)]
                    if value != float(name == label):
                        raise ValueError("Source selector constraint differs from exact amino-acid labels")
                    checked += 1
            last_conformers.append({"state": STATES[state], "residue": meta["residues"][selector],
                                    "index": declared[-1], "amino_acid": labels[-1]})
    if set(meta["subunit_residue_ids"][1]) & set(meta["subunit_residue_ids"][2]):
        raise ValueError("Unbound residues overlap")
    if set(meta["subunit_residue_ids"][0]) != set(meta["subunit_residue_ids"][1]) | set(meta["subunit_residue_ids"][2]):
        raise ValueError("Bound/unbound residue identities differ")
    return {"case_id": case.case_id, "archive_sha256": case.archive_sha256,
        "uai_sha256": case.uai_sha256, "summary_sha256": case.summary_sha256,
        "states": {name: {"source_variables": list(variables), "source_factor_indices": indices}
                   for name, variables, indices in zip(STATES, case.state_variables, state_factors)},
        "selector_labels": {str(selector): meta["residue_aminoAcids"][str(selector)] for selector in case.selectors},
        "source_factor_count": len(case.factors), "all_factors_assigned_exactly_once": True,
        "source_variable_count": len(case.domains), "selector_constraint_entries_checked": checked,
        "source_zero_entries": sum(int(np.count_nonzero(f.weights == 0)) for f in case.factors),
        "scalar_or_selector_only_factors": [], "cross_state_factors": [],
        "temperature_kelvin": case.temperature_kelvin, "gas_constant_kcal_mol_kelvin": case.gas_constant,
        "normalization": "None after source Boltzmann conversion", "last_conformation_labels": last_conformers,
        "objective": "Source-defined log K*=log Z_complex-log Z_protein-log Z_ligand from the declared .sum groups.",
        "limitations": ["Source energy-to-weight underflow zeros remain source zeros; they are not recovered.",
                        "Absolute physical affinity or force-field calibration is not established.",
                        "Residue templates include separate histidine protonation states; no dummy conformation is inferred by numerical index."]}


def condition_sequence(case, assignment):
    if not isinstance(case, SourceCase):
        case = load_case(case)
    assignment = {int(key): value for key, value in assignment.items()}
    if set(assignment) != set(case.selectors):
        raise ValueError("Every shared source selector must be assigned exactly once")
    for selector, value in assignment.items():
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < case.domains[selector]:
            raise ValueError("Invalid shared selector assignment")
    state_factors = _state_factor_indices(case)
    sequence = {case.metadata["residues"][selector]: case.metadata["residue_aminoAcids"][str(selector)][value]
                for selector, value in sorted(assignment.items())}
    models, states = {}, {}
    for state, (name, variables, indices) in enumerate(zip(STATES, case.state_variables, state_factors)):
        selected = set(variables)
        allowed = {v: list(range(case.domains[v])) for v in variables}
        for index in indices:
            factor = case.factors[index]
            conf_scope = [v for v in factor.scope if v in selected]
            if set(factor.scope) & set(case.selectors):
                if len(conf_scope) != 1:
                    raise ValueError("Unsupported selector constraint shape")
                variable = conf_scope[0]
                allowed[variable] = [value for value in allowed[variable]
                    if factor.weights[tuple((assignment | {variable: value})[v] for v in factor.scope)] > 0]
        empty = [v for v in variables if not allowed[v]]
        remap = {variable: i for i, variable in enumerate(variables)}
        factors = []
        if empty:
            values = np.asarray(-math.inf, dtype=np.float64)
            values.flags.writeable = False
            factors = [Factor((), values)]
            domains = tuple(1 for _ in variables)
        else:
            domains = tuple(len(allowed[v]) for v in variables)
            for index in indices:
                factor = case.factors[index]
                conf_scope = tuple(v for v in factor.scope if v in selected)
                logs = []
                for combination in itertools.product(*(allowed[v] for v in conf_scope)):
                    coords = assignment | dict(zip(conf_scope, combination))
                    weight = float(factor.weights[tuple(coords[v] for v in factor.scope)])
                    logs.append(-math.inf if weight == 0 else math.log(weight))
                values = np.asarray(logs, dtype=np.float64).reshape(tuple(len(allowed[v]) for v in conf_scope))
                values.flags.writeable = False
                factors.append(Factor(tuple(remap[v] for v in conf_scope), values))
        metadata = {"source_case_id": case.case_id, "source_archive_sha256": case.archive_sha256,
            "source_uai_sha256": case.uai_sha256, "state": name, "sequence": sequence,
            "source_selector_assignment": {str(v): assignment[v] for v in case.selectors},
            "source_variable_ids": list(variables), "source_domain_indices": {str(v): allowed[v] for v in variables},
            "source_factor_indices": indices, "temperature_kelvin": case.temperature_kelvin,
            "source_gas_constant_kcal_mol_kelvin": case.gas_constant,
            "conditioning_policy": "Remove only selector-inconsistent zero-weight rotamers; retain all compatible conformation indices, including additional metadata-labeled conformers. Their coordinate origin is not inferred from numerical index.",
            "zero_target": bool(empty), "zero_target_source_variables": empty,
            "zero_target_mapping": "Dummy singleton output axes are not a physical conformation witness." if empty else None,
            "source_zero_policy": "Every source zero retained; no new cutoff or underflow conversion.",
            "score_scope": "Represented source computational K* score; no experimental affinity claim."}
        suffix = "-".join(str(assignment[v]) for v in case.selectors)
        models[name] = Model(domains, tuple(factors), case.case_id+"__selectors_"+suffix+"__"+name,
                             "published_computational_model", metadata, case.uai_sha256)
        states[name] = {"source_variable_ids": list(variables), "source_factor_indices": indices,
            "source_domain_indices": {str(v): allowed[v] for v in variables},
            "state_domains": list(domains), "configuration_count": str(math.prod(domains)),
            "zero_target": bool(empty), "selector_zero_domain_proof": empty}
    return models, {"schema_version": 1, "version": VERSION, "case_id": case.case_id,
        "archive_sha256": case.archive_sha256, "uai_sha256": case.uai_sha256,
        "selector_assignment": {str(v): assignment[v] for v in case.selectors}, "sequence": sequence,
        "states": states, "source_factors_assigned_exactly_once": True,
        "log_conversion": "math.log of each positive source binary64 weight; source zeros map to -Infinity; no cutoff.",
        "scope": "Exact source selector restriction and state-factor partition; numerical target is stored binary64 logarithms, not restored unrounded physical energies."}
