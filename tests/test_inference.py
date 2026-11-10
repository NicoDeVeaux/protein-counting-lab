import math

import numpy as np
import pytest

from experiments.inference import (
    InferenceLimit, batched_brute_force, bounded_mass, brute_force, condition_model, log_kstar,
    model_from_dict, variable_elimination,
)


def make_model(domains, factors, **kwargs):
    return model_from_dict({"domains": domains, "factors": factors, **kwargs})


def synthetic(seed, count=5):
    rng = np.random.default_rng(seed)
    domains = rng.integers(2, 4, size=count).tolist()
    factors = [{"scope": [i], "log_values": rng.normal(size=d).tolist()}
               for i, d in enumerate(domains)]
    for i in range(count):
        for j in range(i + 1, count):
            if rng.random() < 0.5:
                values = rng.normal(size=(domains[j], domains[i]))
                values[rng.random(size=values.shape) < 0.1] = -math.inf
                factors.append({"scope": [j, i], "log_values": values.tolist()})
    return make_model(domains, factors, kind="synthetic_control", metadata={"seed": seed})


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("order", ["natural", "min-fill", "min-weight"])
def test_elimination_matches_independent_enumeration(seed, order):
    model = synthetic(seed)
    expected = brute_force(model)["log_z"]
    actual = variable_elimination(model, order=order)["log_z"]
    assert actual == pytest.approx(expected, abs=2e-12)


def test_disconnected_product_and_isolated_variable():
    model = make_model([2, 3, 7], [
        {"scope": [0], "log_values": [math.log(2), math.log(3)]},
        {"scope": [1], "log_values": [math.log(5), math.log(7), math.log(11)]},
    ], constant_log_weight=math.log(13))
    expected = math.log(5 * 23 * 7 * 13)
    assert brute_force(model)["log_z"] == pytest.approx(expected)
    assert variable_elimination(model)["log_z"] == pytest.approx(expected)


def test_hard_zeros_and_all_impossible_model():
    model = make_model([2, 2], [{"scope": [0, 1], "log_values": [0, None, "-inf", 0]}])
    assert variable_elimination(model)["log_z"] == pytest.approx(math.log(2))
    impossible = make_model([2], [{"scope": [0], "log_values": [None, "-inf"]}])
    assert variable_elimination(impossible)["log_z"] == -math.inf
    result = bounded_mass(impossible)
    assert result["log_z_lower"] == result["log_z_upper"] == -math.inf
    assert result["epsilon_met"]


def test_log_domain_avoids_underflow():
    model = make_model([2] * 4, [{"scope": [i], "log_values": [-10000, -10001]} for i in range(4)])
    expected = 4 * (-10000 + math.log1p(math.exp(-1)))
    assert variable_elimination(model)["log_z"] == pytest.approx(expected, abs=1e-10)
    assert brute_force(model)["log_z"] == pytest.approx(expected, abs=1e-10)


def test_relabeling_and_axis_order_preserve_partition():
    model = synthetic(99, 4)
    permutation = [2, 0, 3, 1]
    renamed_domains = [0] * 4
    for old, new in enumerate(permutation):
        renamed_domains[new] = model.domains[old]
    renamed = make_model(renamed_domains, [
        {"scope": [permutation[v] for v in f.scope], "log_values": f.values.tolist()}
        for f in model.factors
    ])
    assert variable_elimination(renamed)["log_z"] == pytest.approx(variable_elimination(model)["log_z"])


def test_conditioning_partition_identity():
    model = synthetic(14, 4)
    terms = [variable_elimination(condition_model(model, {1: value}))["log_z"]
             for value in range(model.domains[1])]
    assert float(np.logaddexp.reduce(terms)) == pytest.approx(variable_elimination(model)["log_z"])
    fully_fixed = condition_model(model, {v: 0 for v in range(4)})
    expected = sum(float(f.values[(0,) * len(f.scope)]) for f in model.factors)
    assert variable_elimination(fully_fixed)["log_z"] == pytest.approx(expected)


@pytest.mark.parametrize("seed", range(8))
def test_prefix_bounds_contain_reference_at_each_budget(seed):
    model = synthetic(seed, 4)
    truth = brute_force(model)["log_z"]
    for nodes in [1, 5, 20, 1000]:
        result = bounded_mass(model, epsilon=0.2, max_nodes=nodes, check_interval=1)
        assert result["log_z_lower"] <= truth + 1e-12
        assert result["log_z_upper"] >= truth - 1e-12
        if result["epsilon_met"]:
            assert math.exp(result["log_z_lower"] - truth) >= 0.8 - 1e-12


def test_frontier_limit_does_not_drop_unevaluated_mass():
    model = synthetic(4, 4)
    result = bounded_mass(model, max_frontier_nodes=1, max_nodes=100)
    assert result["status"] == "frontier_limit"
    assert result["log_z_upper"] >= brute_force(model)["log_z"] - 1e-12


