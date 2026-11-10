"""Synthetic controls for the independent campaign004 reference only."""

import json
import math
import zipfile
from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from experiments.three_state_reference.core import (
    SEMANTICS,
    Archive,
    RawFactor,
    RawModel,
    ReferenceLimits,
    SourceError,
    condition_state,
    load_archive,
    panel_specs,
    parse_sum,
    parse_uai,
    reference_panel,
    reference_state,
    score_states,
    verify_conditioning,
)


def _source(tmp_path, *, scalar=True):
    labels = ["ALA", "VAL", "HIP", "HIE", "HID", "DUMMY"]
    # The last conformation is a second real ALA state and must retain multiplicity.
    maps = [
        {"0": 2, "1": 3}, {"0": 4}, {"1": 5},
    ]
    conformation_labels = [
        {(0, 0): "ALA", (0, 1): "VAL", (0, 2): "HIP", (0, 3): "HIE", (0, 4): "HID", (0, 5): "DUMMY", (0, 6): "ALA", (1, 0): "GLY", (1, 1): "GLY"},
        {(0, 0): "ALA", (0, 1): "VAL", (0, 2): "HIP", (0, 3): "HIE", (0, 4): "HID", (0, 5): "DUMMY"},
        {(1, 0): "GLY"},
    ]
    domains = (6, 1, 7, 2, 6, 1)
    factors = []
    for selector, variable in ((0, 2), (1, 3), (0, 4), (1, 5)):
        state_index = 0 if variable in (2, 3) else 1 if variable == 4 else 2
        values = []
        for aa in range(domains[selector]):
            label = (labels if selector == 0 else ["GLY"])[aa]
            values.extend("1" if conformation_labels[state_index][(selector, c)] == label else "0" for c in range(domains[variable]))
        factors.append(((selector, variable), values))
    factors.extend([
        ((3, 2), ["1", "90", "2", "3", "4", "0", "2", "3", "90", "2", "3", "4", "0", "4"]),
        ((4,), ["2", "7", "2", "3", "4", "0"]),
        ((5,), ["3"]),
    ])
    if scalar:
        factors.append(((), ["5"]))
    summary = {
        "residues": ["A10", "B20"], "residues_to_id": {"A10": 0, "B20": 1},
        "subunit_residue_ids": [[0, 1], [0], [1]],
        "residue_id_to_dissociated_subunit": {"0": 1, "1": 2},
        "residue_aminoAcids": {"0": labels, "1": ["GLY"]},
        "residue_aminoAcids_to_id": {"0": {label: i for i, label in enumerate(labels)}, "1": {"GLY": 0}},
        "residue_id_to_conformationVariable_id": maps,
        "residue_to_conformations": [{r: list(range(domains[v])) for r, v in mapping.items()} for mapping in maps],
        "residue_conformation_pair_to_id": [{str(k): k[1] for k in mapping} for mapping in conformation_labels],
        "residue_conformation_pair_to_aminoAcid": [{str(k): v for k, v in mapping.items()} for mapping in conformation_labels],
        "residue_to_maxAminoAcid_rotamers": [{r: domains[v] for r, v in mapping.items()} for mapping in maps],
    }
    summary_text = (
        "Using the temperature: 298.15 K (25.0 C)\n"
        "Using the Universal Gas Constant 0.0019891 kcal / (mol * K) for the Boltzman constant\n"
        "No normalization after Boltzmann conversions\n"
        + "\n".join(name + "\n" + json.dumps(value, indent=2) for name, value in summary.items())
    )
    parts = ["MARKOV", str(len(domains)), " ".join(map(str, domains)), str(len(factors))]
    parts.extend(" ".join(map(str, (len(scope), *scope))) for scope, _ in factors)
    for _, values in factors:
        parts.extend((str(len(values)), " ".join(values)))
    path = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("synthetic.uai", "\n".join(parts))
        z.writestr("synthetic.uai.query", "2 0 1")
        z.writestr("synthetic.uai.sum", "# comment\n2 1 4 1 5 1 2 2 3")
        z.writestr("uai_conversion_summary.txt", summary_text)
    return load_archive(path)


def _baseline(archive):
    return panel_specs(archive)[0]["sequence"]


