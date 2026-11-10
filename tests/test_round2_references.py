import math

import pytest

from experiments.inference import batched_brute_force, model_from_dict
from scripts.prepare_round2 import analytic_reference, control


@pytest.mark.parametrize("family", ["independent", "chain", "cycle", "clique", "separable", "constant"])
def test_analytic_controls_against_independent_exhaustive_sums(family):
    data = control(family, 4, 3)
    reference = analytic_reference(data)
    result = batched_brute_force(model_from_dict(data))
    assert math.isclose(result["log_z"], float(reference["log_z"]), abs_tol=1e-12)


def test_grid_row_transfer_against_independent_exhaustive_sum():
    data = control("grid4", 16, 2)
    reference = analytic_reference(data)
    result = batched_brute_force(model_from_dict(data))
    assert math.isclose(result["log_z"], float(reference["log_z"]), abs_tol=1e-11)
