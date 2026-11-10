import math
import os
from pathlib import Path
import sys
import hashlib

import pytest

from experiments.round2_watchdog import supervise
from scripts.campaign_round2 import classify_raw, validate_value
import scripts.campaign_round2 as driver


def run_control(tmp_path, code, *, rss=256*1024**2, timeout=2):
    return supervise([sys.executable,"-c",code],cwd=tmp_path,env={"PATH":os.environ["PATH"]},
                     stdout_path=tmp_path/"stdout",stderr_path=tmp_path/"stderr",
                     rss_ceiling_bytes=rss,wall_timeout_seconds=timeout)


def test_watchdog_retains_successful_output(tmp_path):
    result = run_control(tmp_path,"print('control-output')")
    assert result["exit_code"] == 0
    assert result["termination_reason"] is None
    assert (tmp_path/"stdout").read_text() == "control-output\n"
    assert result["cpu_seconds"] >= 0


def test_watchdog_terminates_own_process_on_timeout(tmp_path):
    result = run_control(tmp_path,"import time;time.sleep(2)",timeout=.1)
    assert result["termination_reason"] == "timeout"
    assert result["exit_code"] != 0
    assert result["limit_trigger_seconds"] >= .1
    assert result["kill_seconds"] >= result["limit_trigger_seconds"]


def test_watchdog_detects_touched_allocation(tmp_path):
    result = run_control(tmp_path,"import time;a=bytearray(96*1024*1024);time.sleep(2)",rss=48*1024**2)
    assert result["termination_reason"] == "rss_limit"
    assert result["sampled_peak_rss_bytes"] > 48*1024**2
    assert result["overshoot_bytes"] > 0
    assert result["instantaneous_ceiling_guaranteed"] is False


@pytest.mark.parametrize("source,expected",[("conversion_underflow","unsupported_conversion"),("wrapper_preflight_clique_limit","predicted_table_cap"),("time_limit","timeout"),("state_limit","planned_skip"),("numerical_failure","numerical_failure")])
def test_failure_reasons_remain_distinct(source,expected):
    assert classify_raw({"status":source}) == expected


def test_reference_missing_is_unverified():
    value,result = validate_value({"log_z":2.},None)
    assert value == 2.
    assert result["status"] == "unverified"


def test_zero_mass_never_means_underflow():
    value,result = validate_value({"log_z":"-inf"},{"reference_id":"zero","log_z":"-Infinity","reference_uncertainty":0})
    assert value == -math.inf and result["status"] == "passed"
    _,wrong = validate_value({"log_z":"-inf"},{"reference_id":"positive","log_z":-1000.})
    assert wrong["status"] == "failed" and wrong["zero_mass_agrees"] is False


def test_nan_or_positive_infinity_are_not_valid_results():
    for value in ("nan","inf"):
        with pytest.raises(ValueError):
            validate_value({"log_z":value},None)


def test_catalog_inventory_covers_representation_and_evidence_files(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,"ROOT",tmp_path)
    model = tmp_path/"data/models/example.json"
    proof = tmp_path/"prepared/proof.json"
    model.parent.mkdir(parents=True)
    proof.parent.mkdir(parents=True)
    model.write_text('{"domains":[2]}')
    proof.write_text('{"exact":true}')
    art = lambda p: {"path":str(p.relative_to(tmp_path)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    catalog = {"models":[{"representations":[{"files":[art(model)],"evidence":[art(proof)]}]}]}
    assert set(driver.catalog_artifacts(catalog)) == {model,proof}
    model.write_text('{"domains":[3]}')
    with pytest.raises(ValueError,match="hash mismatch"):
        list(driver.catalog_artifacts(catalog))
