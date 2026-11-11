# Independent grading: campaign 008

Checked on 2026-11-11. The bounded external continuation gate **fails**. The
verified prefix method resolved none of the six queries. Its cheap unresolved
returns are not a speedup over exact solving.

## Prospective selection and execution

The [protocol](PROTOCOL.md) and [premeasurement execution details](AMENDMENT-001.md)
preceded all exact selected-instance counts and timing. All 100 compressed MC2026
Track 1 members were inventoried. Independent parsing reproduced 95 complete
inventories; prefix headers showed that the five eight-MiB-capped members already
violate the original variable and clause limits. That operational cap changed no
eligible member.

There were 24 eligible inputs under the frozen limits. Sorting eligible paths,
shuffling with seed 8008 and selecting the first 12 gives exactly the retained
cohort and six adjacent pairs. An initial metadata-only implementation shuffled
before filtering; it was corrected before any reference counts or measurements.
That correction did not use outcomes. The final public cohort bytes match the
independently audited selection.

All selected files declare ordinary model counting (`c t mc`), with no selected
weighted, projection or independent-support directives. The source formulas use
30–90 declared variables. Each query compares `Z_A/2^n_A` and `Z_B/2^n_B` by exact
integer cross multiplication. The task is a numerical ordering of external CNFs,
not a biological ranking or official competition scoring reproduction.

The measurement completed all 54 invocations: six queries, three methods and three
rotated repetitions. Source, cohort and native executable identities were sealed
before measurement and remained unchanged. Workers ran sequentially. Primary wall
time includes cold worker startup/imports and final output serialization, together
with the input, search, binding and verification operations. Native Lean setup was
performed once and reported separately: 6.593 seconds, including proof audit and
compilation. No interpreted Lean launch was substituted into the primary timings.

## Complete outcome table

Times are medians of all three supervisor measurements in seconds. A resource
failure remains an outcome, not a solved decision or a timing win.

| Query | Certified outcome | Certified seconds | Ganak outcome | Ganak seconds | VE outcome | VE seconds |
|---|---|---:|---|---:|---|---:|
| Q01 | Unresolved | 0.234243 | Timeout | 9.876700 | Table cap | 1.378115 |
| Q02 | Unresolved | 0.961474 | Timeout | 9.884815 | Table cap | 2.082004 |
| Q03 | Unresolved | 0.418190 | Timeout | 9.878813 | Table cap | 1.411071 |
| Q04 | Unresolved | 0.435140 | Solved, A greater | 0.105808 | Table cap | 1.843251 |
| Q05 | Unresolved | 0.337123 | Timeout | 9.882863 | Table cap | 3.390348 |
| Q06 | Unresolved | 1.055213 | Solved, B greater | 0.104224 | Table cap | 0.181777 |

Every certified invocation used all 4,096 allowed expansions and produced two
accepted interval certificates. All 36 lower endpoints remained zero and all
upper endpoints remained positive, so no strict probability ordering could be
established. The prefix method did not reach its eight-second soft search limit;
it stopped at the frozen expansion cap. This does not compare the algorithms after
equal amounts of used CPU/wall time or measure how this search behaves with its
expansion cap removed. Initial root bounds were nonexact in all
six cases. Expansion allocations and certificate bytes were deterministic across
repetitions. Each pair's two cut trees contained 8,194 nodes in total.

The native deterministic Ganak baseline solved Q04 and Q06 in every repetition.
Q04's counts are 48 at 56 variables and 3 at 64 variables, giving A greater.
Q06's counts are 3 at 64 variables and 18,014,398,509,481,984 at 80 variables,
giving B greater. Ganak timed out on the other four complete queries; some first
members were counted before the paired member timed out. In total seven of the
12 inputs have exact references under this run's budgets. The four unresolved
query orders are not asserted to be ties or assigned a guessed direction.

The exact variable-elimination baseline reached its predeclared 262,144-entry
intermediate-table cap on all 18 invocations. This is not an unconstrained VE
benchmark. The data also do not establish that Ganak is universally faster or that
all six exact query answers were obtained.

