# Independent grading: campaign 006

Assessment date: 2026-11-10. This report separates exact discrete-model safety
from performance and biological usefulness. The grader owns this directory and
did not implement the producer, choose favorable measured cases or run timing
workers.

## Controls and findings

The prospective [protocol](PROTOCOL.md), [construction detail](AMENDMENT-001.md)
and executable source seal precede measurements. The independent assignment-product
oracle imports no implementation arithmetic. It uses `Fraction` for affinity.

`python3 -B grader/campaign-006/audit.py` passes on the sealed implementation:

- 144 random nonnegative integer factor models with zero through five variables;
  2,880 independently enumerated prefix enclosures and 857 monotone refinements;
  every exhausted producer equals the independent exact partition.
- 10,000 random actual-value/enclosure worlds; all 1,000 accepted comparisons
  preserve the independent rational ordering. Invalid numeric types, negative or
  reversed endpoints and zero lower denominators are rejected.
- Deterministic controls cover stale generations even when revision numbers repeat,
  replayed tickets, wrong result identities, widening bounds, model-content reuse,
  zero numerator and denominator, exact ties, zero budget and invalid singletons.

The initial audit found two edge cases before the source seal: a non-integer
endpoint could enter the public checker, and a singleton candidate could pass a
vacuous comparison despite an invalid lower denominator. Both were fixed before
timing; the singleton failure was reproduced on the actual Python controller.
The cache API also gained an explicit producer-result identity check before the
seal. All three are covered by deterministic regressions.

`python3 -B grader/campaign-006/audit_mutants.py` substitutes twelve single
mutations into the actual source in memory and requires independent audit
assertions to fail. All twelve are rejected: nonstrict rank, upper endpoint as
lower endpoint, wrong denominator, removed integer validation, removed generation
or revision check, removed result identity or nesting check, incomplete model
identity, invalid singleton acceptance, wrong prefix upper bound and omitted
completion count. This does not edit the measured source.

## Formal scope

The Lean arithmetic model proves that valid enclosing endpoints and its strict
integer predicate imply the true ratio ordering; it also provides arithmetic
composition lemmas. Shared executable cases compare the compiled Lean checker,
the actual Python checker and independent arithmetic. A proof of a mathematical
transcription is not a proof of the Python interpreter or full prefix-tree
implementation. Exhaustive/random oracle checks support that remaining boundary.

The cache accepts enclosures from trusted keyed producers. Generation, revision,
identity and nesting checks prevent particular stale or mismatched results; they
do not authenticate arbitrary external workers or establish numeric soundness of
worker results. The benchmark controller is sequential. Any TLC result concerns
the stated finite cache model rather than an asynchronous production deployment.

## Result-set handling

The initial `results/` collection is retained as a contention diagnostic because
formal checking overlapped CPU execution. Its correctness audit passes for all
96 rows: 47 case/target combinations independently enumerated and matched by the
native VE and enumeration baselines; 282 returned partition intervals enclosing
their exact values; 81 correct strict-winner rows; 78 sound accepted witnesses;
all 32 reported medians matching raw measurements. These timing values are not
used to choose a headline.

The [operational amendment](AMENDMENT-002.md) prescribed exactly one complete quiet
rerun using the same sealed scientific source. Its independent full-row audit also
passes with the same counts: 96 rows, 47 native target checks, 282 sound intervals,
81 correct strict-winner rows, 78 accepted witnesses and 32 correct medians. All
eight cases and all four methods completed without timeouts. Timed regions include model construction,
content identity, producer preparation, controller and certificate operations;
they exclude Python startup/imports, external proof checking and the independent
oracle. The very small synthetic panel does not measure biological preparation,
sampling uncertainty or energy-model error.

## Quiet-run performance verdict

The adaptive-work gate passes. The matched native-VE speedup gate fails.
Use all `results-v2/` measurements for these conclusions; times below are medians
of three fresh-process invocations, with startup/imports outside the timed region.

| Case | Adaptive / fixed expansions | Adaptive ms | Fixed ms | Exact VE ms | Adaptive-work gate |
|---|---:|---:|---:|---:|---|
| uniform8 | 0 / 0 | 0.625 | 0.654 | 0.628 | Trivial root-exact control |
| concentrated8 | 144 / 576 | 4.586 | 10.202 | 1.062 | Pass |
| concentrated12 | 528 / 2,016 | 19.869 | 48.168 | 1.852 | Pass |
| shared12 | 176 / 672 | 6.590 | 12.527 | 1.114 | Pass |
| independent_dense8 | 1,152 / 1,872 | 64.743 | 69.300 | 9.511 | Fail |
| independent_dense12 | 8,656 / 20,000 | 939.157 | 1,496.483 | 170.276 | Pass against capped fixed run |
| near_tie8 | 944 / 256 | 19.099 | 3.722 | 0.519 | Fail; fixed leaves ranking unresolved |
| exact_tie8 | 255 / 64 | 4.208 | 0.845 | 0.187 | Fail; fixed leaves ranking unresolved |

Three nontrivial cases meet the frozen work/time thresholds while the fixed method
also reaches its required partition tolerance. The dense12 comparison additionally
meets the literal gate, but the fixed method exhausts its 20,000-expansion budget
before attaining 1% precision. Both methods still certify its correct winner; this
row is not evidence about the time needed to attain the fixed precision target.
No favorable-case selection is needed for the gate to pass.

Adaptive stopping certifies the strict winner in every one of the seven non-tied
cases and identifies the exact tie in the eighth. Fixed precision leaves both
near_tie8 and exact_tie8 unresolved despite meeting its partition precision target.
This illustrates why a fixed partition-error target does not determine ranking
resolution. Resolving those difficult comparisons costs the adaptive method more
work, which the table retains.

The native exact Python VE baseline is faster in every nontrivial case. The tiny
uniform control differs by about 0.4% and is excluded from the useful-work claim.
Thus the result is a tested, mathematically sound stopping rule with real savings
over this fixed-precision refinement policy, not an overall solver improvement.
Some chain constructions differ by known scalars or gauge transformations; a
specialized symbolic algorithm could exploit these relationships more strongly.
The independent dense controls and the native VE comparison limit extrapolation
from the chain examples.

This makes the formal-methods lane concrete: exact enclosing integer arithmetic,
explicit unresolved states, safe content reuse and independently checked ranking
certificates can be implemented on a laptop. Further useful work should integrate
the certificate policy with a faster domain-native bound producer and test harder
nontrivial targets; enlarging this particular Python prefix enumerator is not
supported as a solver-speedup route by these measurements. The integer surrogate
does not supply interval-certified Boltzmann factors from physical energies or
assay validation.

## Reproduction

Run the independent source controls and mutants from the repository root. After
generating benchmark output, check every row with:

```
python3 -B grader/campaign-006/audit_results.py experiments/certified_rank6/results-v2
```

The same command accepts any retained full result directory. It verifies the
sealed source, all cases/repetitions, raw timing summaries, input coefficient-bit
inventories, every returned partition interval, every claimed strict winner and
the accepted witness table. No old campaign datasets are required.
