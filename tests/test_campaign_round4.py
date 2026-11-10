"""Synthetic controls for the campaign004 controller and freeze contracts."""

from collections import Counter
from copy import deepcopy
from decimal import Decimal
import json
import random
import zipfile

import pytest

from experiments.inference import model_from_dict
import experiments.round2_watchdog as watchdog
from experiments.round3_pipeline import target_fingerprint
import scripts.campaign_round4 as campaign


LABELS = [
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HID", "HIE",
    "HIP", "ILE", "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "VAL",
]
ARMS = ("simplified", "propagated")
REJECTED = (AssertionError, ValueError, KeyError)


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False))


def metadata_archive(path, *, labels=None):
    labels = [*LABELS, "DUMMY"] if labels is None else labels
    summary = {
        "residue_aminoAcids": {"0": labels, "1": ["GLY"]},
        "residues": ["A10", "B20"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("synthetic.uai", "MARKOV\n0\n\n0\n")
        archive.writestr("synthetic.uai.query", "2 0 1\n")
        archive.writestr("uai_conversion_summary.txt", "\n".join(
            key + "\n" + json.dumps(value) for key, value in summary.items()))


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.setattr(campaign, "OUT", tmp_path / "prepared/campaign-004")
    monkeypatch.setattr(campaign, "RUN", tmp_path / "runs/campaign-004")
    implementation = tmp_path / "implementation.py"
    implementation.write_text("# Synthetic implementation identity.\n")
    monkeypatch.setattr(campaign, "implementation_files", lambda: [campaign.artifact(implementation)])
    cases = []
    for index in range(14):
        path = tmp_path / f"sources/case-{index:02d}.zip"
        metadata_archive(path)
        states = []
        for state in campaign.STATES:
            baseline = tmp_path / f"baselines/case-{index:02d}__{state}.json"
            dump(baseline, {"model_id": f"case-{index:02d}__source_first__{state}",
                            "kind": "synthetic_control", "domains": [10 + index],
                            "factors": [{"scope": [0], "log_values": [0] * (10 + index)}],
                            "metadata": {"state": state, "source_factor_indices": [0]}})
            states.append({"state": state, "configuration_count": 10 + index,
                           **campaign.artifact(baseline)})
        cases.append({"case_id": f"case-{index:02d}", "local_path": str(path.relative_to(tmp_path)),
                      "states": states})
    dump(tmp_path / "data/uai23_manifest.json", {"cases": cases})
    grader = tmp_path / "grader/campaign-004/PROTOCOL.md"
    grader.parent.mkdir(parents=True)
    grader.write_text("Synthetic grading protocol.\n")
    dump(tmp_path / "grader/campaign-004/FREEZE.json",
         {"kind": "synthetic grader freeze", "files": [campaign.artifact(grader)]})
    dump(tmp_path / "data/campaign-004/comparator_audit/audit.json", {"kind": "synthetic comparator audit"})
    campaign.OUT.mkdir(parents=True)
    (campaign.OUT / "preflight-tests.txt").write_text("synthetic preflight evidence\n")
    campaign.freeze_preparation()
    return campaign.read(campaign.OUT / "preparation_manifest.json")


def expected_slots(plan):
    return [{"slot_id": f"{panel['panel_id']}/{sequence}/{state}", "panel_id": panel["panel_id"],
             "case_id": plan["pilot"]["case_id"], "sequence_id": sequence, "state": state,
             "method": panel["method"], "arm": panel["arm"], "repeat": panel["repeat"],
             "profile": "common20s-512MiB-16MiB"}
            for panel in plan["panels"] for sequence in panel["query_order"] for state in campaign.STATES]


def raw_references(pilot):
    rows = []
    for variant in pilot["sequences"]:
        sequence = {selector: (variant["label"] if selector == str(pilot["selector"]) else "GLY")
                    for selector in variant["assignment"]}
        spec = {"panel_index": variant["panel_index"], "selector": pilot["selector"],
                "label": variant["label"], "sequence": sequence}
        states = {state: {"case_id": pilot["case_id"], "panel_index": spec["panel_index"],
                          "label": spec["label"], "state": state, "status": "reference-passing success",
                          "values": {"stored_binary64_log": {"logZ": value}}}
                  for state, value in zip(campaign.STATES, ("10", "3", "2"))}
        rows.append({**spec, "states": states,
                     "scores": {"stored_binary64_log": {"status": "finite", "logKstar": "5"}}})
    return {"campaign": "004", "case_id": pilot["case_id"],
            "kind": "independent_raw_source_decimal_reference",
            "source_hashes": {"archive_sha256": pilot["archive"]["sha256"]},
            "planned_panel": [{key: row[key] for key in ("panel_index", "selector", "label", "sequence")}
                              for row in rows],
            "planned_state_rows": len(rows) * 3, "rows": rows}


def execution_inputs(plan):
    dump(campaign.OUT / "references.json", raw_references(plan["pilot"]))
    targets = {}
    for index, variant in enumerate(plan["pilot"]["sequences"]):
        sequence = variant["sequence_id"]
        targets[sequence] = {}
        for arm in ARMS:
            targets[sequence][arm] = {}
            for state in campaign.STATES:
                data = {"domains": [2], "factors": [{"scope": [0], "log_values": [index, index + 1]}]}
                dump(campaign.OUT / "models" / f"{sequence}__{arm}__{state}.json", data)
                targets[sequence][arm][state] = target_fingerprint(model_from_dict(data))
    dump(campaign.OUT / "targets.json", {"targets": targets, "original_models": []})
    (campaign.OUT / "preparation.jsonl").write_text('{"identity":"synthetic preparation"}\n')
    return targets


def query(logs=None, *, score_status="finite", score=5.0):
    logs = dict(zip(campaign.STATES, (10.0, 3.0, 2.0))) if logs is None else logs
    return {"sequence_id": "s", "states": {state: {"status": "complete", "log_z": logs[state]}
                                             for state in campaign.STATES},
            "score": {"status": score_status, "log_k": score}}


def references(logs=None, *, status="finite", score="5"):
    logs = dict(zip(campaign.STATES, ("10", "3", "2"))) if logs is None else logs
    return {"s": {"states": logs, "score": {"status": status, "logKstar": score}}}


@pytest.fixture
def science():
    return {"accuracy": {"log_z_absolute": 1e-8, "log_k_absolute": 3e-8}}


def test_fixed_seed_preserves_pairs_query_order_and_all_756_state_identities(prepared):
    panels = campaign.schedule(prepared["pilot"]["sequences"])
    original_random_state = random.getstate()
    try:
        random.seed(42)
        random.random()
        assert campaign.schedule(prepared["pilot"]["sequences"]) == panels
    finally:
        random.setstate(original_random_state)
    assert len(panels) == 12
    assert {row["panel_id"] for row in panels} == {f"p{i:03d}" for i in range(12)}
    sequences = {row["sequence_id"] for row in prepared["pilot"]["sequences"]}
    assert len(sequences) == 21
    assert Counter((row["method"], row["arm"], row["repeat"]) for row in panels) == Counter(
        (method, arm, repeat) for method in ("ve", "batch") for arm in ARMS for repeat in range(3))
    for repeat in range(3):
        repeated = [row for row in panels if row["repeat"] == repeat]
        assert len({tuple(row["query_order"]) for row in repeated}) == 1
        assert all(set(row["query_order"]) == sequences and len(row["query_order"]) == 21 for row in repeated)
    for left, right in zip(panels[::2], panels[1::2]):
        assert (left["block_id"], left["repeat"], left["method"]) == (right["block_id"], right["repeat"], right["method"])
        assert {left["arm"], right["arm"]} == set(ARMS)
        assert left["query_order"] == right["query_order"]
    slots = prepared["slots"]
    assert slots == expected_slots(prepared)
    assert len({(row["panel_id"], row["sequence_id"]) for row in slots}) == 252
    assert len({(row["sequence_id"], row["state"], row["method"], row["arm"], row["repeat"])
                for row in slots}) == len(slots) == 756


def test_case_selection_uses_sum_and_case_id_tie_break():
    def case(name, counts):
        return {"case_id": name, "states": [{"configuration_count": value} for value in counts]}
    cases = [case("large-product", [4, 4, 4]), case("b", [1, 1, 11]), case("a", [2, 5, 5])]
    assert campaign.select_pilot(cases)["case_id"] == "a"
    assert campaign.select_pilot(list(reversed(cases)))["case_id"] == "a"


def test_panel_keeps_source_assignment_indices_and_compact_non_dummy_panel_order(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    metadata_archive(tmp_path / "source.zip", labels=["DUMMY", "ALA", "HIP", "DUMMY", "HIE", "HID"])
    pilot = campaign.describe_panel({"case_id": "synthetic", "local_path": "source.zip"})
    assert [row["label"] for row in pilot["sequences"]] == ["ALA", "HIP", "HIE", "HID"]
    assert [row["panel_index"] for row in pilot["sequences"]] == [0, 1, 2, 3]
    assert [row["assignment"] for row in pilot["sequences"]] == [
        {"0": index, "1": 0} for index in (1, 2, 4, 5)]


@pytest.mark.parametrize("field,value", [
    ("sequence_id", "unplanned"), ("state", "unplanned"), ("method", "unplanned"),
    ("arm", "unplanned"), ("repeat", 99), ("panel_id", "unplanned"), ("slot_id", "unplanned"),
    ("case_id", "unplanned"), ("profile", "unplanned"),
])
def test_plan_rejects_full_size_ledger_with_changed_identity(prepared, field, value):
    plan = deepcopy(prepared)
    plan["slots"][0][field] = value
    with pytest.raises(REJECTED):
        campaign.verify_plan(plan)


@pytest.mark.parametrize("corruption", ["missing", "duplicate", "extra"])
def test_plan_rejects_missing_duplicate_and_extra_slots(prepared, corruption):
    plan = deepcopy(prepared)
    if corruption == "missing":
        plan["slots"].pop()
    elif corruption == "duplicate":
        plan["slots"][1] = deepcopy(plan["slots"][0])
    else:
        plan["slots"].append({**plan["slots"][0], "slot_id": "extra"})
    with pytest.raises(REJECTED):
        campaign.verify_plan(plan)


@pytest.mark.parametrize("corruption", ["case_counts", "pilot_archive", "assignment", "label", "query_order"])
def test_plan_rejects_selection_or_panel_changes_even_with_unchanged_source_hashes(prepared, corruption):
    plan = deepcopy(prepared)
    if corruption == "case_counts":
        plan["cases"][0]["states"][0]["configuration_count"] += 1
    elif corruption == "pilot_archive":
        plan["pilot"]["archive"] = deepcopy(plan["cases"][1]["archive"])
    elif corruption == "assignment":
        plan["pilot"]["sequences"][0]["assignment"]["1"] = 1
    elif corruption == "label":
        plan["pilot"]["sequences"][0]["label"] = "unplanned"
    else:
        plan["panels"][0]["query_order"].reverse()
    with pytest.raises(REJECTED):
        campaign.verify_plan(plan)


@pytest.mark.parametrize("identity", ["implementation_inventory", "grader_freeze", "grader_protocol", "source_manifest", "preflight_validation", "comparator_audit", "archive"])
def test_plan_checks_every_declared_input_identity(prepared, identity):
    if identity == "implementation_inventory":
        item = prepared[identity][0]
    elif identity == "grader_protocol":
        item = campaign.read(campaign.ROOT / prepared["grader_freeze"]["path"])["files"][0]
    elif identity == "archive":
        item = prepared["cases"][3]["archive"]
    else:
        item = prepared[identity]
    path = campaign.ROOT / item["path"]
    path.write_bytes(path.read_bytes() + b"\nchanged after freeze")
    with pytest.raises(REJECTED):
        campaign.verify_plan(prepared)


def test_normalization_preserves_decimal_values_and_failed_reference_coverage(prepared):
    raw = raw_references(prepared["pilot"])
    raw["rows"].reverse()
    raw["rows"][0]["states"]["complex"]["values"]["stored_binary64_log"]["logZ"] = "10.000000000000000000000000000000000001"
    raw["rows"][0]["scores"]["stored_binary64_log"]["logKstar"] = "5.000000000000000000000000000000000001"
    failed_state = raw["rows"][1]["states"]["ligand"]
    del failed_state["values"]
    failed_state.update({"status": "timeout", "reason": "synthetic reference cap"})
    raw["rows"][1]["scores"]["stored_binary64_log"] = {"status": "unresolved", "reason": "missing reference"}
    result = campaign.normalize_references(raw, prepared["pilot"])
    by_index = {row["panel_index"]: row["sequence_id"] for row in prepared["pilot"]["sequences"]}
    assert set(result) == set(by_index.values())
    assert result[by_index[raw["rows"][0]["panel_index"]]]["states"]["complex"] == "10.000000000000000000000000000000000001"
    failed = result[by_index[raw["rows"][1]["panel_index"]]]
    assert "ligand" not in failed["states"]
    assert failed["score"]["status"] == "unresolved"


@pytest.mark.parametrize("corruption", ["archive", "case", "selector", "sequence", "label", "missing", "duplicate", "extra"])
def test_normalization_rejects_wrong_panel_or_source_identity(prepared, corruption):
    raw = raw_references(prepared["pilot"])
    row = raw["rows"][0]
    if corruption == "archive":
        raw["source_hashes"]["archive_sha256"] = "0" * 64
    elif corruption == "case":
        raw["case_id"] = "different-case"
    elif corruption == "selector":
        row["selector"] = 99
    elif corruption == "sequence":
        row["sequence"]["1"] = "SER"
    elif corruption == "label":
        row["label"] = "different-label"
    elif corruption == "missing":
        raw["rows"].pop()
    elif corruption == "duplicate":
        raw["rows"][1]["panel_index"] = row["panel_index"]
    else:
        raw["rows"].append({**deepcopy(row), "panel_index": 999})
    with pytest.raises(REJECTED):
        campaign.normalize_references(raw, prepared["pilot"])


def test_finite_score_requires_every_state_and_its_own_error_within_tolerance(science):
    assert campaign.validate_query(query(), references(), science)["status"] == "success"
    wrong_score = campaign.validate_query(query(score=5.0000001), references(), science)
    assert wrong_score["status"] != "success"
    assert wrong_score["absolute_log_k_error"] == pytest.approx(1e-7, abs=1e-14)
    wrong_state = query()
    wrong_state["states"]["protein"]["log_z"] += 2e-8
    assert campaign.validate_query(wrong_state, references(), science)["status"] != "success"
    incomplete = query()
    incomplete["states"]["ligand"] = {"status": "panel_budget_skip"}
    assert campaign.validate_query(incomplete, references(), science)["status"] != "success"


def test_decimal_reference_error_is_not_lost_to_binary64_rounding(science):
    logs = {"complex": 1e16, "protein": 0.0, "ligand": 0.0}
    expected = {"complex": "10000000000000000.00000002", "protein": "0", "ligand": "0"}
    result = campaign.validate_query(query(logs, score=1e16), references(expected, score=expected["complex"]), science)
    assert result["state_checks"]["complex"]["status"] == "wrong_answer"
    assert Decimal(str(result["state_checks"]["complex"]["absolute_log_error"])) == Decimal("0.00000002")
    assert result["status"] != "success"


@pytest.mark.parametrize("zero_states", [("protein",), ("ligand",), ("complex", "protein"), tuple(campaign.STATES)])
def test_zero_denominator_including_zero_over_zero_is_correct_but_never_ranked(science, zero_states):
    logs = dict(zip(campaign.STATES, (10.0, 3.0, 2.0)))
    logs.update({state: "-inf" for state in zero_states})
    expected = {state: "-Infinity" if value == "-inf" else str(value) for state, value in logs.items()}
    observed = query(logs, score_status="undefined_zero_denominator", score=None)
    result = campaign.validate_query(observed, references(expected, status="undefined", score=None), science)
    assert result["status"] == "correct_undefined"
    assert result["absolute_log_k_error"] is None
    observed["score"] = {"status": "finite", "log_k": 0.0}
    assert campaign.validate_query(observed, references(expected, status="undefined", score=None), science)["status"] != "success"


def test_exact_zero_numerator_is_rankable_only_with_matching_zero_status(science):
    logs = {"complex": "-inf", "protein": 3.0, "ligand": 2.0}
    expected = {"complex": "-Infinity", "protein": "3", "ligand": "2"}
    ref = references(expected, status="zero numerator", score="-Infinity")
    assert campaign.validate_query(query(logs, score_status="zero_numerator", score="-inf"), ref, science)["status"] == "success"
    assert campaign.validate_query(query(logs, score=-1e300), ref, science)["status"] != "success"
    logs["complex"] = -1e300
    assert campaign.validate_query(query(logs, score_status="zero_numerator", score="-inf"), ref, science)["status"] != "success"


def test_finite_score_status_cannot_hide_negative_infinity(science):
    result = campaign.validate_query(query(score="-inf"), references(), science)
    assert result["status"] != "success"


def test_method_agreement_without_independent_reference_cannot_pass(science):
    assert campaign.validate_query(query(), {}, science)["status"] != "success"
    ref = references()
    del ref["s"]["states"]["ligand"]
    ref["s"]["score"] = {"status": "unresolved"}
    assert campaign.validate_query(query(), ref, science)["status"] != "success"


def journal_query(pilot, sequence):
    variant = next(row for row in pilot["sequences"] if row["sequence_id"] == sequence)
    return {**query(), "sequence_id": sequence, "label": variant["label"],
            "assignment": deepcopy(variant["assignment"])}


@pytest.mark.parametrize("completed", [0, 1, 20])
def test_partial_query_journal_recovers_every_planned_state_slot_without_inventing_success(prepared, completed):
    panels = prepared["panels"]
    recovered = []
    for panel in panels:
        journal = [journal_query(prepared["pilot"], sequence) for sequence in panel["query_order"][:completed]]
        rows = campaign.recover_queries(None, journal, panel, prepared["pilot"], "worker_timeout_not_attempted")
        assert [row["sequence_id"] for row in rows] == panel["query_order"]
        assert rows[:completed] == journal
        for row in rows[completed:]:
            assert row["score"] == {"status": "incomplete", "log_k": None}
            assert set(row["states"]) == set(campaign.STATES)
            assert all(cell["status"] == "worker_timeout_not_attempted" and cell["reason"]
                       for cell in row["states"].values())
        recovered.extend((panel["panel_id"], row["sequence_id"], state)
                         for row in rows for state in row["states"])
    assert len(recovered) == len(set(recovered)) == 756


@pytest.mark.parametrize("corruption", ["duplicate", "extra", "wrong_order", "missing_state", "extra_state", "label", "assignment"])
def test_recovered_journal_rejects_duplicate_extra_and_changed_query_identities(prepared, corruption):
    panel = prepared["panels"][0]
    rows = [journal_query(prepared["pilot"], sequence) for sequence in panel["query_order"][:2]]
    if corruption == "duplicate":
        rows[1] = deepcopy(rows[0])
    elif corruption == "extra":
        rows.append({**deepcopy(rows[0]), "sequence_id": "unplanned"})
    elif corruption == "wrong_order":
        rows.reverse()
    elif corruption == "missing_state":
        del rows[0]["states"]["ligand"]
    elif corruption == "extra_state":
        rows[0]["states"]["unplanned"] = {"status": "complete", "log_z": 0.0}
    elif corruption == "label":
        rows[0]["label"] = "unplanned"
    else:
        rows[0]["assignment"]["1"] = 1
    with pytest.raises(REJECTED):
        campaign.recover_queries(None, rows, panel, prepared["pilot"], "worker_timeout_not_attempted")


def test_final_result_cannot_claim_complete_panel_with_only_a_journal_prefix(prepared):
    panel = prepared["panels"][0]
    rows = [journal_query(prepared["pilot"], panel["query_order"][0])]
    with pytest.raises(REJECTED):
        campaign.recover_queries({"queries": rows}, rows, panel, prepared["pilot"], "not_attempted")


def test_final_result_cannot_hide_an_extra_attempt_in_the_query_journal(prepared):
    panel = prepared["panels"][0]
    rows = [journal_query(prepared["pilot"], sequence) for sequence in panel["query_order"]]
    with pytest.raises(REJECTED):
        campaign.recover_queries({"queries": rows}, [*rows, deepcopy(rows[0])], panel, prepared["pilot"], "not_attempted")


@pytest.mark.parametrize("wrong_hash", [None, "0" * 64])
def test_correct_numbers_do_not_pass_for_missing_or_changed_runtime_target(science, wrong_hash):
    observed = query()
    expected = {state: "a" * 64 for state in campaign.STATES}
    for entry in observed["states"].values():
        entry["target_sha256"] = "a" * 64
    if wrong_hash is None:
        del observed["states"]["complex"]["target_sha256"]
    else:
        observed["states"]["complex"]["target_sha256"] = wrong_hash
    validation = campaign.validate_query(observed, references(), science)
    assert validation["status"] == "success"
    checked = campaign.enforce_target_identity(observed, validation, expected, {})
    assert checked["status"] != "success"
    assert checked["state_checks"]["complex"]["status"] == "target_fingerprint_mismatch"


@pytest.mark.parametrize("corruption", [None, "missing_origin", "wrong_target", "wrong_value", "nonzero_cost"])
def test_exact_target_cache_reuse_requires_a_completed_matching_origin(science, corruption):
    observed = query()
    expected = {state: "a" * 64 for state in campaign.STATES}
    for entry in observed["states"].values():
        entry["target_sha256"] = "a" * 64
    observed["states"]["ligand"].update({"cache_hit": True,
        "cache_origin": {"sequence_id": "previous", "state": "ligand"}, "solver_call_seconds": 0})
    previous = {"status": "complete", "target_sha256": "a" * 64, "log_z": 2.0}
    known = {("previous", "ligand"): previous}
    if corruption == "missing_origin":
        known.clear()
    elif corruption == "wrong_target":
        previous["target_sha256"] = "b" * 64
    elif corruption == "wrong_value":
        previous["log_z"] = 3.0
    elif corruption == "nonzero_cost":
        observed["states"]["ligand"]["solver_call_seconds"] = 1
    checked = campaign.enforce_target_identity(observed, campaign.validate_query(observed, references(), science), expected, known)
    assert (checked["status"] == "success") is (corruption is None)


def test_preparation_budget_skip_is_retained_and_does_not_launch_a_worker(prepared, monkeypatch):
    launched = []
    monkeypatch.setattr(watchdog, "supervise", lambda *args, **kwargs: launched.append(args))
    monkeypatch.setattr(campaign.time, "perf_counter", lambda: 100.0)
    assert campaign.supervise_stage("synthetic-capped-stage", ["unused-worker"], 30, 110) is False
    assert not launched
    rows = [json.loads(line) for line in (campaign.OUT / "preparation.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["identity"] == "synthetic-capped-stage"
    assert rows[0]["status"] == "preparation_budget_skip"
    assert rows[0].get("reason")


def test_failed_source_audit_retains_all_14_audit_attempts_and_blocks_preparation(prepared, monkeypatch):
    attempts = []
    def stage(identity, command, seconds, deadline):
        attempts.append(identity)
        return identity != "audit-case-00"
    monkeypatch.setattr(campaign, "supervise_stage", stage)
    assert campaign.prepare_all() is False
    assert attempts == ["audit-" + case["case_id"] for case in prepared["cases"]]
    failure = campaign.read(campaign.OUT / "gate_failure.json")
    assert failure["reason"]


@pytest.mark.parametrize("corruption", ["sequence", "missing_arm", "extra_arm", "missing_state", "extra_state", "short_hash", "nonhex_hash"])
def test_execution_freeze_rejects_incomplete_or_invalid_target_hash_matrix(prepared, corruption):
    targets = execution_inputs(prepared)
    sequence = prepared["pilot"]["sequences"][0]["sequence_id"]
    if corruption == "sequence":
        targets["extra-sequence"] = deepcopy(targets[sequence])
    elif corruption == "missing_arm":
        del targets[sequence]["propagated"]
    elif corruption == "extra_arm":
        targets[sequence]["extra"] = deepcopy(targets[sequence]["simplified"])
    elif corruption == "missing_state":
        del targets[sequence]["simplified"]["ligand"]
    elif corruption == "extra_state":
        targets[sequence]["simplified"]["extra"] = "a" * 64
    else:
        targets[sequence]["simplified"]["complex"] = "abc" if corruption == "short_hash" else "z" * 64
    dump(campaign.OUT / "targets.json", {"targets": targets, "original_models": []})
    with pytest.raises(REJECTED):
        campaign.freeze_execution()


def test_execution_freeze_preserves_science_schedule_and_all_preparation_hashes(prepared):
    targets = execution_inputs(prepared)
    campaign.freeze_execution()
    manifest = campaign.read(campaign.RUN / "manifest.json")
    assert manifest["scientific_choices"] == prepared["scientific_choices"]
    assert manifest["panels"] == prepared["panels"]
    assert manifest["slots"] == prepared["slots"]
    assert manifest["targets"] == targets
    assert manifest["preparation_manifest"] == campaign.artifact(campaign.OUT / "preparation_manifest.json")
    inventory = {row["path"]: row for row in manifest["file_inventory"]}
    for path in campaign.OUT.rglob("*"):
        if path.is_file():
            assert inventory[str(path.relative_to(campaign.ROOT))] == campaign.artifact(path)
    for item in manifest["file_inventory"]:
        assert item == campaign.artifact(campaign.ROOT / item["path"])


def test_execution_freeze_rejects_numeric_target_file_changed_after_hash_preparation(prepared):
    execution_inputs(prepared)
    sequence = prepared["pilot"]["sequences"][0]["sequence_id"]
    dump(campaign.OUT / "models" / f"{sequence}__simplified__complex.json",
         {"domains": [2], "factors": [{"scope": [0], "log_values": [999, 1000]}]})
    with pytest.raises(REJECTED):
        campaign.freeze_execution()


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.mark.parametrize("bad_identity", [None, "panel", "manifest", "query_order"])
def test_controller_timeout_or_invalid_output_preserves_all_planned_rows(prepared, monkeypatch, bad_identity):
    targets = execution_inputs(prepared)
    campaign.freeze_execution()
    clock = [0.0]
    launches = []
    monkeypatch.setattr(campaign.time, "perf_counter", lambda: clock[0])
    def supervise(command, **kwargs):
        panel = next(row for row in prepared["panels"] if row["panel_id"] == command[-2])
        output = campaign.RUN / "raw" / (panel["panel_id"] + ".json")
        kwargs["stdout_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["stdout_path"].write_text("synthetic worker timeout\n")
        kwargs["stderr_path"].write_text("")
        rows = [journal_query(prepared["pilot"], sequence) for sequence in panel["query_order"][:1]]
        if bad_identity is not None and panel["panel_id"] == "p000":
            rows = [journal_query(prepared["pilot"], sequence) for sequence in panel["query_order"]]
        for row in rows:
            for state in campaign.STATES:
                row["states"][state]["target_sha256"] = targets[row["sequence_id"]][panel["arm"]][state]
        type(output)(str(output) + ".progress.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
        if bad_identity is not None and panel["panel_id"] == "p000":
            raw = {"panel_id": panel["panel_id"], "manifest_sha256": campaign.artifact(campaign.RUN / "manifest.json")["sha256"],
                   "queries": deepcopy(rows), "worker_peak_rss_before_result": 4096, "source_status": "loaded"}
            if bad_identity == "panel":
                raw["panel_id"] = "unplanned"
            elif bad_identity == "manifest":
                raw["manifest_sha256"] = "0" * 64
            else:
                raw["queries"].reverse()
            dump(output, raw)
        clock[0] += 20
        launches.append((panel["panel_id"], kwargs["wall_timeout_seconds"], kwargs["rss_ceiling_bytes"]))
        return {"exit_code": -15, "termination_reason": "timeout", "sampled_peak_rss_bytes": 4096,
                "wall_seconds": 20, "cpu_seconds": .01}
    monkeypatch.setattr(watchdog, "supervise", supervise)
    campaign.run_all()
    panels = read_lines(campaign.RUN / "panels.jsonl")
    queries = read_lines(campaign.RUN / "queries.jsonl")
    states = read_lines(campaign.RUN / "states.jsonl")
    assert len(launches) == len(panels) == 12
    assert {row[1:] for row in launches} == {(20, 512 * 1024**2)}
    assert len(queries) == len({(row["panel_id"], row["sequence_id"]) for row in queries}) == 252
    assert len(states) == len({row["slot_id"] for row in states}) == 756
    if bad_identity is None:
        assert Counter(row["raw"]["status"] for row in states) == {"complete": 36, "timeout": 720}
    else:
        assert panels[0]["status"] != "complete"
    assert all(not row["ranking"]["full_declared_panel"] for row in panels)
    campaign.summarize()
    summary = campaign.read(campaign.RUN / "summary.json")
    assert summary["planned_state_slots"] == 756
    assert summary["planned_queries"] == 252


@pytest.mark.parametrize("changed_query_identity", [None, "panel_id", "sequence_id"])
def test_campaign_budget_exhaustion_records_all_unlaunched_slots(prepared, monkeypatch, changed_query_identity):
    prepared["scientific_choices"]["resources"]["campaign_seconds"] = 1
    dump(campaign.OUT / "preparation_manifest.json", prepared)
    (campaign.OUT / "preparation_manifest.sha256").write_text(
        campaign.artifact(campaign.OUT / "preparation_manifest.json")["sha256"] + "  preparation_manifest.json\n")
    execution_inputs(prepared)
    campaign.freeze_execution()
    launches = []
    monkeypatch.setattr(watchdog, "supervise", lambda *args, **kwargs: launches.append(args))
    monkeypatch.setattr(campaign.time, "perf_counter", lambda: 0.0)
    campaign.run_all()
    assert not launches
    panels = read_lines(campaign.RUN / "panels.jsonl")
    queries = read_lines(campaign.RUN / "queries.jsonl")
    states = read_lines(campaign.RUN / "states.jsonl")
    assert len(panels) == 12 and all(row["status"] == "campaign_budget_skip" for row in panels)
    assert len(queries) == 252 and all(row["validation"]["status"] != "success" for row in queries)
    assert len(states) == 756 and all(row["raw"]["status"] == "campaign_budget_skip" for row in states)
    assert all(row["raw"]["reason"] for row in states)
    if changed_query_identity is not None:
        queries[0][changed_query_identity] = "unplanned"
        (campaign.RUN / "queries.jsonl").write_text("".join(json.dumps(row) + "\n" for row in queries))
        with pytest.raises(REJECTED):
            campaign.summarize()
    else:
        campaign.summarize()


@pytest.mark.parametrize("changed_field", ["references", "targets", "file_inventory"])
def test_execution_manifest_mutation_after_seal_cannot_launch_any_worker(prepared, monkeypatch, changed_field):
    execution_inputs(prepared)
    campaign.freeze_execution()
    path = campaign.RUN / "manifest.json"
    manifest = campaign.read(path)
    sequence = prepared["pilot"]["sequences"][0]["sequence_id"]
    if changed_field == "references":
        manifest["references"][sequence]["states"]["complex"] = "11"
    elif changed_field == "targets":
        manifest["targets"][sequence]["simplified"]["complex"] = "0" * 64
    else:
        manifest["file_inventory"].pop()
    dump(path, manifest)
    launches = []
    def unexpected_launch(*args, **kwargs):
        launches.append(args)
        raise RuntimeError("A changed execution seal launched a worker")
    monkeypatch.setattr(watchdog, "supervise", unexpected_launch)
    with pytest.raises(REJECTED):
        campaign.run_all()
    assert not launches


@pytest.mark.parametrize("choice", ["resources", "accuracy", "reference_policy"])
def test_measurement_plan_rejects_scientific_choices_changed_after_preparation_freeze(prepared, choice):
    execution_inputs(prepared)
    campaign.freeze_execution()
    manifest = campaign.read(campaign.RUN / "manifest.json")
    manifest["scientific_choices"][choice]["unplanned_change"] = True
    with pytest.raises(REJECTED):
        campaign.verify_plan(manifest)
