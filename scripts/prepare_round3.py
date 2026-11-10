"""Freeze prospective preparation, then preserve every static support transform."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import importlib.metadata
import itertools
import json
import math
from pathlib import Path
import platform
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "prepared/campaign-003"


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def artifact(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return artifact(path)


def controls():
    equal = [[0.0, None], [None, 0.0]]
    unequal = [[None, 0.0], [0.0, None]]
    definitions = [
        ("cascade", [2]*12, [{"scope": [0], "log_values": [0, None]}] +
         [{"scope": [i, i+1], "log_values": equal} for i in range(11)], 7.0,
         "Unary hard zero propagates through an equality chain; one surviving assignment."),
        ("local-zero", [2]*6, [{"scope": [0], "log_values": [0, None]},
         {"scope": [5], "log_values": [None, 0]}] +
         [{"scope": [i, i+1], "log_values": equal} for i in range(5)], 0.0,
         "Conflicting endpoint unary constraints cause a proven domain wipeout."),
        ("global-zero", [2]*3, [{"scope": list(edge), "log_values": unequal}
         for edge in [(0,1), (1,2), (2,0)]], 0.0,
         "Odd not-equal cycle is locally arc consistent but globally zero."),
        ("finite-tail", [2]*8, [{"scope": [i], "log_values": [0, -1000]}
         for i in range(8)], 0.0,
         "All finite weights must remain; exp underflow is not a hard-zero permission."),
        ("multiplicity", [5,3,2], [{"scope": [0], "log_values": [None,0,None,0,None]}], 1000.0,
         "Retained nonconsecutive states and isolated-domain multiplicities: twelve equal terms."),
        ("duplicate-zero", [2,2], [{"scope": [0,1], "log_values": equal},
         {"scope": [1,0], "log_values": unequal}], 0.0,
         "Aligned duplicate scopes have disjoint joint support despite separately supported axes."),
    ]
    return [{"schema_version": 1, "model_id": "control003-"+name, "kind": "synthetic_control",
             "domains": domains, "factors": factors, "constant_log_weight": offset,
             "metadata": {"mechanism": mechanism, "generator": "scripts/prepare_round3.py/controls-v1",
                          "seed": 2026110603, "interpretation": "Synthetic mechanism/correctness control; not a protein."}}
            for name, domains, factors, offset, mechanism in definitions]


def control_reference(data):
    with localcontext() as context:
        context.prec = 90
        weights = []
        for state in itertools.product(*(range(q) for q in data["domains"])):
            value = Decimal.from_float(float(data["constant_log_weight"]))
            for factor in data["factors"]:
                entry = factor["log_values"]
                for variable in factor["scope"]:
                    entry = entry[state[variable]]
                if entry is None:
                    value = None
                    break
                value += Decimal.from_float(float(entry))
            if value is not None:
                weights.append(value)
        if weights:
            maximum = max(weights)
            log_z = str(maximum + sum((value-maximum).exp() for value in weights).ln())
        else:
            log_z = "-inf"
    return {"reference_id": "direct-decimal90/"+data["model_id"], "log_z": log_z,
            "reference_uncertainty": 1e-70 if weights else 0.0,
            "kind": "Independent direct enumeration of explicit synthetic log weights, Decimal90; not interval certified.",
            "positive_support_assignments": len(weights), "precision_digits": 90}


def setup_controls():
    references = deepcopy(read(ROOT / "prepared/campaign-002/catalog.json")["references"])
    audit = read(ROOT / "grader/campaign-002/independent_numeric_audit.json")
    fyn = next(item for item in audit["real"] if item["model_id"].startswith("1FYN__"))
    references[fyn["model_id"]] = {"reference_id": "prior-independent-decimal90/1FYN",
        "log_z": fyn["log_z"], "reference_uncertainty": 1e-70,
        "kind": "Known independent campaign002 posthoc reference, prospectively fixed for003.",
        "provenance": artifact(ROOT / "grader/campaign-002/independent_numeric_audit.json")}
    items = []
    for data in controls():
        path = OUT / "controls" / (data["model_id"] + ".json")
        if path.exists():
            assert read(path) == data
        else:
            write(path, data)
        references[data["model_id"]] = control_reference(data)
        items.append(artifact(path))
    path = OUT / "references.json"
    if path.exists():
        assert read(path) == references
    else:
        write(path, references)
    return items


def implementation_files():
    paths = []
    for directory in ["experiments/inference", "experiments/structure", "experiments/zero_support",
                      "experiments/round3_pipeline", "experiments/established_v2", "experiments/round2_watchdog"]:
        paths.extend(path for path in (ROOT / directory).rglob("*")
                     if path.is_file() and path.suffix in {".py", ".md"} and "__pycache__" not in path.parts)
    paths.extend(ROOT / name for name in ["scripts/prepare_round2.py", "scripts/prepare_round3.py",
        "scripts/campaign_round2_v2.py", "scripts/campaign_round3.py", "scripts/execute_round3.py",
        "tests/test_zero_support_round3.py", "tests/test_round3_pipeline.py", "tests/test_prepare_round3.py", "tests/test_driver_round3.py",
        "experiments/established/pyproject.toml", "experiments/established/uv.lock", "pyproject.toml", "uv.lock"])
    return [artifact(path) for path in sorted(set(paths))]


def freeze_preparation():
    from scripts.campaign_round3 import plan_trials
    from scripts.campaign_round2_v2 import resource_profiles

    prior = read(ROOT / "runs/campaign-002/manifest.json")
    models = []
    for model in prior["models"]:
        if model["cohort"] != "published_protein_extension":
            continue
        entry = deepcopy(model)
        original = next(rep for rep in model["representations"] if rep["representation_id"] == "original")
        entry["pipeline_input"] = original["files"][0]
        entry["representations"] = [{"representation_id": arm, "resource_profiles": ["low", "high"]}
                                    for arm in ["simplified", "propagated"]]
        models.append(entry)
    for data in controls():
        models.append({"model_id": data["model_id"], "cohort": "synthetic_measured", "source_id": "synthetic003",
            "pipeline_input": artifact(OUT / "controls" / (data["model_id"] + ".json")),
            "fixed_sequence_and_conditioning": "Explicit synthetic factors; no biological sequence.",
            "source_semantics": "Explicit natural-log factors; only null is a hard zero; constant offset retained.",
            "conversion_checks": artifact(OUT / "controls" / (data["model_id"] + ".json")),
            "preparation_status": "Prospectively included; static transformation has not run.",
            "representations": [{"representation_id": arm, "resource_profiles": ["high"]}
                                for arm in ["simplified", "propagated"]]})
    planned = plan_trials(models)
    assert len(planned) == 324
    manifest = {"campaign": "003", "phase": "preparation", "frozen_at_utc": now(),
        "grader_freeze": artifact(ROOT / "grader/campaign-003/FREEZE.json"),
        "grader_amendment": artifact(ROOT / "grader/campaign-003/AMENDMENT-001.json"),
        "models": models, "planned_trials": planned,
        "references": read(OUT / "references.json"), "reference_artifact": artifact(OUT / "references.json"),
        "accuracy_contracts": prior["accuracy_contracts"],
        "resource_profiles": resource_profiles(artifact(ROOT / "experiments/round2_watchdog/control/result.json")),
        "total_wall_budget_seconds": 900, "preprocessing_limit_seconds": 3,
        "static_preparation": {"row_wall_seconds": 20, "rss_ceiling_bytes": 512*1024**2,
            "total_wall_seconds": 180, "enforcement": "Same external10ms process-tree watchdog; worker lifetime high-water also checked; no instantaneous ceiling guarantee."},
        "implementation_inventory": implementation_files(),
        "algorithms": {"propagation": "Deterministic generalized arc consistency on AND-merged identical-scope hard-zero masks; finite numeric factors never merged/pruned.",
            "algebra": "Immutable exact binary-rational singleton/constant/separable simplifier, same for both arms.",
            "methods": ["ve", "batch", "pyagrum"], "pyagrum_adapter_version": 2,
            "native_memory_mebibytes": 1024, "max_enumerated_states": 20_000_000,
            "state_guard": "Inside cold worker after preparation; no pre-preparation static row skips."},
        "environment": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
            "dependencies": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions() if d.metadata.get("Name")},
            "threads": 1, "concurrency": 1, "seed": 2026110603,
            "cache_policy": "Three fresh-process repeats, no warmup inference and no OS cache flush. Static preparation necessarily touches original inputs. Adjacent randomized arm pairs; repeated rounds separated."},
        "controls": {"measured": [artifact(OUT / "controls" / (data["model_id"]+".json")) for data in controls()],
            "correctness": [artifact(ROOT / "tests/test_zero_support_round3.py"), artifact(ROOT / "tests/test_round3_pipeline.py")],
            "reference_procedure": "Separate direct Decimal90 enumeration of original explicit synthetic factors. Fresh grader will independently check."},
        "preflight_validation": artifact(OUT / "preflight-tests.txt"),
        "clocks": "Cold original-load/propagation/algebra/fingerprint/method wall+CPU; final result JSON encoding/write sidecar wall+CPU. Method CPU aggregates immutable ordering/conversion internals; legacy wall phases retained. External watchdog clocks complete subprocess including startup/output/monitoring.",
        "source_inventory": deepcopy(prior["source_inventory"]),
        "preparation_command": "python scripts/prepare_round3.py prepare-one MODEL_ID ARM",
        "ledger": "prepared/campaign-003/preparation.jsonl; append-only one row per static attempt, with monitor/exit/status/output artifacts; failed and partial artifacts retained.",
        "final_binding_outputs": ["derived numerical model artifacts/hashes", "support/algebra/domain-map proofs", "structure/domain/table counts", "static attempt statuses and logs"],
        "exposure_ledger": [{"event": "prior002", "exposure": "All002outcomes, severe timingdrift, known1FYNsupport/oracle, adapterunitfix.",
                             "effect_on_selection": "Allsixretained; pairedcoldpipelinefollowup; no003proteinprep beforethisfreeze."},
                            {"event": "synthetic_preflight", "exposure": "Synthetic implementation controls and fixed-reference generation only.", "effect_on_selection": "Sixmechanismcontrols declaredbygenerator; no protein inference pilot."}],
        "attestation": "No campaign003 protein loading/preparation/inference has run before this preparation freeze; only immutable old metadata and synthetic controls/tests were inspected. All12 logical models and324rows retained regardless of pruning.",
        "amendment_rule": "Preserve every frozen file and failed attempt; numbered disclosed amendment before code/target/reference/budget/schedule change."}
    path = OUT / "preparation_manifest.json"
    write(path, manifest)
    with (OUT / "preparation_manifest.sha256").open("x") as stream:
        stream.write(artifact(path)["sha256"] + "  preparation_manifest.json\n")
    print(json.dumps({"preparation_manifest": str(path.relative_to(ROOT)), "sha256_prefix": artifact(path)["sha256"][:6], "planned_rows": len(planned)}), flush=True)


def prepare_one(model_id, arm):
    from experiments.inference import load_model
    from experiments.round3_pipeline import prepare_model
    from experiments.structure import model_to_dict
    from scripts.prepare_round2 import structure

    plan = read(OUT / "preparation_manifest.json")
    model = next(item for item in plan["models"] if item["model_id"] == model_id)
    started = time.perf_counter()
    original = load_model(ROOT / model["pipeline_input"]["path"], allow_higher_arity=True)
    prepared, pipeline = prepare_model(original, arm)
    derived = write(OUT / "models" / (model_id+"__"+arm+".json"), model_to_dict(prepared))
    summary = structure(prepared)
    summary["workspace_scope"] = "Two largest arrays plus inputs heuristic; not a live-array upper bound or RSS prediction."
    proof = write(OUT / "proofs" / (model_id+"__"+arm+".json"), {
        "model_id": model_id, "arm": arm, "original": model["pipeline_input"], "derived": derived,
        "pipeline": pipeline, "input_domains": list(original.domains), "output_domains": list(prepared.domains),
        "proof_scope": "Only explicit negative infinity permits domain deletion. Retained factor entries copied; subsequent algebra is exact over stored binary rationals. Surviving Cartesian size is not positive-support enumeration."})
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = {"created_at_utc": now(), "model_id": model_id, "arm": arm, "status": "prepared",
        "derived": derived, "proof": proof, "target_sha256": pipeline["target_sha256"], "structure": summary,
        "preparation_seconds": time.perf_counter()-started,
        "process_peak_rss_bytes": int(rss if sys.platform == "darwin" else rss*1024)}
    write(OUT / "static_raw" / (model_id+"__"+arm+".json"), result)


def prepare_all():
    from experiments.round2_watchdog import supervise
    from scripts.campaign_round3 import THREAD_ENV

    plan = read(OUT / "preparation_manifest.json")
    for item in plan["implementation_inventory"]:
        assert artifact(ROOT / item["path"])["sha256"] == item["sha256"], item["path"]
    ledger = OUT / "preparation.jsonl"
    if ledger.exists():
        raise FileExistsError(ledger)
    started = time.perf_counter()
    models = []
    env = {key: value for key, value in __import__("os").environ.items() if key in {"PATH","TMPDIR","LANG","LC_ALL","VIRTUAL_ENV"}}
    env.update(THREAD_ENV)
    for original in plan["models"]:
        model = deepcopy(original)
        for rep in model["representations"]:
            model_id, arm = model["model_id"], rep["representation_id"]
            output = OUT / "static_raw" / (model_id+"__"+arm+".json")
            stdout = OUT / "static_logs" / (model_id+"__"+arm+".stdout.txt")
            stderr = OUT / "static_logs" / (model_id+"__"+arm+".stderr.txt")
            command = [sys.executable, "scripts/prepare_round3.py", "prepare-one", model_id, arm]
            if time.perf_counter()-started > plan["static_preparation"]["total_wall_seconds"]-20:
                observation = {"status": "total_preparation_budget_skip", "command": command}
            else:
                monitor = supervise(command, cwd=ROOT, env=env, stdout_path=stdout, stderr_path=stderr,
                    rss_ceiling_bytes=plan["static_preparation"]["rss_ceiling_bytes"], wall_timeout_seconds=20)
                observation = {"status": "failed", "command": command, "monitor": monitor,
                               "logs": [artifact(stdout), artifact(stderr)]}
                if monitor["exit_code"] == 0 and not monitor["termination_reason"] and output.exists():
                    result = read(output)
                    if result["process_peak_rss_bytes"] <= plan["static_preparation"]["rss_ceiling_bytes"]:
                        observation.update({"status": "prepared", "result": artifact(output)})
                        rep.update({"files": [result["derived"]], "target_sha256": result["target_sha256"],
                            "structure": result["structure"], "evidence": [result["proof"], artifact(output)],
                            "simplification": "same exact algebra in both arms; only propagated arm restricts hard-zero support first",
                            "target_relation": "Same original stored-log partition sum with explicit exact domain mapping; no finite weight discarded.",
                            "preparation_seconds": result["preparation_seconds"]})
            observation.update({"model_id": model_id, "representation_id": arm, "recorded_at_utc": now()})
            with ledger.open("a") as stream:
                stream.write(json.dumps(observation, allow_nan=False) + "\n")
            if observation["status"] != "prepared":
                raise RuntimeError("Static preparation failure preserved; amendment required before any correction: "+model_id+"/"+arm)
        model["preparation_status"] = "Both declared arms prepared; no partition inference performed."
        models.append(model)
    catalog = {"schema_version": 1, "prepared_at": now(), "models": models, "references": plan["references"],
        "preparation_manifest": artifact(OUT / "preparation_manifest.json"), "preparation_ledger": artifact(ledger),
        "source_inventory": plan["source_inventory"] + [{"source_id": "campaign003-controls-and-contracts",
            "provenance": "Explicit synthetic mechanisms, known prior reference, independent grader freeze/amendment, and immutable preparation plan.",
            "files": [artifact(OUT / "references.json"), artifact(OUT / "preparation_manifest.json"),
                      artifact(ROOT / "grader/campaign-003/AMENDMENT-001.json")] + plan["controls"]["measured"]}],
        "selection_rule": {"published": "All six unchanged002CPDtargets; no outcome selection.", "controls": "All six explicit predeclared mechanisms; high profile only."},
        "exposure_ledger": plan["exposure_ledger"],
        "reference_subset_rule": "Known002references retained; priorindependent1FYNnowprospective; sixsyntheticDecimal90refs. No oracle for otherfiveproteins."}
    write(OUT / "catalog.json", catalog)
    print(json.dumps({"catalog": "prepared/campaign-003/catalog.json", "models": len(models), "static_rows": len(models)*2}), flush=True)


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "setup":
        setup_controls()
    elif action == "freeze-preparation":
        freeze_preparation()
    elif action == "prepare":
        prepare_all()
    elif action == "prepare-one":
        prepare_one(sys.argv[2], sys.argv[3])
    else:
        raise ValueError(action)
