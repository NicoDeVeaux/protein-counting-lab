import copy
import hashlib
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

import scripts.campaign_round3 as driver
import scripts.execute_round3 as execute


ACTUAL_ROOT = driver.ROOT
SCHEMAS = {name: json.loads((ACTUAL_ROOT/"grader/campaign-003"/(name+".schema.json")).read_text())
           for name in ("manifest", "trial")}


def schedule_model(name, profiles=("low", "high")):
    return {"model_id":name, "representations":[{"representation_id":arm, "resource_profiles":list(profiles)}
                                                 for arm in driver.REPRESENTATIONS]}


def test_full_cohort_schedule_is_deterministic_and_preserves_324_identities():
    models = [schedule_model(f"protein-{i}") for i in range(6)] + [schedule_model(f"control-{i}", ("high",)) for i in range(6)]
    rows = driver.plan_trials(models)
    assert rows == driver.plan_trials({"models":list(reversed(models))})
    assert len(rows) == 324
    identities = {(r["model_id"], r["representation_id"], r["method_id"], r["resource_profile_id"], r["repeat"]) for r in rows}
    assert len(identities) == 324
    assert [r["trial_id"] for r in rows] == [f"{i:05d}" for i in range(324)]
    assert [r["schedule_index"] for r in rows] == list(range(324))
    assert [r["repeat"] for r in rows] == sorted(r["repeat"] for r in rows)
    assert all(r["static_skip_reason"] is None for r in rows)
    for first, second in zip(rows[::2], rows[1::2]):
        assert first["block_id"] == second["block_id"]
        assert first["method_id"] == second["method_id"]
        assert {first["representation_id"], second["representation_id"]} == set(driver.REPRESENTATIONS)
    for offset in range(0, len(rows), 6):
        block = rows[offset:offset+6]
        assert len({r["block_id"] for r in block}) == 1
        assert {r["method_id"] for r in block} == set(driver.METHODS)


@pytest.mark.parametrize("corruption", ["duplicate_model", "missing_arm", "exclude_arm", "mismatched_profile", "duplicate_profile"])
def test_schedule_rejects_silent_case_or_arm_selection(corruption):
    models = [schedule_model("control")]
    if corruption == "duplicate_model":
        models.append(copy.deepcopy(models[0]))
    elif corruption == "missing_arm":
        models[0]["representations"].pop()
    elif corruption == "exclude_arm":
        models[0]["representations"][0]["measured"] = False
    elif corruption == "mismatched_profile":
        models[0]["representations"][0]["resource_profiles"] = ["low"]
    else:
        models[0]["representations"][0]["resource_profiles"] = ["low", "low", "high"]
    with pytest.raises(ValueError):
        driver.plan_trials(models)


def test_no_static_enumeration_skip_can_make_preparation_free():
    model = schedule_model("large")
    for rep in model["representations"]:
        rep["structure"] = {"domain_cardinalities":[100]*100}
    assert all(row["static_skip_reason"] is None for row in driver.plan_trials([model]))


