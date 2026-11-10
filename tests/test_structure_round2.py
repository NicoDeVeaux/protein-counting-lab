from fractions import Fraction
import itertools
import math

import numpy as np

from experiments.inference import brute_force, model_from_dict
from experiments.structure import simplify_model, structure_summary, model_to_dict


def model(domains, factors):
    return model_from_dict({"domains": domains, "factors": factors})


def exact_assignment_log(model, assignment):
    values = [float(f.values[tuple(assignment[v] for v in f.scope)]) for f in model.factors]
    return None if -math.inf in values else sum((Fraction(v) for v in values), Fraction(0))


def test_exact_simplification_retains_every_assignment_and_domain():
    source = model([2, 3, 2, 2], [
        {"scope": [0, 1], "log_values": [[1, 2, 3], [2, 3, 4]]},
        {"scope": [1, 2], "log_values": [[0, None], [1, None], [2, None]]},
        {"scope": [2, 3], "log_values": [[4, 4], [4, 4]]},
    ])
    reduced, changes = simplify_model(source)
    assert reduced.domains == source.domains
    assert changes
    for assignment in itertools.product(*(range(d) for d in source.domains)):
        assert exact_assignment_log(source, assignment) == exact_assignment_log(reduced, assignment)
    assert math.isclose(brute_force(source)["log_z"], brute_force(reduced)["log_z"], abs_tol=1e-12)
    assert model_to_dict(reduced)["domains"] == [2, 3, 2, 2]


def test_near_separable_floats_are_not_silently_approximated():
    source = model([2, 2], [{"scope": [0, 1], "log_values": [[.1, .2], [.3, .4]]}])
    reduced, changes = simplify_model(source)
    assert changes == []
    assert reduced.factors[0].scope == (0, 1)


def test_constant_zero_support_is_retained():
    source = model([2, 3], [{"scope": [0, 1], "log_values": [None] * 6}])
    reduced, changes = simplify_model(source)
    assert changes[0]["kind"] == "constant_factor"
    assert brute_force(source)["log_z"] == brute_force(reduced)["log_z"] == -math.inf


def test_non_symmetric_one_axis_factor_keeps_correct_axis():
    source = model([2, 3], [{"scope": [1, 0], "log_values": [[1, 2], [1, 2], [1, 2]]}])
    reduced, changes = simplify_model(source)
    assert changes[0]["kind"] == "independent_of_first_axis"
    assert reduced.factors[0].scope == (0,)
    assert np.array_equal(reduced.factors[0].values, [1, 2])


def test_scope_analysis_distinguishes_chain_clique_and_constant_clique():
    factors = [{"scope": [i, j], "log_values": [[0, 1], [1, 0]]}
               for i in range(5) for j in range(i + 1, 5)]
    clique = model([2] * 5, factors)
    assert structure_summary(clique)["predicted_induced_width"] == 4
    assert int(structure_summary(clique)["predicted_peak_table_entries"]) == 32
    chain = model([2] * 5, [f for f in factors if f["scope"][1] == f["scope"][0] + 1])
    assert structure_summary(chain)["predicted_induced_width"] == 1
    separable = model([2] * 5, [{"scope": f["scope"], "log_values": [[0, 1], [1, 2]]} for f in factors])
    reduced, _ = simplify_model(separable)
    info = structure_summary(reduced)
    assert info["predicted_induced_width"] == 0
    assert info["isolated_variables"] == 5
    assert int(info["predicted_peak_table_entries"]) == 2
