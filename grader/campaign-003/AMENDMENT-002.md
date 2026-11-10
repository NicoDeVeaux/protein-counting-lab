# Campaign 003 amendment 002: premeasurement catalog-format correction

Date: 2026-11-06 UTC. This additive amendment permits a narrowly specified metadata/orchestration correction after static preparation and before measured inference. It does not edit the original protocol, freeze, Amendment 001, preparation manifest, source code, prepared artifacts or failed attempt. `AMENDMENT-002.json` binds this document and the earlier grader records.

## Exposure and reason

The parent reports that static preparation completed 24 rows under preparation manifest prefix `996bf1`, and that the final freeze failed before any trial or execution-manifest write because `catalog.selection_rule` had the wrong schema shape. The parent reports no measured protein inference and no algorithm/runtime error. Failed catalog, diagnostics and partial `runs/campaign-003` are retained. These are parent attestations, not independent audit conclusions. The grader has not read campaign003 implementations, prepared models, pruning counts, timing data or results. The only new schema inspection confirms the existing required metadata shape.

The unchanged inherited manifest schema requires `selection_rule.rule` (string), `baseline_42_mapping` (hashed artifact), `coverage_gaps` (array), and `intended_cells` (array). A format rejection does not establish a computational failure or success. This correction does not alter the campaign's explicitly adaptive status.

## Permitted correction

Create a new `catalog.amendment002.json` from the retained original catalog. Change only `selection_rule` into the required shape, carrying the same frozen all-six CPD cohort and prospective scope:

- `rule` describes the already frozen six-target selection and both arms.
- `baseline_42_mapping` points to the immutable campaign002 mapping with its full hash. It is provenance only: campaign002's 42 baseline models are **not measured in campaign003**.
- `coverage_gaps` and `intended_cells` describe the preparation-manifest cohort/plan and its already known limits. They must not introduce outcome-selected cells, remove failed/no-op cases or reclassify synthetic cases as protein evidence.

All original model records, references, preparation ledger, target/numerical contracts and remaining catalog content must be preserved exactly as JSON values. Retain the original malformed catalog unchanged. The correction may add a separate amendment/provenance record rather than mutate other catalog fields.

A new `execute_round3_v2.py` may only call the **unchanged frozen driver's** existing `freeze`, `run` and `summarize` operations with the replacement catalog and a new run path. Preserve the earlier wrapper/source bug and failed run directory. The replacement wrapper must not rerun target preparation, implement a new kernel, change method/configuration, alter rows/order/repeats, change timers/limits, change references or retry measured trials. Driver and numerical/preprocessing implementation hashes must still match the preparation freeze. If a different change is required, stop this correction and record another exposed amendment before measurements.

## Required evidence before any measured trial

Freeze a correction record with full SHA256 values and paths for the original preparation manifest, original catalog, original orchestration source, failed/partial run artifacts, replacement catalog, replacement wrapper, unchanged driver and relevant source inventory. Bind the grader amendment identity and prospective final run path. Record the observed freeze command, actual diagnostic/traceback, exit status and available time evidence as a distinct **premeasurement schema failure**. Preserve raw diagnostics; use explicit unknown/null fields for evidence that was not recorded rather than inventing timestamps or empty successful outputs.

Record an independent structural comparison confirming that only the permitted catalog field changes and wrapper routing changed, while all prepared artifact hashes, model/reference/ledger values, trial identities and order, numerical/resource contracts and budgets remain fixed. Include the immutable campaign002 mapping hash and its provenance-only role. A new metadata fixture or candidate execution manifest must pass the **full unchanged manifest schema** before the final freeze; retain the validation command, schema hash and result. Metadata validation must not invoke preparation or inference.

The final execution manifest and hash must freeze before the first timed trial. They bind the replacement catalog/wrapper, correction/error evidence and the unchanged preparation manifest/ledger, algorithms, all prepared targets, full trial plan, resources and references. Keep the failed catalog and partial original run in the sealed audit bundle. The failed freeze is not a measured trial and must not be presented as one or hidden from the chronology.

All original grading gates remain unchanged: exact-only hard zeros, original-domain mapping and same-target algebra proof; independent numerical/reference assurance; all-six coverage and every planned failure/skip; cold preprocessing charged into end-to-end time; row/total budgets and RSS interpretation; phase/repeat/order drift checks; no unsupported superiority, oracle upgrade, ETH or biological claim. This amendment permits a prospective format correction; it does not certify the parent attestations or the corrected artifacts before independent phase-two audit.
