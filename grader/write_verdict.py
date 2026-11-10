"""Assemble the independent verdict from grader-owned recomputations."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "grader"


def load(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def evidence(path, locator, observation):
    return {"path_or_url": path, "locator": locator, "sha256": sha(path), "observation": observation}


def finding(id_, kind, statement, evidence_, uncertainty, scope):
    return {"id": id_, "kind": kind, "statement": statement, "evidence": evidence_, "uncertainty": uncertainty, "scope": scope}


def claim(id_, category, statement, conclusion, scope, criteria, ids, limitations, data_class="published_computational_model", **extra):
    return {"claim_id": id_, "category": category, "statement": statement, "data_class": data_class, "conclusion": conclusion, "scope": scope, "criterion_ids": criteria, "evidence_ids": ids, "limitations": limitations, **extra}


def main():
    audit = load("grader/audit_results.json")
    spot = load("grader/spotcheck_results.json")
    bundle = load("runs/review-001/bundle_manifest.json")
    trials = [json.loads(x) for x in (ROOT / "runs/campaign-001/trials.jsonl").read_text().splitlines()]
    cohort = load("data/uai23_manifest.json")
    summary = load("runs/campaign-001/summary.json")
    tree = load("data/uai23_tree.json")
    selection = load("data/uai23_selection.json")
    expected = {x["path"] for x in tree["tree"] if x["path"].startswith("Expanded_3_") and x["path"].endswith(".zip")}
    for n in [4, 5]:
        candidates = [x for x in tree["tree"] if x["path"].startswith(f"Expanded_{n}_") and x["path"].endswith(".zip")]
        expected.add(min(candidates, key=lambda x: (x["size"], x["path"]))["path"])
    assert expected == {x["path"] for x in selection["selected"]} and not tree["truncated"]
    reps = [r for r in trials if r["method"] == "eliminate" and r["repeat"] == 0]
    refs = {r["model_id"]: r["result"]["log_z"] for r in reps}
    bounds = [r for r in trials if r["method"] == "bounded"]
    strict_misses = [r["trial_id"] for r in bounds if not r["result"]["log_z_lower"] <= refs[r["model_id"]] <= r["result"]["log_z_upper"]]
    assert len(strict_misses) == 30
    score_errors = []
    reported_scores = {x["case_id"]: x["modeled_log_kstar"] for x in summary["affinities"]}
    raw_refs = {x["model_id"]: x["raw_longdouble_log_z"] for x in audit["source_conversion"]}
    for case in cohort["cases"]:
        c, p, l = [raw_refs[s["model_id"]] for s in case["states"]]
        score_errors.append({"case_id": case["case_id"], "raw_recomputed_log_kstar": c - p - l, "difference": reported_scores[case["case_id"]] - (c - p - l)})
    exact_max = max(abs(x["difference"]) for x in audit["independent_exact_checks"])
    converted_misses = [x for x in spot["trial_comparisons"] if x.get("strict_contains_converted_80digit_reference") is False]
    structural = {
        "models": len(reps),
        "variable_range": [min(r["result"]["variables"] for r in reps), max(r["result"]["variables"] for r in reps)],
        "represented_induced_width_n_minus_one": sum(r["result"]["metrics"]["induced_width"] == r["result"]["variables"] - 1 for r in reps),
        "peak_table_equals_full_joint_grid": sum(r["result"]["metrics"]["peak_table_bytes"] == 8 * int(r["result"]["state_count"]) for r in reps),
        "configuration_range": [min(int(r["result"]["state_count"]) for r in reps), max(int(r["result"]["state_count"]) for r in reps)],
        "scope": "Represented factor scopes and tested elimination only; no proof of intrinsic interaction complexity or absence of constant/separable tables."
    }
    times = audit["timing_medians"]
    numerical = {
        "all_exact_trial_checks": len(audit["independent_exact_checks"]),
        "maximum_raw_reference_log_difference": exact_max,
        "strict_bound_misses_against_chosen_ve_reference": strict_misses,
        "tolerance_relaxed_bound_checks_passed": sum(x["within_tolerance_contains"] for x in audit["independent_bound_checks"]),
        "high_precision_models": len(spot["decimal_checks"]),
        "high_precision_configurations": sum(x["states"] for x in spot["decimal_checks"]),
        "high_precision_converted_model_bound_misses": len(converted_misses),
        "high_precision_bound_checks": sum(x["method"] == "bounded" for x in spot["trial_comparisons"]),
        "maximum_high_precision_converted_endpoint_miss": max(max(float(x["signed_converted_lower_error"]), -float(x["signed_converted_upper_error"]), 0) for x in spot["trial_comparisons"] if x["method"] == "bounded"),
        "maximum_high_precision_source_to_log_model_delta": max(abs(float(x["conversion_delta_log_z"])) for x in spot["decimal_checks"]),
        "modeled_affinity_recomputations": score_errors,
        "arithmetic_note": "First independent enumeration uses float64 on this platform (longdouble mantissa 52); separate Decimal computations use 80 digits. Neither is an outward-rounded certificate."
    }
    performance = {
        "median_of_model_batch_over_eliminate_kernel_ratios": statistics.median(x["batch_over_eliminate_kernel"] for x in audit["timing_ratios"]),
        "batch_faster_kernel_model_count": sum(x["batch_over_eliminate_kernel"] < 1 for x in audit["timing_ratios"]),
        "eliminate_faster_kernel_model_count": sum(x["batch_over_eliminate_kernel"] > 1 for x in audit["timing_ratios"]),
        "maximum_model_kernel_ratio": max(x["batch_over_eliminate_kernel"] for x in audit["timing_ratios"]),
        "median_of_model_wall_ratios": statistics.median(x["batch_over_eliminate_wall"] for x in audit["timing_ratios"]),
        "maximum_model_wall_ratio": max(x["batch_over_eliminate_wall"] for x in audit["timing_ratios"]),
        "maximum_model_median_kernel_seconds": {m: max(x["kernel"] for x in by_model.values()) for m, by_model in times.items()},
        "maximum_process_rss_bytes": {m: max(r["result"]["process_peak_rss_bytes"] for r in trials if r["method"] == m) for m in ["eliminate", "batch", "bounded"]},
        "loadavg_1minute_range": [min(r["system_loadavg_at_start"][0] for r in trials), max(r["system_loadavg_at_start"][0] for r in trials)],
        "scope": "Aggregation of original frozen timing records only; clocks were not independently rerun."
    }
    (OUT / "summary_checks.json").write_text(json.dumps({"structural": structural, "numerical": numerical, "performance": performance, "selection_matches_frozen_tree": True}, indent=2) + "\n")
    findings = [
        finding("F0", "artifact", "The frozen bundle is intact and the prospective source/input snapshots match; all 410 planned trials are present with no driver failures.", [evidence("grader/audit_results.json", "/bundle_files_verified and /trial_statuses", "1,342 files, 60,496,583 bytes; 284 complete exact trials, 108 epsilon-reached and 18 exact bounded trials."), evidence("grader/spotcheck_results.json", "/manifest_source_snapshot_checks", "Campaign source snapshot and campaign/schedule manifest digests match.")], "Local recorded timestamps and hashes establish an auditable chain, not cryptographic proof of when code was first executed.", "This frozen bundle only."),
        finding("F1", "artifact", "The 14-case/42-state source-first artifact is validated against its published UAI representation, including all 35,459 converted entries, zeros, allowed domains, state separation, and complete factor coverage.", [evidence("grader/audit_results.json", "/source_conversion", "Every stored table entry equals log(float(source weight)), or null for source zero; full original factor coverage and state-variable coverage pass."), evidence("grader/summary_checks.json", "/selection_matches_frozen_tree", "Selection reproduces the declared rule from the untruncated frozen repository tree."), evidence("grader/spotcheck_results.json", "/nonzero_literal_to_float_zero", "No positive source token became zero during binary64 parsing.")], "Discrete source approximations/zeros remain. Tiny rounding from logs is measured on the spot-check subset; source energy generation was not reconstructed.", "14 source-first fixed-sequence cases from 9 PDB IDs; not a validated sequence-design benchmark or measured-affinity benchmark."),
        finding("F2", "positive", "All 284 exact trial values agree with a separate raw-factor product/sum enumeration within the prospective tolerance; 80-digit spot checks on 20 state models corroborate the numerical scale.", [evidence("grader/audit_results.json", "/independent_exact_checks", f"Maximum log difference {exact_max:.3g}; every trial passes."), evidence("grader/spotcheck_results.json", "/decimal_checks and /trial_comparisons", "30,284 configurations independently enumerated with Decimal at 80 digits; raw weights and converted log models evaluated separately."), evidence("grader/summary_checks.json", "/numerical/modeled_affinity_recomputations", "All 14 modeled log K-star identities recompute within tolerance.")], "Finite floating/Decimal checks are not interval proofs. The first raw enumeration used float64 despite the platform's longdouble type name.", "Partition sums and scores in these fixed discrete models."),
        finding("F3", "failure", "Literal strict containment is false: 30/126 stored intervals miss the chosen VE reference by rounding-scale amounts. All 126 pass the prospective tolerance-relaxed check.", [evidence("grader/summary_checks.json", "/numerical", "30 misses against chosen VE reference; 126 tolerance-relaxed passes."), evidence("grader/spotcheck_results.json", "/trial_comparisons", "42/60 subset intervals also miss the 80-digit converted-model reference; maximum endpoint miss about 1.36e-14 log units.")], "The error is numerically tiny relative to the declared 1e-8-plus-relative tolerance, but logically rules out rigorous enclosures. Unrounded combinatorial reasoning is distinct from float64 certification.", "Correct the original claim to tolerance-relaxed containment; retain frozen outputs."),
        finding("F4", "limitation", "This cohort is easy for the tested conventional implementations and does not test sparse-graph benefits: all 42 represented elimination scopes have induced width n-1 and form a full joint table.", [evidence("grader/summary_checks.json", "/structural and /performance", "1-8 variables; 10-10,054,800 configurations; full-joint peak tables in all 42. Maximum model median VE kernel 0.098 s and batch kernel 1.003 s."), evidence("grader/audit_results.json", "/timing_ratios", "VE faster on 22/42 kernel medians, batch faster on 20/42; median batch/VE kernel ratio 1.04, largest 12.47; median wall ratio 1.01.")], "Three original timing repeats, shared workstation load, no independent clock rerun. States are nested in cases/PDBs; these ratios are descriptive, not population effects. Constant/separable table simplification was not tested.", "Observed implementation/memory tradeoff against named batch enumeration. Largest VE RSS 122 MB versus batch at most 46 MB; no general solver superiority or graph-theoretic lower bound."),
        finding("F5", "negative", "The literal Section 4 schedule fails its four necessary gates at every fixed illustrative N; first joint passing lambda is 10,909,384,704 for beta=1.", [evidence("grader/audit_results.json", "/schedule and /first_r_gate_lambda", "Independent square-root-block enumeration across ceil-log intervals matches beta 1/2/3 first lambdas 10,909,384,704; 17,045,913,600; 26,011,238,400. r>=2 first occurs at lambda 521,284."), evidence("grader/spotcheck_results.json", "/eth_parameter_source_excerpt", "The archived TeX lemma matches the stated parameter transcription.")], "Checks concern four necessary gates only, for the literal schedule. No enormous N, construction, SAT counter, or runtime crossover was computed.", "ETH-specific feasibility analysis; not an implementation, proof validation, or exclusion of optimized parameters/other manuscript routines. Minimum integer N for beta=1 is 2**10909384703+1."),
        finding("F6", "artifact", "All 63 experimental affinity labels independently match the supplement, including 29 missing error entries; the retrieved package lacks the prepared molecular inputs and numerical score/energy files for a direct matched-input rerun.", [evidence("grader/spotcheck_results.json", "/supplement", "Independent pypdf extraction matches every normalized field and nested ZIP listing contains eight analysis files only."), evidence("data/raw/ayyildiz2025/analysis_source/bbkstar.py", "readPdb and output/cache references", "Script references ./osprey_Arg-binder-build.pdb and generated score/energy files absent from the supplied package.")], "This is an inventory of the retrieved package, not proof that no other repository or author can supply inputs. Missing errors have no assumed statistical meaning.", "Useful data-preparation/reproduction-gap artifact; 63 rows belong to five related binding pockets, not 63 independent systems."),
        finding("F7", "limitation", "Neither ETH-derived computational improvement nor improved biological prediction was tested.", [evidence("runs/review-001/claims.json", "/claims/novel_speedup and /claims/biology", "Parent explicitly declines both claims."), evidence("data/README.md", "Published experimental labels", "The UAI systems and measured-label systems are unpaired.")], "Absence of a matched experiment is not a negative biological result or evidence that ensemble counting cannot help.", "Generic counting and exactness within a model remain separate from biological validity."),
        finding("F8", "limitation", "The best justified next experiment is a small, prospective conventional resource/structure study; a full ETH-to-protein implementation is not justified by this campaign.", [evidence("grader/summary_checks.json", "/structural and /performance", "Current models do not probe a structural or resource boundary."), evidence("grader/audit_results.json", "/schedule", "Literal-schedule feasibility obstruction reinforces deferring the full manuscript pipeline.")], "Recommendation, not a measured result. No next experiment is warranted if the only objective is demonstrating this literal schedule on practical protein sizes.", "Select cases by structural/resource covariates before outcomes, compare a mature conventional solver, and retain all resource-limited cases. Biological testing should wait for one reproducible matched molecular-model/label system.")
    ]
    criteria = []
    for cid, status, reason, ids in [
        ("P1", "pass", "Raw inputs, pinned source, versions, transformations, and separate data classes are traceable; local selection and conversion independently verified.", ["F0", "F1", "F6"]),
        ("C1", "pass", "Fixed source-first weighted sums, state separation, zeros, and all 14 modeled score identities independently match.", ["F1", "F2"]),
        ("C2", "partial", "Exact computations pass all audited tolerance checks. Strict bound containment is false; tolerance-relaxed containment is supported.", ["F2", "F3"]),
        ("F1", "pass", "Named enumeration/elimination comparison has matching targets, explicit scope, fresh sequential processes, original repeats, and process RSS; practical and general scope remain limited.", ["F4"]),
        ("R1", "pass", "Frozen manifests/source snapshots/input hashes and all planned trial records verify; independent diagnostics preserve originals.", ["F0"]),
        ("U1", "pass", "Prospective numerical tolerance, repeat ranges, floating-bound disclaimer, convenience cohort, and lack of biological inference are appropriate to a bounded exploratory study.", ["F2", "F3", "F4", "F7"]),
        ("B1", "not_tested", "Measured labels were prepared but never paired with the tested models; no biological comparison occurred.", ["F6", "F7"]),
        ("N1", "pass", "Literal-schedule failure and package reproduction gap are independently checkable and narrowly scoped; all campaign trials are retained.", ["F0", "F5", "F6"]),
        ("E1", "pass", "Only source-grounded literal-schedule analysis qualifies as ETH-specific progress; ordinary inference is correctly labeled.", ["F5", "F7"]),
        ("E2", "pass", "Exact transcription, fixed beta/N interpretation, complete earlier-interval exclusion, parameter tuples, and boundary interpretation independently checked.", ["F5"])
    ]:
        criteria.append({"criterion_id": cid, "status": status, "rationale": reason, "evidence_ids": ids})
    claims = [
        claim("artifact", "validated_benchmark_artifact", "14 public UAI cases yield a checked 42-state source-first fixed-sequence artifact.", "supported", "Published discrete representation only.", ["P1", "C1", "R1"], ["F0", "F1"], ["One sequence per case; source approximations retained; no sequence optimum or experimental calibration."]),
        claim("correctness", "useful_measurement", "Exact algorithms agree within prospective tolerance; all bounds contain the chosen reference.", "partially_supported", "Exact agreement and tolerance-relaxed containment are supported; strict containment is rejected.", ["C2", "U1"], ["F2", "F3"], ["30/126 strict misses against chosen floating reference; no interval certification."]),
        claim("small_cohort_feasibility", "useful_measurement", "The tested conditioned cohort is tractable with conventional local inference.", "supported", "These 42 state models on recorded local hardware.", ["F1", "R1", "U1"], ["F4"], ["1-8 variables and represented full-joint tables; no sparse-graph or broad scalability evidence."]),
        claim("literal_schedule", "eth_specific_progress", "Four necessary literal-schedule gates fail at illustrative sizes; beta=1 first passes at lambda 10,909,384,704.", "supported", "Identified Section 4 parameter schedule only.", ["N1", "E1", "E2"], ["F5"], ["Not all construction hypotheses, a runtime crossover, implementation, or theorem validation."], data_class="theoretical_schedule", eth_subtype="source_grounded_feasibility_analysis"),
        claim("reproduction_gap", "useful_measurement", "The retrieved 2025 package supplies labels/scripts but lacks prepared inputs and numeric score/energy files for direct matched-input replay.", "supported", "Retrieved package inventory.", ["P1", "N1"], ["F6"], ["No claim that inputs are unavailable elsewhere; reconstruction not attempted."], data_class="experimental_measurement"),
        claim("novel_speedup", "computational_improvement", "A novel counting algorithm or ETH-derived computational speedup improves this task.", "not_tested", "No such implementation/comparison was performed or claimed.", ["F1", "E1"], ["F4", "F7"], ["Descriptive conventional VE/batch differences do not establish this claim."], eth_subtype="none"),
        claim("biology", "biological_evidence", "More exact or faster counting improves measured affinity prediction.", "not_tested", "No matched model/measurement evaluation.", ["B1"], ["F6", "F7"], ["Unpaired datasets; no biological null result follows."], data_class="mixed")
    ]
    recomputations = []
    for id_, purpose, method, result, inputs, independent, ids in [
        ("R0", "Bundle integrity and prospective snapshots", "SHA-256 all 1,342 files, manifest/source checks, trial-ID completeness and embedded/raw equality.", "matched", ["runs/review-001/bundle_manifest.json"], "Does not use worker verification code.", ["F0"]),
        ("R1", "Raw source-to-model conversion", "Separate UAI parser and independent domain/factor reconstruction; every 35,459 entry and original factor/variable coverage checked.", "matched", ["data/raw/uai23/", "data/models/uai23/"], "No worker parser or conversion function imported.", ["F1"]),
        ("R2", "Partition sums on all 42 models", "Product/sum enumeration from original source weights with separate NumPy coordinate enumeration; compare all 284 exact trials.", "matched", ["data/raw/uai23/", "runs/campaign-001/trials.jsonl"], "No worker log-domain summation, model parser, or conversion function imported; platform longdouble equals float64.", ["F2"]),
        ("R3", "Higher-precision and conversion spot checks", "80-digit Decimal direct products/sums/logs over 30,284 configurations in 20 models; raw and stored-log targets evaluated separately.", "matched", ["data/raw/uai23/", "data/models/uai23/"], "Separate numerical library and arithmetic path from worker NumPy log-domain core.", ["F2"]),
        ("R4", "Reported bound containment", "Compare every endpoint against chosen VE/raw references with and without prospective tolerance; check 60 endpoints against 80-digit model values.", "partly_matched", ["runs/campaign-001/trials.jsonl", "grader/spotcheck_results.json"], "Independent reference computation; approximate method itself was not rerun.", ["F3"]),
        ("R5", "ETH schedule transcription and minimality", "Independent exhaustive enumeration of integer square-root blocks within every earlier nu interval; exact necessary inequalities and source excerpt checked.", "matched", ["experiments/eth_schedule/source/main_full_version.tex", "runs/eth-schedule-001/"], "No schedule experiment code imported or reused; no global monotonicity assumption.", ["F5"]),
        ("R6", "2025 label artifact and reproduction gap", "Independent pypdf extraction of every Table S1 row, full field comparison, nested ZIP inventory, and referenced input/output inspection.", "matched", ["data/raw/ayyildiz2025/", "data/ayyildiz2025_affinities.json"], "Different PDF text extractor and separately written parser.", ["F6"]),
        ("R7", "Timing/structure interpretation", "Reaggregate medians, ratios, scope width, full-joint table size, process RSS, status counts, and model score relation.", "matched", ["runs/campaign-001/trials.jsonl", "data/uai23_tree.json"], "Separate aggregation; original clock measurements were not independently repeated.", ["F4"])
    ]:
        recomputations.append({"id": id_, "purpose": purpose, "inputs": inputs, "command_or_method": method, "result": result, "independent_of": independent, "evidence_ids": ids})
    verdict = {
        "rubric_id": "protein-counting-exploratory-v1",
        "rubric_sha256": audit["rubric_sha256"],
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "bundle": {"manifest_path": "runs/review-001/bundle_manifest.json", "manifest_sha256": audit["bundle_sha256"], "received_at_utc": "2026-11-06T12:01:42Z", "integrity_status": "verified", "files_exposed": audit["exposed_paths"], "notes": "All bundle files hashed; semantic categories and post-exposure diagnostics recorded in grader/POSTEXPOSURE.md. Later parent reports/plots excluded."},
        "independence": {"rubric_preceded_results": True, "deviations": [], "statement": "Rubric frozen before worker outputs were viewed. Separate grader-owned recomputations; parent claims were visible before recomputation. Procedural independence does not eliminate bias."},
        "overall": {"label": "informative", "rationale": "A validated computational artifact, numerical checks, a bounded schedule obstruction, and a reproducibility gap are useful outcomes. The strict-containment clause needs correction; computational novelty, sparse-structure benefits, and biological improvement remain untested."},
        "criteria": criteria,
        "claims": claims,
        "findings": findings,
        "recomputations": recomputations,
        "limitations": [
            "One source-first sequence per case; 42 states are nested in 14 cases and 9 PDB systems, with smallest-archive selection for two groups.",
            "Represented factor scopes are dense; no simplification of constant/separable tables, sequence optimization, or sparse-structure benefit was tested.",
            "Source UAI factors retain model approximations and zeros; no molecular preparation or continuous-energy validation was reproduced.",
            "Float64 endpoints are not rigorous certificates; strict containment fails at roundoff scale despite all tolerance-relaxed checks passing.",
            "Only 20 models received 80-digit spot checks; all 42 received independently implemented float64 raw-product enumeration. No formal rounding-error proof was attempted.",
            "Original timings were reaggregated but not independently rerun; 3 repeats and shared workstation load limit fine performance comparisons. Download, parsing, and molecular preparation are outside timing scope.",
            "No established external solver was benchmarked; no full ETH routine, replacement construction, or protein reduction was implemented.",
            "The literal-schedule audit checks necessary gates only; it does not rule out alternate schedules or assess the theorem.",
            "The biological label inventory is not a prediction evaluation; package absence does not imply global unavailability."
        ],
        "amendments": []
    }
    (OUT / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")


if __name__ == "__main__":
    main()
