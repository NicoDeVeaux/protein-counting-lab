# Campaign 007 prospective verification protocol

Frozen by the independent grader on 2026-11-10 before evaluating the new checker.
This is a correctness and trust-boundary study, not a speedup benchmark.

## Target contract

The input is a finite nonnegative-integer factor model on `n` binary variables,
a binary split certificate and claimed partition endpoints. The intended partition
is the sum, over all `2^n` assignments, of the product of factor values. Factor
tables may be represented as binary decision trees, but the public input's variable
count, scopes and coefficients must retain their meaning under that translation.

A leaf at prefix `p` bounds the contribution of every remaining assignment using
conditional factor minima/maxima and `2^(n - length(p))`. A split replaces one
prefix with its zero and one children and sums both child intervals. No branch may
be omitted or duplicated. Splits below depth `n` are invalid. Claimed endpoints
must equal the checked construction or satisfy an explicitly proved permitted
weakening rule. They must enclose the independently computed partition.

Lean must prove the executable construction's soundness for all well-formed inputs,
including factor extrema, completion multiplicity and binary-cut coverage. A proof
assuming the produced endpoints enclose the partition does not achieve this gate.
The checker must not compute the full global partition by exhaustive enumeration
merely to validate its enclosure. Its parser, translation, serialization and runtime
remain explicit trust boundaries unless separately proved.

The result concerns the exact parsed model. Binding that model to the caller's
intended target requires an independent expected identity or canonical input bytes.
A checksum copied from an untrusted certificate does not establish that binding.
Changing an in-range variable or coefficient may form another valid model, so the
test must distinguish a valid different target from malformed input.

## Fixed validation panel

Use ordinary source factor tables and an independent assignment-product oracle.
The oracle must not import the producer's interval arithmetic or Lean transcription.
Use exact integers throughout; no floating tolerance is permitted.

- Deterministic controls: zero variables; no factors; scalar factors; zero and
  positive constant factors; repeated factors; unused variables; sparse scopes;
  chain and complete pairwise factors; nonuniform tables; and coefficients above
  `2^128`.
- Seeded tiny models: seed `7007`, 60 models with variable counts cycling through
  `0..5`, factor counts `0..6`, scopes of arity at most three, coefficients `0..9`.
  Check the root leaf, a complete binary cut and partially refined cuts after
  `1`, `3` and `7` valid prefix splits where possible. Repeated equivalent cuts
  may be reported as duplicate controls rather than extra coverage.
- Integration controls: campaign-006 `concentrated8`, `shared12` and
  `independent_dense8`, using their first candidate's three state models and cuts
  after `0`, `1` and `16` splits where possible. Independently enumerate those
  states outside the checker. Use the supplied immutable model content, not labels.

For every accepted certificate, compare parsed target identity, verified endpoints
and the independent exact partition. A fully refined cut must return the exact
partition. Compare the exported source table's value with the parsed decision tree
on every assignment for tiny models; this tests the translation boundary directly.

## Rejection and mutation controls

Check parser behavior on negative/noninteger weights or indices, out-of-range
variables, malformed nodes, incomplete/extra children, depth overflow, truncated
tokens, trailing garbage and malformed endpoint order. Require complete input
consumption. Extra input must not silently change which model was checked.

On fixtures where the change matters, reject a forged endpoint, a missing branch,
a wrong completion multiplicity and an export that changes a coefficient or scope
while retaining the expected source identity. Altered valid cuts may remain valid
certificates if the new checked bounds and target are honestly declared; do not
mislabel that as a soundness failure.

Demonstrate that a changed completion factor or dropped-child implementation is
detected by the Lean proof or executable differential harness. Also show at least
one actual Python exporter mutation is rejected by the independent oracle/binding
check. Do not edit historical campaign source to create these mutants.

## Evidence and interpretation

Record theorem names, Lean version, exact axiom reports, expected/observed controls,
accepted/rejected totals and every exclusion/failure. Reject `sorryAx`, native
evaluation shortcuts such as `Lean.ofReduceBool`, and undeclared axioms. Standard
Lean axioms must be listed if used. Retain the actual API and parser assumptions.

Report certificate nodes/bytes and checking cost only if measured, without a solver
speedup claim. No molecular inputs, external counting corpus, cloud resources or
bulk historical data are needed. Successful checking narrows the producer trust
gap; it does not prove the Python interpreter, physical energies, biological
accuracy, or the ETH algorithm.
