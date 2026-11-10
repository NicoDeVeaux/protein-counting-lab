"""Recheck the retained native-comparator and biological-input evidence without execution."""

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


def audit():
    snapshots = read('data/campaign-004/comparator_audit/source_snapshots/index.json')
    checked = []
    for row in snapshots:
        data = (ROOT / row['snapshot_path']).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        git_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert sha == row['sha256'] and git_blob == row['expected_git_blob_sha']
        checked.append({'path': row['snapshot_path'], 'sha256': sha, 'git_blob_sha': git_blob})
    tree = read('data/uai23_tree.json')
    assert tree['truncated'] is False
    files = [row['path'] for row in tree['tree'] if row['type'] == 'blob']
    other = [path for path in files if not path.endswith('.zip')]
    assert other == ['README.md']
    java = (ROOT / 'data/campaign-004/comparator_audit/source_snapshots/BBKStar.java').read_text()
    assert 'public BBKStar(ConfSpaceIteration protein, ConfSpaceIteration ligand, ConfSpaceIteration complex' in java
    assert all('if (' + field + ' == null)' in java for field in (
        'confEcalcMinimized', 'confSearchFactoryMinimized', 'confSearchFactoryRigid', 'pfuncFactory'))
    with zipfile.ZipFile(ROOT / 'data/raw/ayyildiz2025/JCC-46-0-s002.zip') as source:
        members = source.namelist()
        script = source.read('analysis_code/bbkstar.py').decode()
        assert './osprey_Arg-binder-build.pdb' in script
        assert not any(name.lower().endswith(('.pdb', '.ccs', '.emat', '.omol', '.confspace')) for name in members)
        assert 'cpuCores=16' in script and 'heapSizeMiB=30000' in script
    counts = read('data/ayyildiz2025_affinities.json')
    rows = counts if isinstance(counts, list) else counts.get('measurements', counts.get('records'))
    assert len(rows) == 63
    result = {'native_source_snapshots_rehashed_against_git_blob_ids': checked,
              'retained_benchmark_tree_non_zip_files': other,
              'bbk_source_requires_three_conformation_spaces_and_energy_search_pfunc_objects': True,
              'same_target_bbkor_aobb_comparator_run': False,
              'comparison_limit': 'Bounded retained official-source availability audit; no proof that a compatible solver could not be obtained or implemented.',
              'experimental_label_records': len(rows), 'supplement_members': members,
              'referenced_prepared_pdb_absent_from_supplement': './osprey_Arg-binder-build.pdb',
              'prepared_conformation_spaces_or_energy_matrices_present': False,
              'biological_accuracy_tested': False,
              'primary_publication_context': [
                  {'url': 'https://proceedings.mlr.press/v216/pezeshki23a/pezeshki23a.pdf',
                   'scope': 'Equations3-5 define selector-conditioned Boltzmann state sums and bound/unbound ratio; UFO is approximate positive-factor thresholding.'},
                  {'url': 'https://ics.uci.edu/~dechter/publications/r274-supplemental.pdf',
                   'scope': 'Section2.0.3 describes the released modified UAI/.sum state encoding; original comparison is not this local fixed-panel test.'}],
              'physical_limit': 'The present audit establishes the released encoded state ratio. Additional conformers have real template labels and finite energy entries; their coordinate origin, force-field calibration and physical absolute offsets are not independently reconstructed. Finite-energy underflow zeros preclude calling it an exact unrounded physical partition model.'}
    (OUT / 'scope_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('native_source_snapshots_rehashed_against_git_blob_ids', 'supplement_members')}, indent=2))


if __name__ == '__main__':
    audit()
