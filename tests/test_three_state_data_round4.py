from dataclasses import replace
import itertools
import json
import math
import zipfile

import numpy as np
import pytest

from experiments.inference import brute_force
from experiments.three_state_data import SourceCase, SourceFactor, audit_case, condition_sequence, load_case


def source_case():
    constraint = np.asarray([[1.,0.,1.], [0.,1.,0.]])
    factors = [SourceFactor(pair, constraint.copy()) for pair in [(0,2),(1,3),(0,4),(1,5)]]
    factors += [SourceFactor((variable,), np.asarray(weights, dtype=float)) for variable, weights in
                [(2,[2,3,5]), (3,[7,11,13]), (4,[17,19,23]), (5,[29,31,37])]]
    factors += [SourceFactor((2,3), np.arange(1.,10.).reshape(3,3))]
    metadata = {
        "residues": ["A1", "B2"], "residues_to_id": {"A1":0,"B2":1},
        "subunit_residue_ids": [[0,1],[0],[1]], "residue_id_to_dissociated_subunit": {"0":1,"1":2},
        "residue_aminoAcids": {"0":["ALA","VAL"],"1":["GLY","SER"]},
        "residue_aminoAcids_to_id": {"0":{"ALA":0,"VAL":1},"1":{"GLY":0,"SER":1}},
        "residue_id_to_conformationVariable_id": [{"0":2,"1":3},{"0":4},{"1":5}],
        "residue_to_conformations": [{"0":[0,1,2],"1":[0,1,2]},{"0":[0,1,2]},{"1":[0,1,2]}],
        "residue_conformation_pair_to_aminoAcid": [
            {"(0, 0)":"ALA","(0, 1)":"VAL","(0, 2)":"ALA","(1, 0)":"GLY","(1, 1)":"SER","(1, 2)":"GLY"},
            {"(0, 0)":"ALA","(0, 1)":"VAL","(0, 2)":"ALA"},
            {"(1, 0)":"GLY","(1, 1)":"SER","(1, 2)":"GLY"}]}
    return SourceCase("synthetic-three-state", (2,2,3,3,3,3), tuple(factors), (0,1), ((2,3),(4,),(5,)),
                      metadata, "a"*64, "b"*64, "c"*64, 298.15, .0019891)


def write_archive(path, case, *, sum_text="2\n1 4\n1 5\n1\n2 2 3\n", normalization=True):
    sections = ["MARKOV", str(len(case.domains)), " ".join(map(str,case.domains)), str(len(case.factors))]
    sections += [str(len(f.scope))+" "+" ".join(map(str,f.scope)) for f in case.factors]
    for factor in case.factors:
        sections += [str(factor.weights.size), " ".join(map(str,factor.weights.flat))]
    summary = "Objective Type: KstarMAP\nUsing the temperature: 298.15 K\nUniversal Gas Constant 0.0019891 kcal\n"
    summary += "No normalization after Boltzmann conversions\n" if normalization else "Unknown normalization\n"
    summary += "\n".join(key+"\n"+json.dumps(value) for key,value in case.metadata.items())
    with zipfile.ZipFile(path,"w") as archive:
        archive.writestr("synthetic.uai", "\n".join(sections))
        archive.writestr("synthetic.uai.query", "2 0 1\n")
        archive.writestr("synthetic.uai.sum", sum_text)
        archive.writestr("uai_conversion_summary.txt", summary)


@pytest.mark.parametrize("assignment,expected", [
    ({0:0,1:0}, (922.,40.,66.)), ({0:1,1:0}, (318.,19.,66.)),
    ({0:0,1:1}, (484.,40.,31.)), ({0:1,1:1}, (165.,19.,31.))])
def test_conditional_three_state_partitions_match_closed_forms(assignment, expected):
    case = source_case()
    audit_case(case)
    models, proof = condition_sequence(case, assignment)
    for (name, model), value in zip(models.items(), expected):
        assert brute_force(model)["log_z"] == pytest.approx(math.log(value), abs=1e-12)
        assert proof["states"][name]["source_factor_indices"] == model.metadata["source_factor_indices"]
    observed = [brute_force(model)["log_z"] for model in models.values()]
    assert observed[0]-observed[1]-observed[2] == pytest.approx(math.log(expected[0]/expected[1]/expected[2]), abs=1e-12)


def test_source_joint_partition_is_product_not_kstar_ratio():
    case = source_case()
    assignment = {0:0,1:0}
    joint = 0.0
    for values in itertools.product(range(3),repeat=4):
        coords = assignment | dict(zip([2,3,4,5],values))
        joint += math.prod(f.weights[tuple(coords[v] for v in f.scope)] for f in case.factors)
    assert joint == 922*40*66
    assert joint != pytest.approx(922/40/66)


def test_additional_metadata_labeled_conformer_is_retained_without_index_heuristics():
    models, proof = condition_sequence(source_case(),{0:0,1:0})
    assert proof["states"]["complex"]["source_domain_indices"] == {"2":[0,2],"3":[0,2]}
    assert models["complex"].domains == (2,2)
    assert models["complex"].factors[-1].values.tolist() == [[math.log(1),math.log(3)], [math.log(7),math.log(9)]]


