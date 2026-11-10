"""Independently decode archived factors, recheck reductions and enumerate pilot references."""

from collections import Counter
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import re
import sys
import time
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STATES = ('complex', 'protein', 'ligand')


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def named(text, key):
    match = re.search(r'^' + re.escape(key) + r'\s*$', text, re.M)
    assert match, key
    return json.JSONDecoder().raw_decode(text[match.end():].lstrip())[0]


def archive(case):
    with zipfile.ZipFile(ROOT / case['local_path']) as z:
        blob = z.read(case['case_id'] + '.uai')
        summary = z.read('uai_conversion_summary.txt').decode()
        query = list(map(int, z.read(case['case_id'] + '.uai.query').split()))
        assert query[0] == len(query) - 1
        selectors = query[1:]
        text = z.read(case['case_id'] + '.uai.sum').decode()
        token = iter(re.sub(r'#[^\n]*', '', text).split())
        denominator = [[int(next(token)) for _ in range(int(next(token)))] for _ in range(int(next(token)))]
        numerator = [[int(next(token)) for _ in range(int(next(token)))] for _ in range(int(next(token)))]
        assert next(token, None) is None and len(denominator) == 2 and len(numerator) == 1
        groups = numerator + denominator
        keys = ('residues', 'residues_to_id', 'subunit_residue_ids', 'residue_id_to_dissociated_subunit',
                'residue_aminoAcids', 'residue_aminoAcids_to_id', 'residue_id_to_conformationVariable_id',
                'residue_to_conformations', 'residue_conformation_pair_to_aminoAcid')
        meta = {key: named(summary, key) for key in keys}
        energies = {state: z.read('emat.' + state + '.txt').decode() for state in STATES}
    tokens = iter(blob.split())
    assert next(tokens) == b'MARKOV'
    domains = [int(next(tokens)) for _ in range(int(next(tokens)))]
    scopes = [[int(next(tokens)) for _ in range(int(next(tokens)))] for _ in range(int(next(tokens)))]
    factors = []
    underflow_parse = 0
    for scope in scopes:
        size = int(next(tokens))
        shape = tuple(domains[v] for v in scope)
        assert size == math.prod(shape)
        lexemes = [next(tokens).decode() for _ in range(size)]
        values = np.asarray([float(value) for value in lexemes], dtype=np.float64).reshape(shape)
        assert np.isfinite(values).all() and (values >= 0).all()
        underflow_parse += sum(value == 0 and Decimal(lexeme) != 0 for value, lexeme in zip(values.flat, lexemes))
        factors.append((scope, values, lexemes))
    assert next(tokens, None) is None and underflow_parse == 0
    assert sorted(selectors + sum(groups, [])) == list(range(len(domains)))
    assert len(set(selectors + sum(groups, []))) == len(domains)
    assert groups == [[int(value) for value in group.values()] for group in meta['residue_id_to_conformationVariable_id']]
    assert selectors == list(range(len(meta['residues'])))
    assert meta['residues_to_id'] == {residue: i for i, residue in enumerate(meta['residues'])}
    assert set(meta['subunit_residue_ids'][0]) == set(meta['subunit_residue_ids'][1]) | set(meta['subunit_residue_ids'][2])
    assert not set(meta['subunit_residue_ids'][1]) & set(meta['subunit_residue_ids'][2])
    assert 'No normalization after Boltzmann conversions' in summary and 'Objective Type: KstarMAP' in summary
    temperature = float(re.search(r'Using the temperature:\s*([0-9.eE+\-]+)\s*K', summary)[1])
    gas = float(re.search(r'Universal Gas Constant\s+([0-9.eE+\-]+)\s*kcal', summary)[1])
    assert temperature == 298.15 and gas == 0.0019891
    owners = [[] for _ in groups]
    for i, (scope, _, _) in enumerate(factors):
        touched = [j for j, group in enumerate(groups) if set(scope) & set(group)]
        assert len(touched) == 1 and set(scope) <= set(selectors + groups[touched[0]])
        owners[touched[0]].append(i)
    checked = 0
    extra = []
    for state, group in enumerate(meta['residue_id_to_conformationVariable_id']):
        assert list(map(int, group)) == meta['subunit_residue_ids'][state]
        for residue, variable in group.items():
            variable, selector = int(variable), int(residue)
            aa = meta['residue_aminoAcids'][residue]
            assert len(aa) == domains[selector] and len(set(aa)) == len(aa)
            assert meta['residue_aminoAcids_to_id'][residue] == {name: i for i, name in enumerate(aa)}
            assert meta['residue_to_conformations'][state][residue] == list(range(domains[variable]))
            labels = [meta['residue_conformation_pair_to_aminoAcid'][state][str((selector, c))] for c in range(domains[variable])]
            assert set(labels) <= set(aa)
            constraints = [i for i in owners[state] if selector in factors[i][0]]
            assert len(constraints) == 1
            scope, values, _ = factors[constraints[0]]
            assert set(scope) == {selector, variable}
            for choice, label in enumerate(aa):
                for conf, conf_label in enumerate(labels):
                    x = {selector: choice, variable: conf}
                    assert values[tuple(x[v] for v in scope)] == int(label == conf_label)
                    checked += 1
            if state:
                assert int(meta['residue_id_to_dissociated_subunit'][residue]) == state
            extra.append({'state': STATES[state], 'variable': variable, 'last_index': domains[variable] - 1,
                          'residue': meta['residues'][selector], 'last_label': labels[-1]})
    return {'domains': domains, 'selectors': selectors, 'groups': groups, 'factors': factors,
            'meta': meta, 'owners': owners, 'energy_text': energies, 'RT': temperature * gas,
            'constraint_entries': checked, 'last_conformers': extra, 'uai_sha256': digest(blob),
            'source_summary': summary, 'adapter_underflow_entries': underflow_parse}


