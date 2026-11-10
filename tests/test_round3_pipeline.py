from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from experiments.inference import Factor, model_from_dict
from experiments.round3_pipeline import prepare_model, target_fingerprint


ROOT = Path(__file__).resolve().parents[1]
DATA = {"model_id": "cold-pipeline-control", "domains": [3, 2], "constant_log_weight": 700,
        "factors": [{"scope": [0], "log_values": [None, -1.0, None]},
                    {"scope": [1, 0], "log_values": [[0, -2, 0], [0, None, 0]]}]}


def test_fingerprint_binds_numeric_target_not_metadata():
    model = model_from_dict(DATA)
    original = target_fingerprint(model)
    assert target_fingerprint(replace(model, metadata={"elapsed": 999}, model_id="renamed")) == original
    factors = list(model.factors)
    factors[0] = Factor(factors[0].scope, np.asarray([-np.inf, -1.0001, -np.inf]))
    assert target_fingerprint(replace(model, factors=tuple(factors))) != original
    assert target_fingerprint(replace(model, factors=tuple(reversed(model.factors)))) != original


@pytest.mark.parametrize("representation", ["simplified", "propagated"])
@pytest.mark.parametrize("method", ["ve", "batch", "pyagrum"])
def test_cold_cli_matches_frozen_target_and_includes_preparation(tmp_path, representation, method):
    if method == "pyagrum":
        pytest.importorskip("pyagrum")
    original = model_from_dict(DATA)
    prepared, pipeline = prepare_model(original, representation)
    source = tmp_path / "input.json"
    source.write_text(json.dumps(DATA))
    output = tmp_path / "result.json"
    result = subprocess.run([sys.executable, "-m", "experiments.round3_pipeline", str(source),
        "--representation", representation, "--method", method,
        "--expected-target-sha256", pipeline["target_sha256"], "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    raw = json.loads(output.read_text())
    assert raw["status"] == "complete", raw
    assert raw["log_z"] == pytest.approx(697.0, abs=1e-10)
    assert raw["pipeline"]["target_sha256"] == target_fingerprint(prepared)
    assert raw["input_state_count"] == "6"
    assert raw["state_count"] == ("1" if representation == "propagated" else "6")
    for name in ["load_seconds", "load_cpu_seconds", "propagation_seconds", "propagation_cpu_seconds",
                 "simplification_seconds", "simplification_cpu_seconds", "target_validation_seconds",
                 "target_validation_cpu_seconds", "inference_seconds", "inference_cpu_seconds"]:
        assert raw["pipeline"][name] >= 0
    sidecar = json.loads(Path(raw["pipeline"]["serialization_timing_sidecar"]).read_text())
    assert sidecar["serialization_seconds"] >= 0
    assert sidecar["serialization_cpu_seconds"] >= 0
    assert sidecar["process_peak_rss_bytes_after_result"] >= raw["process_peak_rss_bytes"]
    assert sidecar["cold_total_through_result_seconds"] >= raw["pipeline"]["cold_total_seconds"]


def test_target_mismatch_is_retained_without_inference(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(DATA))
    output = tmp_path / "result.json"
    subprocess.run([sys.executable, "-m", "experiments.round3_pipeline", str(source),
        "--representation", "propagated", "--method", "ve", "--expected-target-sha256", "0" * 64,
        "--output", str(output)], cwd=ROOT, capture_output=True, check=True, timeout=15)
    raw = json.loads(output.read_text())
    assert raw["status"] == "target_fingerprint_mismatch"
    assert "log_z" not in raw
    assert raw["pipeline"]["inference_seconds"] == 0


def test_cold_preprocessing_deadline_stops_before_inference(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(DATA))
    output = tmp_path / "result.json"
    subprocess.run([sys.executable, "-m", "experiments.round3_pipeline", str(source),
        "--representation", "propagated", "--method", "ve", "--preprocessing-limit-seconds", "0.000001",
        "--output", str(output)], cwd=ROOT, capture_output=True, check=True, timeout=15)
    raw = json.loads(output.read_text())
    assert raw["status"] == "preprocessing_time_limit"
    assert "log_z" not in raw
    assert raw["pipeline"]["inference_seconds"] == 0
