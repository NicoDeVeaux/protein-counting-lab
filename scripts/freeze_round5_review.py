#!/usr/bin/env python3
"""Seal campaign-005 inputs and measured/derived evidence before final audit."""

import datetime
import hashlib
import json
from pathlib import Path


root = Path.cwd()
paths = set()
for prefix in ('data/campaign-005', 'prepared/campaign-005', 'runs/campaign-005',
               'runs/campaign-005-control', 'experiments/energy_recovery5', 'experiments/rigid_affinity5'):
    for path in (root/prefix).rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            paths.add(path.relative_to(root))
for pattern in ('scripts/campaign5*.py', 'scripts/plot_round5.py', 'scripts/freeze_round5_review.py',
                'tests/test_rigid_affinity5.py', 'outputs/campaign-005*'):
    paths.update(path.relative_to(root) for path in root.glob(pattern) if path.is_file())
activation = json.loads((root/'prepared/campaign-005/ACTIVATION.json').read_text())
paths.update(Path(e['path']) for e in activation['files'])
grader_dir = root/'grader/campaign-005'
for pattern in ('FREEZE*', 'AMENDMENT*', 'ACTIVATION_REVIEW*'):
    paths.update(path.relative_to(root) for path in grader_dir.glob(pattern) if path.is_file())
review = json.loads((grader_dir/'ACTIVATION_REVIEW-002.json').read_text())
paths.update(Path(e['path']) for e in review['files'])
entries = []
for relative in sorted(paths):
    path = root/relative
    entries.append({'path': str(relative), 'bytes': path.stat().st_size,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
bundle = {'campaign': '005', 'sealed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'scope': 'Measurement/input/analysis evidence; final independent audit outputs and parent guide are separate.',
          'files': entries, 'file_count': len(entries), 'bytes': sum(e['bytes'] for e in entries)}
output = root/'runs/campaign-005-review'
output.mkdir(exist_ok=False)
manifest = output/'bundle_manifest.json'
with manifest.open('x') as f:
    json.dump(bundle, f, indent=2);f.write('\n')
digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
with (output/'bundle_manifest.sha256').open('x') as f:
    f.write(digest+'  '+str(manifest.relative_to(root))+'\n')
print(json.dumps({'files': len(entries), 'bytes': bundle['bytes'], 'seal': digest[:6]}))