def test_shared_selectors_asymmetric_scope_and_real_last_conformer(tmp_path):
    archive = _source(tmp_path)
    sequence = _baseline(archive)
    target = condition_state(archive, sequence, "complex", {7: "complex"})
    assert target.variables == (2, 3)
    assert target.domain_maps == ((0, 6), (0, 1))
    assert target.factors[2].scope == (3, 2)
    assert target.factors[2].source_indices == (0, 6, 7, 13)
    assert target.factors[2].weights == (1.0, 2.0, 3.0, 4.0)
    result = reference_state(target)
    assert result["status"] == "reference-passing success"
    assert result["positive_assignments"] == 4
    assert Decimal(result["values"]["source_binary64"]["Z"]) == 50
    assert result["precision_120_minus_90_logZ"]["source_binary64"] is not None
    # Ligand has no selector 0: its local variable is 5, not selector index 1.
    ligand = condition_state(archive, sequence, "ligand", {7: "complex"})
    assert ligand.variables == (5,) and ligand.domain_maps == ((0,),)
    assert Decimal(reference_state(ligand)["values"]["source_binary64"]["Z"]) == 3


def test_direct_three_state_ratio_and_full_panel_no_dummy(tmp_path):
    archive = _source(tmp_path)
    result = reference_panel(archive, scalar_owners={7: "complex"})
    assert result["planned_state_rows"] == 15
    assert [row["label"] for row in result["rows"]] == ["ALA", "VAL", "HIP", "HIE", "HID"]
    baseline = result["rows"][0]
    assert all(v["status"] == "reference-passing success" for v in baseline["states"].values())
    assert baseline["states"]["complex"]["positive_assignments"] == 4
    with localcontext() as context:
        context.prec = 120
        expected = (Decimal(50) / Decimal(6)).ln()
        assert abs(Decimal(baseline["scores"]["source_binary64"]["logKstar"]) - expected) < Decimal("1e-110")
    assert baseline["states"]["protein"]["conditioning_proof"]["variables"] == [4]
    assert {"HIP", "HIE", "HID"} <= {row["label"] for row in result["rows"]}
    assert all(len(h) == 64 for h in result["source_hashes"]["members"].values())


def test_scalar_ownership_required_and_cross_state_factor_rejected(tmp_path):
    archive = _source(tmp_path)
    with pytest.raises(SourceError, match="unassigned"):
        condition_state(archive, _baseline(archive), "complex")
    bad_factor = RawFactor(8, (2, 4), ("1",) * 42, (1.0,) * 42)
    bad = replace(archive, model=RawModel(archive.model.domains, (*archive.model.factors, bad_factor)))
    with pytest.raises(SourceError, match="crosses state"):
        condition_state(bad, _baseline(bad), "protein", {7: "complex"})


def test_metadata_filter_requires_actual_source_zero_witness(tmp_path):
    archive = _source(tmp_path)
    factor = archive.model.factors[0]
    altered = list(factor.weights)
    # Source row now permits VAL conformer 1 under ALA selector 0.
    altered[1] = 1.0
    lexemes = list(factor.lexemes)
    lexemes[1] = "1"
    invalid = replace(factor, weights=tuple(altered), lexemes=tuple(lexemes))
    archive = replace(archive, model=RawModel(archive.model.domains, (invalid, *archive.model.factors[1:])))
    with pytest.raises(SourceError, match="exact-zero witness"):
        condition_state(archive, _baseline(archive), "complex", {7: "complex"})


@pytest.mark.parametrize("zero_states,expected", [
    (("complex",), "zero numerator"), (("protein",), "undefined"),
    (("ligand",), "undefined"), (("complex", "protein", "ligand"), "undefined"),
])
def test_ratio_zero_rules(tmp_path, zero_states, expected):
    archive = _source(tmp_path)
    states = {}
    for state in ("complex", "protein", "ligand"):
        target = condition_state(archive, _baseline(archive), state, {7: "complex"})
        if state in zero_states:
            factor = target.factors[0]
            zero = replace(factor, lexemes=("0",) * len(factor.lexemes), weights=(0.0,) * len(factor.weights))
            target = replace(target, factors=(zero, *target.factors[1:]))
        states[state] = reference_state(target)
        assert states[state]["status"] == "reference-passing success"
        if state in zero_states:
            assert states[state]["positive_assignments"] == 0
            assert states[state]["passes"][0]["zero_proof"] == "complete source-zero-aware enumeration"
    score = score_states(states)
    assert score["status"] == expected
    assert score["logKstar"] == ("-Infinity" if expected == "zero numerator" else None)


def test_tiny_positive_and_semantics_discrepancy(tmp_path):
    archive = _source(tmp_path)
    target = condition_state(archive, _baseline(archive), "ligand", {7: "complex"})
    factor = target.factors[-1]
    smallest = float.fromhex("0x0.0000000000001p-1022")
    target = replace(target, factors=(*target.factors[:-1], replace(factor, lexemes=(repr(smallest),), weights=(smallest,))))
    result = reference_state(target)
    assert result["positive_assignments"] == 1
    for semantics in SEMANTICS:
        assert Decimal(result["values"][semantics]["Z"]) > 0
        assert Decimal(result["values"][semantics]["logZ"]).is_finite()
    assert Decimal(result["conversion_logZ_differences"]["stored_binary64_log_minus_source_binary64"]) != 0
    assert all(abs(Decimal(value)) < Decimal("1e-10") for value in result["precision_120_minus_90_logZ"].values())


