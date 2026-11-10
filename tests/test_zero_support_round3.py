from fractions import Fraction
import itertools
import math
import random

import numpy as np
import pytest

from experiments.inference import Factor, Model, model_from_dict
from experiments.structure import model_to_dict
from experiments.zero_support import propagate_model


def model(data):
    return model_from_dict(data, allow_higher_arity=True)


def assignments(domains):
    return itertools.product(*(range(q) for q in domains))


def exact_log_weight(instance, assignment):
    terms = []
    for factor in instance.factors:
        value = float(factor.values[tuple(assignment[v] for v in factor.scope)])
        if value == -math.inf:
            return None
        terms.append(Fraction(value))
    return sum(terms, Fraction(0))


def log_partition(instance):
    weights = [float(value) for assignment in assignments(instance.domains)
               if (value := exact_log_weight(instance, assignment)) is not None]
    if not weights:
        return -math.inf
    maximum = max(weights)
    return maximum + math.log(math.fsum(math.exp(value - maximum) for value in weights))


def assert_replay(instance, ledger):
    allowed = [list(range(q)) for q in instance.domains]
    for event in ledger["deletions"]:
        scope = event["scope"]
        assert event["allowed_before"] == {str(v): allowed[v] for v in scope}
        for variable_string, values in event["removed_original_indices"].items():
            variable = int(variable_string)
            for value in values:
                for local in itertools.product(*(allowed[v] if v != variable else [value]
                                                 for v in scope)):
                    assignment = dict(zip(scope, local))
                    assert any(
                        float(instance.factors[index].values[tuple(assignment[v] for v in instance.factors[index].scope)]) == -math.inf
                        for index in event["source_factor_indices"]
                    )
        for variable_string, values in event["removed_original_indices"].items():
            variable = int(variable_string)
            allowed[variable] = [value for value in allowed[variable] if value not in values]
    assert allowed == ledger["retained_original_indices"]


def assert_equivalent(instance, *, simplify=True):
    result, ledger = propagate_model(instance, simplify=simplify)
    assert len(result.domains) == len(instance.domains)
    assert_replay(instance, ledger)
    if ledger["status"] == "proven_zero":
        assert all(exact_log_weight(instance, a) is None for a in assignments(instance.domains))
        assert all(exact_log_weight(result, a) is None for a in assignments(result.domains))
        assert result.domains == tuple(1 for _ in instance.domains)
        assert ledger["inconsistency_proof"] is not None
    else:
        retained = ledger["retained_original_indices"]
        assert result.domains == tuple(map(len, retained))
        for assignment in assignments(instance.domains):
            if any(assignment[v] not in retained[v] for v in range(len(retained))):
                assert exact_log_weight(instance, assignment) is None
        for reduced_assignment in assignments(result.domains):
            original_assignment = tuple(retained[v][value] for v, value in enumerate(reduced_assignment))
            assert exact_log_weight(result, reduced_assignment) == exact_log_weight(instance, original_assignment)
    assert log_partition(result) == pytest.approx(log_partition(instance), abs=1e-12)
    restored = model(model_to_dict(result))
    assert restored.domains == result.domains
    for assignment in assignments(result.domains):
        assert exact_log_weight(restored, assignment) == exact_log_weight(result, assignment)
    assert all(not factor.values.flags.writeable for factor in result.factors)
    return result, ledger


def random_instance(seed):
    rng = random.Random(seed)
    domains = [rng.randint(1, 3) for _ in range(rng.randint(0, 5))]
    factors = []
    for _ in range(rng.randint(0, 10)):
        scope = rng.sample(range(len(domains)), rng.randint(0, min(3, len(domains))))
        values = [None if rng.random() < .25 else rng.randint(-12, 12) / 4
                  for _ in range(math.prod(domains[v] for v in scope))]
        factors.append({"scope": scope, "log_values": values})
    return model({"domains": domains, "factors": factors})


@pytest.mark.parametrize("seed", range(50))
def test_random_weighted_models_preserve_exact_assignment_weights_and_sum(seed):
    assert_equivalent(random_instance(seed))


