# Public export and verification

The public Git repository contains original implementation/test code, research guides, independent grader reports and figures. The release archive contains the exported numerical results, reference calculations, execution journals, provenance and the CC0 Ras-design archive. `DATA_RELEASE.json` pins the release URL, size and SHA-256.

`PUBLICATION_MANIFEST.json` identifies each exported research file, its storage location, original SHA-256, exported SHA-256 and whether its metadata changed. Original hashes are historical evidence, not a claim that redacted files still validate against original research seals. Use `python3 publication.py verify` to verify this public export; `--code-only` verifies just the Git portion.

Local home paths, private policy breadcrumbs and query strings on signed download redirects were redacted in a separate export. No numerical scores or experimental outcomes were edited. The README, local agent guidance and ignore rules were rewritten for publication; their changes are identified in the manifest. New publication tooling and documentation are identified as publication additions. Source code implementing the scientific calculations otherwise remains unchanged.

Copied upstream software, full papers/thesis extractions and sources without verified redistribution terms are excluded. Converted energy-table payloads from the UAI/INRAE inputs are also excluded: conversion alone does not establish a new license. The original source URLs, hashes and rebuild scripts are retained where available. `UPSTREAM_ARTIFACTS.json` records every omission, including artifacts that were generated or extracted and therefore have no direct download URL. Fetching an upstream file is an explicit opt-in local operation, not permission to redistribute it.

The deposited `rasDesigns.zip` archive is included verbatim under its dataset CC0 terms and retains its original author scripts/data. It is not relabeled as project software. OSPREY's software archive, binary and copied source files are excluded and may be obtained separately under their upstream licenses.

Extraction rejects absolute/traversing paths, links, devices, unexpected members and mismatched checksums. Existing conflicting files are not overwritten. Downloads are public unauthenticated GitHub release/source requests; this project requires no credentials.

The original research environment included two independent numerical implementations, documented synthetic failures/fixes and bounded experiments. Publication does not repeat those experiments or turn the small pilots into validation of physical affinity. Aggregate preparation cost was not measured. See the individual independent reports for the exact scientific and resource qualifications.

This is written by an AI agent (model name unavailable) on Nico DeVeaux's behalf.
