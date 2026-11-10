"""Retrieve and compile a preselected public UAI protein benchmark subset."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RAW = DATA / 'raw' / 'uai23'
MODELS = DATA / 'models' / 'uai23'
RAW.mkdir(parents=True, exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)
SELECTION = json.loads((DATA / 'uai23_selection.json').read_text())

def sha256(blob):
    return hashlib.sha256(blob).hexdigest()

def named_json(text, name):
    match = re.search(r'^' + re.escape(name) + r'\s*$', text, re.M)
    if not match:
        raise ValueError('Missing conversion metadata: ' + name)
    return json.JSONDecoder().raw_decode(text[match.end():].lstrip())[0]

def parse_uai(text):
    tokens = iter(text.split())
    if next(tokens) != 'MARKOV':
        raise ValueError('Only non-normalized MARKOV UAI factors are supported')
    n = int(next(tokens))
    domains = [int(next(tokens)) for _ in range(n)]
    count = int(next(tokens))
    scopes = [[int(next(tokens)) for _ in range(int(next(tokens)))] for _ in range(count)]
    factors = []
    for scope in scopes:
        count = int(next(tokens))
        assert count == math.prod(domains[v] for v in scope)
        values = [float(next(tokens)) for _ in range(count)]
        if any(v < 0 or not math.isfinite(v) for v in values):
            raise ValueError('Invalid source factor')
        factors.append({'scope': scope, 'values': values})
    assert next(tokens, None) is None
    return domains, factors

def offset(coords, scope, domains):
    index = 0
    for var in scope:
        index = index * domains[var] + coords[var]
    return index

def download(item):
    target = RAW / Path(item['path']).name
    url = 'https://raw.githubusercontent.com/dechterlab/uai23-KstarMAP-benchmarks/' + SELECTION['commit'] + '/' + urllib.parse.quote(item['path'])
    retrieved = datetime.now(timezone.utc).isoformat()
    if target.exists():
        blob = target.read_bytes()
    else:
        request = urllib.request.Request(url, headers={'User-Agent': 'protein-counting-lab academic reproducibility'})
        with urllib.request.urlopen(request, timeout=60) as response:
            blob = response.read(item['size'] + 1)
        assert len(blob) == item['size']
        target.write_bytes(blob)
    git_blob = hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest()
    assert git_blob == item['sha'], (target.name, git_blob, item['sha'])
    return item, target, {'source_url': url, 'retrieved_utc': retrieved, 'sha256': sha256(blob), 'git_blob_sha': git_blob, 'bytes': len(blob), 'local_path': str(target.relative_to(ROOT))}

def compile_case(item, target, provenance):
    with zipfile.ZipFile(target) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    uai_name = next(name for name in members if name.endswith('.uai'))
    domains, factors = parse_uai(members[uai_name].decode())
    selectors_tokens = members[uai_name + '.query'].decode().split()
    selectors = [int(x) for x in selectors_tokens[1:]]
    assert len(selectors) == int(selectors_tokens[0])
    summary = members['uai_conversion_summary.txt'].decode()
    state_maps = named_json(summary, 'residue_id_to_conformationVariable_id')
    amino_acids = named_json(summary, 'residue_aminoAcids')
    residues = named_json(summary, 'residues')
    selected_aa = {v: 0 for v in selectors}
    sequence = {residues[v]: amino_acids[str(v)][0] for v in selectors}
    case_id = Path(uai_name).stem
    state_records = []
    for state_index, state_name in enumerate(['complex', 'protein', 'ligand']):
        state_vars = [int(v) for v in state_maps[state_index].values()]
        state_set = set(state_vars)
        selected_factors = []
        for factor_index, factor in enumerate(factors):
            touched = set(factor['scope']) & state_set
            if touched:
                assert set(factor['scope']) <= state_set | set(selectors)
                selected_factors.append((factor_index, factor))
        allowed = {v: list(range(domains[v])) for v in state_vars}
        for _, factor in selected_factors:
            conf_vars = [v for v in factor['scope'] if v in state_set]
            aa_vars = [v for v in factor['scope'] if v in selected_aa]
            if len(conf_vars) == 1 and aa_vars:
                v = conf_vars[0]
                allowed[v] = [value for value in allowed[v] if factor['values'][offset(selected_aa | {v: value}, factor['scope'], domains)] > 0]
        if any(not values for values in allowed.values()):
            raise ValueError('Empty rotamer domain for declared source-first sequence')
        remap = {var: index for index, var in enumerate(state_vars)}
        new_factors = []
        original_factor_indices = []
        for factor_index, factor in selected_factors:
            conf_scope = [v for v in factor['scope'] if v in state_set]
            values = []
            for combination in itertools.product(*(allowed[v] for v in conf_scope)):
                coords = selected_aa | dict(zip(conf_scope, combination))
                weight = factor['values'][offset(coords, factor['scope'], domains)]
                values.append(None if weight == 0 else math.log(weight))
            new_factors.append({'scope': [remap[v] for v in conf_scope], 'log_values': values})
            original_factor_indices.append(factor_index)
        model_id = case_id + '__source_first__' + state_name
        model = {
            'schema_version': 1, 'model_id': model_id, 'kind': 'published_computational_model',
            'domains': [len(allowed[v]) for v in state_vars], 'factors': new_factors,
            'constant_log_weight': 0.0,
            'metadata': {
                'source_repository': SELECTION['source_repository'], 'source_commit': SELECTION['commit'],
                'archive_sha256': provenance['sha256'], 'uai_member': uai_name,
                'uai_member_sha256': sha256(members[uai_name]), 'source_factor_indices': original_factor_indices,
                'state': state_name, 'state_index': state_index,
                'source_variable_ids': state_vars, 'source_domain_indices': {str(v): allowed[v] for v in state_vars},
                'sequence_policy': 'index zero of every source amino-acid selector, before inference; no outcome selection',
                'sequence': sequence, 'source_selector_assignment': selected_aa,
                'factor_convention': 'source UAI nonnegative weights; natural logarithm; last scope variable varies fastest (C order)',
                'temperature_kelvin': 298.15, 'source_gas_constant_kcal_mol_kelvin': 0.0019891,
                'conditioning': 'Source amino-acid selector constraints conditioned and disallowed zero-weight rotamers removed losslessly. All state energy factors retained.',
                'limitations': ['Source UAI conversion already contains underflow zeros; these are preserved.', 'Input is a published discrete computational model, not experimental affinity data.', 'No affinity scoring or sequence optimization has been run.'],
            },
        }
        path = MODELS / (model_id + '.json')
        encoded = json.dumps(model, separators=(',', ':'), allow_nan=False).encode() + b'\n'
        path.write_bytes(encoded)
        state_records.append({'model_id': model_id, 'path': str(path.relative_to(ROOT)), 'sha256': sha256(encoded), 'domains': model['domains'], 'configuration_count': math.prod(model['domains']), 'factor_count': len(new_factors), 'table_entries': sum(len(f['log_values']) for f in new_factors), 'zero_entries': sum(v is None for f in new_factors for v in f['log_values'])})
    record = provenance | {'case_id': case_id, 'pdb_id': case_id[:4], 'original_domains': domains, 'source_zero_entries': sum(v == 0 for f in factors for v in f['values']), 'source_zero_selector_constraint_entries':sum(v == 0 for f in factors if set(f['scope']) & set(selectors) for v in f['values']), 'source_zero_energy_entries':sum(v == 0 for f in factors if not set(f['scope']) & set(selectors) for v in f['values']), 'selector_domains': [domains[v] for v in selectors], 'selected_sequence': sequence, 'states': state_records}
    print(json.dumps({'case_id':case_id, 'state_domains':[s['domains'] for s in state_records], 'configurations':[s['configuration_count'] for s in state_records]}), flush=True)
    return record

if __name__ == '__main__':
    assert sum(item['size'] for item in SELECTION['selected']) < 150_000_000
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        downloaded = list(pool.map(download, SELECTION['selected']))
    records = [compile_case(*entry) for entry in downloaded]
    manifest = {'schema_version':1, 'created_utc':datetime.now(timezone.utc).isoformat(), 'source_repository':SELECTION['source_repository'], 'commit':SELECTION['commit'], 'selection_rule':SELECTION['selection_rule'], 'affinity_score_relation':'For each fixed source-first sequence, log K* = log Z_complex - log Z_protein - log Z_ligand. These are discrete model scores, not experimentally measured affinities.', 'zero_semantics':'Source UAI files include both selector-consistency zeros and source-represented zero Boltzmann factors. No discarded positive source values or newly applied thresholds.', 'license_status':'Public repository; no explicit repository license was supplied. Retain author attribution; no redistribution authorization inferred.', 'download_bytes':sum(p['bytes'] for p in records), 'cases':records}
    (DATA/'uai23_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'manifest':'data/uai23_manifest.json','cases':len(records),'models':sum(len(p['states']) for p in records)}),flush=True)
