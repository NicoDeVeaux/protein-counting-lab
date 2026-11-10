"""Reconcile all unrounded state/ratio errors and rank decisions from sealed raw results."""

from collections import Counter
from decimal import Decimal, localcontext
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STATES = ('complex', 'protein', 'ligand')
SEMANTICS = ('stored_binary64_log', 'source_binary64', 'source_decimal_lexeme')


def read(path):
    return json.loads((ROOT / path).read_text())


def lines(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines()]


def audit():
    references = read('prepared/campaign-004/references.json')
    manifest = read('runs/campaign-004/manifest.json')
    refs = {}
    conversion_max = {name: Decimal(0) for name in SEMANTICS}
    precision_max = {name: Decimal(0) for name in SEMANTICS}
    for row in references['rows']:
        seq = f"s{row['panel_index']:02d}_{row['label']}"
        refs[seq] = {}
        for semantics in SEMANTICS:
            logs = {state: Decimal(row['states'][state]['values'][semantics]['logZ']) for state in STATES}
            assert all(value.is_finite() for value in logs.values())
            value = logs['complex'] - logs['protein'] - logs['ligand']
            score = row['scores'][semantics]
            assert score['status'] == 'finite' and Decimal(score['logKstar']) == value
            refs[seq][semantics] = value
            precision_max[semantics] = max(precision_max[semantics], abs(Decimal(score['precision_120_minus_90_logKstar'])))
            conversion_max[semantics] = max(conversion_max[semantics], abs(value - Decimal(row['scores']['source_binary64']['logKstar'])))
        assert manifest['references'][seq]['states'] == {
            state: row['states'][state]['values']['stored_binary64_log']['logZ'] for state in STATES}
        assert manifest['references'][seq]['score'] == row['scores']['stored_binary64_log']
    orders = {name: sorted(refs, key=lambda seq: refs[seq][name], reverse=True) for name in SEMANTICS}
    assert all(order == orders['stored_binary64_log'] for order in orders.values())
    primary = 'stored_binary64_log'
    order = orders[primary]
    gaps = [{'upper': a, 'lower': b, 'gap': str(refs[a][primary] - refs[b][primary])} for a, b in zip(order, order[1:])]
    minimum = min(gaps, key=lambda x: Decimal(x['gap']))
    eps = Decimal('3.03e-8')
    query_ledger = {(r['panel_id'], r['sequence_id']): r for r in lines('runs/campaign-004/queries.jsonl')}
    state_ledger = {(r['panel_id'], r['sequence_id'], r['state']): r for r in lines('runs/campaign-004/states.jsonl')}
    variants = {row['sequence_id']: row for row in manifest['pilot']['sequences']}
    panels = []
    state_errors, score_errors = [], []
    checked_states, checked_scores = set(), set()
    for planned in manifest['panels']:
        panel_id = planned['panel_id']
        panel = read('runs/campaign-004/raw/' + panel_id + '.json')
        assert panel['status'] == 'panel_record_complete'
        observed = {}
        for query in panel['queries']:
            seq = query['sequence_id']
            checked_scores.add((panel_id, seq))
            reference_row = references['rows'][int(seq[1:3])]
            assert reference_row['label'] == query['label']
            assert query['assignment'] == variants[seq]['assignment']
            assert query['assignment'] == {str(v): (int(seq[1:3]) if v == 3 else 0) for v in range(6)}
            logs = {}
            for state in STATES:
                raw = query['states'][state]
                assert raw['status'] in ('complete', 'complete_cached_exact_target')
                value = Decimal.from_float(raw['log_z'])
                target = Decimal(reference_row['states'][state]['values'][primary]['logZ'])
                error = abs(value - target)
                assert error <= Decimal('1e-8')
                ledger = state_ledger[(panel_id, seq, state)]
                assert ledger['raw'] == raw and ledger['validation']['status'] == 'pass'
                assert float(error) == ledger['validation']['absolute_log_error']
                state_errors.append(error)
                checked_states.add((panel_id, seq, state))
                logs[state] = raw['log_z']
            raw_score = query['score']
            assert raw_score['status'] == 'finite'
            assert raw_score['log_k'] == math.fsum((logs['complex'], -logs['protein'], -logs['ligand']))
            value = Decimal.from_float(raw_score['log_k'])
            error = abs(value - refs[seq][primary])
            assert error <= Decimal('3e-8')
            ledger = query_ledger[(panel_id, seq)]
            assert ledger['score'] == raw_score and ledger['validation']['status'] == 'success'
            assert float(error) == ledger['validation']['absolute_log_k_error']
            score_errors.append(error)
            observed[seq] = value
        assert set(observed) == set(refs)
        comparisons = Counter()
        for a, b in itertools.combinations(refs, 2):
            delta_ref, delta_observed = refs[a][primary] - refs[b][primary], observed[a] - observed[b]
            if abs(delta_ref) <= 2 * eps:
                comparisons['reference_uncertain'] += 1
            elif abs(delta_observed) <= 2 * eps:
                comparisons['observed_uncertain'] += 1
            else:
                comparisons['resolved'] += 1
                assert (delta_ref > 0) == (delta_observed > 0)
        observed_order = sorted(observed, key=observed.get, reverse=True)
        assert observed_order == order
        top = {}
        for k in (1, 3, 5):
            gap = refs[order[k-1]][primary] - refs[order[k]][primary]
            top[str(k)] = {'members': order[:k], 'boundary_gap': str(gap),
                           'reference_boundary_uncertain': gap <= 2 * eps,
                           'observed_boundary_uncertain': observed[observed_order[k-1]] - observed[observed_order[k]] <= 2 * eps}
            assert set(observed_order[:k]) == set(order[:k])
        panels.append({'panel_id': panel_id, 'method': panel['method'], 'arm': panel['arm'],
                       'repeat': panel['repeat'], 'full_panel': True,
                       'pairwise': dict(comparisons), 'top_k': top})
    assert checked_scores == set(query_ledger) and checked_states == set(state_ledger)
    result = {'reference_scores_recomputed': len(refs), 'state_outputs_recompared': len(state_errors),
              'query_outputs_recompared': len(score_errors), 'max_absolute_log_z_error': str(max(state_errors)),
              'max_absolute_log_k_error': str(max(score_errors)), 'nonfinite_or_undefined_scores': 0,
              'source_numerical_semantics_rank_identical': True,
              'max_log_k_conversion_difference_vs_source_binary64': {name: str(value) for name, value in conversion_max.items()},
              'max_log_k_precision120_minus90': {name: str(value) for name, value in precision_max.items()},
              'minimum_adjacent_reference_gap': minimum,
              'reference_order': [{'sequence_id': seq, 'log_k': str(refs[seq][primary])} for seq in order],
              'baseline_is_best_in_declared_panel': order[0] == 's00_LEU',
              'top1_gap': str(refs[order[0]][primary] - refs[order[1]][primary]),
              'panels': panels,
              'limits': ['Tolerance envelopes are numerical evidence, not directed intervals.',
                         'All252 scores are12 repeated evaluations of21 variants on one source case.',
                         'No biological labels or predictive accuracy are evaluated.']}
    (OUT / 'ranking_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('panels', 'reference_order')}, indent=2))


if __name__ == '__main__':
    with localcontext() as context:
        context.prec = 120
        audit()
