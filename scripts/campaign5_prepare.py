#!/usr/bin/env python3
"""Match published variants to canonical rigid-model conformer domains."""

import hashlib
import json
import math
from pathlib import Path
import re


AA = dict(zip(
    ['ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY', 'HIS', 'ILE',
     'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER', 'THR', 'TRP', 'TYR', 'VAL',
     'HID', 'HIE', 'HIP', 'CYX'],
    'ARNDCQEGHILKMFPSTWYVHHHC'))


def identity(row):
    return '/'.join(f"{m['wild_type']}{m['residue_number']}{m['mutant']}"
                    for m in sorted(row['mutations'], key=lambda x: x['residue_number']))


def prepare(metadata, labels):
    matrices = {m['member']: m for m in metadata['matrices']}
    configs = [c for c in metadata['configs']
               if re.fullmatch(r'rasDesigns/retrospective/bbks/ks[0-9]+\.cfs', c['config_member'])]
    assert len(configs) == 34
    candidates = []
    selected = []
    for row in labels['rows']:
        if not row['mutations']:
            continue
        variant = identity(row)
        desired = {str(m['residue_number'] + 125): m for m in row['mutations']}
        eligible = []
        for config in configs:
            record = {'variant': variant, 'source_row': row['source_row'],
                      'config_member': config['config_member'], 'status': 'excluded'}
            positions = matrices[config['states']['complex']['matrix_member']]['positions']
            by_res = {p['residue']: p for p in positions}
            if not set(desired).issubset(by_res):
                record['reason'] = 'Mutation position outside flexible positions'
                candidates.append(record)
                continue
            if any(AA[by_res[r]['wild_type']] != m['wild_type'] for r, m in desired.items()):
                record['reason'] = 'Prepared wild-type residue differs from label'
                candidates.append(record)
                continue
            state_slots = []
            supported = True
            for version in ('wild_type', 'mutant'):
                for state in ('complex', 'protein', 'ligand'):
                    member = config['states'][state]['matrix_member']
                    info = matrices[member]
                    domains = []
                    for pos in info['positions']:
                        template = pos['wild_type']
                        if version == 'mutant' and pos['residue'] in desired:
                            wanted = desired[pos['residue']]['mutant']
                            templates = set(t for t in pos['conformer_labels'] if AA[t] == wanted)
                            if len(templates) != 1:
                                supported = False
                                break
                            template = next(iter(templates))
                        domain = [i for i, t in enumerate(pos['conformer_labels']) if t == template]
                        if not domain:
                            supported = False
                            break
                        domains.append(domain)
                    if not supported:
                        break
                    state_slots.append({'version': version, 'state': state,
                                        'matrix_member': member, 'matrix_sha256': info['sha256'],
                                        'domains': domains,
                                        'assignments': math.prod(map(len, domains))})
                if not supported:
                    break
            if not supported:
                record['reason'] = 'Missing or ambiguous source mutant template'
            elif any(s['assignments'] > 1_000_000 for s in state_slots):
                record['reason'] = 'Per-state Cartesian count exceeds 1000000'
                record['slot_counts'] = [s['assignments'] for s in state_slots]
            else:
                record.update(status='eligible', total_assignments=sum(s['assignments'] for s in state_slots),
                              slots=state_slots)
                eligible.append(record)
            candidates.append(record)
        if eligible:
            winner = min(eligible, key=lambda r: (r['total_assignments'],
                         int(re.search(r'ks(\d+)\.cfs$', r['config_member']).group(1))))
            selected.append(dict(winner))
    selected.sort(key=lambda r: (r['total_assignments'], r['variant'],
                  int(re.search(r'ks(\d+)\.cfs$', r['config_member']).group(1))))
    total = 0
    exhausted = False
    for record in selected:
        if exhausted or total + record['total_assignments'] > 50_000_000:
            exhausted = True
            record['status'] = 'excluded_total_prefix_cap'
        else:
            record['status'] = 'admitted'
            total += record['total_assignments']
    all_variants = [identity(r) for r in labels['rows'] if r['mutations']]
    return {'scope': 'Prospective model-transfer mechanistic pilot; no direct matched-assay validation.',
            'initial_variants': all_variants, 'canonical_configs': len(configs),
            'candidate_pairs': candidates, 'selected_unique_variants': selected,
            'admitted_assignments': total,
            'variants_without_eligible_config': sorted(set(all_variants)-{r['variant'] for r in selected})}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(json.loads(args.metadata.read_text()), json.loads(args.labels.read_text()))
    result['inputs'] = [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                       for p in (args.metadata, args.labels)]
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({'admitted': sum(r['status']=='admitted' for r in result['selected_unique_variants']),
                      'initial_variants': len(result['initial_variants']),
                      'assignments': result['admitted_assignments'],
                      'excluded_no_eligible': len(result['variants_without_eligible_config'])}))
