import itertools
import math
import random

import numpy as np
import pytest

pytest.importorskip("pyagrum", reason="Established comparator requires its separately locked runtime")

from experiments.established_v2 import run_pyagrum
from experiments.inference import model_from_dict


def test_moderate_clique_regression_for_native_memory_units():
    from experiments.established import run_pyagrum as original_adapter
    data={"domains":[4]*10,"factors":[
        {"scope":[i,j],"log_values":[0.0]*16}
        for i,j in itertools.combinations(range(10),2)
    ]}
    model=model_from_dict(data)
    with pytest.raises(Exception,match="bad_alloc"):
        original_adapter(model)
    result=run_pyagrum(model)
    assert result["status"]=="complete"
    assert result["log_z"]==pytest.approx(10*math.log(4),abs=1e-10)
    assert result["adapter_version"]==2
    assert result["metrics"]["native_memory_mebibytes"]==1024
    assert result["metrics"]["estimated_peak_clique_table_bytes"]==8*4**10


def reference(data):
    total = -math.inf
    for assignment in itertools.product(*(range(d) for d in data["domains"])):
        terms = [float(data.get("constant_log_weight", 0))]
        for factor in data["factors"]:
            values = np.asarray(factor["log_values"], dtype=object).reshape(tuple(data["domains"][v] for v in factor["scope"]))
            raw = values[tuple(assignment[v] for v in factor["scope"])]
            terms.append(-math.inf if raw is None else float(raw))
        total = float(np.logaddexp(total, sum(terms)))
    return total


def check(data):
    result = run_pyagrum(model_from_dict(data))
    assert result["status"] == "complete", result
    expected = reference(data)
    if expected == -math.inf:
        assert result["log_z"] == -math.inf
    else:
        assert result["log_z"] == pytest.approx(expected, abs=1e-10, rel=1e-12)
    return result


@pytest.mark.parametrize("domains", [[], [1], [3], [1,3,2]])
def test_constants_and_isolated_variables(domains):
    check({"domains": domains, "constant_log_weight": 1200, "factors": [{"scope": [], "log_values": -3.0}]})


def test_asymmetric_unsorted_scope_and_nonpower_domains():
    data = {"domains": [2,3,5], "factors": [
        {"scope": [2,0], "log_values": [[.1, -1.2],[.4,.5],[-1,0],[2,1],[.7,.2]]},
        {"scope": [1,2], "log_values": np.arange(15).reshape(3,5).tolist()},
        {"scope": [1], "log_values": [1,2,3]},
    ]}
    result = check(data)
    assert result["metrics"]["conditional_queries"] == 3


def test_duplicate_factors_and_offsets():
    check({"domains": [2,3], "constant_log_weight": -10000, "factors": [
        {"scope": [0], "log_values": [5,6]},
        {"scope": [0], "log_values": [1,-4]},
        {"scope": [0,1], "log_values": [[1000,1001,999],[998,999,997]]},
        {"scope": [1,0], "log_values": [[0,1],[2,3],[4,5]]},
    ]})


def test_preserves_hard_zeros():
    check({"domains": [2,3], "factors": [
        {"scope": [0,1], "log_values": [[None,-1,0],[None,None,None]]}
    ]})


@pytest.mark.parametrize("factor", [
    {"scope": [], "log_values": None},
    {"scope": [0], "log_values": [None,None]},
])
def test_all_zero_factor(factor):
    check({"domains": [2], "factors": [factor]})


def test_incompatible_cross_factor_constraints():
    same = [[0,None],[None,0]]
    different = [[None,0],[0,None]]
    check({"domains": [2,2,2], "factors": [
        {"scope": [0,1], "log_values": same},
        {"scope": [1,2], "log_values": same},
        {"scope": [0,2], "log_values": different},
    ]})


@pytest.mark.parametrize("seed", range(20))
def test_random_small_models(seed):
    rng = random.Random(seed)
    domains = [rng.randint(1,4) for _ in range(rng.randint(1,6))]
    factors = [{"scope": [i], "log_values": [rng.uniform(-5,5) for _ in range(q)]}
               for i,q in enumerate(domains)]
    for i,j in itertools.combinations(range(len(domains)),2):
        if rng.random() < .5:
            scope = [i,j] if rng.random() < .5 else [j,i]
            factors.append({"scope": scope,
                            "log_values": [rng.uniform(-5,5) for _ in range(math.prod(domains[v] for v in scope))]})
    check({"domains": domains, "factors": factors})


def test_rejects_positive_entry_conversion_to_zero():
    result = run_pyagrum(model_from_dict({"domains": [2], "factors": [
        {"scope": [0], "log_values": [0,-1000]},
    ]}))
    assert result["status"] == "conversion_underflow"
    assert "log_z" not in result
    assert result["metrics"]["new_zero_entries"] == 1


def test_rejects_merged_factor_underflow():
    result = run_pyagrum(model_from_dict({"domains": [2], "factors": [
        {"scope": [0], "log_values": [0,-500]},
        {"scope": [0], "log_values": [0,-500]},
    ]}))
    assert result["status"] == "conversion_underflow"


def test_finite_negative_overflow_does_not_become_false_zero_support():
    result = run_pyagrum(model_from_dict({"domains": [2], "factors": [
        {"scope": [0], "log_values": [-1e308, -1e308]},
        {"scope": [0], "log_values": [-1e308, -1e308]},
    ]}))
    assert result["status"] == "conversion_overflow"
    assert "log_z" not in result


def test_rejects_inaccurate_subnormal_conversion():
    result = run_pyagrum(model_from_dict({"domains": [2], "factors": [
        {"scope": [0], "log_values": [0,-744]},
    ]}))
    assert result["status"] == "conversion_accuracy_limit"


def test_clique_cap_prevents_queries():
    result = run_pyagrum(model_from_dict({"domains": [3,3], "factors": [
        {"scope": [0,1], "log_values": [0]*9},
    ]}), max_table_bytes=32)
    assert result["status"] == "wrapper_preflight_clique_limit"
    assert result["metrics"]["preflight_max_clique_table_bytes"] == 72
    assert result["metrics"]["conditional_queries"] == 0


def test_linear_inference_failure_does_not_falsely_claim_zero_support():
    factors = [{"scope": [i,j], "log_values": [[-600,0],[0,-600]]}
               for i,j in itertools.combinations(range(5),2)]
    result = run_pyagrum(model_from_dict({"domains": [2]*5, "factors": factors}))
    assert result["status"] in ("numerical_failure", "numerical_failure_or_zero_support")
    assert "log_z" not in result
