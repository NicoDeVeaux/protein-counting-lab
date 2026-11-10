#!/usr/bin/env python3
"""Execute the frozen model-transfer panel and journal every state attempt."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import signal
import sys
import time
import zipfile

from experiments.energy_recovery5.java_matrix import decode
from experiments.rigid_affinity5.core import enumerate_state, relative_scores


def append(path, record):
    with path.open('a') as stream:
        stream.write(json.dumps(record, allow_nan=False) + '\n')
        stream.flush()


def timeout_handler(signum, frame):
    raise TimeoutError('State or remaining campaign wall timer expired')


def main(activation_path):
    started = time.monotonic()
    cpu_started = time.process_time()
    activation = json.loads(activation_path.read_text())
    for entry in activation['files']:
        assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']
    plan = json.loads(Path(activation['plan']).read_text())
    output = Path(activation['output'])
    output.mkdir(parents=True, exist_ok=False)
    versions = {'python': sys.version, 'platform': platform.platform(),
                'numpy': importlib.metadata.version('numpy')}
    (output/'startup.json').write_text(json.dumps({'versions': versions,
         'activation_sha256': hashlib.sha256(activation_path.read_bytes()).hexdigest(),
         'started_at_unix': time.time()}, indent=2)+'\n')
    matrices = {}
    count = 0
    signal.signal(signal.SIGALRM, timeout_handler)
    with zipfile.ZipFile(activation['archive']) as archive:
        for query in plan['selected_unique_variants']:
            if query['status'] != 'admitted':
                continue
            values = {'wild_type': {}, 'mutant': {}}
            failed = False
            for slot in query['slots']:
                row = {'variant': query['variant'], 'config_member': query['config_member'],
                       **slot, 'started_after_seconds': time.monotonic()-started}
                append(output/'attempts.jsonl', {**row, 'status': 'started'})
                slot_started, slot_cpu = time.monotonic(), time.process_time()
                try:
                    if time.monotonic()-started > activation['total_seconds']:
                        raise TimeoutError('Total scoring wall guard exceeded')
                    remaining = activation['total_seconds'] - (time.monotonic()-started)
                    signal.setitimer(signal.ITIMER_REAL, min(activation['state_seconds'], remaining))
                    member = slot['matrix_member']
                    if member not in matrices:
                        raw = archive.read(member)
                        assert hashlib.sha256(raw).hexdigest() == slot['matrix_sha256']
                        matrices[member] = decode(raw)
                    result = enumerate_state(matrices[member], slot['domains'],
                                             activation['rt_decimal'], cap=activation['state_cap'])
                    assert result['assignments'] == slot['assignments']
                    elapsed = time.monotonic()-slot_started
                    if elapsed > activation['state_seconds']:
                        raise TimeoutError('State wall guard exceeded')
                    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    if sys.platform != 'darwin':
                        peak *= 1024
                    if peak > activation['rss_bytes']:
                        raise MemoryError('Observed worker lifetime RSS guard exceeded')
                    row.update(status='complete', result=result, wall_seconds=elapsed,
                               cpu_seconds=time.process_time()-slot_cpu,
                               worker_lifetime_peak_rss_bytes=peak,
                               finished_after_seconds=time.monotonic()-started)
                    values[slot['version']][slot['state']] = result
                    count += result['assignments']
                except Exception as error:
                    row.update(status='failed', error_type=type(error).__name__, error=str(error),
                               wall_seconds=time.monotonic()-slot_started)
                    failed = True
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                append(output/'states.jsonl', row)
            score_error = None
            try:
                scores = None if failed else relative_scores(values['mutant'], values['wild_type'])
            except Exception as error:
                failed, scores = True, None
                score_error = {'type': type(error).__name__, 'message': str(error)}
            append(output/'queries.jsonl', {'variant': query['variant'], 'source_row': query['source_row'],
                    'config_member': query['config_member'],
                    'status': 'failed' if failed else 'complete', 'scores': scores,
                    'score_error': score_error})
    (output/'completion.json').write_text(json.dumps({'assignments': count,
        'wall_seconds': time.monotonic()-started, 'cpu_seconds': time.process_time()-cpu_started,
        'finished_at_unix': time.time(), 'inference_cache_reuse': False,
        'rss_scope': 'Worker self lifetime high-water after each state; not instantaneous enforcement.'},
        indent=2)+'\n')
    print(json.dumps({'output': str(output), 'assignments': count,
                      'wall_seconds': time.monotonic()-started}))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
