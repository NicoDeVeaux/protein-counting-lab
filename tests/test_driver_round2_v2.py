import copy
import hashlib
import json

import pytest

import scripts.campaign_round2_v2 as driver
import scripts.execute_round2_v2 as execute


def fixture_catalog(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    amendment = tmp_path/"amendment.json"
    amendment.write_text('{"native_memory_mebibytes":1024}')
    art = {"path":"amendment.json","sha256":hashlib.sha256(amendment.read_bytes()).hexdigest()}
    model = {"model_id":"control","cohort":"synthetic_measured",
             "fixed_sequence_and_conditioning":"none","source_semantics":"stored log target",
             "representations":[{"representation_id":"original","files":[{"path":"model.json","sha256":"0"*64}],"target_relation":"original target"}]}
    rows = [{"trial_id":"00000","model_id":"control","representation_id":"original","method_id":"pyagrum","resource_profile_id":"high","accuracy_contract_id":"exact_numeric","repeat":0,"schedule_index":0,"static_skip_reason":None},
            {"trial_id":"00001","model_id":"control","representation_id":"original","method_id":"ve","resource_profile_id":"high","accuracy_contract_id":"exact_numeric","repeat":0,"schedule_index":1,"static_skip_reason":None}]
    catalog = {"amendment":art,"models":[model]}
    prior = {"models":[copy.deepcopy(model)],"planned_trials":copy.deepcopy(rows)}
    return catalog,rows,prior


def test_corrective_matrix_accepts_full_unchanged_targets(tmp_path,monkeypatch):
    catalog,rows,prior = fixture_catalog(tmp_path,monkeypatch)
    assert driver.check_corrective_matrix(catalog,rows,prior) is None


def test_corrective_matrix_rejects_failure_only_selection(tmp_path,monkeypatch):
    catalog,rows,prior = fixture_catalog(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match="full unchanged original trial matrix"):
        driver.check_corrective_matrix(catalog,rows[:1],prior)


def test_corrective_matrix_rejects_reordered_trials(tmp_path,monkeypatch):
    catalog,rows,prior = fixture_catalog(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match="full unchanged original trial matrix"):
        driver.check_corrective_matrix(catalog,list(reversed(rows)),prior)


@pytest.mark.parametrize("change",["hash","conditioning","semantics"])
def test_corrective_matrix_rejects_target_changes(tmp_path,monkeypatch,change):
    catalog,rows,prior = fixture_catalog(tmp_path,monkeypatch)
    model = catalog["models"][0]
    if change == "hash":
        model["representations"][0]["files"][0]["sha256"] = "1"*64
    elif change == "conditioning":
        model["fixed_sequence_and_conditioning"] = "another sequence"
    else:
        model["source_semantics"] = "different temperature"
    with pytest.raises(ValueError,match="changed a model"):
        driver.check_corrective_matrix(catalog,rows,prior)


def test_corrective_matrix_requires_intact_dated_amendment(tmp_path,monkeypatch):
    catalog,rows,prior = fixture_catalog(tmp_path,monkeypatch)
    (tmp_path/"amendment.json").write_text("changed")
    with pytest.raises(ValueError,match="hash mismatch"):
        driver.check_corrective_matrix(catalog,rows,prior)
    del catalog["amendment"]
    with pytest.raises(ValueError,match="dated, hashed amendment"):
        driver.check_corrective_matrix(catalog,rows,prior)


def test_execution_wrapper_uses_new_namespace_and_all_three_stages(tmp_path,monkeypatch):
    monkeypatch.setattr(execute,"ROOT",tmp_path)
    calls = []
    monkeypatch.setattr(execute,"freeze",lambda catalog,run_dir:calls.append(("freeze",catalog,run_dir)))
    monkeypatch.setattr(execute,"run",lambda run_dir:calls.append(("run",run_dir)))
    monkeypatch.setattr(execute,"summarize",lambda run_dir:calls.append(("summarize",run_dir)))
    execute.main()
    destination = tmp_path/"runs/campaign-002-amendment-001"
    assert calls == [("freeze",tmp_path/"prepared/campaign-002/amended_catalog.json",destination),("run",destination),("summarize",destination)]