def test_literal_zero_not_restored_and_positive_adapter_underflow_rejected():
    assert parse_uai("MARKOV 1 1 1 1 0 1 0.0").factors[0].weights == (0.0,)
    with pytest.raises(SourceError, match="underflow"):
        parse_uai("MARKOV 1 1 1 1 0 1 1e-999")
    with pytest.raises(SourceError, match="finite nonnegative"):
        parse_uai("MARKOV 1 1 1 1 0 1 NaN")


def test_caps_preserve_all_planned_records(tmp_path):
    archive = _source(tmp_path)
    result = reference_panel(archive, ReferenceLimits(max_assignments=1), {7: "complex"})
    assert len(result["rows"]) == 5
    assert sum(len(row["states"]) for row in result["rows"]) == 15
    assert result["rows"][0]["states"]["complex"]["status"] == "memory/resource-policy rejection"
    assert result["rows"][0]["scores"]["source_binary64"]["status"] == "unresolved"
    expired = reference_panel(archive, ReferenceLimits(total_seconds=0.000001), {7: "complex"}, started_monotonic=0)
    assert len(expired["rows"]) == 5
    assert all(state["status"] == "timeout" for row in expired["rows"] for state in row["states"].values())


def test_sum_group_order_and_overlap():
    assert parse_sum("2 1 4 2 5 6 1 3 1 2 3") == {"complex": (1, 2, 3), "protein": (4,), "ligand": (5, 6)}
    with pytest.raises(SourceError, match="overlap"):
        parse_sum("2 1 4 1 5 1 2 4 6")


def test_unfixed_shared_selector_is_error(tmp_path):
    archive = _source(tmp_path)
    with pytest.raises(SourceError, match="every shared selector"):
        condition_state(archive, {0: "ALA"}, "complex", {7: "complex"})


def test_parser_retains_scalar_and_rejects_wrong_size():
    model = parse_uai("MARKOV 0 1 0 1 2.75")
    assert model.domains == () and model.factors[0].scope == ()
    assert model.factors[0].weights == (2.75,)
    with pytest.raises(SourceError, match="incorrect table size"):
        parse_uai("MARKOV 1 2 1 1 0 1 1")


def test_independent_serialized_entry_and_scalar_verification(tmp_path):
    archive = _source(tmp_path)
    sequence = _baseline(archive)
    target = condition_state(archive, sequence, "complex", {7: "complex"})
    # Construct the advertised external JSON contract, without importing its writer.
    payload = {
        "schema_version": 1, "model_id": "synthetic-complex", "kind": "synthetic", "log_base": "e",
        "domains": [2, 2],
        "factors": [
            {"scope": [0], "log_values": [0.0, 0.0]},
            {"scope": [1], "log_values": [0.0, 0.0]},
            {"scope": [1, 0], "log_values": [[0.0, math.log(2)], [math.log(3), math.log(4)]]},
            {"scope": [], "log_values": math.log(5)},
        ],
        "metadata": {
            "source_case_id": "synthetic", "source_archive_sha256": archive.source_hashes["archive_sha256"],
            "source_uai_sha256": archive.source_hashes["members"]["synthetic.uai"], "state": "complex",
            "sequence": {"A10": "ALA", "B20": "GLY"},
            "source_selector_assignment": {"0": 0, "1": 0}, "source_variable_ids": [2, 3],
            "source_domain_indices": {"2": [0, 6], "3": [0, 1]}, "source_factor_indices": [0, 1, 4, 7],
            "temperature_kelvin": 298.15, "source_gas_constant_kcal_mol_kelvin": 0.0019891,
            "zero_target": False,
        },
    }
    result = verify_conditioning(archive, sequence, "complex", payload, {7: "complex"})
    assert result["status"] == "pass"
    assert result["checked_numeric_entries"] == 9
    assert result["conditioned_source_sha256"] == target.proof["conditioned_source_sha256"]
    payload["factors"][-1]["log_values"] = 0.0
    assert verify_conditioning(archive, sequence, "complex", payload, {7: "complex"})["status"] == "fail"
    payload["factors"][-1]["log_values"] = math.log(5)
    payload["factors"][2]["scope"] = [0, 1]
    assert verify_conditioning(archive, sequence, "complex", payload, {7: "complex"})["status"] == "fail"
    payload["factors"][2]["scope"] = [1, 0]
    payload["factors"].pop()
    assert verify_conditioning(archive, sequence, "complex", payload, {7: "complex"})["status"] == "fail"