def test_exact_prefix_enumeration():
    model = synthetic(42, 3)
    result = bounded_mass(model, epsilon=0, max_nodes=10000, check_interval=1)
    expected = brute_force(model)["log_z"]
    assert result["status"] == "exact"
    assert result["log_z_lower"] == pytest.approx(expected)
    assert result["log_z_upper"] == pytest.approx(expected)


def test_memory_guard_blocks_intermediate_before_allocation():
    model = make_model([3, 3, 3], [
        {"scope": [0, 1], "log_values": [0] * 9},
        {"scope": [0, 2], "log_values": [0] * 9},
    ])
    with pytest.raises(InferenceLimit) as err:
        variable_elimination(model, order="natural", max_table_bytes=80)
    assert err.value.reason == "intermediate_table_limit"
    assert err.value.metrics["blocked_table_bytes"] == 216
    with pytest.raises(InferenceLimit) as err:
        variable_elimination(model, max_table_bytes=8)
    assert err.value.reason == "input_factor_exceeds_table_limit"


def test_invalid_shapes_and_values_are_rejected():
    for domains, factors in [
        ([0], []), ([True], []),
        ([2], [{"scope": [0], "log_values": [0]}]),
        ([2, 3], [{"scope": [0, 1], "log_values": [[0, 0], [0, 0], [0, 0]]}]),
        ([2], [{"scope": [0, 0], "log_values": [0] * 4}]),
        ([2], [{"scope": [1], "log_values": [0, 0]}]),
        ([2], [{"scope": [0], "log_values": [0, math.nan]}]),
        ([2], [{"scope": [0], "log_values": [0, math.inf]}]),
    ]:
        with pytest.raises(ValueError):
            make_model(domains, factors)


def test_explicit_order_validation_and_state_guard():
    model = synthetic(1, 3)
    with pytest.raises(ValueError):
        variable_elimination(model, order=[0, 0, 1])
    with pytest.raises(InferenceLimit) as err:
        brute_force(model, max_states=1)
    assert err.value.reason == "state_limit"


def test_log_kstar_is_ratio_of_existing_partitions():
    assert log_kstar(math.log(30), math.log(2), math.log(3)) == pytest.approx(math.log(5))
    assert log_kstar(-math.inf, 1, 1) == -math.inf
    with pytest.raises(ValueError):
        log_kstar(1, -math.inf, 1)


def test_empty_model():
    model = make_model([], [])
    assert brute_force(model)["log_z"] == 0
    assert variable_elimination(model)["log_z"] == 0
    assert bounded_mass(model, check_interval=1)["log_z_lower"] == 0
    assert batched_brute_force(model)["log_z"] == 0


def test_synthetic_controls_are_labeled_and_reproducible():
    from experiments.inference.controls import synthetic_control
    first = synthetic_control(family="random-sparse", variables=5, domain_size=2, seed=17)
    assert first == synthetic_control(family="random-sparse", variables=5, domain_size=2, seed=17)
    assert first["kind"] == "synthetic_control"
    assert first["metadata"]["seed"] == 17
    model = model_from_dict(first)
    assert variable_elimination(model)["log_z"] == pytest.approx(brute_force(model)["log_z"])


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("batch_states", [1, 7, 31, 65536])
def test_batched_enumeration_matches_scalar(seed, batch_states):
    model = synthetic(seed, 4)
    reference = brute_force(model)["log_z"]
    result = batched_brute_force(model, batch_states=batch_states)
    assert result["log_z"] == pytest.approx(reference, abs=2e-12)
    assert result["metrics"]["states_evaluated"] == model.n_states


def test_batched_enumeration_underflow_and_hard_zeros():
    model = make_model([2, 3], [
        {"scope": [0], "log_values": [-10000, -10001]},
        {"scope": [1, 0], "log_values": [-10000, None, -10002, -10003, None, -10001]},
    ])
    assert batched_brute_force(model, batch_states=2)["log_z"] == pytest.approx(brute_force(model)["log_z"])
    impossible = make_model([2], [{"scope": [0], "log_values": [None, None]}])
    assert batched_brute_force(impossible)["log_z"] == -math.inf


def test_batched_guards_and_small_memory_chunks():
    model = synthetic(1, 3)
    with pytest.raises(InferenceLimit) as err:
        batched_brute_force(model, max_states=1)
    assert err.value.reason == "state_limit"
    with pytest.raises(InferenceLimit) as err:
        batched_brute_force(model, max_batch_bytes=1)
    assert err.value.reason == "batch_array_limit"
    result = batched_brute_force(model, max_batch_bytes=48)
    assert result["metrics"]["batch_states_effective"] == 1
    assert result["metrics"]["estimated_peak_batch_array_bytes"] <= 48
    assert result["log_z"] == pytest.approx(brute_force(model)["log_z"])