def test_all_binary_pair_and_unary_support_masks():
    for pair_mask, left_mask, right_mask in itertools.product(range(16), range(4), range(4)):
        instance = model({"domains": [2, 2], "factors": [
            {"scope": [1, 0], "log_values": [value if pair_mask & (1 << i) else None
                                              for i, value in enumerate([.25, 1.5, -2, .125])]},
            {"scope": [0], "log_values": [0.5 if left_mask & (1 << i) else None for i in range(2)]},
            {"scope": [1], "log_values": [-.25 if right_mask & (1 << i) else None for i in range(2)]},
        ]})
        assert_equivalent(instance)


@pytest.mark.parametrize("seed", range(20))
def test_propagation_is_idempotent_on_the_represented_target(seed):
    once, first_ledger = propagate_model(random_instance(seed))
    twice, second_ledger = propagate_model(once)
    assert once.domains == twice.domains
    assert len(once.factors) == len(twice.factors)
    for left, right in zip(once.factors, twice.factors):
        assert left.scope == right.scope
        assert np.array_equal(left.values, right.values)
    if first_ledger["status"] == "arc_consistent":
        assert second_ledger["removed_domain_values"] == 0


def test_isolated_domains_and_constant_factor_multiplicity_are_retained():
    instance = model({"domains": [2, 3, 5], "factors": [
        {"scope": [0, 1], "log_values": [.25] * 6},
        {"scope": [], "log_values": -2},
    ]})
    result, ledger = assert_equivalent(instance)
    assert result.domains == (2, 3, 5)
    assert ledger["removed_domain_values"] == 0
    assert log_partition(result) == pytest.approx(math.log(30) - 1.75)


def test_chained_deletions_reach_a_fixed_point_and_preserve_unsorted_factors():
    instance = model({"domains": [3, 2, 2], "factors": [
        {"scope": [0, 1], "log_values": [0, None, 0, 0, None, 0]},
        {"scope": [2, 1], "log_values": [None, .25, None, .5]},
        {"scope": [2], "log_values": [None, 0]},
    ]})
    result, ledger = assert_equivalent(instance, simplify=False)
    assert result.domains == (2, 1, 1)
    assert ledger["retained_original_indices"] == [[1, 2], [1], [1]]
    assert ledger["fixpoint_rounds"] >= 2
    assert result.factors[1].scope == (2, 1)


def test_duplicate_unsorted_scope_constraints_are_intersected_without_numeric_merging():
    instance = model({"domains": [2, 2], "factors": [
        {"scope": [0, 1], "log_values": [0, None, None, .25]},
        {"scope": [1, 0], "log_values": [None, .5, .75, None]},
    ]})
    _, ledger = assert_equivalent(instance, simplify=False)
    assert ledger["status"] == "proven_zero"
    assert len(ledger["constraints"]) == 1
    assert ledger["constraints"][0]["source_factor_indices"] == [0, 1]
    assert ledger["constraints"][0]["hard_zero_entries_after_scope_intersection"] == 4


def test_arc_consistency_does_not_claim_global_feasibility_for_an_odd_cycle():
    same = [0, None, None, 0]
    different = [None, 0, 0, None]
    instance = model({"domains": [2, 2, 2], "factors": [
        {"scope": [0, 1], "log_values": same},
        {"scope": [1, 2], "log_values": same},
        {"scope": [0, 2], "log_values": different},
    ]})
    result, ledger = assert_equivalent(instance)
    assert ledger["status"] == "arc_consistent"
    assert ledger["inconsistency_proof"] is None
    assert result.domains == (2, 2, 2)
    assert log_partition(result) == -math.inf


def test_higher_arity_and_unsorted_scopes_preserve_weighted_target():
    instance = model({"domains": [2, 3, 2], "factors": [
        {"scope": [2, 0, 1], "log_values": [None, .5, None, None, .25, None,
                                             None, .75, None, None, 1, None]},
        {"scope": [2], "log_values": [None, 0]},
    ]})
    result, ledger = assert_equivalent(instance, simplify=False)
    assert result.domains == (2, 1, 1)
    assert ledger["retained_original_indices"] == [[0, 1], [1], [1]]


