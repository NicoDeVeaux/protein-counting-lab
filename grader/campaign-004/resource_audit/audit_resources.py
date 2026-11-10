"""Independently reconcile sealed campaign004 records without production imports."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import struct


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ISSUES = []


def read(path):
    return json.loads((ROOT / path).read_text())


def lines(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines()]


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def check(value, message):
    if not value:
        ISSUES.append(message)


def verify(items, label):
    check(len({item['path'] for item in items}) == len(items), label + ': duplicate paths')
    for item in items:
        path = ROOT / item['path']
        check(path.is_file(), label + ': missing ' + item['path'])
        if path.is_file():
            check(digest(item['path']) == item['sha256'], label + ': hash ' + item['path'])
            if 'bytes' in item:
                check(path.stat().st_size == item['bytes'], label + ': size ' + item['path'])


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def fingerprint(model):
    hashed = hashlib.sha256(b'campaign003-numerical-target-v1\0')

    def integers(values):
        hashed.update(struct.pack('>Q', len(values)))
        for value in values:
            hashed.update(struct.pack('>Q', value))

    def shape(value):
        if not isinstance(value, list):
            return []
        dimensions = [len(value)]
        if value:
            child = shape(value[0])
            check(all(shape(item) == child for item in value), 'ragged factor')
            dimensions += child
        return dimensions

    def flattened(value):
        if isinstance(value, list):
            for item in value:
                yield from flattened(item)
        else:
            yield -math.inf if value in (None, '-inf') else float(value)

    integers(model['domains'])
    hashed.update(struct.pack('>Q', len(model['factors'])))
    for factor in model['factors']:
        integers(factor['scope'])
        dimensions = shape(factor['log_values'])
        check(dimensions == [model['domains'][i] for i in factor['scope']], 'factor dimensions')
        integers(dimensions)
        for value in flattened(factor['log_values']):
            hashed.update(struct.pack('<d', value))
    return hashed.hexdigest()


def span(values):
    return {'minimum': min(values), 'maximum': max(values), 'median': statistics.median(values),
            'max_over_min': max(values) / min(values)}


def main():
    bundle_path = 'runs/campaign-004-review/bundle_manifest.json'
    bundle = read(bundle_path)
    verify(bundle['files'], 'bundle')
    prior = read('runs/campaign-003-review/bundle_manifest.json')
    verify(prior['files'], 'prior003')
    index = {item['path']: item for item in bundle['files']}
    absent_prior = [item['path'] for item in prior['files'] if item['path'] not in index]
    changed_prior = [item['path'] for item in prior['files'] if item['path'] in index and index[item['path']]['sha256'] != item['sha256']]
    check(not absent_prior and not changed_prior, 'prior003 missing or changed within004 bundle')

    prep_path = 'prepared/campaign-004/preparation_manifest.json'
    final_path = 'runs/campaign-004/manifest.json'
    prep, final = read(prep_path), read(final_path)
    for path in (prep_path, final_path, 'grader/campaign-004/FREEZE.json'):
        sidecar = str(Path(path).with_suffix('.sha256'))
        check((ROOT / sidecar).read_text().split()[0] == digest(path), path + ' seal')
    verify(read('grader/campaign-004/FREEZE.json')['files'], 'grader freeze')
    verify(prep['implementation_inventory'], 'implementation inventory')
    verify(final['file_inventory'], 'final inventory')
    verify([prep['source_manifest'], prep['preflight_validation'], prep['comparator_audit'], prep['grader_freeze']], 'prep identities')
    verify([final['preparation_manifest'], final['reference_artifact'], final['preparation_ledger']], 'final identities')
    shared = set(prep) - {'phase', 'frozen_at_utc'}
    check(all(prep[key] == final[key] for key in shared), 'scientific choices/prep-to-final fields changed')
    check(set(final) - set(prep) == {'preparation_manifest', 'references', 'reference_artifact', 'targets', 'preparation_ledger', 'file_inventory'}, 'unexpected final manifest additions')

    # Reconstruct the prospective fixed schedule without invoking its generator.
    expected_panels = []
    rng = random.Random(2026110604)
    for repeat in range(3):
        order = [entry['sequence_id'] for entry in prep['pilot']['sequences']]
        rng.shuffle(order)
        methods = ['ve', 'batch']
        rng.shuffle(methods)
        for method in methods:
            arms = ['simplified', 'propagated']
            rng.shuffle(arms)
            for arm in arms:
                expected_panels.append({'panel_id': f'p{len(expected_panels):03d}', 'block_id': f'r{repeat}-{method}',
                    'repeat': repeat, 'method': method, 'arm': arm, 'query_order': list(order)})
    check(expected_panels == prep['panels'], 'schedule differs from seed')
    expected_slots = [{'slot_id': f"{panel['panel_id']}/{sequence_id}/{state}", 'panel_id': panel['panel_id'],
        'case_id': prep['pilot']['case_id'], 'sequence_id': sequence_id, 'state': state,
        'method': panel['method'], 'arm': panel['arm'], 'repeat': panel['repeat'], 'profile': 'common20s-512MiB-16MiB'}
        for panel in expected_panels for sequence_id in panel['query_order'] for state in ['complex', 'protein', 'ligand']]
    check(expected_slots == prep['slots'], 'declared state slot schedule')

    panels, queries, states = (lines('runs/campaign-004/' + name + '.jsonl') for name in ('panels', 'queries', 'states'))
    check(len(panels) == len({p['panel']['panel_id'] for p in panels}) == 12, 'panel count/duplicates')
    check([p['panel'] for p in panels] == expected_panels, 'observed panel identities/order')
    check(len(queries) == len({(q['panel_id'], q['sequence_id']) for q in queries}) == 252, 'query count/duplicates')
    check([(q['panel_id'], q['sequence_id']) for q in queries] == [(p['panel_id'], s) for p in expected_panels for s in p['query_order']], 'observed query order')
    check(len(states) == len({s['slot_id'] for s in states}) == 756, 'state count/duplicates')
    check([{key:state[key] for key in expected} for state, expected in zip(states, expected_slots)] == expected_slots, 'observed state identities/order')
    check(queries == [q for p in panels for q in p['query_results']], 'query ledger vs panel records')
    expected_raw = {f"runs/campaign-004/raw/{p['panel_id']}.json" + suffix for p in expected_panels
                    for suffix in ['', '.stdout.txt', '.stderr.txt', '.timing.json', '.progress.jsonl']}
    actual_raw = {str(p.relative_to(ROOT)) for p in (ROOT / 'runs/campaign-004/raw').iterdir() if p.is_file()}
    check(actual_raw == expected_raw, 'unexpected/missing raw attempt files')
    check({p.name for p in (ROOT/'runs/campaign-004/records').iterdir()} == {p['panel_id']+'.json' for p in expected_panels}, 'unexpected/missing record attempts')

    model_checks = 0
    for sequence_id, arms in final['targets'].items():
        for arm, targets in arms.items():
            for state, expected in targets.items():
                check(fingerprint(read(f'prepared/campaign-004/models/{sequence_id}__{arm}__{state}.json')) == expected,
                      f'prepared target fingerprint {sequence_id}/{arm}/{state}')
                model_checks += 1

    state_index = {(s['panel_id'], s['sequence_id'], s['state']): s for s in states}
    panel_rows, cache_count, direct_count, previous_finish = [], 0, 0, None
    for record in panels:
        panel = record['panel']; pid = panel['panel_id']; monitor = record['monitor']
        check(record == read(f'runs/campaign-004/records/{pid}.json'), 'record JSON vs ledger ' + pid)
        verify(record['artifacts'], pid + ' artifacts')
        raw = read(f'runs/campaign-004/raw/{pid}.json')
        timing = read(f'runs/campaign-004/raw/{pid}.json.timing.json')
        check(record['timing_sidecar'] == timing, 'timing sidecar vs record ' + pid)
        check(raw['queries'] == lines(f'runs/campaign-004/raw/{pid}.json.progress.jsonl'), 'journal vs raw ' + pid)
        check([q['sequence_id'] for q in raw['queries']] == panel['query_order'], 'raw query order ' + pid)
        check(raw['manifest_sha256'] == digest(final_path), 'worker manifest identity ' + pid)
        check(raw['archive_sha256'] == prep['pilot']['archive']['sha256'], 'worker archive identity ' + pid)
        check(all(raw[key] == panel[key] for key in ('panel_id', 'method', 'arm', 'repeat')), 'raw panel identity ' + pid)
        check(monitor['exit_code'] == 0 and monitor['termination_reason'] is None and record['status'] == 'complete', 'panel completion ' + pid)
        check(raw['source_status'] == 'loaded' and raw['source_load_seconds'] < 5, 'source load completion ' + pid)
        check(monitor['wall_seconds'] < 20, 'panel outer wall cap ' + pid)
        check(utc(monitor['started_at_utc']) >= utc(final['frozen_at_utc']), 'worker before execution freeze ' + pid)
        check(utc(monitor['started_at_utc']) <= utc(raw['started_at_utc']) <= utc(raw['finished_at_utc']) <= utc(monitor['finished_at_utc']), 'worker clock containment ' + pid)
        if previous_finish is not None:
            check(utc(monitor['started_at_utc']) >= previous_finish, 'overlapping workers ' + pid)
        previous_finish = utc(monitor['finished_at_utc'])
        peak = max(monitor['sampled_peak_rss_bytes'], raw['worker_peak_rss_before_result'], timing['worker_peak_rss_after_result'])
        check(peak == record['whole_peak_rss_bytes'] and peak < 512*1024**2, 'whole peak/cap ' + pid)
        check(0 <= raw['cold_worker_seconds_before_result'] <= timing['cold_worker_seconds_through_result'] <= monitor['wall_seconds'], 'nested worker scope ' + pid)
        check(0 <= timing['serialization_seconds'] <= timing['cold_worker_seconds_through_result'], 'serialization scope ' + pid)
        check(raw['source_load_seconds'] + sum(q['wall_seconds'] for q in raw['queries']) <= raw['cold_worker_seconds_before_result'], 'sum of query phases ' + pid)
        check(sum(q['cpu_seconds'] for q in raw['queries']) + raw['source_load_cpu_seconds'] <= raw['cold_worker_cpu_seconds_before_result'] + 1e-9, 'sum query CPU phases ' + pid)
        known = {}; cached = []; direct = []; state_table_estimates = []
        for query in raw['queries']:
            check(utc(raw['started_at_utc']) <= utc(query['started_at_utc']) <= utc(query['finished_at_utc']) <= utc(raw['finished_at_utc']), 'query clock containment ' + pid)
            check(query['score']['status'] == 'finite', 'nonfinite query ' + pid)
            for state, entry in query['states'].items():
                identity = (pid, query['sequence_id'], state)
                check(entry == state_index[identity]['raw'], 'state raw ledger mismatch ' + str(identity))
                check(entry['status'] == 'complete' and state_index[identity]['validation']['status'] == 'pass', 'state completion ' + str(identity))
                check(entry['target_sha256'] == final['targets'][query['sequence_id']][panel['arm']][state], 'runtime prepared target fingerprint ' + str(identity))
                check(utc(query['started_at_utc']) <= utc(entry['started_at_utc']) <= utc(entry['finished_at_utc']) <= utc(query['finished_at_utc']), 'state clock containment ' + str(identity))
                check(int(entry['input_state_count']) <= 20_000_000, 'state Cartesian cap ' + str(identity))
                if entry.get('cache_hit'):
                    origin = entry['cache_origin']; key = (origin['sequence_id'], origin['state'])
                    check(key in known, 'nonpreceding cache origin ' + str(identity))
                    if key in known:
                        prior_entry = known[key]
                        check(not prior_entry.get('cache_hit') and prior_entry['status'] == 'complete', 'cache origin not direct completion ' + str(identity))
                        check(prior_entry['target_sha256'] == entry['target_sha256'] and prior_entry['log_z'] == entry['log_z'], 'cache target/value mismatch ' + str(identity))
                    check(entry['solver_call_seconds'] == entry['solver_call_cpu_seconds'] == 0, 'cache solver time ' + str(identity))
                    cached.append('/'.join(identity[1:])); cache_count += 1
                else:
                    direct.append('/'.join(identity[1:])); direct_count += 1
                    metrics = entry['metrics']
                    estimates = [value for key,value in metrics.items() if key in
                        ('peak_table_bytes', 'estimated_peak_live_array_bytes', 'estimated_peak_batch_array_bytes')]
                    state_table_estimates.extend(estimates)
                    check(entry['solver_call_seconds'] >= 0 and entry['solver_call_cpu_seconds'] >= 0, 'negative solver time ' + str(identity))
                check(entry['propagation_seconds'] + entry['simplification_seconds'] <= entry['preparation_seconds'] + 1e-8, 'nested preparation phases ' + str(identity))
                known[(query['sequence_id'], state)] = entry
        qresults = record['query_results']
        check(all(q['validation']['status'] == 'success' and q['panel_status'] == 'complete' for q in qresults), 'query success status ' + pid)
        check(record['accepted_scores_under_panel_policy'] == len(qresults) == 21, 'accepted coverage ' + pid)
        check(len(cached) == 20 and len(direct) == 43, 'unexpected cache/direct count ' + pid)
        panel_rows.append({'panel_id': pid, 'method': panel['method'], 'arm': panel['arm'], 'repeat': panel['repeat'],
            'wall_seconds': monitor['wall_seconds'], 'cpu_seconds': monitor['cpu_seconds'],
            'whole_peak_rss_bytes': peak, 'sampled_peak_rss_bytes': monitor['sampled_peak_rss_bytes'],
            'worker_peak_before_result': raw['worker_peak_rss_before_result'], 'worker_peak_after_result': timing['worker_peak_rss_after_result'],
            'rss_samples': monitor['rss_samples'], 'sampling_errors': monitor['sampling_errors'],
            'source_load_seconds': raw['source_load_seconds'], 'source_load_cpu_seconds': raw['source_load_cpu_seconds'],
            'conditioning_seconds_sum': sum(q['conditioning_seconds'] for q in raw['queries']),
            'query_wall_seconds_sum': sum(q['wall_seconds'] for q in raw['queries']),
            'preparation_seconds_sum': sum(s['preparation_seconds'] for q in raw['queries'] for s in q['states'].values()),
            'solver_seconds_sum': sum(s['solver_call_seconds'] for q in raw['queries'] for s in q['states'].values()),
            'cold_worker_seconds_before_result': raw['cold_worker_seconds_before_result'],
            'serialization_seconds': timing['serialization_seconds'], 'controller_seconds': record['controller_seconds'],
            'cache_hits': len(cached), 'direct_calls': len(direct), 'cached_slots': cached,
            'host_load_average_after': record['system_load_average_after'], 'table_estimates_bytes_max': max(state_table_estimates) if state_table_estimates else None})

    stages = lines('prepared/campaign-004/preparation.jsonl')
    expected_stage_ids = ['audit-' + c['case_id'] for c in prep['cases']] + ['prepare-panel','independent-references','verify-targets']
    check([stage['identity'] for stage in stages] == expected_stage_ids, 'preparation stage count/order')
    check(all(stage['status'] == 'completed' for stage in stages), 'preparation failures')
    stage_caps = [30]*14 + [120, 310, 60]
    last_end = utc(prep['frozen_at_utc'])
    for stage, cap in zip(stages, stage_caps):
        monitor = stage['monitor']
        check(utc(monitor['started_at_utc']) >= last_end, 'preparation overlap/pre-freeze ' + stage['identity'])
        last_end = utc(monitor['finished_at_utc'])
        check(monitor['wall_seconds'] < cap and monitor['sampled_peak_rss_bytes'] < 512*1024**2, 'preparation cap ' + stage['identity'])
        check(monitor['exit_code'] == 0 and monitor['termination_reason'] is None, 'preparation completion ' + stage['identity'])
        verify(stage['logs'], stage['identity'] + ' logs')
    check(last_end <= utc(final['frozen_at_utc']), 'execution freeze before preparation completion')
    prep_complete = read('prepared/campaign-004/preparation_completion.json')
    complete = read('runs/campaign-004/completion.json')
    check(prep_complete['all_required_stages_completed'] and prep_complete['elapsed_seconds'] < 900, 'preparation total')
    check(complete['elapsed_seconds'] < 300, 'measurement campaign total')
    refs_status = read('prepared/campaign-004/reference_slot_status.json')
    check(len(refs_status) == len({(s['sequence_id'], s['state']) for s in refs_status}) == 63, 'reference ledger identities')
    check(all(s['status'] == 'reference-passing success' for s in refs_status), 'reference ledger failures')
    summary = read('runs/campaign-004/summary.json')
    check(summary['planned_queries'] == len(queries) and summary['planned_state_slots'] == len(states), 'summary coverage')
    check(summary['correct_scores'] == sum(q['validation']['status']=='success' for q in queries), 'summary successes')
    check(summary['controller_seconds'] == sum(p['controller_seconds'] for p in panels), 'summary controller sum')

    comparisons = {}
    for method in ('batch', 've'):
        arm_stats = {}
        paired = []
        for arm in ('simplified', 'propagated'):
            rows = [p for p in panel_rows if p['method'] == method and p['arm'] == arm]
            arm_stats[arm] = {key: span([row[key] for row in rows]) for key in ('wall_seconds','cpu_seconds','whole_peak_rss_bytes')}
            arm_stats[arm]['repeat2_over_repeat0_wall'] = rows[2]['wall_seconds'] / rows[0]['wall_seconds']
        for repeat in range(3):
            left = next(p for p in panel_rows if p['method']==method and p['arm']=='simplified' and p['repeat']==repeat)
            right = next(p for p in panel_rows if p['method']==method and p['arm']=='propagated' and p['repeat']==repeat)
            order = [p['arm'] for p in panel_rows if p['method']==method and p['repeat']==repeat]
            paired.append({'repeat':repeat, 'arm_order':order, 'baseline_over_pruned_wall':left['wall_seconds']/right['wall_seconds'],
                'baseline_over_pruned_cpu':left['cpu_seconds']/right['cpu_seconds'], 'baseline_over_pruned_whole_peak':left['whole_peak_rss_bytes']/right['whole_peak_rss_bytes']})
        comparisons[method] = {'arms':arm_stats,'paired_ratios':paired}

    result = {'completed_at_utc':datetime.now(timezone.utc).isoformat(), 'all_invariants_pass':not ISSUES, 'issues':ISSUES,
        'bundle':{'path':bundle_path,'sha256':digest(bundle_path),'files':len(bundle['files']),'bytes':sum(item['bytes'] for item in bundle['files']),
                  'all_hashes_match':not any('hash ' in issue or 'missing ' in issue for issue in ISSUES)},
        'prior003':{'files':len(prior['files']),'all_rechecked':True,'absent_from004':absent_prior,'changed_within004':changed_prior},
        'preparation_manifest_sha256':digest(prep_path),'execution_manifest_sha256':digest(final_path),
        'ledger':{'panels':len(panels),'queries':len(queries),'state_slots':len(states),'reference_slots':len(refs_status),
                  'prepared_numeric_fingerprints_checked':model_checks,'cache_hits':cache_count,'direct_solver_calls':direct_count,
                  'panel_statuses':dict(Counter(p['status'] for p in panels)), 'query_statuses':dict(Counter(q['validation']['status'] for q in queries)),
                  'state_statuses':dict(Counter(s['raw']['status'] for s in states)), 'reference_statuses':dict(Counter(s['status'] for s in refs_status))},
        'chronology':{'grader_freeze':read('grader/campaign-004/FREEZE.json')['frozen_at_utc'],'preparation_freeze':prep['frozen_at_utc'],
                      'first_static_stage':stages[0]['monitor']['started_at_utc'],'last_static_stage':stages[-1]['monitor']['finished_at_utc'],
                      'execution_freeze':final['frozen_at_utc'],'first_measurement':panels[0]['monitor']['started_at_utc'],
                      'last_measurement':panels[-1]['monitor']['finished_at_utc'],'bundle_freeze':bundle['frozen_at_utc'],
                      'shared_prep_final_fields_equal':all(prep[k]==final[k] for k in shared),'exposure':prep['exposure'],
                      'qualification':'Source grammar/numeric prefix inspection preceded preparation freeze; disclosed as preflight, no new conditioned partition/rank outcome established. Local timestamps/seals do not certify absence of undisclosed work.'},
        'costs':{'static_stage_wall_seconds_sum':sum(s['monitor']['wall_seconds'] for s in stages),
                 'static_elapsed_seconds':prep_complete['elapsed_seconds'],'reference_outer_wall_seconds':stages[15]['monitor']['wall_seconds'],
                 'panel_preparation_outer_wall_seconds':stages[14]['monitor']['wall_seconds'],
                 'measurement_outer_wall_seconds_sum':sum(p['wall_seconds'] for p in panel_rows),
                 'measurement_outer_cpu_seconds_sum':sum(p['cpu_seconds'] for p in panel_rows),
                 'measurement_campaign_elapsed_seconds':complete['elapsed_seconds'],
                 'premeasurement_validation_seconds':complete['premeasurement_validation_seconds'],
                 'controller_seconds_sum':sum(p['controller_seconds'] for p in panel_rows),
                 'unassigned_campaign_seconds':complete['elapsed_seconds']-sum(p['wall_seconds'] for p in panel_rows)-complete['premeasurement_validation_seconds']-sum(p['controller_seconds'] for p in panel_rows)},
        'comparisons':comparisons, 'panel_rows':panel_rows,
        'scope_qualifications':[
            'Cold means fresh worker with raw ZIP parse included; operating-system file/page caches were not flushed.',
            'Outer row wall includes spawn/imports, manifest read, source parse, conditioning, propagation/simplification/fingerprint, inference or declared cache reuse, ratio, journals/result/sidecar/stdout and reaping. Internal cold_worker clock starts after imports/manifest read.',
            'Controller hash/reference validation and ledger writing occur after row timer and remain in campaign elapsed; controller_seconds stops before own record/ledger write.',
            'Two resource caps are policies:16MiB counts estimated table/batch-array storage,20M state cap is checked by batch enumeration; VE uses table and wall policy. All recorded Cartesian state counts are below20M.',
            'Worker lifetime high-water includes source parsing and serialization and is cumulative across queries, not per-query memory. Sampled RSS is process-tree summed; no instantaneous ceiling guaranteed.',
            'Nominal10ms sampling sleep is not achieved cadence; observations have no sample timestamps. No overshoot occurred; no ceiling guarantee follows.',
            'Cache is per fresh worker,20 repeated identical protein targets reused and43 direct solves; conditioning/transform/fingerprint repeated and charged for all63 slots. No cross-worker cache observed in code or ledger.',
            'Three paired repetitions per method on one selected model and fixed panel give local costs only. Both arms full21coverage; no coverage gain. No domain comparator or biological validation executed.',
            'Frozen random schedule places pruned first in all three batch pairs. Batch direction is repeat-consistent but lacks order balance. VE includes both orders and pruned is slower in all three pairs.',
            'Imported package versions are declared at preparation freeze; each worker does not separately report import versions. No source/algorithm choice changed between stored preparation and final manifests.',
            'Audit checks sealed evidence and code paths rather than externally trusted timestamps or exhaustive historical process logs.'
        ]}
    (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pass':result['all_invariants_pass'],'issues':ISSUES,'ledger':result['ledger'],'costs':result['costs'],'comparisons':comparisons},indent=2))


if __name__ == '__main__':
    main()
