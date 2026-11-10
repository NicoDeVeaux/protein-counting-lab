"""Audit source-to-conditioned-table preparation without performing inference."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import zipfile

from acquire_uai23 import ROOT, parse_uai

manifest = json.loads((ROOT/'data/uai23_manifest.json').read_text())
records = []
for case in manifest['cases']:
    with zipfile.ZipFile(ROOT/case['local_path']) as archive:
        name = next(n for n in archive.namelist() if n.endswith('.uai'))
        domains, factors = parse_uai(archive.read(name).decode())
        selector_tokens = archive.read(name+'.query').decode().split()
        selectors = set(map(int,selector_tokens[1:]))
    scalar_indices = [i for i,f in enumerate(factors) if not f['scope']]
    aa_only_indices = [i for i,f in enumerate(factors) if f['scope'] and set(f['scope']) <= selectors]
    assert not scalar_indices and not aa_only_indices, (case['case_id'],scalar_indices,aa_only_indices)
    counts = Counter()
    covered_variables = set(selectors)
    state_variable_sets = []
    entries_checked = 0
    for state in case['states']:
        path = ROOT/state['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == state['sha256']
        model = json.loads(path.read_text())
        meta = model['metadata']
        variables = meta['source_variable_ids']
        state_variable_sets.append(set(variables))
        assert not set(variables) & selectors
        covered_variables.update(variables)
        selector_assignment = {int(k):v for k,v in meta['source_selector_assignment'].items()}
        allowed = {int(k):v for k,v in meta['source_domain_indices'].items()}
        indices = meta['source_factor_indices']
        assert len(indices) == len(set(indices)) == len(model['factors'])
        counts.update(indices)
        for variable in variables:
            expected_allowed = []
            for candidate in range(domains[variable]):
                valid = True
                for index in indices:
                    f = factors[index]
                    if variable not in f['scope'] or not set(f['scope']) & selectors:
                        continue
                    assert set(f['scope']) - selectors == {variable}
                    coordinates = selector_assignment | {variable:candidate}
                    flattened = 0
                    for v in f['scope']:
                        flattened = flattened*domains[v]+coordinates[v]
                    valid &= f['values'][flattened] > 0
                if valid:
                    expected_allowed.append(candidate)
            assert expected_allowed == allowed[variable]
        for index, compiled in zip(indices, model['factors']):
            source = factors[index]
            expected_scope = [variables.index(v) for v in source['scope'] if v not in selectors]
            assert compiled['scope'] == expected_scope
            for flat_index, log_value in enumerate(compiled['log_values']):
                residual = flat_index
                source_assignment = dict(selector_assignment)
                for local_variable in reversed(compiled['scope']):
                    residual, digit = divmod(residual, model['domains'][local_variable])
                    variable = variables[local_variable]
                    source_assignment[variable] = allowed[variable][digit]
                assert residual == 0
                original_flat = sum(source_assignment[v]*math.prod(domains[t] for t in source['scope'][j+1:]) for j,v in enumerate(source['scope']))
                weight = source['values'][original_flat]
                assert (log_value is None) == (weight == 0)
                if weight:
                    assert math.isclose(log_value, math.log(weight), rel_tol=0, abs_tol=1e-13)
                entries_checked += 1
    assert set(counts) == set(range(len(factors))), (case['case_id'],'missing source factors')
    assert all(count == 1 for count in counts.values()), (case['case_id'],'duplicated source factor')
    assert covered_variables == set(range(len(domains)))
    assert all(not a & b for i,a in enumerate(state_variable_sets) for b in state_variable_sets[i+1:])
    records.append({'case_id':case['case_id'],'status':'pass','source_factor_count':len(factors),'source_factors_covered_exactly_once':True,'source_scalar_factor_indices':scalar_indices,'source_amino_acid_only_factor_indices':aa_only_indices,'all_source_variables_covered':True,'conformation_groups_disjoint':True,'conditioned_domain_indices_exactly_match_selector_constraints':True,'compiled_table_entries_checked_against_source':entries_checked})

report = {'schema_version':1,'checked_utc':datetime.now(timezone.utc).isoformat(),'manifest_sha256':hashlib.sha256((ROOT/'data/uai23_manifest.json').read_bytes()).hexdigest(),'purpose':'Data preparation validation only; no partition function or benchmark timing was evaluated.','status':'pass','cases':records,'case_count':len(records),'compiled_table_entries_checked':sum(r['compiled_table_entries_checked_against_source'] for r in records)}
(ROOT/'data/uai23_preparation_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'pass','cases':len(records),'entries_checked':report['compiled_table_entries_checked']}))