def energy_audit(raw):
    counts = Counter()
    examples = []
    mismatches = []
    threshold = -math.log(float.fromhex('0x0.0000000000001p-1022') / 1) * raw['RT']
    for state, group in enumerate(raw['groups']):
        text = raw['energy_text'][STATES[state]]
        single, pair = text.split('pairs:')
        entries = {}
        lines = [line.split() for line in single.splitlines()[1:] if line.strip()]
        for parts in lines[1:]:
            variable = int(parts[0])
            assert len(parts) - 1 == raw['domains'][group[variable]]
            for c, value in enumerate(parts[1:]):
                entries[(group[variable], c)] = value
        rows = [line.split() for line in pair.splitlines() if line.strip()]
        for parts in rows[1:]:
            left, conf = map(int, parts[0].split(':'))
            coordinates = [(p, c) for p in range(left) for c in range(raw['domains'][group[p]])]
            assert len(parts) - 1 == len(coordinates)
            for (right, other), value in zip(coordinates, parts[1:]):
                entries[(group[right], other, group[left], conf)] = value
        for index in raw['owners'][state]:
            scope, weights, _ = raw['factors'][index]
            if set(scope) & set(raw['selectors']):
                continue
            assert 1 <= len(scope) <= 2
            for coordinate in np.ndindex(weights.shape):
                if len(scope) == 1:
                    key = (scope[0], coordinate[0])
                else:
                    ordered = sorted(zip(scope, coordinate), key=lambda x: group.index(x[0]))
                    key = (*ordered[0], *ordered[1])
                lexeme = entries[key]
                energy = Decimal(lexeme)
                half = Decimal(5).scaleb(energy.as_tuple().exponent - 1)
                lo, hi = float(energy - half), float(energy + half)
                value = float(weights[coordinate])
                counts['energy_entries'] += 1
                if value == 0:
                    counts['source_zero_energy_entries'] += 1
                    # Rounded text may straddle the subnormal underflow boundary.
                    if hi < threshold:
                        mismatches.append({'state': STATES[state], 'factor': index, 'coordinate': coordinate,
                                           'energy_text': lexeme, 'issue': 'zero_below_underflow_boundary'})
                    elif lo > threshold + raw['RT'] * math.log(2):
                        counts['zero_finite_energy_certainly_underflows_binary64'] += 1
                        if len(examples) < 3:
                            examples.append({'state': STATES[state], 'factor': index, 'coordinate': coordinate,
                                             'energy_text': lexeme, 'source_weight': 0.0})
                    else:
                        counts['zero_near_underflow_boundary'] += 1
                else:
                    effective = -raw['RT'] * math.log(value)
                    if not lo - 1e-11 <= effective <= hi + 1e-11:
                        mismatches.append({'state': STATES[state], 'factor': index, 'coordinate': coordinate,
                                           'energy_text': lexeme, 'source_weight': value, 'effective_energy': effective})
                    counts['positive_weight_energy_rounding_checks'] += 1
    return {'counts': dict(counts), 'underflow_examples': examples, 'mismatches': mismatches,
            'scope': 'All released rounded text energy entries; bounds from final printed decimal place. Not recovery of original full precision energies or proof of coordinate origin.'}


