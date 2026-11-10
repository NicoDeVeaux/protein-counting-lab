#!/usr/bin/env python3
"""Download and verify this research export without credentials."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parent


def sha256(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or '..' in path.parts or '\\' in name:
        raise ValueError('Unsafe archive path')
    target = ROOT.joinpath(*path.parts)
    if not target.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Archive path escapes repository')
    return target


def fetch(url, expected_sha, expected_size, destination):
    request = urllib.request.Request(url, headers={'User-Agent': 'protein-counting-lab-publication/1'})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open('wb') as stream:
        shutil.copyfileobj(response, stream, 1024*1024)
    if destination.stat().st_size != expected_size or sha256(destination) != expected_sha:
        raise ValueError('Download size or SHA-256 mismatch')


def manifest():
    return json.loads((ROOT/'PUBLICATION_MANIFEST.json').read_text())


def verify(code_only=False):
    checked = missing = 0
    for entry in manifest()['files']:
        if code_only and entry['storage'] != 'git':
            continue
        path = safe_path(entry['path'])
        if not path.is_file():
            missing += 1
        elif path.stat().st_size != entry['bytes'] or sha256(path) != entry['sha256']:
            raise ValueError('Exported file mismatch: '+entry['path'])
        else:
            checked += 1
    if missing:
        raise ValueError(f'{missing} expected files missing; use download for the bulk data')
    print(json.dumps({'verified_files': checked, 'code_only': code_only}))


def download():
    release = json.loads((ROOT/'DATA_RELEASE.json').read_text())
    expected = {e['path']: e for e in manifest()['files'] if e['storage']=='release'}
    with tempfile.TemporaryDirectory(prefix='protein-counting-download-') as temporary:
        archive = Path(temporary)/release['file']
        fetch(release['url'], release['sha256'], release['bytes'], archive)
        seen = set()
        with tarfile.open(archive, 'r:gz') as source:
            for member in source:
                if not member.isfile() or member.name not in expected or member.name in seen:
                    raise ValueError('Unexpected archive member')
                entry = expected[member.name]
                if member.size != entry['bytes']:
                    raise ValueError('Unexpected member size')
                target = safe_path(member.name)
                if target.exists():
                    if not target.is_file() or sha256(target) != entry['sha256']:
                        raise ValueError('Refusing to overwrite conflicting file: '+member.name)
                else:
                    temporary_file = Path(temporary)/'extracted-file'
                    with source.extractfile(member) as stream, temporary_file.open('wb') as output:
                        shutil.copyfileobj(stream, output)
                    if sha256(temporary_file) != entry['sha256']:
                        raise ValueError('Extracted member checksum mismatch')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(temporary_file), str(target))
                seen.add(member.name)
        if seen != set(expected):
            raise ValueError('Archive is incomplete')
    verify()


def fetch_upstream(name):
    entries = json.loads((ROOT/'UPSTREAM_ARTIFACTS.json').read_text())['artifacts']
    entry = next((e for e in entries if e['path']==name), None)
    if not entry or not entry['source_urls']:
        raise ValueError('No direct source URL recorded; consult the original acquisition/rebuild scripts')
    target = safe_path(name)
    if target.exists():
        if sha256(target) != entry['original_sha256']:
            raise ValueError('Conflicting upstream file already exists')
        print('Already present with expected checksum: '+name)
        return
    with tempfile.TemporaryDirectory(prefix='protein-counting-source-') as temporary:
        output = Path(temporary)/'source'
        fetch(entry['source_urls'][0], entry['original_sha256'], entry['bytes'], output)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(output), str(target))
    print('Fetched verified upstream artifact: '+name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('verify')
    check.add_argument('--code-only', action='store_true')
    sub.add_parser('download')
    upstream = sub.add_parser('fetch-upstream')
    upstream.add_argument('--path', required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        verify(args.code_only)
    elif args.command == 'download':
        download()
    else:
        fetch_upstream(args.path)
