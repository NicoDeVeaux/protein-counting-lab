# Campaign 003 amendment 003: representation-classification metadata

Date: 2026-11-06 UTC. This additive amendment permits another narrowly scoped catalog-format correction before measured inference. Earlier grader freezes/amendments, preparation manifest, algorithms, targets, proofs, catalogs and failed attempts remain unchanged. `AMENDMENT-003.json` binds this document and the preceding grader records.

## Exposure and schema issue

The parent reports a second final-freeze failure at zero timed trials: the catalog's descriptive `representations[*].simplification` strings do not match the inherited schema enum. The parent reports retaining catalog prefix `9becf6` and the partial run, then using the unchanged driver's freeze path with a validation-capture callback, without running a measured worker, to retain `runs/campaign-003-schema-diagnostic/candidate.json` and `all-schema-errors.json`. The parent reports exactly 24 enum errors and no other schema errors. These are parent attestations, not independent phase-two findings. No pruning outcomes, timing or numerical results have been disclosed to the grader.

The grader inspected only the unchanged schema field. It permits `unchanged`, `exact_constant_scope`, `exact_separable`, `multiple_exact`, and `unverified_or_approximate`. The grader has not inspected the campaign003 catalog, candidate, diagnostics, implementations, prepared data or outcomes. This amendment does not certify that the reported enum errors are the only errors.

## Permitted correction

Create a new catalog and thin version-three wrapper, preserving every older catalog, wrapper, failed freeze and diagnostic. The new catalog may change only each representation's `simplification` enum and add a field retaining its original descriptive value verbatim, such as `simplification_description_original`. Do not overwrite an existing field with a different value. Preserve all other catalog values, including Amendment 002's corrected selection metadata, original targets, derived hashes, mappings, proofs, preparation ledger, references, numerical contracts, resource policies and exact trial identities/order.

Classify the enum deterministically from the **already bound serialized algebra-transformation proof kinds**, with an explicit mapping table retained in the correction record:

| Bound algebra evidence | Metadata class |
|---|---|
| No algebraic rewrite | `unchanged` |
| Only exact constant/scope/singleton reductions | `exact_constant_scope` |
| Only exact separable/decomposition reductions | `exact_separable` |
| Both classes of exact reductions | `multiple_exact` |

This field classifies algebra only. Hard-zero support propagation, state deletion and original-domain mapping remain separately described and audited; a no-algebra-change label must not imply no support pruning. Classifying a proof kind is not a new proof and does not validate the existing certificate. Do not use observed pruning efficacy, runtime, a solver answer or numeric closeness to choose the class. An absent, ambiguous, unrecognized, approximate or unverified proof kind cannot be forced into an exact class merely to pass the schema. Stop the proposed correction for that case or retain `unverified_or_approximate` with the original exact same-target claim gate failed; any further methodological change needs a separate exposed amendment.

The new wrapper may only call the unchanged frozen driver's existing `freeze`, `run` and `summarize` operations on the replacement catalog and a new run path. Do not rerun preparation, change an inference/preprocessing implementation or configuration, alter a clock/endpoint, add retries, or change the measured matrix, order, limits, references or accuracy contract. Numerical and preprocessing implementation hashes must remain those frozen before preparation, reported by the parent as preparation manifest prefix `996bf1`.

## Evidence required before launch

Extend the immutable correction ledger with full hashes and paths for both prior failed catalogs/wrappers/partial runs, all actual error evidence, the captured candidate and full schema-error list, the replacement catalog/wrapper, the unchanged driver/source inventory and the original preparation manifest. Record available commands, exit statuses and time evidence without manufacturing missing fields. Preserve the distinction between premeasurement schema failures and measured trial outcomes.

Retain the explicit proof-kind-to-enum mapping and a complete structural comparison proving that the catalog changes are limited to the specified enum fields and copied descriptions. Independently compare all target/artifact/proof/reference/plan/resource values against the unchanged predecessor and preparation freeze. Validate the **entire corrected candidate** against the **unchanged full manifest schema**, not only the repaired field; retain the candidate, validator/schema hashes, command and all validation messages. The validation/capture path must not execute preprocessing or a measured worker.

Freeze the final execution manifest and hash before the first timed trial. Bind this amendment, the complete correction/failure chronology, replacement catalog/wrapper and all unchanged preparation and measurement-plan evidence. If any other schema or semantic problem appears, retain it and resolve it prospectively without silently broadening this amendment.

All original grading gates remain unchanged. In particular, semantic correctness and exact support/algebra proofs require independent audit regardless of schema acceptance. Every planned row and failure remains visible; cold preprocessing is charged into end-to-end cost; fixed numerical/resource/reference contracts and drift limits still control interpretation. This is a premeasurement metadata correction, not a numerical validation or a speed verdict.