def conditioned(raw, choices, state):
    variables = raw['groups'][state]
    labels = raw['meta']['residue_aminoAcids']
    maps = {}
    for residue, variable in raw['meta']['residue_id_to_conformationVariable_id'][state].items():
        variable = int(variable)
        chosen = labels[residue][choices[int(residue)]]
        maps[variable] = [c for c in range(raw['domains'][variable])
                          if raw['meta']['residue_conformation_pair_to_aminoAcid'][state][str((int(residue), c))] == chosen]
        assert maps[variable]
    factors = []
    lexemes = []
    for index in raw['owners'][state]:
        scope, weights, text = raw['factors'][index]
        conf = [v for v in scope if v in variables]
        vals, source = [], []
        for cs in itertools.product(*(maps[v] for v in conf)):
            assign = choices | dict(zip(conf, cs))
            offset = 0
            for v in scope:
                offset = offset * raw['domains'][v] + assign[v]
            w = float(weights.flat[offset])
            vals.append(-math.inf if w == 0 else math.log(w))
            source.append(text[offset])
        shape = tuple(len(maps[v]) for v in conf)
        factors.append(([variables.index(v) for v in conf], np.asarray(vals).reshape(shape)))
        lexemes.append(source)
    return [len(maps[v]) for v in variables], factors, lexemes, maps


def compare_original(actual, expected_domains, expected, ignore_identity=False):
    domains, factors = PRIOR.parse(actual)
    assert domains == expected_domains
    if ignore_identity:
        factors = [(s, v) for s, v in factors if s or float(v) != 0]
        expected = [(s, v) for s, v in expected if s or float(v) != 0]
    assert len(factors) == len(expected), (len(factors), len(expected))
    for (scope, values), (want_scope, want_values) in zip(factors, expected):
        assert scope == want_scope and values.shape == want_values.shape
        assert values.tobytes() == want_values.tobytes()
    return sum(v.size for _, v in expected)


def direct_reference(domains, factors, lexemes, precision):
    with localcontext() as ctx:
        ctx.prec = precision
        converted = []
        for (_, vals), texts in zip(factors, lexemes):
            converted.append([[Decimal(0) if float(v) == -math.inf else Decimal.from_float(float(v)).exp(),
                               Decimal.from_float(float(s)), Decimal(s)] for v, s in zip(vals.flat, texts)])
        totals = [Decimal(0), Decimal(0), Decimal(0)]
        positive = 0
        for assignment in itertools.product(*(range(q) for q in domains)):
            product = [Decimal(1), Decimal(1), Decimal(1)]
            for i, (scope, _) in enumerate(factors):
                offset = 0
                for v in scope:
                    offset = offset * domains[v] + assignment[v]
                values = converted[i][offset]
                if values[0] == 0:
                    break
                product = [x * y for x, y in zip(product, values)]
            else:
                positive += 1
                totals = [x + y for x, y in zip(totals, product)]
        return {'positive_assignments': positive,
                'log_values': {name: str(z.ln()) if z else '-Infinity' for name, z in zip(
                    ('stored_binary64_log', 'source_binary64', 'source_decimal_lexeme'), totals)}}


