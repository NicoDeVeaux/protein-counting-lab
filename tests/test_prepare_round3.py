from decimal import Decimal, localcontext
import math

import pytest

from experiments.inference import brute_force, model_from_dict
from experiments.round3_pipeline import prepare_model
from scripts.prepare_round3 import control_reference, controls


@pytest.mark.parametrize("data", controls(), ids=lambda data: data["model_id"])
def test_measured_control_reference_and_both_arms(data):
    reference = control_reference(data)
    suffix = data["model_id"].removeprefix("control003-")
    expected_support = {"cascade": 1, "local-zero": 0, "global-zero": 0,
                        "finite-tail": 256, "multiplicity": 12, "duplicate-zero": 0}
    assert reference["positive_support_assignments"] == expected_support[suffix]
    if expected_support[suffix] == 0:
        assert reference["log_z"] == "-inf"
    elif suffix == "cascade":
        assert Decimal(reference["log_z"]) == 7
    elif suffix == "finite-tail":
        assert Decimal(reference["log_z"]) == 0
    else:
        with localcontext() as context:
            context.prec = 80
            assert abs(Decimal(reference["log_z"]) - (Decimal(1000)+Decimal(12).ln())) < Decimal("1e-70")
    original = model_from_dict(data)
    for arm in ("simplified", "propagated"):
        prepared, _ = prepare_model(original, arm)
        result = brute_force(prepared, max_states=5000)
        expected = -math.inf if reference["log_z"] == "-inf" else float(reference["log_z"])
        if math.isinf(expected):
            assert result["log_z"] == expected
        else:
            assert result["log_z"] == pytest.approx(expected, abs=1e-10)