## Independent validation

The auditor checks the retained raw records, summary rows and actual private
certificate bytes, rather than relying on the experiment's verdict:

| Check | Result |
|---|---|
| Source/cohort/method seal | All 18 sealed file hashes match; saved and current seals agree |
| Selected CNF-to-table translation | 2,598 clause-factor tables match the independent source-literal oracle |
| Tiny parser/semantic controls | Eight valid and eight invalid inputs behave as expected |
| Raw result coverage | All 54 query/method/repetition records present exactly once |
| Summary times | All 18 medians recomputed from every repetition |
| Native exact references | Seven instance counts consistent across repetitions and available partial VE counts |
| Expected-model certificate replay | All 36 retained certificates accepted by the pinned native checker |
| Source clause/table/decision-tree values | 129,456 independent per-factor assignment checks pass |
| Bounds versus available exact references | All 21 repeated reference-enclosure checks pass |
| Continuation gate | Zero qualifying strict queries; fail |

The Ganak wrapper uses the pinned native ARM release with integer arithmetic,
`--prob 0`, one thread and a fixed seed. The independent output audit requires an
exact integer result, ordinary-counting task marker, zero epsilon/delta and a
consistent satisfiability status. Its reported log estimate is not used as a
reference. Exact counts and normalized comparisons use arbitrary-precision
integers throughout.

The native Lean backend compiles the unchanged campaign-007 construction checker.
Its prior control audit matches the interpreted checker, and the exact theorem
reports permit only the documented standard axioms. This proves enclosure for
the parsed decision-tree model. Original DIMACS parsing, table/tree translation,
input identity and native compiler/runtime remain explicit trust boundaries; they
are independently checked here rather than proved as one end-to-end CNF theorem.
The Python comparison is the previously checked strict integer predicate, not a
new native rank-request interface.

Full source formulas and certificate payloads remain outside the public Git
export while their redistribution terms are unverified. Public records retain
their source pointers, hashes, dimensions, endpoint/count results and timings.
The original payloads were available to this audit. Reproduction requires fetching
the pinned source and generating a fresh run; the public metadata alone is not
the original complete certificate payload.

## Interpretation and stopping decision

The gate required at least two nontrivial strict queries resolved correctly in all
three repetitions at no more than half the median total time of a matched exact
baseline. None qualified. Faster abstention and baseline timeouts cannot satisfy
that gate.

Verification is a measurable cost: the binding/serialization/native-check call
accounts for roughly 21–46% of certified total median wall time across these six
queries. However, this failure is not explained only by checking overhead. The
producer's zero lower bounds cannot resolve any of these orderings even if the
checker were free. Faster hardware with the same expansion cap would still produce
the same unresolved intervals sooner; reducing checker overhead alone cannot
resolve these queries.

The supported next action is to archive the verified construction and pause this
particular 4,096-expansion configuration as-is. A sensitivity run allowing the
prefix method to spend the full common wall budget was not performed. Such a run
could in principle alter its solve rate on the four Ganak-timeout queries; their
exact orders remain unconfirmed. It would be a separate, prospectively declared
secondary experiment, not a replacement for this failed primary gate.

This narrow negative result does not rule out higher expansion budgets, stronger
bound producers, other layouts, better search algorithms or certified partial
decisions as a general idea. Those require new evidence rather than a stronger
claim from the present data. No biological improvement, ETH implementation,
general counting speedup or new competitive solver follows.

## Reproduction

From the repository root, the independent audits accept explicit paths to the
pinned original archive/cohort and retained private certificate directory:

```sh
python3 -B grader/campaign-008/audit_inputs.py ARCHIVE COHORT_DIRECTORY
python3 -B grader/campaign-008/audit_results.py RESULTS_DIRECTORY COHORT_DIRECTORY PRIVATE_CERTIFICATES NATIVE_CHECKER
```

The second command reruns the certificate checker after timing, verifies source
identity and every available exact reference, recomputes summaries, and applies
the frozen continuation gate. Build/audit computation is kept outside the measured
campaign. Do not overwrite retained runs or tune the cohort using these results.
