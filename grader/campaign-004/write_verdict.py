"""Assemble campaign004 independent findings and seal the audit artifacts."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


def identity(path):
    data = (ROOT / path).read_bytes()
    return {'path': path, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def main():
    resources = read('grader/campaign-004/resource_audit/audit.json')
    semantics = read('grader/campaign-004/semantics_audit.json')
    ranking = read('grader/campaign-004/ranking_audit.json')
    scope = read('grader/campaign-004/scope_audit.json')
    assert resources['all_invariants_pass'] and not resources['issues']
    assert len(semantics['all14_source_audits']) == 14
    assert not any(row['energy_checks']['mismatches'] for row in semantics['all14_source_audits'])
    assert semantics['fresh_decimal_target_rows'] == 63 and semantics['representations_checked'] == 126
    assert ranking['state_outputs_recompared'] == 756 and ranking['query_outputs_recompared'] == 252
    assert all(panel['pairwise'] == {'resolved': 210} for panel in ranking['panels'])
    counts = Counter()
    for row in semantics['all14_source_audits']:
        counts.update(row['energy_checks']['counts'])
    now = datetime.now(timezone.utc).isoformat()
    verdict = {
        'schema_version': 1, 'campaign': '004', 'completed_at_utc': now,
        'verdict': 'verified_source_encoding_three_state_scoring_and_fixed_panel_ranking_no_general_pruning_gain',
        'headline': 'All21 encoded template scores/ranks verified; equal coverage, no material memory gain, method-specific timing with batch order confound; physical/bio interpretation unestablished.',
        'no_preferred_winner_required': True,
        'bundle': resources['bundle'],
        'preparation_manifest_sha256': resources['preparation_manifest_sha256'],
        'execution_manifest_sha256': resources['execution_manifest_sha256'],
        'grader_freeze': identity('grader/campaign-004/FREEZE.json'),
        'gates': [
            {'gate': 'integrity_prospectivity', 'judgment': 'qualified_pass',
             'evidence': '8428 bundle hashes and8031prior hashes match; scientific choices/prep-final fields match; complete schedule/full ledger; disclosed prefreeze grammar/numeric-prefix inspection; local chronology is not externally trusted.'},
            {'gate': 'source_encoding_decomposition', 'judgment': 'pass_all14cases',
             'evidence': 'Independent raw source parsing,691factor owners,386544selector constraint entries, all42old source-first models, all rounded energy entries, temperature/sign and sum groups; no scalar/offset omitted.'},
            {'gate': 'physical_affinity_interpretation', 'judgment': 'not_established_restrict_to_source_encoding_diagnostics',
             'evidence': 'Finite-energy source underflow zeros established; full precision energies, additional-conformer coordinate origin and physical energy calibration/absolute offsets not independently reconstructed.'},
            {'gate': 'same_target_preprocessing', 'judgment': 'pass_all126representations',
             'evidence': 'Independent GAC deletion replay/reverse fixed point, original state maps, exact Fraction factor identities and numeric fingerprints; no new positive-weight threshold.'},
            {'gate': 'independent_reference_numerics_and_rank', 'judgment': 'pass_complete_fixed_panel',
             'evidence': 'All63fresh Decimal90/120 raw-source references in3semantics;756logZ/252logKchecks;210resolved pair orders per panel and exact full orders/top1,3,5; no forced uncertain ties.'},
            {'gate': 'coverage_resources_comparison', 'judgment': 'qualified_local_cost_findings_no_coverage_memory_or_general_solver_win',
             'evidence': 'Both arms finish full21;240valid same-worker identical-target cachehits and516directcalls; all costs charged/separated. All3batch pairs pruned first; VE pruning slower withbothorders. No native comparator.'},
            {'gate': 'interpretation_usefulness', 'judgment': 'useful_encoded_scoring_validation_and_bounded_tradeoff',
             'evidence': 'BaselineLEU ranks first; no panel alternative improves encoded score. No physical/biological prediction, ETH or portable speedup evidence.'}
        ],
        'integrity_and_ledger': resources['ledger'],
        'source_semantics': {
            'audited_cases': 14,
            'source_factors': sum(row['source_factors'] for row in semantics['all14_source_audits']),
            'selector_constraint_entries': sum(row['constraint_entries'] for row in semantics['all14_source_audits']),
            'source_first_equivalence_models': semantics['source_first_equivalence_models'],
            'source_first_equivalence_numeric_entries': semantics['source_first_equivalence_numeric_entries'],
            'new_original_models': semantics['new_original_models'],
            'new_original_numeric_entries': semantics['new_original_numeric_entries'],
            'exact_reduction_entry_checks': semantics['exact_reduction_entry_checks'],
            'energy_source_checks': dict(counts), 'energy_source_mismatches': 0,
            'temperature_kelvin': 298.15, 'gas_constant_kcal_per_mol_kelvin': 0.0019891,
            'target': 'Ideal sum exp(stored binary64 log factor values); source literal zeros remain exact zeros; logK=logZC-logZP-logZL.',
            'physical_target_recovered': False,
            'real_template_mapped_last_conformers_retained': True,
            'source_positive_values_thresholded_or_restored': False
        },
        'numerics_and_rank': {key: value for key, value in ranking.items() if key != 'panels'},
        'costs': resources['costs'], 'comparisons': resources['comparisons'],
        'scope_qualifications': resources['scope_qualifications'],
        'chronology': resources['chronology'],
        'exposure_and_deviations': {
            'adaptive_to_previous_campaigns': True,
            'parent_candidate_claims_received_before_phase2_checks': True,
            'parent_plots_or_later_narratives_read': False,
            'scientific_prep_final_fields_unchanged': True,
            'prefreeze_source_grammar_numeric_prefix_inspection_disclosed': True,
            'counterbalanced_batch_order_achieved': False,
            'batch_all3_pruned_first': True,
            'phase1_intended_counterbalancing_not_realized': 'Frozen randomization happened to use one batch order inall3pairs; no outcome-adaptive schedule change is found. This limits timing inference.',
            'retained_initial_prefreeze_synthetic_preflight': '14fixture-related failures,122passes; final frozen preflight136passes.',
            'grader_check_development': 'Initial independent audit serialization rejected a numpy integer; initial rank checker assumed a different panel status label. Corrected grader-only formatting/record interpretation; sealed payloads and scientific criteria unchanged; checks rerun.',
            'external_trusted_chronology': False
        },
        'comparator_and_biology': scope,
        'unsupported_claims': ['Exact unrounded physical partition functions or absolute physical affinity.',
                               'Experimental biological-prediction accuracy or an improved mutation.',
                               'Twenty-one distinct natural amino acids.',
                               'General solver superiority, order-robust batch speedup, coverage gain or material whole-worker memory gain.',
                               'Native BBK*/AOBB-K* performance comparison.', 'ETH or a novel counting algorithm.'],
        'validation': {'independent_scripts': ['audit_semantics.py', 'audit_ranking.py', 'audit_scope.py', 'resource_audit/audit_resources.py'],
                       'production_imports_in_independent_checks': False,
                       'reused_independent_helper': identity('grader/campaign-003/audit_semantics.py'),
                       'directed_interval_certificate': False,
                       'new_measured_experiment_runs_by_grader': False},
        'audits': [identity('grader/campaign-004/' + path) for path in (
            'semantics_audit.json', 'ranking_audit.json', 'scope_audit.json', 'resource_audit/audit.json')],
        'report_path': 'grader/campaign-004/REPORT.md'
    }
    (OUT / 'verdict.json').write_text(json.dumps(verdict, indent=2) + '\n')
    paths = sorted(str(path.relative_to(ROOT)) for path in OUT.rglob('*') if path.is_file()
                   and path.name not in ('AUDIT_SEAL.json', 'AUDIT_SEAL.sha256')
                   and '__pycache__' not in path.parts)
    seal = {'campaign': '004', 'sealed_at_utc': now,
            'bundle': resources['bundle'], 'files': [identity(path) for path in paths],
            'external_immutable_helper': identity('grader/campaign-003/audit_semantics.py')}
    seal_path = OUT / 'AUDIT_SEAL.json'
    seal_path.write_text(json.dumps(seal, indent=2) + '\n')
    sha = hashlib.sha256(seal_path.read_bytes()).hexdigest()
    (OUT / 'AUDIT_SEAL.sha256').write_text(sha + '  grader/campaign-004/AUDIT_SEAL.json\n')
    print(json.dumps({'verdict': verdict['verdict'], 'audit_files': len(paths), 'audit_seal': sha[:6]}))


if __name__ == '__main__':
    main()