def artifact(path, root):
    return {"path":str(path.relative_to(root)), "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def test_preparation_manifest_binds_schedule_references_resources_and_code(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    implementation = tmp_path/"implementation.py"
    implementation.write_text("frozen code")
    models = [schedule_model("control")]
    document = {"models":models, "planned_trials":driver.plan_trials(models), "resource_profiles":[],
                "total_wall_budget_seconds":900, "preprocessing_limit_seconds":3,
                "references":{"control":{"log_z":"0"}}, "implementation_inventory":[artifact(implementation,tmp_path)]}
    path = tmp_path/"preparation.json"
    path.write_text(json.dumps(document))
    catalog = {"models":copy.deepcopy(models), "preparation_manifest":artifact(path,tmp_path), "references":copy.deepcopy(document["references"])}
    assert driver.verify_preparation_manifest(catalog, document["planned_trials"], []) == document
    with pytest.raises(ValueError, match="full trial schedule"):
        driver.verify_preparation_manifest(catalog, document["planned_trials"][:-1], [])
    with pytest.raises(ValueError, match="resource budgets"):
        driver.verify_preparation_manifest(catalog, document["planned_trials"], [{"different":True}])
    catalog["references"]["control"]["log_z"] = "1"
    with pytest.raises(ValueError, match="reference"):
        driver.verify_preparation_manifest(catalog, document["planned_trials"], [])
    catalog["references"] = document["references"]
    catalog["models"][0]["pipeline_input"] = {"path":"different", "sha256":"a"*64}
    with pytest.raises(ValueError, match="prospective input"):
        driver.verify_preparation_manifest(catalog, document["planned_trials"], [])
    catalog["models"] = models
    implementation.write_text("changed after freeze")
    with pytest.raises(ValueError, match="Implementation changed"):
        driver.verify_preparation_manifest(catalog, document["planned_trials"], [])


def test_catalog_artifact_rejects_path_escape_and_wrong_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    path = tmp_path/"input.json"
    path.write_text("input")
    good = artifact(path,tmp_path)
    assert list(driver.catalog_artifacts(good)) == [path]
    with pytest.raises(ValueError, match="hash mismatch"):
        list(driver.catalog_artifacts({**good,"sha256":"0"*64}))
    with pytest.raises(ValueError, match="outside"):
        list(driver.catalog_artifacts({"path":"../outside", "sha256":"0"*64}))


def test_worker_command_always_uses_original_input_and_cold_budget():
    model = {"pipeline_input":{"path":"original.json"}}
    rep = {"files":[{"path":"cached-prepared.json"}], "target_sha256":"a"*64}
    row = {"representation_id":"propagated", "method_id":"batch"}
    command = driver.worker_command("python",model,rep,row,{"table_cap_bytes":1024,"wall_timeout_seconds":10},Path("out.json"))
    assert command[:4] == ["python","-m","experiments.round3_pipeline","original.json"]
    assert "cached-prepared.json" not in command
    assert command[command.index("--expected-target-sha256")+1] == "a"*64
    assert command[command.index("--preprocessing-limit-seconds")+1] == "3"
    assert command[command.index("--time-limit-seconds")+1] == "10"
    assert command[command.index("--max-states")+1] == "20000000"


def run_fixture(tmp_path, monkeypatch, raw_status="complete", wrong_target=False, invalid_sidecar=False, post_result_peak=None):
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    monkeypatch.setattr(driver,"schema",lambda name:SCHEMAS[name])
    run_dir = tmp_path/"run"
    run_dir.mkdir()
    (run_dir/"manifest.json").write_text("{}")
    source = tmp_path/"original.json"
    source.write_text("{}")
    commands = tmp_path/"commands.json"
    commands.write_text('{"python":"fixture-python"}')
    model = schedule_model("control",("high",))
    model.update({"pipeline_input":artifact(source,tmp_path), "cohort":"correctness_control"})
    for rep in model["representations"]:
        rep.update({"target_sha256":"a"*64, "structure":{"predicted_largest_intermediate_bytes":16,
                    "predicted_workspace_bytes":48, "domain_cardinalities":[2]}})
    rows = driver.plan_trials([model])[:2]
    profile = driver.legacy.resource_profiles({"path":"unused", "sha256":"b"*64})[1]
    manifest = {"planned_trials":rows,"models":[model],"resource_profiles":[profile],
                "environment":{"commands":artifact(commands,tmp_path)},"total_wall_budget_seconds":900,
                "references":{"control":{"reference_id":"independent-control","log_z":"0"}}}
    monkeypatch.setattr(driver,"verify",lambda path:manifest)
    def supervise(command, **kwargs):
        kwargs["stdout_path"].write_text("retained stdout")
        kwargs["stderr_path"].write_text("")
        output = Path(command[command.index("--output")+1])
        raw = {"status":raw_status,"pipeline":{"target_sha256":"f"*64 if wrong_target else "a"*64,
               "load_seconds":.001,"propagation_seconds":.002,"simplification_seconds":.003,
               "target_validation_seconds":.0001,"inference_seconds":.01,"propagation_cpu_seconds":.001},
               "metrics":{"kernel_elapsed_seconds":.009},"log_z":0.0,"process_peak_rss_bytes":4096}
        output.write_text(json.dumps(raw))
        sidecar = {"serialization_seconds":.0004,"serialization_cpu_seconds":.0002}
        if post_result_peak is not None:
            sidecar["process_peak_rss_bytes_after_result"] = post_result_peak
        Path(str(output)+".timing.json").write_text("invalid json" if invalid_sidecar else json.dumps(sidecar))
        return {"started_at_utc":"2026-11-06T14:00:00Z","finished_at_utc":"2026-11-06T14:00:01Z",
                "exit_code":0,"signal":None,"termination_reason":None,"wall_seconds":.03,"cpu_seconds":.02,
                "rss_baseline_bytes":1024,"sampled_peak_rss_bytes":4096,"limit_trigger_seconds":None,
                "kill_seconds":None,"overshoot_bytes":0}
    monkeypatch.setattr(driver,"supervise",supervise)
    driver.run(run_dir)
    return run_dir, [json.loads(line) for line in (run_dir/"trials.jsonl").read_text().splitlines()]


def test_cold_pipeline_records_prep_inside_total_and_binds_runtime_target(tmp_path, monkeypatch):
    _, rows = run_fixture(tmp_path,monkeypatch)
    assert len(rows) == 2
    for row in rows:
        assert row["status"] == "success"
        assert row["timing"]["wall_seconds"] == .03
        assert row["timing"]["phases"]["propagation"] == .002
        assert row["timing"]["phases"]["target_fingerprint"] == .0001
        assert row["timing"]["phase_cpu_seconds"]["propagation"] == .001
        assert row["timing"]["phases"]["serialization"] == .0004
        assert row["timing"]["phase_cpu_seconds"]["serialization"] == .0002
        assert Path(tmp_path/row["serialization_timing_artifact"]["path"]).is_file()
        assert "offline_algebra_preparation_seconds" not in row["timing"]


def test_wrong_runtime_target_cannot_pass_a_matching_numeric_value(tmp_path, monkeypatch):
    _, rows = run_fixture(tmp_path,monkeypatch,wrong_target=True)
    assert all(row["status"] == "invalid_output" for row in rows)
    assert all(row["validation"]["status"] != "passed" for row in rows)


def test_enumeration_guard_keeps_cold_preparation_cost_and_every_row(tmp_path, monkeypatch):
    run_dir, rows = run_fixture(tmp_path,monkeypatch,raw_status="state_limit")
    assert all(row["status"] == "planned_skip" for row in rows)
    assert all(row["timing"]["wall_seconds"] == .03 and row["timing"]["phases"]["propagation"] == .002 for row in rows)
    driver.summarize(run_dir)
    summary = json.loads((run_dir/"summary.json").read_text())
    assert summary["recorded_trials"] == summary["planned_trials"] == 2
    assert summary["status_counts"] == {"planned_skip":2}
    assert not summary["missing_trial_ids"]


def test_preprocessing_timeout_is_retained_as_censored_stage(tmp_path, monkeypatch):
    _, rows = run_fixture(tmp_path,monkeypatch,raw_status="preprocessing_time_limit")
    assert all(row["status"] == "timeout" and row["failure_stage"] == "preprocessing" for row in rows)
    assert all(row["timing"]["right_censored"] for row in rows)


def test_wrapper_preserves_new_namespace_and_execution_order(tmp_path, monkeypatch):
    monkeypatch.setattr(execute,"ROOT",tmp_path)
    calls = []
    monkeypatch.setattr(execute,"prepare",lambda:calls.append(("prepare",)))
    monkeypatch.setattr(execute,"freeze",lambda catalog,path:calls.append(("freeze",catalog,path)))
    monkeypatch.setattr(execute,"run",lambda path:calls.append(("run",path)))
    monkeypatch.setattr(execute,"summarize",lambda path:calls.append(("summarize",path)))
    execute.main()
    assert calls == [("prepare",),("freeze",tmp_path/"prepared/campaign-003/catalog.json",tmp_path/"runs/campaign-003"),
                     ("run",tmp_path/"runs/campaign-003"),("summarize",tmp_path/"runs/campaign-003")]


def test_preparation_wrapper_freezes_before_static_target_work(monkeypatch):
    calls = []
    module = SimpleNamespace(setup_controls=lambda:calls.append("controls"),
                             freeze_preparation=lambda:calls.append("freeze_preparation"),
                             prepare_all=lambda:calls.append("prepare_all"))
    monkeypatch.setitem(sys.modules,"scripts.prepare_round3",module)
    execute.prepare()
    assert calls == ["controls", "freeze_preparation", "prepare_all"]


def test_invalid_timing_sidecar_retains_rows_as_infrastructure_failure(tmp_path, monkeypatch):
    _, rows = run_fixture(tmp_path,monkeypatch,invalid_sidecar=True)
    assert len(rows) == 2
    assert all(row["status"] == "infrastructure_error" for row in rows)
    assert all("sidecar" in row["failure_detail"] for row in rows)


def test_result_serialization_high_water_can_adjudicate_rss_failure(tmp_path, monkeypatch):
    peak = 600*1024**2
    _, rows = run_fixture(tmp_path,monkeypatch,post_result_peak=peak)
    for row in rows:
        assert row["status"] == "rss_limit"
        assert row["memory"]["rss_peak_bytes"] == 4096
        assert row["memory"]["worker_reported_before_result_peak_rss_bytes"] == 4096
        assert row["memory"]["worker_reported_after_result_peak_rss_bytes"] == peak
        assert row["memory"]["worker_reported_lifetime_peak_rss_bytes"] == peak
        assert row["memory"]["overshoot_bytes"] == peak-row["memory"]["rss_ceiling_bytes"]
        assert "Later stdout" in row["memory"]["worker_high_water_scope"]
