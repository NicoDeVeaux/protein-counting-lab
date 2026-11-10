#!/usr/bin/env python3
"""Inventory archived design definitions without executing author scripts."""

import ast
import hashlib
import json
from pathlib import Path
import zipfile


def catalog(archive: Path) -> dict:
    records = []
    with zipfile.ZipFile(archive) as z:
        for name in sorted(z.namelist()):
            if not name.endswith('.cfs'):
                continue
            raw = z.read(name)
            tree = ast.parse(raw.decode())
            values = {}
            for node in tree.body:
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    raise ValueError(f'Unexpected config syntax: {name}')
                key = node.targets[0]
                if not isinstance(key, ast.Name) or key.id in values:
                    raise ValueError(f'Unexpected config key: {name}')
                values[key.id] = ast.literal_eval(node.value)
            if set(values) != {'mol', 'strand_defs', 'strand_flex'}:
                raise ValueError(f'Unexpected config fields: {name}')
            records.append({'archive_path': name,
                            'sha256': hashlib.sha256(raw).hexdigest(),
                            'bytes': len(raw), 'config': values})
    return {'archive_path': str(archive),
            'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'scope': 'Static config metadata only; no score or matrix evaluation.',
            'configs': records}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = catalog(args.archive)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({'configs': len(result['configs']), 'output': str(args.output)}))
