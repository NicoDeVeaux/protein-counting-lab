# Protein counting experiments

Exploratory experiments on discrete protein design: partition functions, ensemble affinity scores, exact preprocessing, numerical references, and independent grading. This repository preserves useful results and negative findings from five local CPU campaigns.

The latest study uses full-precision rigid energy matrices from the published c-Raf/Ras archive. All 78 state calculations for 13 admitted variants pass independent high-precision references. Ensemble counting reverses two pairwise variant rankings and changes no mutation-effect directions. A small model-transfer comparison does not establish improved biological prediction.

| Study | Result |
|---|---|
| Initial inference pilot | Conventional finite-model inference and numerical checks; no demonstrated biological improvement. |
| [Campaign 002](CAMPAIGN-002.md) | Established-solver comparison, adapter correction and retained reruns; broad timing claims rejected. |
| [Campaign 003](CAMPAIGN-003.md) | Exact hard-zero propagation helps one supplied model; larger cases remain bounded negative results. |
| [Campaign 004](CAMPAIGN-004.md) | Full three-state ranking for 21 residue templates; baseline remains best, no general pruning win. |
| [Campaign 005](CAMPAIGN-005.md) | Counting changes prioritization in a full-precision rigid model; assay/model mismatch prevents direct biological validation. |

The independent grader freezes criteria before fresh measurements and checks saved outputs separately from experiment implementations. This is research code, not a production solver or evidence of an ETH breakthrough.

## Code and data

Code, tests, reports and figures live in Git. Bulk results and licensed inputs are attached to the [data release](https://github.com/NicoDeVeaux/protein-counting-lab/releases/tag/v2026.11.10). From a clone:

```sh
python3 publication.py verify --code-only
python3 publication.py download
python3 publication.py verify
```

The downloader verifies the compressed SHA-256 and every extracted file. It restores data into this working tree; skip downloading if you only want to read the code and results summaries.

For the latest model's core checks:

```sh
uv sync --frozen --group dev
uv run --group dev pytest -q tests/test_rigid_affinity5.py
uv run python -m unittest experiments.energy_recovery5.test_java_matrix
```

Earlier campaigns also require upstream inputs excluded from the mirror. Their pinned URLs, checksums and exclusion reasons are in [UPSTREAM_ARTIFACTS.json](UPSTREAM_ARTIFACTS.json); `python3 publication.py fetch-upstream --path PATH` downloads an explicitly selected direct source. See [RUNNING.md](RUNNING.md) and the campaign guides. Existing measured output locations are intentionally not overwritten.

## Publication boundaries

This is a privacy-redacted export. Original scientific outputs are retained, but local paths, private policy references and signed download URL query strings were removed. Historical freeze hashes describe original workspace bytes and must not be mistaken for checksums of edited public metadata. [PUBLICATION_MANIFEST.json](PUBLICATION_MANIFEST.json) records original/export hashes and omissions; [PUBLICATION.md](PUBLICATION.md) explains verification.

No new scientific measurements were made for publication. Read the independent [campaign-005 verdict](grader/campaign-005/REPORT.md) and [result figure](outputs/campaign-005-v2.png) for the substantive findings and qualifications.

Original software is MIT-licensed. Data and attributed transcriptions retain the terms described in [THIRD_PARTY.md](THIRD_PARTY.md). Please cite the original papers and datasets when using their material.

This is written by an AI agent (model name unavailable) on Nico DeVeaux's behalf.
