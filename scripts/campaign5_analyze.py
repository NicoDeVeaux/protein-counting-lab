#!/usr/bin/env python3
"""Apply the prospectively frozen mechanistic and contextual analysis rules."""

import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np


def ranks(values):
    values = np.asarray(values, dtype=float)
    return 1 + np.sum(values[..., None, :] < values[..., :, None], axis=-1) + 0.5 * (
        np.sum(values[..., None, :] == values[..., :, None], axis=-1)-1)


def correlation(x, y):
    x, y = ranks(x), ranks(y)
    x = x - np.mean(x, axis=-1, keepdims=True)
    y = y - np.mean(y, axis=-1, keepdims=True)
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.sum(x*y, axis=-1)/np.sqrt(np.sum(x*x, axis=-1)*np.sum(y*y, axis=-1))


def interval(values):
    finite = np.asarray(values)[np.isfinite(values)]
    return {'percentile_95': np.quantile(finite, [0.025, 0.975]).tolist() if len(finite) else None,
            'defined_resamples': len(finite), 'undefined_resamples': len(values)-len(finite)}


def contextual_stats(points, seed):
    y = np.asarray([p['observed_log_relative_binding'] for p in points])
    predictions = {method: np.asarray([p['scores'][f'delta_log_k_{method}'] for p in points])
                   for method in ('ensemble', 'gmec')}
    n = len(y)
    rng = np.random.default_rng(seed)
    permutations = (np.asarray(list(itertools.permutations(range(n))), dtype=int) if n <= 9
                    else np.asarray([rng.permutation(n) for _ in range(10000)]))
    indexes = rng.integers(0, n, size=(10000, n))
    output, boots = {}, {}
    for method, x in predictions.items():
        rho = float(correlation(x, y))
        null = correlation(x, y[permutations])
        extreme = int(np.count_nonzero(np.abs(null) >= abs(rho)-1e-12))
        boots[method] = correlation(x[indexes], y[indexes])
        output[method] = {'n': n, 'spearman_rho': rho,
                          'nominal_two_sided_permutation_p': extreme / len(permutations),
                          'permutations': len(permutations), 'bootstrap': interval(boots[method])}
    output['paired_rho_difference_bootstrap'] = interval(boots['ensemble']-boots['gmec'])
    output['qualification'] = ('Model-transfer context, relative radioactivity rather than Kd. '
        'Variant bootstrap and nominal permutation assume exchangeability; correlated small panel '
        'does not establish a biological winner or generalization.')
    return output


def direction(value, allowance):
    return 'positive' if value > allowance else 'negative' if value < -allowance else 'unresolved'


def main():
    root = Path.cwd()
    activation_path = root/'prepared/campaign-005/ACTIVATION.json'
    activation = json.loads(activation_path.read_text())
    analysis_plan = json.loads(Path(activation['analysis_plan']).read_text())
    queries_path = root/'runs/campaign-005/queries.jsonl'
    queries = [json.loads(line) for line in queries_path.read_text().splitlines()]
    labels_path = root/'data/campaign-005/source_discovery/kras_S2_labels.json'
    labels = {r['source_row']: r for r in json.loads(labels_path.read_text())['rows']}
    points = []
    for q in queries:
        label = labels[q['source_row']]
        point = {**q, 'experimental_relative_binding_percent_raw': label['experimental_relative_binding_percent_raw'],
                 'experimental_kd_um_raw': label['experimental_kd_um_raw'],
                 'measurement_error': 'unknown, not supplied in S2',
                 'stratum': 'unmapped-Kd-context' if label['experimental_kd_um_raw'] else 'Fridman-relative-binding-transfer'}
        if q['status'] == 'complete':
            point['observed_log_relative_binding'] = math.log(float(label['experimental_relative_binding_percent_raw'])/100)
            point['directions'] = {m: direction(q['scores'][f'delta_log_k_{m}'], 1e-7)
                                   for m in ('ensemble', 'gmec')}
            point['resolved_direction_reversal'] = set(point['directions'].values()) == {'positive', 'negative'}
        points.append(point)
    complete = [p for p in points if p['status'] == 'complete']
    orders = []
    for a, b in itertools.combinations(complete, 2):
        signs = {m: direction(a['scores'][f'delta_log_k_{m}']-b['scores'][f'delta_log_k_{m}'], 2e-7)
                 for m in ('ensemble', 'gmec')}
        status = ('unresolved' if 'unresolved' in signs.values() else
                  'reversed' if len(set(signs.values())) == 2 else 'concordant')
        orders.append({'variants': [a['variant'], b['variant']], 'directions': signs, 'status': status})
    fridman = [p for p in complete if p['stratum'] == 'Fridman-relative-binding-transfer']
    result = {'scope': activation['scope'], 'primary': {
        'variants_scheduled': activation['expected_variants'], 'variants_complete': len(complete),
        'direction_reversals': sum(p['resolved_direction_reversal'] for p in complete),
        'pairwise_order_status': {s: sum(o['status']==s for o in orders) for s in ('concordant', 'reversed', 'unresolved')},
        'ensemble_correction_range': [min(p['scores']['delta_log_k_ensemble_correction'] for p in complete),
                                      max(p['scores']['delta_log_k_ensemble_correction'] for p in complete)]},
        'points': points, 'pairwise_orders': orders,
        'Fridman_relative_binding_context': contextual_stats(fridman, analysis_plan['statistics']['seed']),
        'Kd_context': {'n': len(complete)-len(fridman), 'inferential_statistics': None,
                      'reason': 'Original row-specific assay mapping unresolved; fewer than six points.'},
        'inputs': [{'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                   for p in (activation_path, queries_path, labels_path, Path(activation['analysis_plan']).resolve())]}
    out=root/'outputs/campaign-005-analysis.json'
    with out.open('x') as f: json.dump(result, f, indent=2, allow_nan=False);f.write('\n')
    print(json.dumps({'primary':result['primary'],'Fridman':result['Fridman_relative_binding_context']},indent=2))


if __name__ == '__main__':
    main()
