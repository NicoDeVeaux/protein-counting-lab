# Campaign 007: checked partition-bound construction

This is a small formal follow-up to [campaign 006](CAMPAIGN-006.md). The earlier
Lean ranking theorem assumed its partition intervals enclosed the true values.
The new checker recomputes partition bounds from a finite factor model and a
binary split certificate, and proves that construction sound. It does not require
an enclosure assumption supplied by Python.

## What changed

The Python exporter records the actual prefixes expanded by the existing
`PartitionBounds` producer. It builds a binary cut retaining both open subtrees
and subtrees that already became exact. Each factor table is serialized as a small
decision tree with variable indices and nonnegative integer leaves.

Lean independently traverses those factor trees. At each cut leaf it computes
conditional factor extrema, multiplies them, and multiplies by the number of
remaining assignments. At each split it evaluates both the zero and one branches
and adds their bounds. It rejects out-of-range variables, splits below full depth
and endpoints that differ from the recomputed construction.

The proof covers factor bounds, products, completion multiplicity and recursive
split coverage. A further corollary composes six checked state certificates into
a strict three-state affinity ordering, with no supplied-enclosure premise. The
JSON CLI checks individual partitions; the composition is exercised directly in
the Lean runner. The checker does not enumerate the global assignment space to
validate its bounds. A root certificate for an empty-factor model with 1,000
variables is included as an executable control; this is not a performance result.

The new [implementation](experiments/partition_certificate7/core.py) imports the
unchanged campaign-006 producer. The [verification bridge](experiments/partition_certificate7/verify.py)
checks the complete canonical model against an independently supplied expected
model before calling Lean. The old campaign's source, measurements and conclusions
are preserved.

## Checks and limits

The [prospective protocol](grader/campaign-007/PROTOCOL.md) fixes a small validation
panel. The [independent report](grader/campaign-007/REPORT.md) records the exact
outcomes, malformed inputs, source mutants and remaining assumptions.

The Python audit checks 382 actual producer certificates across 80 case/target
combinations and 45,237 assignment-level translation/coverage comparisons. The
Lean audit also accepts 355 certificates constructed independently of the
exporter. Forged bounds, malformed cuts and incorrect model binding are exercised
separately. Deliberately changed completion arithmetic and split construction
must fail the proof checks. All eleven theorems pass an exact axiom audit using
only Lean's standard `propext` and `Quot.sound`.

The proof concerns the parsed decision-tree model. Translation of original Python
scope/table inputs, the expected-model binding code, JSON decoding, the compiler
and runtime remain explicit trust boundaries. The translation and binding are
independently tested, not kernel-proved. In particular, reusing a faulty translator
on both sides of a model comparison is not an independent mathematical guarantee.

The raw Lean JSON decoder normalizes duplicate object keys. It verifies the model
it actually parses; it does not authenticate an external filename or reject every
ambiguous representation. The bound Python entry point constructs unique fields
after its expected-model check. See the [formal guide](formal/campaign-007/lean/README.md) for its exact interface and
axiom audit.

This narrows the mathematical bound-producer trust gap. It does not establish a
solver speedup, physical Boltzmann-weight certification, biological accuracy or an
ETH implementation. Checker costs were not included in campaign-006 timings.

## Reproduce

No historical bulk data or third-party Python packages are needed. Lean 4.35.0 is
pinned; only bundled libraries are used.

```sh
python3 -B -m experiments.partition_certificate7 --case concentrated8 --expansions 16
python3 -B grader/campaign-007/audit.py
python3 -B grader/campaign-007/audit_lean.py
sh formal/campaign-007/lean/check.sh
```

The first command exports and verifies a real partial producer state. The grader
commands independently check source tables, cut coverage, parser controls and the
actual Lean executable. The formal runner audits axioms and requires proof mutants
to fail. Builds use temporary directories.

The next useful engineering gate is a faster bound producer that emits this kind
of checkable evidence, evaluated with checking and preprocessing costs retained.
The input translation can also be moved into a proved decoder in a later step.
