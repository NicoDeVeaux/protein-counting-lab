"""A bounded source-model binding-score ranking pilot with complete ledgers."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import resource
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "prepared/campaign-004"
RUN = ROOT / "runs/campaign-004"
STATES = ("complex", "protein", "ligand")
THREADS = {"OPENBLAS_NUM_THREADS":"1", "OMP_NUM_THREADS":"1", "MKL_NUM_THREADS":"1",
           "VECLIB_MAXIMUM_THREADS":"1", "PYTHONHASHSEED":"0"}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def read_preparation():
    path = OUT/"preparation_manifest.json"
    assert artifact(path)["sha256"] == (OUT/"preparation_manifest.sha256").read_text().split()[0],"Preparation manifest seal mismatch"
    return read(path)


def artifact(path):
    path = Path(path)
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False)+"\n")
    return artifact(path)


def peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value*1024)


def named(text, key):
    match = re.search(r"^"+re.escape(key)+r"\s*$", text, re.M)
    return json.JSONDecoder().raw_decode(text[match.end():].lstrip())[0]


def select_pilot(cases):
    return min(cases, key=lambda case:(sum(state["configuration_count"] for state in case["states"]), case["case_id"]))


def describe_panel(case):
    path = ROOT / case["local_path"]
    with zipfile.ZipFile(path) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".uai"))
        query = archive.read(member+".query").decode().split()
        selectors = [int(value) for value in query[1:]]
        assert int(query[0]) == len(selectors)
        summary = archive.read("uai_conversion_summary.txt").decode()
    amino = named(summary, "residue_aminoAcids")
    residues = named(summary, "residues")
    valid = lambda labels:[index for index,label in enumerate(labels) if label.upper() != "DUMMY"]
    chosen = next(selector for selector in selectors if len(valid(amino[str(selector)])) >= 2)
    base = {str(selector):valid(amino[str(selector)])[0] for selector in selectors}
    sequences = [{"sequence_id": f"s{ordinal:02d}_{amino[str(chosen)][index]}", "panel_index": ordinal,
                  "source_value_index": index,
                  "label": amino[str(chosen)][index], "assignment": base | {str(chosen):index}}
                 for ordinal,index in enumerate(valid(amino[str(chosen)]))]
    return {"case_id": case["case_id"], "archive": artifact(path), "selector": chosen,
            "residue": residues[chosen], "sequences": sequences, "selector_ids":selectors,
            "amino_acid_templates":{str(selector):amino[str(selector)] for selector in selectors},
            "panel_scope": "Source residue templates, with distinct histidine protonation labels; source-first fixed background, not an experimentally validated mutation panel."}


def schedule(sequences):
    rng = random.Random(2026110604)
    panels = []
    for repeat in range(3):
        order = [row["sequence_id"] for row in sequences]
        rng.shuffle(order)
        methods = ["ve", "batch"]
        rng.shuffle(methods)
        for method in methods:
            arms = ["simplified", "propagated"]
            rng.shuffle(arms)
            block = f"r{repeat}-{method}"
            for arm in arms:
                panels.append({"panel_id": f"p{len(panels):03d}", "block_id": block, "repeat": repeat,
                    "method": method, "arm": arm, "query_order": list(order)})
    return panels


def implementation_files():
    files = []
    for directory in ["experiments/three_state_data", "experiments/three_state_reference", "experiments/three_state_rank",
                      "experiments/inference", "experiments/structure", "experiments/zero_support", "experiments/round3_pipeline",
                      "experiments/round2_watchdog"]:
        files += [path for path in (ROOT / directory).rglob("*") if path.is_file() and path.suffix in {".py", ".md"} and "__pycache__" not in path.parts]
    files += [ROOT / name for name in ["scripts/campaign_round4.py", "scripts/execute_round4.py",
        "tests/test_three_state_data_round4.py", "tests/test_three_state_reference_round4.py", "tests/test_three_state_rank_round4.py",
        "tests/test_campaign_round4.py", "experiments/established/pyproject.toml", "experiments/established/uv.lock"]]
    return [artifact(path) for path in sorted(set(files))]


def derive_slots(panels, pilot):
    return [{"slot_id": f"{panel['panel_id']}/{sequence_id}/{state}", "panel_id": panel["panel_id"],
             "case_id":pilot["case_id"], "sequence_id":sequence_id, "state":state,
             "method":panel["method"], "arm":panel["arm"], "repeat":panel["repeat"], "profile":"common20s-512MiB-16MiB"}
            for panel in panels for sequence_id in panel["query_order"] for state in STATES]


def verify_targets(targets, pilot):
    assert set(targets) == {row["sequence_id"] for row in pilot["sequences"]}
    for arms in targets.values():
        assert set(arms) == {"simplified","propagated"}
        for states in arms.values():
            assert set(states) == set(STATES)
            assert all(isinstance(value,str) and re.fullmatch(r"[0-9a-f]{64}",value) for value in states.values())


def verify_plan(plan):
    assert plan["campaign"] == "004" and len(plan["cases"]) == 14
    assert len({case["case_id"] for case in plan["cases"]}) == 14
    for item in [plan["source_manifest"],plan["preflight_validation"],plan["comparator_audit"]]:
        assert artifact(ROOT/item["path"]) == item,item["path"]
    original = read(ROOT / plan["source_manifest"]["path"])
    expected_cases = [{"case_id":case["case_id"],"states":case["states"],"archive":artifact(ROOT / case["local_path"])} for case in original["cases"]]
    assert plan["cases"] == expected_cases
    assert select_pilot(plan["cases"])["case_id"] == plan["pilot"]["case_id"]
    assert plan["panels"] == schedule(plan["pilot"]["sequences"])
    assert plan["pilot"] == describe_panel(select_pilot(original["cases"]))
    assert len(plan["panels"]) == 12 and len({row["panel_id"] for row in plan["panels"]}) == 12
    assert len(plan["slots"]) == 12*len(plan["pilot"]["sequences"])*3
    assert len({row["slot_id"] for row in plan["slots"]}) == len(plan["slots"])
    assert plan["slots"] == derive_slots(plan["panels"],plan["pilot"])
    for item in plan["implementation_inventory"] + [plan["grader_freeze"]] + [case["archive"] for case in plan["cases"]]:
        assert artifact(ROOT / item["path"]) == item, item["path"]
    for item in read(ROOT / plan["grader_freeze"]["path"])["files"]:
        assert artifact(ROOT / item["path"]) == item,item["path"]
    if plan["phase"] == "measurement":
        item = plan["preparation_manifest"]
        assert artifact(ROOT/item["path"]) == item
        prior = read_preparation()
        for key in ["cases","pilot","panels","slots","scientific_choices","implementation_inventory","source_manifest",
                    "comparator_audit","preflight_validation","grader_freeze","root","environment"]:
            assert plan[key] == prior[key],key


def freeze_preparation():
    original = read(ROOT / "data/uai23_manifest.json")
    selected = select_pilot(original["cases"])
    pilot = describe_panel(selected)
    panels = schedule(pilot["sequences"])
    slots = derive_slots(panels,pilot)
    science = {"target": "Represented raw-source KstarMAP three-state score: sum exp(stored binary64 math.log weights); source zeros retained; no recovered physical-energy or experimental affinity claim.",
        "case_rule": "Minimum sum of existing source-first C/P/L Cartesian counts; case_id tie break.",
        "panel_rule": "First source selector with at least2 non-DUMMY labels, all such labels in source order; other selectors source-first non-DUMMY.",
        "methods": ["ve", "batch"], "arms": ["simplified", "propagated"], "seed": 2026110604,
        "ordering": "Deterministic min-fill VE; batch65536; no numerical threshold pruning.",
        "cache": "Raw archive parsed once per fresh panel worker; exact identical transformed state targets memoized by numerical fingerprint within panel only; conditioning/transform/hash still charged. Same policy both arms; no cross-worker cache.",
        "resources": {"panel_wall_seconds": 20, "rss_bytes": 512*1024**2, "table_bytes": 16*1024**2,
            "max_states": 20_000_000, "source_load_seconds": 5, "closeout_reserve_seconds": .5,
            "campaign_seconds": 300, "threads": 1, "concurrency": 1},
        "preparation_resources": {"total_seconds": 900, "audit_row_seconds": 30, "panel_prepare_seconds": 120,
            "reference_outer_seconds": 310, "target_verify_seconds":60, "rss_bytes": 512*1024**2},
        "reference_policy": {"semantics": "stored_binary64_log primary; source_binary64 and source_decimal_lexeme conversion diagnostics",
            "precisions": [90,120], "max_assignments": 1_000_000, "state_seconds": 60, "total_seconds": 300,
            "rss_mib": 512, "precision_log_agreement": 1e-10, "failed_references": "Retain all, never replace panel or upgrade method agreement."},
        "accuracy": {"log_z_absolute": 1e-8, "log_k_absolute": 3e-8, "exact_zero_required": True,
            "rank_score_envelope":3.03e-8,"reference_numeric_allowance_per_log":1e-10,
            "undefined_denominator": "Never rank; preserve explicit score status, including0/0.",
            "top_k": [1,3,5], "ranking": "Reference/observed envelopes, uncertain boundaries explicit; incomplete coverage blocks full-panel top-k claim.",
            "certificate": "Numerical acceptance, not directed interval certification."},
        "phase_scopes": "Fresh-worker startup/source ZIP parse, per-query conditioning and arm transformations, target verification, all inference or explicitly traced cache reuse, ratio and progress/result writes plus reaping under common outerwatchdog. Reference generation separate. Controller hash/reference validation recorded separately inside campaign total. Query RSS is cumulative worker high-water, not per-query allocation. Pollsleep0.01 requested, not achievedcadence guarantee.",
        "comparator_policy": "No compatible drop-in BBK*/AOBB executable found in bounded official source audit; preserve availability gap, no claim of comparison to those engines."}
    plan = {"campaign": "004", "phase": "preparation", "frozen_at_utc": now(), "root": str(ROOT),
        "grader_freeze": artifact(ROOT / "grader/campaign-004/FREEZE.json"), "source_manifest": artifact(ROOT / "data/uai23_manifest.json"),
        "cases": [{"case_id": case["case_id"], "states": case["states"], "archive": artifact(ROOT / case["local_path"])} for case in original["cases"]],
        "pilot": pilot, "panels": panels, "slots": slots, "scientific_choices": science,
        "implementation_inventory": implementation_files(),
        "preflight_validation": artifact(OUT / "preflight-tests.txt"),
        "comparator_audit": artifact(ROOT / "data/campaign-004/comparator_audit/audit.json"),
        "exposure": "Adaptive after003; read-only source-grammar inspection (headers/.query/.sum/summary/conformer labels and selected UAI prefix) informed decoder implementation. No004 protein conditioning, partition inference or reference computation before this freeze. Formal14source audits run afterfreeze. Synthetic controls only beforefreeze.",
        "environment": {"python": sys.version, "platform": platform.platform(),
            "packages": {name:importlib.metadata.version(name) for name in ["numpy","psutil","pytest"]},
            "threads": THREADS, "cache_policy": "Fresh processes, no OS cache flush, no warmup inference."}}
    verify_plan(plan)
    path = OUT / "preparation_manifest.json"
    write(path, plan)
    (OUT / "preparation_manifest.sha256").write_text(artifact(path)["sha256"]+"  preparation_manifest.json\n")
    print(json.dumps({"preparation_manifest": artifact(path)["sha256"][:6], "sequences": len(pilot["sequences"]), "panels":12, "state_slots":len(slots)}), flush=True)


def stage_worker(action, value=None):
    from experiments.three_state_data import load_case, audit_case, condition_sequence
    from experiments.inference import load_model
    from experiments.round3_pipeline import prepare_model
    from experiments.structure import model_to_dict

    plan = read_preparation()
    started = time.perf_counter()
    if action == "audit":
        item = next(case for case in plan["cases"] if case["case_id"] == value)
        case = load_case(ROOT / item["archive"]["path"])
        assert case.archive_sha256 == item["archive"]["sha256"]
        audit = audit_case(case)
        states, proof = condition_sequence(case, {selector:0 for selector in case.selectors})
        baseline = []
        for old_state in item["states"]:
            assert artifact(ROOT/old_state["path"])["sha256"] == old_state["sha256"]
            old = load_model(ROOT / old_state["path"])
            name = old.metadata["state"]
            current = states[name]
            assert old.metadata["sequence"] == current.metadata["sequence"]
            assert old.metadata["source_domain_indices"] == current.metadata["source_domain_indices"]
            assert old.metadata["source_variable_ids"] == current.metadata["source_variable_ids"]
            assert old.domains == current.domains
            assert len(current.factors) == len(old.metadata["source_factor_indices"])
            assert current.metadata["source_factor_indices"] == old.metadata["source_factor_indices"]
            checked = 0
            for new_factor, old_factor in zip(current.factors, old.factors):
                assert new_factor.scope == old_factor.scope
                assert (new_factor.values == old_factor.values).all()
                checked += int(new_factor.values.size)
            extras = old.factors[len(current.factors):]
            assert len(extras) == 1 and extras[0].scope == () and float(extras[0].values) == 0.0
            baseline.append({"state":name,"checked_entries":checked,"old_model":artifact(ROOT / old_state["path"]),
                             "identity_scalar_zero_ignored":True})
        write(OUT / "audits" / (case.case_id+".json"), {"status":"pass", "audit":audit,
            "source_first_baseline_equivalence":baseline,
            "elapsed_seconds":time.perf_counter()-started, "worker_peak_rss_bytes":peak()})
    elif action == "verify-targets":
        from experiments.three_state_reference import load_archive, verify_conditioning

        source = load_archive(ROOT / plan["pilot"]["archive"]["path"])
        items = []
        for variant in plan["pilot"]["sequences"]:
            labels = {int(selector):source.summary["residue_aminoAcids"][selector][index]
                      for selector,index in variant["assignment"].items()}
            for state in STATES:
                path = OUT / "models" / f"{variant['sequence_id']}__original__{state}.json"
                result = verify_conditioning(source,labels,state,read(path))
                items.append({"sequence_id":variant["sequence_id"],"state":state,"verification":result,"model":artifact(path)})
        write(OUT / "independent_target_verification.json", {"results":items,"all_pass":all(item["verification"]["status"]=="pass" for item in items),
            "elapsed_seconds":time.perf_counter()-started,"worker_peak_rss_bytes":peak()})
        assert all(item["verification"]["status"]=="pass" for item in items)
    else:
        case = load_case(ROOT / plan["pilot"]["archive"]["path"])
        assert case.archive_sha256 == plan["pilot"]["archive"]["sha256"]
        targets, models = {}, []
        for variant in plan["pilot"]["sequences"]:
            sequence_id = variant["sequence_id"]
            states, proof = condition_sequence(case, {int(key):value for key,value in variant["assignment"].items()})
            targets[sequence_id] = {}
            for state, model in states.items():
                item = write(OUT / "models" / f"{sequence_id}__original__{state}.json", model_to_dict(model))
                models.append({"sequence_id":sequence_id,"state":state,"model":item})
            evidence = {"conditioning":proof,"arms":{}}
            for arm in ("simplified","propagated"):
                targets[sequence_id][arm] = {}
                evidence["arms"][arm] = {}
                for state, model in states.items():
                    prepared, preparation = prepare_model(model,arm)
                    item = write(OUT / "models" / f"{sequence_id}__{arm}__{state}.json", model_to_dict(prepared))
                    targets[sequence_id][arm][state] = preparation["target_sha256"]
                    evidence["arms"][arm][state] = {"model":item,"preparation":preparation,"states":str(prepared.n_states)}
            write(OUT / "proofs" / (sequence_id+".json"), evidence)
        write(OUT / "targets.json", {"targets":targets,"original_models":models,"elapsed_seconds":time.perf_counter()-started,"worker_peak_rss_bytes":peak()})


def supervise_stage(identity, command, seconds, deadline):
    from experiments.round2_watchdog import supervise

    plan = read_preparation()
    logs = OUT / "logs"
    env = {key:value for key,value in os.environ.items() if key in {"PATH","TMPDIR","LANG","LC_ALL","VIRTUAL_ENV"}}
    env.update(THREADS)
    if time.perf_counter()+seconds+.25 > deadline:
        monitor = None
        row = {"identity":identity,"command":command,"status":"preparation_budget_skip","recorded_at_utc":now(),
               "reason":"Remaining total preparation budget cannot accommodate the complete frozen stage timeout plus0.25s."}
    else:
        monitor = supervise(command,cwd=ROOT,env=env,stdout_path=logs/(identity+".stdout.txt"),stderr_path=logs/(identity+".stderr.txt"),
            rss_ceiling_bytes=plan["scientific_choices"]["preparation_resources"]["rss_bytes"],wall_timeout_seconds=seconds)
        row = {"identity":identity,"command":command,"monitor":monitor,"recorded_at_utc":now(),
            "status":"completed" if monitor["exit_code"]==0 and not monitor["termination_reason"] else "failed",
            "logs":[artifact(logs/(identity+".stdout.txt")),artifact(logs/(identity+".stderr.txt"))]}
        if row["status"] == "failed":
            row["reason"] = monitor["termination_reason"] or f"Stage exited with code {monitor['exit_code']}"
    with (OUT / "preparation.jsonl").open("a") as stream:
        stream.write(json.dumps(row,allow_nan=False)+"\n")
    return monitor is not None and monitor["exit_code"] == 0 and not monitor["termination_reason"]


def prepare_all():
    started = time.perf_counter()
    plan = read_preparation()
    verify_plan(plan)
    assert not (OUT / "preparation.jsonl").exists()
    deadline = started + plan["scientific_choices"]["preparation_resources"]["total_seconds"]
    resources = plan["scientific_choices"]["preparation_resources"]
    references = plan["scientific_choices"]["reference_policy"]
    okay = True
    for case in plan["cases"]:
        result = supervise_stage("audit-"+case["case_id"], [sys.executable,"scripts/campaign_round4.py","audit",case["case_id"]],resources["audit_row_seconds"],deadline)
        okay = result and okay
    command = [sys.executable,"-m","experiments.three_state_reference","--archive",plan["pilot"]["archive"]["path"],
        "--output",str(OUT/"references.json"),"--max-assignments",str(references["max_assignments"]),
        "--state-seconds",str(references["state_seconds"]),"--total-seconds",str(references["total_seconds"]),"--memory-mib",str(references["rss_mib"])]
    downstream = [("prepare-panel",[sys.executable,"scripts/campaign_round4.py","prepare-panel"],resources["panel_prepare_seconds"]),
                  ("independent-references",command,resources["reference_outer_seconds"]),
                  ("verify-targets",[sys.executable,"scripts/campaign_round4.py","verify-targets"],resources["target_verify_seconds"])]
    for identity,command,seconds in downstream:
        if okay:
            okay = supervise_stage(identity,command,seconds,deadline)
        else:
            with (OUT/"preparation.jsonl").open("a") as stream:
                stream.write(json.dumps({"identity":identity,"command":command,"status":"upstream_gate_blocked",
                    "reason":"A required earlier source/preparation/reference stage did not complete under its frozen policy.","recorded_at_utc":now()})+"\n")
    raw = read(OUT/"references.json") if (OUT/"references.json").exists() else None
    rows = {row["panel_index"]:row for row in raw["rows"]} if raw is not None else {}
    reference_slots = []
    for variant in plan["pilot"]["sequences"]:
        for state in STATES:
            entry = rows.get(variant["panel_index"],{}).get("states",{}).get(state)
            reference_slots.append({"sequence_id":variant["sequence_id"],"state":state,
                "status":entry["status"] if entry is not None else "not_completed",
                "reason":entry.get("reason") if entry is not None else "Reference process absent/failed or upstream gate blocked."})
    write(OUT/"reference_slot_status.json",reference_slots)
    write(OUT / "preparation_completion.json", {"elapsed_seconds":time.perf_counter()-started,"finished_at_utc":now(),"all_required_stages_completed":okay})
    if not okay:
        write(OUT/"gate_failure.json",{"gate":"source/preparation/reference","reason":"At least one required frozen stage did not complete; no measured panel launched."})
    return okay


def normalize_references(raw, pilot):
    result = {}
    assert raw["case_id"] == pilot["case_id"]
    assert raw["source_hashes"]["archive_sha256"] == pilot["archive"]["sha256"]
    by_index = {row["panel_index"]:row for row in raw["rows"]}
    assert len(by_index) == len(raw["rows"]) == len(pilot["sequences"])
    for variant in pilot["sequences"]:
        row = by_index[variant["panel_index"]]
        assert row["label"] == variant["label"] and row["selector"] == pilot["selector"]
        expected_sequence = {selector:pilot["amino_acid_templates"][selector][index] for selector,index in variant["assignment"].items()}
        assert row["sequence"] == expected_sequence
        assert set(row["states"]) == set(STATES)
        states = {state:entry["values"]["stored_binary64_log"]["logZ"] for state,entry in row["states"].items()
                  if entry["status"] == "reference-passing success"}
        result[variant["sequence_id"]] = {"states":states,"score":row["scores"]["stored_binary64_log"],"label":row["label"]}
    return result


def freeze_execution():
    plan = read_preparation()
    verify_plan(plan)
    raw_refs = read(OUT / "references.json")
    refs = normalize_references(raw_refs,plan["pilot"])
    targets = read(OUT / "targets.json")["targets"]
    verify_targets(targets,plan["pilot"])
    from experiments.inference import load_model
    from experiments.round3_pipeline import target_fingerprint
    for variant in plan["pilot"]["sequences"]:
        for arm in ("simplified","propagated"):
            for state in STATES:
                path = OUT/"models"/f"{variant['sequence_id']}__{arm}__{state}.json"
                assert target_fingerprint(load_model(path,allow_higher_arity=True)) == targets[variant["sequence_id"]][arm][state]
    manifest = deepcopy(plan)
    manifest.update({"phase":"measurement","frozen_at_utc":now(),"preparation_manifest":artifact(OUT/"preparation_manifest.json"),
        "references":refs,"reference_artifact":artifact(OUT/"references.json"),"targets":targets,
        "preparation_ledger":artifact(OUT/"preparation.jsonl")})
    assert manifest["scientific_choices"] == plan["scientific_choices"]
    assert manifest["panels"] == plan["panels"] and manifest["slots"] == plan["slots"]
    inventory = set(ROOT/item["path"] for item in plan["implementation_inventory"])
    for directory in [OUT,ROOT/"grader/campaign-004",ROOT/"data/campaign-004/comparator_audit"]:
        inventory.update(path for path in directory.rglob("*") if path.is_file())
    inventory.update(ROOT/case["archive"]["path"] for case in plan["cases"])
    inventory.update(ROOT/state["path"] for case in plan["cases"] for state in case["states"])
    inventory.add(ROOT/"data/uai23_manifest.json")
    manifest["file_inventory"] = [artifact(path) for path in sorted(inventory)]
    path = RUN / "manifest.json"
    write(path,manifest)
    (RUN/"manifest.sha256").write_text(artifact(path)["sha256"]+"  manifest.json\n")
    print(json.dumps({"execution_manifest":artifact(path)["sha256"][:6],"panels":12,"queries":12*len(plan["pilot"]["sequences"])}),flush=True)


def validate_query(query, refs, science):
    from experiments.three_state_rank.core import number

    expected = refs.get(query["sequence_id"],{})
    checks = {}
    for state in STATES:
        value = query["states"][state]
        if value["status"] != "complete":
            checks[state] = {"status":"not_complete"}
        elif state not in expected.get("states",{}):
            checks[state] = {"status":"unverified"}
        else:
            try:
                observed, reference = number(value["log_z"]),number(expected["states"][state])
            except (ValueError,TypeError,KeyError):
                checks[state] = {"status":"invalid_numeric_output"}
                continue
            if math.isfinite(observed) and math.isfinite(reference):
                with localcontext() as context:
                    context.prec = 140
                    error = float(abs(Decimal.from_float(observed)-Decimal(expected["states"][state])))
            else:
                error = 0. if observed==reference else math.inf
            checks[state] = {"status":"pass" if error<=science["accuracy"]["log_z_absolute"] else "wrong_answer", "absolute_log_error":None if math.isinf(error) else error}
    complete_correct = all(item["status"] == "pass" for item in checks.values())
    score = expected.get("score",{})
    observed = query["score"]
    valid_status = (score.get("status") == "finite" and observed["status"] == "finite") or (score.get("status") == "zero numerator" and observed["status"] == "zero_numerator")
    error = None
    if complete_correct and valid_status:
        try:
            x,y = number(observed["log_k"]),number(score["logKstar"])
        except (ValueError,TypeError,KeyError):
            return {"state_checks":checks,"status":"invalid_score_output","absolute_log_k_error":None}
        if math.isfinite(x) and math.isfinite(y):
            with localcontext() as context:
                context.prec = 140
                error = float(abs(Decimal.from_float(x)-Decimal(score["logKstar"])))
        else:
            error = 0. if x == y else math.inf
    status = "success" if error is not None and error<=science["accuracy"]["log_k_absolute"] else "not_ranked"
    if any(item["status"] == "wrong_answer" for item in checks.values()):
        status = "wrong_answer"
    if error is not None and error > science["accuracy"]["log_k_absolute"]:
        status = "wrong_answer"
    if complete_correct and score.get("status") == "undefined" and observed["status"] == "undefined_zero_denominator":
        status = "correct_undefined"
    return {"state_checks":checks,"status":status,"absolute_log_k_error":None if error is not None and not math.isfinite(error) else error}


def recover_queries(raw, progress, panel, pilot, stopped_status):
    supplied = raw["queries"] if raw is not None else progress
    ids = [row["sequence_id"] for row in supplied]
    expected = panel["query_order"]
    assert ids == expected[:len(ids)] and len(ids)==len(set(ids))
    if raw is not None:
        assert ids == expected
        assert supplied == progress
    by_id = {row["sequence_id"]:row for row in supplied}
    variants = {row["sequence_id"]:row for row in pilot["sequences"]}
    result = []
    for sequence_id in expected:
        if sequence_id in by_id:
            row = by_id[sequence_id]
            assert set(row["states"]) == set(STATES)
            assert row["label"] == variants[sequence_id]["label"]
            assert row["assignment"] == variants[sequence_id]["assignment"]
        else:
            row = {"sequence_id":sequence_id,"label":variants[sequence_id]["label"],"assignment":variants[sequence_id]["assignment"],
                   "states":{state:{"status":stopped_status,"reason":"No completed query journal entry before panel stop."} for state in STATES},
                   "score":{"status":"incomplete","log_k":None}}
        result.append(row)
    return result


def read_progress(path):
    rows = []
    lines = path.read_text().splitlines(keepends=True)
    for index,line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except ValueError:
            reason = "truncated_final_entry" if index==len(lines)-1 and not line.endswith("\n") else "malformed_journal_entry"
            return rows,reason
    return rows,None


def enforce_target_identity(query, validation, expected, known):
    wrong = False
    for state in STATES:
        entry = query["states"][state]
        if entry["status"] == "target_fingerprint_mismatch":
            wrong = True
        if entry["status"] != "complete":
            continue
        if entry.get("target_sha256") != expected[state]:
            validation["state_checks"][state] = {"status":"target_fingerprint_mismatch"}
            wrong = True
            continue
        if entry.get("cache_hit"):
            origin = entry.get("cache_origin",{})
            previous = known.get((origin.get("sequence_id"),origin.get("state")))
            if (previous is None or previous.get("status") != "complete" or previous.get("target_sha256") != entry["target_sha256"]
                    or previous.get("log_z") != entry.get("log_z") or entry.get("solver_call_seconds") != 0):
                validation["state_checks"][state] = {"status":"invalid_cache_origin"}
                wrong = True
                continue
        known[(query["sequence_id"],state)] = entry
    if wrong:
        validation["status"] = "wrong_target_or_cache"
        validation["absolute_log_k_error"] = None
    return validation


def run_all():
    from experiments.round2_watchdog import supervise
    from experiments.three_state_rank import ranking_check

    started = time.perf_counter()
    manifest_path = RUN/"manifest.json"
    assert artifact(manifest_path)["sha256"] == (RUN/"manifest.sha256").read_text().split()[0],"Execution manifest seal mismatch"
    manifest = read(manifest_path)
    for name in ("panels.jsonl","queries.jsonl","states.jsonl","completion.json"):
        if (RUN/name).exists():
            raise FileExistsError(RUN/name)
    for directory in ("raw","records"):
        if (RUN/directory).exists() and any((RUN/directory).iterdir()):
            raise FileExistsError(RUN/directory)
    verify_plan(manifest)
    for item in manifest["file_inventory"]:
        assert artifact(ROOT/item["path"]) == item,item["path"]
    science = manifest["scientific_choices"]
    env = {key:value for key,value in os.environ.items() if key in {"PATH","TMPDIR","LANG","LC_ALL","VIRTUAL_ENV"}}
    env.update(THREADS)
    premeasurement_validation_seconds = time.perf_counter()-started
    for panel in manifest["panels"]:
        panel_id = panel["panel_id"]
        output = RUN / "raw" / (panel_id+".json")
        stdout,stderr = Path(str(output)+".stdout.txt"),Path(str(output)+".stderr.txt")
        command = [sys.executable,"-m","experiments.three_state_rank",str(RUN/"manifest.json"),panel_id,str(output)]
        budget_skip = time.perf_counter()-started+science["resources"]["panel_wall_seconds"]+.25 > science["resources"]["campaign_seconds"]
        monitor = None if budget_skip else supervise(command,cwd=ROOT,env=env,stdout_path=stdout,stderr_path=stderr,
            rss_ceiling_bytes=science["resources"]["rss_bytes"],wall_timeout_seconds=science["resources"]["panel_wall_seconds"])
        controller_started = time.perf_counter()
        record = {"panel":panel,"command":command,"monitor":monitor,"artifacts":[] if budget_skip else [artifact(stdout),artifact(stderr)],
            "status":"campaign_budget_skip" if budget_skip else "error","query_results":[],"system_load_average_after":list(os.getloadavg())}
        raw = None
        if output.exists():
            record["artifacts"].append(artifact(output))
            try:
                raw = read(output)
            except ValueError as error:
                record["result_read_error"] = str(error)
        if raw is not None:
            try:
                assert raw["panel_id"] == panel_id
                assert raw["manifest_sha256"] == artifact(RUN/"manifest.json")["sha256"]
                assert [row["sequence_id"] for row in raw["queries"]] == panel["query_order"]
                assert isinstance(raw["worker_peak_rss_before_result"],int) and raw["worker_peak_rss_before_result"]>=0
                for key in ("method","arm","repeat"):
                    assert raw[key] == panel[key]
            except (AssertionError,KeyError,TypeError) as error:
                record["status"] = "invalid_output_identity"
                record["result_identity_error"] = type(error).__name__
                raw = None
        if raw is not None:
            timing_path = Path(str(output)+".timing.json")
            try:
                timing = read(timing_path) if timing_path.exists() else {}
            except ValueError as error:
                timing = {}
                record["timing_read_error"] = str(error)
            if not isinstance(timing,dict) or not isinstance(timing.get("worker_peak_rss_after_result",0),int) or timing.get("worker_peak_rss_after_result",0)<0:
                timing = {}
                record["timing_read_error"] = "Malformed result high-water timing sidecar"
            if timing:
                record["artifacts"].append(artifact(timing_path))
            record["timing_sidecar"] = timing
            record["whole_peak_rss_bytes"] = max(monitor["sampled_peak_rss_bytes"],raw["worker_peak_rss_before_result"],timing.get("worker_peak_rss_after_result",0))
            record["status"] = "complete" if not monitor["termination_reason"] and monitor["exit_code"]==0 else "failed"
            if not timing or raw["source_status"] != "loaded":
                record["status"] = "infrastructure_or_source_error"
            if record["whole_peak_rss_bytes"] > science["resources"]["rss_bytes"]:
                record["status"] = "rss_limit"
        elif monitor is not None and "result_identity_error" not in record:
            record["status"] = monitor["termination_reason"] or "worker_error"
            record["whole_peak_rss_bytes"] = monitor["sampled_peak_rss_bytes"]
        progress_path = Path(str(output)+".progress.jsonl")
        progress = []
        if progress_path.exists():
            record["artifacts"].append(artifact(progress_path))
            progress,progress_error = read_progress(progress_path)
            if progress_error:
                record["progress_read_error"] = progress_error
                if raw is not None:
                    record["status"] = "journal_error"
        if "result_identity_error" in record:
            progress = []
        try:
            queries = recover_queries(raw,progress,panel,manifest["pilot"],record["status"])
        except (AssertionError,KeyError,TypeError) as error:
            record["status"] = "journal_or_identity_error"
            record["journal_error"] = type(error).__name__
            queries = recover_queries(None,[],panel,manifest["pilot"],record["status"])
        observed = {}
        known = {}
        for query in queries:
            validation = validate_query(query,manifest["references"],science)
            validation = enforce_target_identity(query,validation,manifest["targets"][query["sequence_id"]][panel["arm"]],known)
            query_row = {"panel_id":panel_id,"case_id":manifest["pilot"]["case_id"],"method":panel["method"],"arm":panel["arm"],"repeat":panel["repeat"],
                         "sequence_id":query["sequence_id"],"validation":validation,"score":query["score"],"panel_status":record["status"]}
            record["query_results"].append(query_row)
            with (RUN/"queries.jsonl").open("a") as stream:
                stream.write(json.dumps(query_row,allow_nan=False)+"\n")
            for state in STATES:
                slot = next(item for item in manifest["slots"] if item["panel_id"]==panel_id and item["sequence_id"]==query["sequence_id"] and item["state"]==state)
                trial = dict(slot, raw=query["states"][state], validation=validation["state_checks"][state],panel_status=record["status"],
                             source_archive=manifest["pilot"]["archive"],reference_artifact=manifest["reference_artifact"],panel_evidence=record["artifacts"])
                with (RUN/"states.jsonl").open("a") as stream:
                    stream.write(json.dumps(trial,allow_nan=False)+"\n")
            if validation["status"] == "success":
                observed[query["sequence_id"]] = query["score"]["log_k"]
        eligible = {key:value["score"]["logKstar"] for key,value in manifest["references"].items()
                    if value["score"]["status"] in ("finite","zero numerator")}
        record["ranking"] = ranking_check(observed,eligible,science["accuracy"]["rank_score_envelope"])
        record["ranking"]["full_declared_panel"] = record["ranking"]["full_panel"] and len(eligible)==len(manifest["pilot"]["sequences"]) and record["status"]=="complete"
        record["ranking"]["top_k_scope"] = "full declared panel" if record["ranking"]["full_declared_panel"] else "defined reference-covered subset only; no full-panel claim"
        record["accepted_scores_under_panel_policy"] = len(observed) if record["status"] == "complete" else 0
        record["controller_seconds"] = time.perf_counter()-controller_started
        write(RUN/"records"/(panel_id+".json"),record)
        with (RUN/"panels.jsonl").open("a") as stream:
            stream.write(json.dumps(record,allow_nan=False)+"\n")
        print(json.dumps({"panel":panel_id,"method":panel["method"],"arm":panel["arm"],"status":record["status"],"correct_scores":sum(row["validation"]["status"]=="success" for row in record["query_results"]),"elapsed_seconds":time.perf_counter()-started}),flush=True)
    write(RUN/"completion.json",{"finished_at_utc":now(),"elapsed_seconds":time.perf_counter()-started,
        "premeasurement_validation_seconds":premeasurement_validation_seconds})


def summarize():
    assert artifact(RUN/"manifest.json")["sha256"] == (RUN/"manifest.sha256").read_text().split()[0]
    manifest = read(RUN/"manifest.json")
    rows = [json.loads(line) for line in (RUN/"panels.jsonl").read_text().splitlines()]
    assert len(rows)==len({row["panel"]["panel_id"] for row in rows})==12
    assert [row["panel"] for row in rows] == manifest["panels"]
    queries = [json.loads(line) for line in (RUN/"queries.jsonl").read_text().splitlines()]
    states = [json.loads(line) for line in (RUN/"states.jsonl").read_text().splitlines()]
    assert len(queries)==len({(row["panel_id"],row["sequence_id"]) for row in queries})==12*len(manifest["pilot"]["sequences"])
    assert [(row["panel_id"],row["sequence_id"]) for row in queries] == [(panel["panel_id"],sequence_id) for panel in manifest["panels"] for sequence_id in panel["query_order"]]
    assert queries == [query for row in rows for query in row["query_results"]]
    assert len(states)==len({row["slot_id"] for row in states})==len(manifest["slots"])
    assert [{key:row[key] for key in slot} for slot,row in zip(manifest["slots"],states)] == manifest["slots"]
    summary = {"panels":12,"planned_queries":sum(len(panel["query_order"]) for panel in manifest["panels"]),
        "planned_state_slots":len(manifest["slots"]),"correct_scores":sum(item["validation"]["status"]=="success" for row in rows for item in row["query_results"]),
        "correct_undefined":sum(item["validation"]["status"]=="correct_undefined" for row in rows for item in row["query_results"]),
        "scores_under_panel_policy":sum(row["accepted_scores_under_panel_policy"] for row in rows),
        "panel_statuses":[row["status"] for row in rows],"controller_seconds":sum(row["controller_seconds"] for row in rows),
        "all_source_audits":14,"biological_accuracy_tested":False,"domain_comparator_executed":False}
    write(RUN/"summary.json",summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "audit":
        stage_worker("audit",sys.argv[2])
    elif action == "prepare-panel":
        stage_worker("prepare-panel")
    elif action == "verify-targets":
        stage_worker("verify-targets")
    else:
        raise ValueError(action)
