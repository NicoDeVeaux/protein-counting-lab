"""Independently reconcile the sealed campaign003 record without importing experiment code."""

from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'runs/campaign-003-amendment-003'


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def lines(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines() if line.strip()]


def diff(a, b, path=''):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        return [path+'/'+k for k in a.keys() ^ b.keys()] + [p for k in a.keys() & b.keys() for p in diff(a[k], b[k], path+'/'+k)]
    if isinstance(a, list):
        return [path] if len(a) != len(b) else [p for i, (x, y) in enumerate(zip(a, b)) for p in diff(x, y, path+'/'+str(i))]
    return [] if a == b else [path]


def audit():
    bundle_path = 'runs/campaign-003-review/bundle_manifest.json'
    bundle = read(bundle_path)
    assert sha(bundle_path).startswith('19ed41')
    inventory = bundle['files']
    assert len({f['path'] for f in inventory}) == len(inventory)
    total_bytes = 0
    for f in inventory:
        p = ROOT / f['path']
        assert p.is_file(), f
        assert p.stat().st_size == f['bytes'], f
        assert sha(f['path']) == f['sha256'], f
        total_bytes += f['bytes']
    freezes = []
    for name in ['FREEZE', 'AMENDMENT-001', 'AMENDMENT-002', 'AMENDMENT-003']:
        p = 'grader/campaign-003/'+name+'.json'
        d = read(p)
        assert sha(p) == (ROOT / (p[:-5]+'.sha256')).read_text().split()[0]
        for f in d['files']:
            assert sha(f['path']) == f['sha256']
        freezes.append({'path': p, 'sha256': sha(p), 'time': d['frozen_at_utc']})
    manifest_path = 'runs/campaign-003-amendment-003/manifest.json'
    manifest = read(manifest_path)
    prep = read('prepared/campaign-003/preparation_manifest.json')
    planned = read('runs/campaign-003-amendment-003/planned_trials.json')
    rows = lines('runs/campaign-003-amendment-003/trials.jsonl')
    assert manifest['planned_trials'] == planned == prep['planned_trials']
    assert manifest['references'] == prep['references']
    for key in ['resource_profiles', 'total_wall_budget_seconds', 'preprocessing_limit_seconds']:
        assert manifest[key] == prep[key], key
    accuracy_wording_diff = diff(prep['accuracy_contracts'], manifest['accuracy_contracts'])
    assert accuracy_wording_diff == ['/0/target_definition', '/0/source_semantics', '/0/acceptance_rule', '/0/reference_plan', '/0/zero_mass_rule'] or set(accuracy_wording_diff) == {'/0/target_definition','/0/source_semantics','/0/acceptance_rule','/0/reference_plan','/0/zero_mass_rule'}
    for k in ['accuracy_contract_id','kind','strict_interval_claim','certificate_plan']:
        assert manifest['accuracy_contracts'][0][k] == prep['accuracy_contracts'][0][k]
    assert '1e-8+64*eps64*max(1,abs(reference_log_z),sum_abs_restored_log_offsets)' in manifest['accuracy_contracts'][0]['acceptance_rule'].replace(' ','')
    assert '1e-8+64*eps64*max(1,abs(reference_log_z),sum_abs_restored_log_offsets)' in prep['accuracy_contracts'][0]['acceptance_rule'].replace(' ','')
    implementation_checks = []
    for f in prep['implementation_inventory']:
        assert sha(f['path']) == f['sha256'], f
        implementation_checks.append(f['path'])
    schemas = {name: read('grader/campaign-003/'+name+'.schema.json') for name in ['manifest', 'trial']}
    for s in schemas.values():
        jsonschema.Draft202012Validator.check_schema(s)
    jsonschema.validate(manifest, schemas['manifest'])
    for row in rows:
        jsonschema.validate(row, schemas['trial'])
    assert len(planned) == len(rows) == 324
    assert len({r['trial_id'] for r in rows}) == len(rows)
    index = {r['trial_id']: r for r in rows}
    identity = ['trial_id', 'model_id', 'representation_id', 'method_id', 'resource_profile_id', 'accuracy_contract_id', 'repeat', 'block_id']
    profiles = {p['resource_profile_id']: p for p in manifest['resource_profiles']}
    mhash = sha(manifest_path)
    previous_finish = manifest['frozen_at_utc']
    sidecars, raw_outputs, rss_over, phase_failures = 0, 0, [], []
    for plan in planned:
        row = index[plan['trial_id']]
        assert all(row[k] == plan[k] for k in identity), plan
        assert row['manifest_sha256'] == mhash
        assert row['retry_of'] is None
        assert row['started_at_utc'] >= previous_finish
        assert row['finished_at_utc'] >= row['started_at_utc']
        previous_finish = row['finished_at_utc']
        monitor = row['monitor']
        assert monitor['started_at_utc'] == row['started_at_utc']
        assert monitor['finished_at_utc'] == row['finished_at_utc']
        assert monitor['wall_seconds'] == row['timing']['wall_seconds']
        assert abs((datetime.fromisoformat(row['finished_at_utc'])-datetime.fromisoformat(row['started_at_utc'])).total_seconds()-monitor['wall_seconds']) < .01
        cap = profiles[row['resource_profile_id']]['rss_ceiling_bytes']
        observed = max(row['memory'].get('rss_peak_bytes') or 0, row['memory'].get('worker_reported_lifetime_peak_rss_bytes') or 0)
        if observed > cap:
            rss_over.append(row['trial_id'])
            assert row['status'] == 'rss_limit'
        artifact = row['output'].get('artifact')
        if artifact is not None:
            raw = read(artifact['path'])
            assert sha(artifact['path']) == artifact['sha256']
            assert raw['pipeline']['target_sha256'] == row['prepared_target_sha256']
            assert raw['pipeline'] == row['pipeline']
            assert raw['model_sha256'] == row['pipeline_input']['sha256']
            assert raw['model_id'] == row['model_id']
            raw_outputs += 1
            sidecar = read(row['serialization_timing_artifact']['path'])
            assert sidecar == row['serialization_timing']
            assert sha(row['serialization_timing_artifact']['path']) == row['serialization_timing_artifact']['sha256']
            assert sidecar['cold_total_through_result_seconds'] >= raw['pipeline']['cold_total_seconds']
            assert sidecar['cold_total_through_result_seconds'] < row['timing']['wall_seconds']
            assert row['timing']['phases']['serialization'] == sidecar['serialization_seconds']
            assert row['memory']['worker_reported_lifetime_peak_rss_bytes'] == max(raw['process_peak_rss_bytes'], sidecar['process_peak_rss_bytes_after_result'])
            p = raw['pipeline']
            constituents = sum(p.get(k, 0) for k in ['load_seconds', 'propagation_seconds', 'simplification_seconds', 'target_validation_seconds', 'inference_seconds'])
            assert constituents <= p['cold_total_seconds']+.0001
            sidecars += 1
    bymodel = {m['model_id']: m for m in manifest['models']}
    original = read('grader/campaign-003/FREEZE.json')['fixed_published_targets']
    for m in original:
        current = bymodel[m['model_id']]
        original_file = next(r for r in m['representations'] if r['representation_id'] == 'original')['files'][0]
        assert current['pipeline_input'] == original_file
    assert len([m for m in manifest['models'] if m['cohort'] == 'published_protein_extension']) == 6
    for before in prep['models']:
        after = bymodel[before['model_id']]
        for k, v in before.items():
            if k not in ['representations', 'preparation_status']:
                assert after[k] == v, (before['model_id'], k)
        assert [(r['representation_id'], r['resource_profiles']) for r in before['representations']] == [(r['representation_id'], r['resource_profiles']) for r in after['representations']]
    catalogs = [read('prepared/campaign-003/'+n) for n in ['catalog.json', 'catalog.amendment-002.json', 'catalog.amendment-003.json']]
    change2, change3 = diff(catalogs[0], catalogs[1]), diff(catalogs[1], catalogs[2])
    provenance = {'/format_amendment','/source_inventory','/exposure_ledger'}
    assert all(p.startswith('/selection_rule') or p in provenance for p in change2), change2
    assert all(p.endswith('/simplification') or p.endswith('/simplification_description') or p in provenance or p.startswith('/format_amendment/') for p in change3), change3
    for a,b in zip(catalogs,catalogs[1:]):
        for key in ['source_inventory','exposure_ledger']:
            assert b[key][:len(a[key])] == a[key]
    for a, b in zip(catalogs[1]['models'], catalogs[2]['models']):
        for x, y in zip(a['representations'], b['representations']):
            assert x['simplification'] == y['simplification_description']
    fixture = read('prepared/campaign-003/complete-corrected-schema-fixture.json')
    jsonschema.validate(fixture, schemas['manifest'])
    errors = read('runs/campaign-003-schema-diagnostic/all-schema-errors.json')
    ledger = lines('prepared/campaign-003/preparation.jsonl')
    assert len(errors)==24 and all(e['path'][-1]=='simplification' for e in errors)
    candidate=read('runs/campaign-003-schema-diagnostic/candidate.json')
    independent_errors=list(jsonschema.Draft202012Validator(schemas['manifest']).iter_errors(candidate))
    assert len(independent_errors)==24
    assert all(e.absolute_path[-1]=='simplification' for e in independent_errors)
    assert len(ledger)==24
    assert {(r['model_id'],r['representation_id']) for r in ledger}=={(m['model_id'],a) for m in prep['models'] for a in ['simplified','propagated']}
    previous=prep['frozen_at_utc']
    static_wall=0
    for r in ledger:
        assert r['status']=='prepared'
        monitor=r['monitor']
        assert monitor['started_at_utc']>=previous
        assert r['recorded_at_utc']>=monitor['finished_at_utc']
        previous=monitor['finished_at_utc']
        assert monitor['wall_seconds']<prep['static_preparation']['row_wall_seconds']
        result=read(r['result']['path'])
        assert max(result['process_peak_rss_bytes'],monitor['sampled_peak_rss_bytes'])<=prep['static_preparation']['rss_ceiling_bytes']
        static_wall+=monitor['wall_seconds']
    assert static_wall<prep['static_preparation']['total_wall_seconds']
    assert previous<manifest['frozen_at_utc']
    failed=[]
    for directory in ['runs/campaign-003','runs/campaign-003-amendment-002']:
        assert not (ROOT/directory/'manifest.json').exists()
        assert not (ROOT/directory/'trials.jsonl').exists()
        assert not (ROOT/directory/'raw').exists()
        failure=read(directory+'/freeze_failure.json')
        assert failure['recorded_at_utc']<manifest['frozen_at_utc']
        failed.append({'path':directory+'/freeze_failure.json','sha256':sha(directory+'/freeze_failure.json'),'recorded_at_utc':failure['recorded_at_utc']})
    binding3=read('prepared/campaign-003/binding-amendment-003.json')
    assert binding3['validated_at_utc']<manifest['frozen_at_utc']<rows[0]['started_at_utc']
    constants={'constant_factor','independent_of_first_axis','independent_of_second_axis'}
    for m in manifest['models']:
        for rep in m['representations']:
            proof=read('prepared/campaign-003/proofs/'+m['model_id']+'__'+rep['representation_id']+'.json')
            kinds={t['kind'] for t in proof['pipeline']['algebra_transformations']}
            assert kinds<=constants|{'exact_binary_rational_additive_split'}
            expected='unchanged' if not kinds else 'exact_constant_scope' if kinds<=constants else 'exact_separable' if kinds=={'exact_binary_rational_additive_split'} else 'multiple_exact'
            assert rep['simplification']==expected
    outcome = Counter(r['status'] for r in rows)
    grouped = defaultdict(Counter)
    for r in rows:
        grouped[bymodel[r['model_id']]['cohort']][r['status']] += 1
    result = {
        'bundle': {'path': bundle_path, 'sha256': sha(bundle_path), 'files': len(inventory), 'bytes': total_bytes, 'all_match': True},
        'grader_records': freezes,
        'manifest_sha256': mhash, 'preparation_manifest_sha256': sha('prepared/campaign-003/preparation_manifest.json'),
        'schemas_pass': True, 'planned_observed': len(rows), 'missing_duplicate_or_extra': 0,
        'original_targets_and_prospective_fields_unchanged': True, 'implementation_hashes_checked': implementation_checks,
        'accuracy_wording_difference_paths': accuracy_wording_diff,
        'accuracy_wording_interpretation': 'Final frozen driver rewrites descriptive contract prose; same exact-zero rule and tolerance formula. This is not literal byte equality of contract descriptions. Actual acceptance calculations audited separately.',
        'catalog_amendment002_diff_paths': change2, 'catalog_amendment003_diff_paths': change3,
        'additional_catalog_metadata': 'Both corrected catalogs also append source_inventory and exposure_ledger records and add/update the format_amendment pointer. These are provenance additions beyond the literal field-only wording; prior entries and every computational value remain unchanged.',
        'full_corrected_fixture_schema_passes': True, 'schema_diagnostics_shape': type(errors).__name__,
        'preparation_rows': len(ledger), 'preparation_first_row_keys': list(ledger[0]),
        'static_preparation_wall_seconds_sum':static_wall,'static_preparation_first_start':ledger[0]['monitor']['started_at_utc'],'static_preparation_last_finish':previous,
        'both_failed_freezes_have_zero_recorded_trials_or_execution_manifest':True,'failed_freeze_records':failed,
        'failed_candidate_independent_schema_errors':len(independent_errors),'failed_candidate_error_scope':'All 24 paths terminate in simplification; no other schema errors.',
        'binding003_validated_at_utc':binding3['validated_at_utc'],'all_enum_classes_reproduced_from_proof_kinds':True,
        'chronology_limit':'Stored timestamps, immutable artifacts and code paths support ordering; no external trusted timestamp or exhaustive historical process log certifies absence of undisclosed prior work. Failure recorded_at times are record creation, not exact exception times.',
        'raw_outputs_and_sidecars_reconciled': sidecars, 'observed_rss_over_ceiling': rss_over,
        'outcomes': dict(outcome), 'outcomes_by_cohort': {k: dict(v) for k,v in grouped.items()},
        'first_trial_start': rows[0]['started_at_utc'], 'last_trial_finish': rows[-1]['finished_at_utc'],
        'sum_trial_wall_seconds': sum(r['timing']['wall_seconds'] for r in rows),
        'all_trials_sequential_chronology': True,
    }
    (OUT/'integrity_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['bundle','planned_observed','raw_outputs_and_sidecars_reconciled','outcomes','outcomes_by_cohort','sum_trial_wall_seconds']},indent=2))


if __name__ == '__main__':
    audit()
