# Reproducing the bounded external gate

See [the campaign result](../../CAMPAIGN-008.md) and
[independent protocol](../../grader/campaign-008/PROTOCOL.md). This directory contains
the frozen implementation and public evidence; original upstream inputs and full
factor-tree certificates are intentionally separate.

## Inputs and tools

`select.py` pins the official MC2026 public Track 1 archive's URL and SHA-256.
Download that archive into a separate temporary data directory. Run from the repo
root, choosing a fresh destination:

```sh
python3 -B -m experiments.external_count8.select /path/to/mc2026_track1_public.tar /path/to/fresh-cohort
```

The selector verifies the archive, inventories every member and reproduces the
prospective seed-8008 cohort without consulting solver results. Its generated
`COHORT.json` must match the saved cohort bytes before using this result's identity.
No bulk data from earlier research campaigns is needed.

Obtain the pinned native ARM64 Ganak release identified in
[baseline-provenance.json](baseline-provenance.json), verify archive and executable
digests, and use its extracted `ganak` executable. Another architecture/version
requires a new documented experiment identity. No solver binary is included here.

Build the native checker once, outside measurement, with
`lean_native.build_checker(empty_build_directory)`. It copies the unchanged
campaign-007 proof and CLI, audits all eleven theorem reports and builds with the
pinned Lean toolchain. It returns executable location, build cost and digests.
The local build needs Lean 4.35.0 and its native C toolchain; Python uses only the
standard library. [LEAN_BUILD.md](LEAN_BUILD.md) explains the implementation.

## Evidence identities and new measurements

`SOURCE_SEAL.json` identifies every measured source/configuration file and both
executables. Saved result copies preserve this seal. The runner refuses changed
sources, changed input bytes, changed binaries or an existing output directory.
Native builds may have different binary bytes even with identical source.

For a new measurement, use a dedicated checkout and fresh data/build/output
directories. Preserve the supplied seal as the original reference before creating
a new prospective seal with `run --seal`; do not overwrite historical measurements
or present a replacement seal as the original one. Record any source/configuration
change and the new executable identities before counting the selected inputs.

```sh
python3 -B -m experiments.external_count8.run --ganak /path/to/ganak --checker /path/to/checker8 --seal
python3 -B -m experiments.external_count8.run --ganak /path/to/ganak --checker /path/to/checker8 --inputs /path/to/fresh-cohort --output /path/to/fresh-results --private /path/to/fresh-private-certificates
```

The first command requires that the reference seal has already been preserved
separately; it refuses to replace an existing seal. Local paths are runtime inputs
and do not belong in public provenance. A new run is new evidence, not a substitute
for the saved negative result.

The supervisor measures complete fresh-worker wall time and kills the entire
worker process group on timeout. Workers execute sequentially. Do not overlap
other campaign computation with measurement. The prefix method reserves time for
verification within the hard deadline; the amendment fixes its soft search budget.
OS caches and unrelated host activity were not controlled, and three repetitions
do not establish portable performance or statistical significance.

## Audit and data boundaries

`grader/campaign-008/audit_inputs.py` independently verifies archive membership,
the cohort, parser controls and clause/factor semantics.
`grader/campaign-008/audit_results.py` independently checks saved measurements,
medians, references, source seals and private certificate replay. Use each script's
`--help` for its explicit source/cohort/checker/evidence paths.

The primary `seconds` field is supervisor wall time. `worker_seconds` is a nested
diagnostic and must not replace it. CSV times are medians over all three repeats;
expansion/node/byte diagnostics are taken from the first repeat and happen to be
identical across repeats here. Never calculate medians only from successful runs.

Full certificates encode upstream factor tables. Keep them with the source CNFs
outside the public mirror until redistribution terms are established. Public raw
records retain their hashes and filenames, exact counts where available, endpoint
bounds, timings and statuses. Seven input references were confirmed; remaining
unknowns stay explicit. The checker establishes parsed-model enclosures rather than
authenticating an external dataset by itself.