def test_factor_slice_audit_maps_nonconsecutive_original_indices_and_scalars():
    entries = [None] * 12
    for row, column, value in [(1, 0, .25), (1, 2, .5), (3, 0, 1), (3, 2, -1)]:
        entries[3 * row + column] = value
    instance = model({"domains": [3, 2, 4], "factors": [
        {"scope": [2, 0], "log_values": entries},
        {"scope": [0], "log_values": [0, None, 0]},
        {"scope": [], "log_values": 5},
    ]})
    result, ledger = assert_equivalent(instance, simplify=False)
    assert result.domains == (2, 2, 2)
    pair, unary, scalar = ledger["factor_restrictions"]
    assert pair["input_factor_index"] == pair["restricted_factor_index_before_algebra"] == 0
    assert pair["scope"] == [2, 0]
    assert pair["input_shape"] == [4, 3]
    assert pair["original_indices_per_axis"] == [[1, 3], [0, 2]]
    assert pair["restricted_shape"] == [2, 2]
    assert unary["original_indices_per_axis"] == [[0, 2]]
    assert scalar["scope"] == scalar["input_shape"] == scalar["original_indices_per_axis"] == scalar["restricted_shape"] == []
    assert scalar["restricted_factor_index_before_algebra"] == 2


@pytest.mark.parametrize("domains", [[], [1], [2, 3]])
def test_scalar_hard_zero_has_safe_zero_target_representation(domains):
    _, ledger = assert_equivalent(model({"domains": domains, "constant_log_weight": None}))
    assert ledger["status"] == "proven_zero"
    assert ledger["inconsistency_proof"]["kind"] == "scalar_hard_zero"
    assert "not a feasible-assignment witness" in ledger["mapping_semantics"]
    assert all(item["restricted_factor_index_before_algebra"] is None for item in ledger["factor_restrictions"])
    assert all(item["representation"] == "replaced_by_canonical_proven_zero" for item in ledger["factor_restrictions"])


def test_finite_extreme_logs_and_negative_zero_are_never_threshold_pruned():
    instance = model({"domains": [3, 2], "factors": [
        {"scope": [1, 0], "log_values": [-1e308, -0.0, -1000, 1e308, None, -744]},
    ]})
    result, ledger = propagate_model(instance, simplify=False)
    assert ledger["removed_domain_values"] == 0
    assert np.array_equal(result.factors[0].values.view(np.uint64), instance.factors[0].values.view(np.uint64))
    assert ledger["status"] == "arc_consistent"


def test_inputs_are_not_mutated_or_given_output_metadata():
    instance = model({"domains": [3], "metadata": {"provenance": "test"}, "factors": [
        {"scope": [0], "log_values": [None, -.25, None]},
    ]})
    saved = instance.factors[0].values.copy()
    propagate_model(instance)
    assert np.array_equal(instance.factors[0].values, saved)
    assert instance.metadata == {"provenance": "test"}
    assert not instance.factors[0].values.flags.writeable


def test_adding_a_hard_zero_constraint_can_only_remove_supported_domain_values():
    base = model({"domains": [3, 3], "factors": [
        {"scope": [0, 1], "log_values": [0, None, None, 0, 0, None, None, 0, 0]},
    ]})
    stronger = model({**model_to_dict(base), "factors": model_to_dict(base)["factors"] + [
        {"scope": [1], "log_values": [None, 0, None]},
    ]})
    _, before = propagate_model(base)
    _, after = assert_equivalent(stronger)
    for original, restricted in zip(before["retained_original_indices"], after["retained_original_indices"]):
        assert set(restricted) <= set(original)


@pytest.mark.parametrize("value", [math.nan, math.inf])
def test_invalid_log_values_are_rejected_instead_of_being_treated_as_support(value):
    bad = Model((2,), (Factor((0,), np.array([0.0, value])),))
    with pytest.raises(ValueError, match="invalid log value"):
        propagate_model(bad)