def audit():
    source_manifest = read('data/uai23_manifest.json')
    cases = source_manifest['cases']
    chosen = min(cases, key=lambda c: (sum(s['configuration_count'] for s in c['states']), c['case_id']))
    results = []
    source_entries = 0
    raw_chosen = None
    for case in cases:
        raw = archive(case)
        choices = {v: next(i for i, label in enumerate(raw['meta']['residue_aminoAcids'][str(v)]) if label != 'DUMMY')
                   for v in raw['selectors']}
        equivalent = []
        for j, state in enumerate(STATES):
            domains, factors, _, _ = conditioned(raw, choices, j)
            old = next(s for s in case['states'] if s['model_id'].endswith('__' + state))
            n = compare_original(read(old['path']), domains, factors, True)
            source_entries += n
            equivalent.append({'state': state, 'checked_entries': n, 'cartesian_assignments': math.prod(domains)})
        ea = energy_audit(raw)
        results.append({'case_id': case['case_id'], 'source_variables': len(raw['domains']),
                        'source_factors': len(raw['factors']), 'state_groups': dict(zip(STATES, raw['groups'])),
                        'state_factor_ids': dict(zip(STATES, raw['owners'])),
                        'constraint_entries': raw['constraint_entries'], 'source_first_equivalence': equivalent,
                        'last_conformers': raw['last_conformers'], 'adapter_underflow_entries': raw['adapter_underflow_entries'],
                        'source_zero_entries': sum(int(np.count_nonzero(v == 0)) for _, v, _ in raw['factors']),
                        'energy_checks': ea})
        if case['case_id'] == chosen['case_id']:
            raw_chosen = raw
        print('source audit', case['case_id'], len(ea['mismatches']), flush=True)
    raw = raw_chosen
    labels = raw['meta']['residue_aminoAcids']
    selected = next(v for v in raw['selectors'] if sum(label != 'DUMMY' for label in labels[str(v)]) >= 2)
    references = read('prepared/campaign-004/references.json')
    assert selected == 3 and raw['meta']['residues'][selected] == 'F338'
    assert len(references['rows']) == 21
    target_catalog = read('prepared/campaign-004/targets.json')
    checked_models, entries, reduction_entries = [], 0, 0
    reference_errors = []
    for i, label in enumerate(x for x in labels[str(selected)] if x != 'DUMMY'):
        seq = f's{i:02d}_{label}'
        proof = read('prepared/campaign-004/proofs/' + seq + '.json')
        choices = {v: next(j for j, aa in enumerate(labels[str(v)]) if aa != 'DUMMY') for v in raw['selectors']}
        choices[selected] = labels[str(selected)].index(label)
        assert proof['conditioning']['selector_assignment'] == {str(k): v for k, v in choices.items()}
        row = references['rows'][i]
        assert row['label'] == label and row['selector'] == selected
        assert row['sequence'] == {str(v): labels[str(v)][choices[v]] for v in raw['selectors']}
        for j, state in enumerate(STATES):
            domains, factors, texts, maps = conditioned(raw, choices, j)
            original = read('prepared/campaign-004/models/' + seq + '__original__' + state + '.json')
            entries += compare_original(original, domains, factors)
            md = original['metadata']
            assert md['source_domain_indices'] == {str(v): cs for v, cs in maps.items()}
            assert md['source_variable_ids'] == raw['groups'][j]
            assert md['source_factor_indices'] == raw['owners'][j]
            assert md['source_selector_assignment'] == {str(k): v for k, v in choices.items()}
            assert md['source_uai_sha256'] == raw['uai_sha256']
            assert math.prod(domains) <= 1000000
            ref = row['states'][state]
            assert ref['status'] == 'reference-passing success' and ref['cartesian_assignments'] == math.prod(domains)
            fresh = {}
            for precision in (90, 120):
                answer = direct_reference(domains, factors, texts, precision)
                fresh[str(precision)] = answer
                assert answer['positive_assignments'] == ref['positive_assignments']
                stored = next(p for p in ref['passes'] if p['precision'] == precision)
                for semantics, value in answer['log_values'].items():
                    error = abs(Decimal(value) - Decimal(stored['values'][semantics]['logZ']))
                    assert error < Decimal('1e-70')
                    if precision == 120:
                        assert abs(Decimal(value) - Decimal(ref['values'][semantics]['logZ'])) < Decimal('1e-100')
                    reference_errors.append(str(error))
            arms = {}
            for arm in ('simplified', 'propagated'):
                ap = proof['arms'][arm][state]['preparation']
                am = read(proof['arms'][arm][state]['model']['path'])
                od, of = PRIOR.parse(am)
                assert PRIOR.fingerprint(od, of) == ap['target_sha256'] == target_catalog['targets'][seq][arm][state]
                if arm == 'propagated':
                    rd, rf = PRIOR.replay(domains, factors, ap['propagation_proof'])
                else:
                    rd, rf = domains, factors
                assert rd == od
                count = PRIOR.algebra(rf, of, ap['algebra_transformations'])
                reduction_entries += count
                arms[arm] = {'domains': od, 'cartesian_assignments': math.prod(od),
                             'factor_entries': sum(v.size for _, v in of), 'exact_entry_checks': count}
            checked_models.append({'sequence_id': seq, 'state': state, 'original_cartesian_assignments': math.prod(domains),
                                   'positive_assignments': ref['positive_assignments'], 'fresh_reference': fresh, 'arms': arms})
        print('panel audit', seq, flush=True)
    result = {'independence': 'New raw ZIP/UAI/sum/summary/energy parser and all63 Decimal90/120 direct references; no production imports. Reuses sealed campaign003 grader parse/fingerprint/support-replay/Fraction-algebra helpers, not experiment preprocessing.',
              'all14_source_audits': results, 'source_first_equivalence_models': 42,
              'source_first_equivalence_numeric_entries': source_entries, 'new_original_models': 63,
              'new_original_numeric_entries': entries, 'representations_checked': 126,
              'exact_reduction_entry_checks': reduction_entries, 'fresh_decimal_target_rows': 63,
              'fresh_decimal_precision_passes': 126, 'fresh_numeric_semantics_per_pass': 3,
              'max_fresh_vs_frozen_reference_log_error': max(reference_errors, key=Decimal),
              'models': checked_models, 'source_scope': 'Source-defined encoded KstarMAP ratio; rounded energy checks do not establish physical coordinate origin or missing physical offset calibration.'}
    (OUT / 'semantics_audit.json').write_text(json.dumps(result, indent=2, default=lambda value: value.item()) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('all14_source_audits', 'models')}, indent=2))


spec = importlib.util.spec_from_file_location('campaign003_independent_helpers', OUT.parent / 'campaign-003/audit_semantics.py')
PRIOR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PRIOR)

if __name__ == '__main__':
    audit()
