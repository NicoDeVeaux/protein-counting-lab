"""Record a final judgment from preserved independent audit outputs."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "grader/campaign-002"


def read(name):
    return json.loads((OUT/name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original=read("original_integrity_audit.json")
    corrected=read("corrected_audit.json")
    numeric=read("independent_numeric_audit.json")
    resources=read("original_resource_audit.json")
    summary=read("final_summary_audit.json")
    freeze=read("FREEZE.json")
    assert not original["integrity_errors"] and not corrected["integrity_errors"]
    assert not original["grader_payload_integrity_errors"] and not corrected["schema_errors"]
    assert not original["schema_errors"]["manifest"] and not original["schema_errors"]["trials"]
    assert not original["reconciliation_errors"]
    assert all(digest(ROOT/x["path"])==x["sha256"] for x in freeze["files"])
    fyn=next(x for x in numeric["real"] if x["model_id"].startswith("1FYN__"))
    verdict={
        "schema_version":1,
        "campaign":"002",
        "completed_at_utc":datetime.now(timezone.utc).isoformat(),
        "verdict":"informative_conventional_feasibility_with_qualified_comparison",
        "headline":"Verified artifacts and a useful local regime; disclosed native-quota correction; broad timing superiority unresolved.",
        "no_winner_required":True,
        "grader_freeze_sha256":digest(OUT/"FREEZE.json"),
        "protocol_sha256":digest(OUT/"PROTOCOL.md"),
        "original_bundle":original["bundle"],
        "corrected_bundle":{"path":corrected["bundle_path"],"sha256":corrected["bundle_sha256"],"files":corrected["bundle_files"],"bytes":corrected["bundle_bytes"]},
        "original_execution_manifest_sha256":original["manifest_sha256"],
        "corrected_execution_manifest_sha256":corrected["manifest_sha256"],
        "integrity":{"all_hashes_match":True,"schemas_pass":True,"original_planned_and_observed":828,"corrected_planned_and_observed":828,"missing_or_duplicate_rows":0,"frozen_grader_payload_unchanged":True,"original_and_corrected_rows_preserved":True},
        "adaptation":{"classification":"disclosed_corrective_full_matrix_rerun_after_exposure","prior_report_used_adaptively":True,"parent_unit_suspicion_disclosed_before_independent_source_check":True,"official_source_independently_obtained":True,"outcome_selected_diagnostics_separate":True,"fresh_oracle_postexposure":True,"model_target_reference_accuracy_resource_matrix_and_order_unchanged":True,"premeasurement_schema_rejection_preserved":True,"blind_replication_claim":False,"fresh_context_is_procedural_not_bias_guarantee":True,"parent_plots_or_later_narrative_read":False},
        "gates":[
            {"gate":"integrity_prospectivity","judgment":"pass_with_disclosed_adaptation","evidence":"All bundle hashes, schemas, trial identities and timestamps reconcile; initial corrected manifest rejection preceded zero trials; original artifacts retained."},
            {"gate":"semantics_numerics","judgment":"pass_for_audited_scope_partial_accuracy_coverage","evidence":"All67 representations/eight reductions and selected raw CPD entries checked; frozen-reference successes pass; fresh Decimal controls and1FYN support audit pass; grid8 still has no adequate oracle."},
            {"gate":"representation_coverage","judgment":"useful_bounded_coverage","evidence":"No sparse larger published-protein, high-order or>64-domain family. Dense-join obstructions and exact algebra controls are useful within their represented scope."},
            {"gate":"resource_comparison","judgment":"qualified_feasibility_pass_broad_timing_unresolved","evidence":"Native scheduler unit correction resolves15errors; process/table limits and failures retained. Static workspace is not an upper bound; corrected repeat/schedule drift prevents broad speed ranking."},
            {"gate":"interpretation_usefulness","judgment":"pass_with_scope_limits","evidence":"Usable conventional local regimes, conversion/representation limits and an actionable hard-zero hypothesis. No ETH, novel algorithm, affinity or biological improvement evidence."}
        ],
        "original_outcomes":original["status_counts"],
        "corrected_outcomes":corrected["status_counts"],
        "corrected_outcomes_by_cohort":summary["corrected_cohort_counts"],
        "status_transitions":corrected["status_transitions"],
        "changed_status_rows":corrected["changed_status_rows"],
        "semantics":{"representations_checked":67,"serialized_exact_reductions_checked":8,"selected_raw_CPD_pair_entries_checked":75264,"selected_BKB_template_domain_coordinates_checked":True,"all_domains_preserved":True,"target":"Source-first fixed-AA single-state beta1 numerical Etmp+BKB+pair target; SELF not added; literal1.0E38 alone is hard zero; stored binary64 logs define numerical inference.","nonselected_source_coordinate_completeness":"Relies on preserved worker full-grid bitset audit; grader reconstructs selected entries exhaustively.","larger_protein_models":6,"listed_position_range":[23,30],"nontrivial_variable_range":[10,25],"sparse_larger_published_protein_coverage":False,"synthetic_pooling_into_protein_results_allowed":False},
        "numerics":{"original_successes_recompared":471,"original_max_error_against_frozen_references":resources["max_absolute_log_error_against_frozen_references"],"corrected_successes_recompared":corrected["frozen_ref_successes_recompared"],"corrected_max_error_against_frozen_references":corrected["max_error_against_frozen_refs"],"fresh_Decimal_precision_digits":90,"fresh_synthetic_reference_checks":10,"synthetic_target_factor_checks":11,"fresh_baseline_real_checks":2,"fresh_extension_checks":1,"oneFYN":fyn,"corrected_posthoc_real_trial_checks":corrected["posthoc_high_precision_trial_checks"],"frozen_unverified_statuses_upgraded":False,"remaining_unverified_grid8_completions_per_campaign":12,"strict_interval_certificate":False,"reference_scope":"Historical baseline references plus frozen analytic/transfer synthetic references; fresh grader calculations are post-exposure audit evidence, not a new prospective oracle."},
        "resource":{"table_profiles_bytes":[16777216,134217728],"RSS_profiles_bytes":[134217728,536870912],"timeout_profiles_seconds":[10,20],"native_original_scheduler_quota_bytes":1048576,"native_corrected_scheduler_quota_bytes":1073741824,"native_scheduler_is_RSS_ceiling":False,"all15_native_original_exceptions_recovered":True,"original_exceptions_show_host_RAM_exhaustion":False,"sampling_interval_seconds":0.01,"instantaneous_RSS_ceiling_guaranteed":False,"measured_RSS_limit_rows":0,"named_table_policy_rejections":108,"positive_entry_underflow_rejections":72,"roundtrip_tolerance_rejections":6,"enumeration_state_policy_skips":126,"static_workspace_is_upper_bound":False,"workspace_counterexample":{"model":"1FYN original","static_workspace_bytes":252905192,"kernel_estimated_peak_live_array_bytes":268710632},"oneFYN_largest_table_bytes_both_representations":126443520,"oneFYN_corrected_original_VE_peak_RSS_bytes_range":[455327744,496058368],"oneFYN_corrected_simplified_VE_peak_RSS_bytes_range":[207142912,207568896],"preparation_time_includes_artifact_serialization":False,"full_raw_source_to_result_time_measured":False},
        "timing":{"broad_superiority_supported":False,"stable_crossover_supported":False,"dispersion":corrected["dispersion_summary"],"unchanged_custom_methods_corrected_over_original_by_schedule_quartile":corrected["unchanged_custom_methods_corrected_over_original_by_schedule_quartile"],"cause_of_drift_established":False,"kernel_and_wall_scopes_must_remain_separate":True,"early_trials_or_timeouts_removed":False},
        "useful_findings":["Published-source conversion/reduction artifact and unchanged original42 baseline are auditable.","1FYN completed numerical results have a new independent posthoc high-precision check, with a demonstrated local table/RSS regime.","Constant/separable synthetic controls validate exact algebraic removal of represented graph complexity.","Native quota errors and positive-entry conversion rejections are isolated from host-memory or mathematical impossibility.","Failure retention and large timing drift prevent a misleading aggregate solver winner."],
        "next_hypothesis":{"name":"exact_hard_zero_propagation_before_dense_inference","basis":"1FYN declared15805440 -> unary635040 -> arc476280 -> positive263088; purely verifier support analysis.","measured_campaign_method":False,"benchmark_speedup_established":False,"new_experiment_performed_for_this_hypothesis":False},
        "unsupported_claims":["ETH implementation or theorem-to-program advance","novel counting algorithm","general solver superiority or clean runtime crossover","intrinsic counting hardness from this represented dense scope","improved biological prediction, affinity ranking or molecular validity"],
        "audit_limits":["Convenience cohort and correlated states; no population-general inference.","Full selected CPD entries and representation identities checked, but unused source coordinates not independently fully rebuilt.","Only two baseline cases and one new protein case receive fresh Decimal enumeration; prior baseline high-precision evidence is reused and disclosed.","Grid8 reference remains inadequate; other five new protein targets yield no validated result under these policies.","Decimal and binary64 comparisons are numerical checks, not outward-rounded certificates.","Native comparator reconstructs logZ with nconditional queries; no native one-query Z API comparison.","Workspace estimate excludes allocations and is not conservative; sampled RSS is not an instantaneous hard guarantee.","No archived telemetry establishes why corrected timings drift; all raw observations and censoring remain.","No further timing experiment or implementation change was made by the grader; standalone verifier runtime is not a measured benchmark."],
        "report_path":"grader/campaign-002/REPORT.md"
    }
    (OUT/"verdict.json").write_text(json.dumps(verdict,indent=2,allow_nan=False)+"\n")
    files=[]
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.name not in ["audit_manifest.json","audit_manifest.sha256"]:
            files.append({"path":str(path.relative_to(ROOT)),"sha256":digest(path),"bytes":path.stat().st_size})
    audit_manifest={"completed_at_utc":datetime.now(timezone.utc).isoformat(),"phase":"final_independent_audit","frozen_original_bundle_sha256":original["bundle"]["sha256"],"frozen_combined_bundle_sha256":corrected["bundle_sha256"],"frozen_grader_payload_reverified":True,"files":files}
    path=OUT/"audit_manifest.json"
    path.write_text(json.dumps(audit_manifest,indent=2,allow_nan=False)+"\n")
    (OUT/"audit_manifest.sha256").write_text(digest(path)+"  "+str(path.relative_to(ROOT))+"\n")
    assert all(digest(ROOT/x["path"])==x["sha256"] for x in files)
    print(json.dumps({"verdict":verdict["verdict"],"audit_manifest_prefix":digest(path)[:6],"audit_files":len(files),"numeric_successes_recompared":len(corrected["posthoc_high_precision_trial_checks"]),"report_bytes":(OUT/"REPORT.md").stat().st_size}))


if __name__=="__main__":
    main()
