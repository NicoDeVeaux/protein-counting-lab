import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from experiments.inference import brute_force, model_from_dict
from experiments.round3_pipeline import prepare_model
from experiments.three_state_data import condition_sequence
from experiments.three_state_rank import ranking_check, score_ratio
from test_three_state_data_round4 import source_case, write_archive


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("logs,status,value", [
    ({"complex": 10, "protein": 3, "ligand": 2}, "finite", 5),
    ({"complex": "-inf", "protein": 3, "ligand": 2}, "zero_numerator", "-inf"),
    ({"complex": 10, "protein": "-inf", "ligand": 2}, "undefined_zero_denominator", None),
    ({"complex": "-inf", "protein": "-inf", "ligand": 2}, "undefined_zero_denominator", None),
    ({"complex": 10, "protein": 3, "ligand": "-inf"}, "undefined_zero_denominator", None),
    ({"complex": 10}, "incomplete", None),
])
def test_ratio_zero_and_missing_state_rules(logs, status, value):
    result = score_ratio(logs)
    assert result == {"status": status, "log_k": value}


def test_scalar_offsets_are_restored_in_ratio():
    logs = {}
    for state, offset, unary in [("complex", 1000, [0,1]), ("protein", 700, [2,3]), ("ligand", 200, [1,2])]:
        model = model_from_dict({"domains": [2], "constant_log_weight": offset,
                                 "factors": [{"scope": [0], "log_values": unary}]})
        logs[state] = brute_force(model)["log_z"]
    assert score_ratio(logs)["log_k"] == pytest.approx(97-math.log1p(math.e), abs=1e-10)


def test_exact_near_resolvable_and_wrong_rankings():
    reference = {"a": 5., "b": 4., "c": 3., "d": 2., "e": 1., "f": 0.}
    correct = ranking_check(reference, reference)
    assert correct["pairwise"]["wrong"] == 0
    assert all(cell["status"] == "compatible_with_reference_envelope" for cell in correct["top_k"].values())
    wrong = reference | {"a": -1.}
    assert ranking_check(wrong, reference)["top_k"]["1"]["status"] == "wrong"
    near = {"a": 1., "b": 1.+1e-12, "c": 0.}
    result = ranking_check(near, near)
    assert result["pairwise"]["uncertain_reference"] == 1
    assert result["top_k"]["1"]["boundary_uncertain"]
    tied = {"a": 1., "b": 1., "c": 0.}
    assert ranking_check(tied, tied)["top_k"]["1"]["boundary_uncertain"]
    assert ranking_check({"a": 5.}, reference)["top_k"]["1"]["status"] == "incomplete_panel"
    with pytest.raises(ValueError):
        ranking_check({"a": float("nan")}, {"a": 1.})


@pytest.mark.parametrize("method", ["ve", "batch"])
@pytest.mark.parametrize("arm", ["simplified", "propagated"])
def test_complete_cold_panel_and_safe_identical_state_cache(tmp_path, method, arm):
    archive = tmp_path / "source.zip"
    source = source_case()
    write_archive(archive, source)
    sequences = [{"sequence_id": f"s{i}", "label": label, "assignment": {"0": i, "1": 0}}
                 for i,label in enumerate(["ALA", "VAL"])]
    targets = {}
    for sequence in sequences:
        models, _ = condition_sequence(source, {int(k):v for k,v in sequence["assignment"].items()})
        targets[sequence["sequence_id"]] = {arm: {state:prepare_model(model,arm)[1]["target_sha256"]
                                                for state,model in models.items()}}
    manifest = {"root": str(tmp_path), "pilot": {"case_id":"synthetic","archive": {"path": "source.zip",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}, "sequences": sequences},
        "panels": [{"panel_id": "p0", "method": method, "arm": arm, "repeat": 0, "query_order": ["s0", "s1"]}],
        "targets": targets, "scientific_choices": {"resources": {"panel_wall_seconds": 20,
            "closeout_reserve_seconds": .5, "source_load_seconds": 5, "table_bytes": 1024**2, "max_states": 1000},
            "phase_scopes": "Synthetic complete cold pipeline"}}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    output = tmp_path / "result.json"
    result = subprocess.run([sys.executable, "-m", "experiments.three_state_rank", str(manifest_path), "p0", str(output)],
                            cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    raw = json.loads(output.read_text())
    assert raw["source_status"] == "loaded"
    assert len(raw["queries"]) == 2
    for query, partition in zip(raw["queries"], [922,318]):
        assert query["score"]["status"] == "finite"
        assert query["score"]["log_k"] == pytest.approx(math.log(partition)-math.log(40 if partition==922 else 19)-math.log(66), abs=1e-10)
    cached = raw["queries"][1]["states"]["ligand"]
    assert cached["cache_hit"] and cached["cache_origin"] == {"sequence_id": "s0", "state": "ligand"}
    assert cached["solver_call_seconds"] == 0 and "metrics" not in cached
    timing = json.loads(Path(str(output)+".timing.json").read_text())
    assert timing["worker_peak_rss_after_result"] >= raw["worker_peak_rss_before_result"]
    assert sum(1 for _ in Path(str(output)+".progress.jsonl").open()) == 2
