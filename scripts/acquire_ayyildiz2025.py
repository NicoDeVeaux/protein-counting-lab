"""Retrieve published supplemental data and extract Table S1 without fitting models."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import urllib.request
import zipfile

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw' / 'ayyildiz2025'
RAW.mkdir(parents=True, exist_ok=True)
URL = 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12202725/supplementaryFiles'
PACKAGE = RAW / 'supplementaryFiles.zip'
if not PACKAGE.exists():
    with urllib.request.urlopen(URL, timeout=90) as response:
        payload = response.read(15_000_001)
    assert len(payload) <= 15_000_000 and payload.startswith(b'PK')
    PACKAGE.write_bytes(payload)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

with zipfile.ZipFile(PACKAGE) as archive:
    assert archive.testzip() is None
    for name in ['JCC-46-0-s001.pdf', 'JCC-46-0-s002.zip']:
        (RAW / name).write_bytes(archive.read(name))
code_root = RAW / 'analysis_source'
code_root.mkdir(exist_ok=True)
with zipfile.ZipFile(RAW / 'JCC-46-0-s002.zip') as archive:
    assert archive.testzip() is None
    for name in archive.namelist():
        if name.endswith('/'):
            continue
        assert name.startswith('analysis_code/') and len(Path(name).parts) == 2
        (code_root / Path(name).name).write_bytes(archive.read(name))

pdf = RAW / 'JCC-46-0-s001.pdf'
document = pymupdf.open(pdf)
records = []
pocket = None
pocket_sequence = None
extracted = []
for page_index, page in enumerate(document):
    text = page.get_text(sort=True)
    extracted.append('PAGE ' + str(page_index + 1) + '\n' + text)
    for line in text.splitlines():
        heading = re.fullmatch(r'\s*(Arg|Tyr|Trp|Ile|His)-binder\s*\(([A-Z]+)\)\s*', line)
        if heading:
            pocket, pocket_sequence = heading.groups()
        row = re.fullmatch(r'\s*([ACDEFGHIKLMNPQRSTVWY])\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?|-)\s*', line)
        if row and pocket:
            residue, kd, error = row.groups()
            records.append({
                'record_id': pocket + '_' + residue,
                'pocket': pocket, 'pocket_sequence': pocket_sequence,
                'peptide_variable_residue': residue,
                'kd_nm': float(kd),
                'reported_error_nm': None if error == '-' else float(error),
                'reported_error_qualifier': 'not reported (-)' if error == '-' else 'Table S1 column labeled Error [nM]; statistical definition not specified here',
                'source_page_1based': page_index + 1,
                'source_row_text': line.strip(),
            })
pdf.with_suffix('.txt').write_text('\n'.join(extracted))
counts = {p: sum(r['pocket'] == p for r in records) for p in ['Arg','Tyr','Trp','Ile','His']}
assert counts == {'Arg':17,'Tyr':11,'Trp':13,'Ile':13,'His':9}, counts
assert len({r['record_id'] for r in records}) == len(records)
assert all(r['kd_nm'] > 0 for r in records)
assert all(r['reported_error_nm'] is None or r['reported_error_nm'] >= 0 for r in records)

dataset = {
    'schema_version':1,
    'kind':'published_experimental_affinity_measurements',
    'source_article_doi':'10.1002/jcc.70160',
    'source_table':'Supporting Information Table S1',
    'source_pdf':'data/raw/ayyildiz2025/JCC-46-0-s001.pdf',
    'source_pdf_sha256':digest(pdf),
    'units':{'kd_nm':'nM','reported_error_nm':'nM'},
    'scope':'63 published peptide-binding affinity labels for five designed armadillo-repeat binding pockets. These are existing experimental data; no new wet-lab experiment or model prediction was performed.',
    'record_counts_by_pocket':counts,
    'missing_error_count':sum(r['reported_error_nm'] is None for r in records),
    'records':records,
}
output = ROOT / 'data' / 'ayyildiz2025_affinities.json'
output.write_text(json.dumps(dataset,indent=2)+'\n')

bbkstar = (code_root / 'bbkstar.py').read_text()
assert "epsilon=0.68" in bbkstar
assert "./osprey_Arg-binder-build.pdb" in bbkstar
raw_names = sorted(p.name for p in code_root.iterdir() if p.is_file())
manifest = {
    'schema_version':1, 'retrieved_utc':datetime.now(timezone.utc).isoformat(),
    'source_article_url':'https://pmc.ncbi.nlm.nih.gov/articles/PMC12202725/',
    'supplement_package_url':URL,
    'package_sha256':digest(PACKAGE), 'package_bytes':PACKAGE.stat().st_size,
    'article_license':'CC BY 4.0 per article; retain article and supplemental attribution.',
    'parser':'scripts/acquire_ayyildiz2025.py', 'pymupdf_version':pymupdf.__version__,
    'normalized_dataset':str(output.relative_to(ROOT)), 'normalized_dataset_sha256':digest(output),
    'analysis_code_files':raw_names,
    'original_files':[{'path':str(p.relative_to(ROOT)), 'sha256':digest(p), 'bytes':p.stat().st_size} for p in [pdf, RAW/'JCC-46-0-s002.zip', *sorted(code_root.iterdir())] if p.is_file()],
    'reproduction_gaps':[
        'Supplemental ZIP contains source scripts, but no prepared OSPREY input PDB referenced as ./osprey_Arg-binder-build.pdb in bbkstar.py.',
        'No original computed BBK* / flex ddG / PocketOptimizer score tables are present in the supplemental ZIP.',
        'No original energy matrices or prepared conformation spaces are present.',
        'Re-running the published epsilon sweep would require reconstruction of missing molecular preparation and appropriate OSPREY runtime; not attempted in this campaign.',
        'This artifact enables later experimental validation but is not itself a biological prediction result.',
    ],
    'availability_attempts':[
        {'url':'https://pmc.ncbi.nlm.nih.gov/articles/instance/12202725/bin/JCC-46-0-s002.zip','result':'HTML preparing-to-download response, not a ZIP'},
        {'url':'https://europepmc.org/articles/PMC12202725/bin/JCC-46-0-s002.zip','result':'HTTP 403'},
        {'url':URL,'result':'Successful ZIP package; CRC verified'},
    ],
}
(ROOT/'data'/'ayyildiz2025_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'records':len(records),'counts':counts,'missing_errors':dataset['missing_error_count'],'dataset':str(output)}))