def test_unsorted_scope_is_preserved_and_indexed_in_source_order():
    case = source_case()
    factors = tuple(SourceFactor(tuple(reversed(f.scope)), f.weights.T.copy()) if len(f.scope)==2 else f for f in case.factors)
    modified = replace(case,factors=factors)
    audit_case(modified)
    models, _ = condition_sequence(modified,{0:0,1:0})
    assert models["complex"].factors[-1].scope == (1,0)
    assert brute_force(models["complex"])["log_z"] == pytest.approx(math.log(922), abs=1e-12)


@pytest.mark.parametrize("scope,weights", [((),np.asarray(1.)), ((0,),np.ones(2)), ((2,4),np.ones((3,3)))])
def test_unassigned_or_cross_state_factor_is_rejected(scope,weights):
    case = source_case()
    modified = replace(case,factors=case.factors+(SourceFactor(scope,weights),))
    with pytest.raises(ValueError,match="unassigned scalar/selector-only|crosses source states"):
        audit_case(modified)


def test_selector_label_constraint_mismatch_is_rejected():
    case = source_case()
    wrong = case.factors[0].weights.copy()
    wrong[0,2] = 0.0
    modified = replace(case,factors=(SourceFactor((0,2),wrong),)+case.factors[1:])
    with pytest.raises(ValueError,match="differs from exact amino-acid labels"):
        audit_case(modified)


@pytest.mark.parametrize("assignment", [{0:0}, {0:2,1:0}, {0:True,1:0}, {0:-1,1:0}])
def test_incomplete_or_invalid_sequence_assignment_is_rejected(assignment):
    with pytest.raises(ValueError):
        condition_sequence(source_case(),assignment)


def test_source_zero_and_subnormal_weights_are_preserved():
    case = source_case()
    weights = case.factors[-1].weights.copy()
    weights[0,0] = np.nextafter(0.0,1.0)
    weights[0,2] = 0.0
    modified = replace(case,factors=case.factors[:-1]+(SourceFactor((2,3),weights),))
    models,_ = condition_sequence(modified,{0:0,1:0})
    values = models["complex"].factors[-1].values
    assert math.isfinite(values[0,0]) and values[0,0] == math.log(float(weights[0,0]))
    assert values[0,1] == -math.inf


def test_archive_metadata_sum_groups_and_shapes(tmp_path):
    path=tmp_path/"source.zip"
    write_archive(path,source_case())
    loaded=load_case(path)
    assert loaded.state_variables == ((2,3),(4,),(5,))
    assert loaded.selectors == (0,1)
    assert loaded.metadata["residue_aminoAcids"]["0"] == ["ALA","VAL"]
    assert len(loaded.archive_sha256) == len(loaded.uai_sha256) == 64
    assert all(not f.weights.flags.writeable for f in loaded.factors)
    assert audit_case(loaded)["source_factor_count"] == 9


def test_disagreement_between_sum_and_summary_is_rejected(tmp_path):
    path=tmp_path/"bad.zip"
    write_archive(path,source_case(),sum_text="2\n1 5\n1 4\n1\n2 2 3\n")
    with pytest.raises(ValueError,match="disagree"):
        load_case(path)


def test_unverified_normalization_is_rejected(tmp_path):
    path=tmp_path/"bad.zip"
    write_archive(path,source_case(),normalization=False)
    with pytest.raises(ValueError,match="normalization"):
        load_case(path)


def test_conditioning_does_not_mutate_source_and_outputs_are_immutable():
    case=source_case()
    before=[f.weights.copy() for f in case.factors]
    models,_=condition_sequence(case,{0:0,1:0})
    for old,factor in zip(before,case.factors):
        assert np.array_equal(old,factor.weights)
    assert all(not f.values.flags.writeable for m in models.values() for f in m.factors)


def test_empty_template_domain_proves_zero_without_fabricating_a_conformer():
    case=source_case()
    metadata=json.loads(json.dumps(case.metadata))
    metadata["residue_aminoAcids"]["0"].append("LEU")
    metadata["residue_aminoAcids_to_id"]["0"]["LEU"]=2
    factors=tuple(SourceFactor(f.scope,np.vstack([f.weights,np.zeros(3)]))
        if f.scope in {(0,2),(0,4)} else f for f in case.factors)
    case=replace(case,domains=(3,2,3,3,3,3),factors=factors,metadata=metadata)
    audit_case(case)
    models,proof=condition_sequence(case,{0:2,1:0})
    assert brute_force(models["complex"])["log_z"] == -math.inf
    assert brute_force(models["protein"])["log_z"] == -math.inf
    assert brute_force(models["ligand"])["log_z"] == pytest.approx(math.log(66),abs=1e-12)
    assert proof["states"]["complex"]["source_domain_indices"]["2"] == []
    assert models["complex"].metadata["zero_target"]
    assert "not a physical conformation" in models["complex"].metadata["zero_target_mapping"]
