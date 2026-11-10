# Independent grading: campaign 007

Checked on 2026-11-10 against the new construction checker and its Python adapter.
The prospective [protocol](PROTOCOL.md) preceded implementation evaluation.
Historical campaign code and result files were not changed for this audit.

## Outcome

The new checker makes a substantive improvement over campaign 006's trust boundary.
Its theorem proves partition enclosure from the executable factor-bound and split
construction. It does not assume that the supplied endpoints already enclose the
partition. The actual checker evaluates the factor decision trees and the supplied
cut; it does not enumerate every global assignment to validate a bound.

The independent source and executable audits pass:

| Check | Observed result |
|---|---|
| Source models | 11 deterministic plus 60 seeded tiny targets; nine integration case/state combinations |
| Actual producer exports | 382 certificates, all independently valid |
| Source-table/decision-tree and cut-coverage checks | 45,237 assignment-level checks |
| Independently constructed root/full/BFS cuts | 355 certificates accepted with the independently calculated endpoints |
| Actual producer certificates checked by Lean | 382 accepted with exactly the submitted endpoints |
| Expected-model Python/Lean bridge | 382 valid requests accepted |
| Python malformed/mismatched binding controls | 20 rejected |
| Lean malformed or forged certificate controls | 27 rejected or invalid; none accepted |
| Truncated, trailing or invalid raw JSON lines | Seven invalid |
| Actual exporter source mutants | Three rejected by independent value/bound assertions |

Counts are executions over case/target combinations, not globally distinct models.
Duplicate simple cuts remain controls rather than additional mathematical coverage.
All random choices use the prospectively fixed seed 7007. The independent oracle
uses source-table assignment products and exact integers; it imports no producer
interval arithmetic or Lean transcription.

The exporter mutants change a factor row, halve the claimed output endpoints, or
omit recorded splits. They are applied to the real exporter source in memory.
Independent source-value and cut-bound assertions detect each mutation before the
expected-model binding check. Historical implementation files remain untouched.

## Proof review

`factor_bounds_sound` establishes that conditional extrema enclose the value of
each factor under every compatible environment. `model_bounds_sound` composes
these nonnegative integer bounds. `uniform_mass_bounds` establishes the completion
multiplier, and `leaf_bounds_sound` applies it to a prefix's contribution.
`cut_bounds_sound` checks both children of every split and adds their enclosures,
rejecting a split with no remaining variable. `check_sound` then derives enclosure
from the executable check's acceptance, without an enclosure premise.

The semantic partition `mass` recursively assigns each of the `n` binary variables
false and true and sums both contributions. It is the mathematical target, not a
routine evaluated by the certificate checker. The model validator rejects a factor
index outside `0..n-1`; the validity/congruence lemmas establish that a valid model
does not depend on unassigned variables outside that range.

The audited build used Lean 4.35.0 and only standard `propext`/`Quot.sound` axioms
in all 11 reported theorems. No `sorryAx`, native evaluation shortcut, extra
assumption about endpoint correctness or unproved numerical bound was accepted.
The exact theorem/axiom output is produced by the verifier on each build.

The final `checked_greater_sound` corollary composes six accepted partition
certificates into a strict affinity ordering with positive actual denominator
products. Its premises validate the partition construction rather than assuming
true endpoints. The JSON CLI exposes individual partition requests; the composed
predicate is exercised directly by the Lean runner. That runner passes 27 curated
individual cases, six rank cases and three deliberately unprovable mutants
(missing completion count, omitted right branch and minimum used as upper bound).
These implementation fixtures are separate from the 737 independently selected
certificate executions above.

## Source identity and parser boundary

A changed model with honestly recomputed bounds is valid for its own target and
was accepted by raw Lean. The same certificate was rejected as `binding_mismatch`
when submitted with the original expected model through the public Python bridge.
This is the intended distinction: the mathematical theorem cannot know which
external model the caller intended.

The adapter compares the complete canonical factor descriptor and variable count
against the caller-supplied immutable model. It rejects Python booleans/floats,
malformed shapes and extra or missing fields before serializing unique fields for
Lean. Source-table-to-decision-tree translation is independently tested rather
than proved in Lean. The caller's source model and this translation/binding layer
remain trusted alongside the parser, compiler/runtime and integer/IO machinery.

The raw Lean JSON decoder normalizes duplicate object keys. A raw line containing
`"n":0,"n":1` was accepted according to the resulting parsed model; this is not
counted among the rejection controls. A raw integral decimal `"n":1.0` was invalid
in the inspected parser. The bound Python entrypoint emits a five-field object
only after strict target binding, and no bypass of that binding was found.
The raw CLI is therefore a checker for its parsed model, not a strict canonical
JSON or external identity verifier. No unique-key raw-syntax guarantee is claimed.

## Scope and reproduction

A supplemental, post-exposure structural control verified an empty-factor model
with 1,000 binary variables using one root leaf and exact endpoints `2^1000`.
It passed without constructing those global assignments. This supports the code
inspection that checking follows the supplied cut; it is not a timing result or
an addition to the frozen scientific panel.

Run from the repository root:

```sh
python3 -B grader/campaign-007/audit.py
python3 -B grader/campaign-007/audit_lean.py
```

The second command compiles the Lean proof, audits its reported axioms and checks
the actual JSON-line executable. No old bulk data, molecular inputs or external
competition instances are needed.

This establishes checked finite-model partition bounds for the supplied parsed
decision-tree model, with an independently tested adapter to the original factor
tables. It does not prove the Python interpreter or the parser/encoding itself,
establish a faster solver, validate biological energies, or implement the ETH
counting algorithm. Certificate checking work remains a cost to account for in
any later performance experiment.
