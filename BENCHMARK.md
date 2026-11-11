# What the benchmark measures

**Project closed on 2026-11-11.** These are completed, frozen studies and a
record of evaluator requirements. No optimization campaign or integration is
scheduled. See [the final decision](CONCLUSION.md).

There are two separately frozen performance studies. [Campaign 008](CAMPAIGN-008.md)
is the completed external continuation gate: six normalized count-ordering queries
from MC2026, with native verification costs charged and Ganak as a strong exact
baseline. It failed for the 4,096-expansion configuration: no certified ordering
was resolved. A larger-budget sensitivity remains unmeasured.

The internal development benchmark is **campaign006: certified strict top-1 ranking
on finite integer factor models**. Its prospective rules are in
[the independent protocol](grader/campaign-006/PROTOCOL.md); the
[implementation design](experiments/certified_rank6/DESIGN.md) explains the algorithms
and trust boundary. Earlier campaigns have their own frozen protocols and measure
different scientific questions; they are not interchangeable leaderboard entries.

Given three candidates, each described by complex, protein and ligand factor
models, calculate enough information to identify the unique largest
`K = Z_complex / (Z_protein * Z_ligand)`. Each Z sums nonnegative integer products
over binary assignments. A winner is accepted only if its rigorous lower affinity
bound exceeds every competing upper bound. Ties, invalid denominators and
unresolved rankings are explicit outcomes. A faster unresolved answer does not
count as a solved ranking.

## Frozen cases, competitors and outputs

There are eight synthetic cases with three candidates each and8 or 12binary
variables per state: uniform weights, two concentrated chains, a shared-state
chain, two independent dense graphs, a near tie and an exact tie. Main-panel
weights are strictly positive. Separate controls cover zeros, malformed bounds,
stale results and model-identity mix-ups. No molecular energies or assay labels
enter this benchmark.

| Method | Work performed |
|---|---|
| Adaptive | Refine exact integer partition enclosures until strict top-1 is certified or the budget is reached. |
| Fixed precision | Refine every distinct partition to 1% relative enclosure width, then attempt the same ranking certificate. |
| Exact VE | Native variable elimination on the identical factor models. |
| Enumeration | Exhaustively sum the identical models. |

Adaptive and fixed methods receive 20,000 prefix expansions per case. All methods
reuse only identical complete model targets within an invocation. There are three
repetitions with rotated method order, a 30-second invocation limit and a ten-minute
campaign limit. Timing includes model construction, identities, preprocessing,
cache/controller work and certification; it excludes Python startup/imports,
serialization, separate input inventory and independent validation.

The independent grader recomputes partitions by assignment-product enumeration,
uses exact rational affinity comparisons, and checks claimed intervals and
winners. Lean proves the mathematical certificate checker and interval
composition; it does not prove Python's frontier implementation. TLC checks a
finite model of deferred cache delivery. See the
[grader report](grader/campaign-006/REPORT.md) for adversarial and mutation checks.

The primary saved measurements are
[the second-run CSV](experiments/certified_rank6/results-v2/RESULTS.csv).
The first run is retained as a resource-contention diagnostic, according to the
prospective [operational amendment](grader/campaign-006/AMENDMENT-002.md).
Source seals and raw measurements accompany both runs. Uniform and identical-state
controls cannot establish a substantive adaptive-performance win. The frozen useful
work gate requires at least two other solved cases with at most half the fixed
method's expansions and 80% of its median time. A solver-speedup claim additionally
requires beating exact VE on those same cases.

## Requirements for a separate discovery-loop project

The current harness is a reproducible experiment, not an external competition
grader or a protected leaderboard. Its eight public cases and local source are
visible to an optimizer. Optimizing only those cases can reward memorized
thresholds and generator-specific shortcuts.

A subsequent optimization campaign should freeze a separate evaluator revision
and allow edits only to a candidate solver/policy. Useful search targets include
variable order, frontier scheduling, refinement batch size, candidate selection,
shared-state simplification and choosing between exact VE and bounded search.
Keep the exact certificate predicate fixed; replacing it requires a new proof and
grading contract. Changing a model or an energy table changes the target.

Use the public panel for development, then evaluate once on independently selected
external models and held-out graph families, seeds, sizes, coefficient ranges and
rank gaps. The evaluator must own reference answers, budgets and timing. It should
recompute identity and certificate validity, reject wrong answers, retain timeouts
and unsolved cases, and charge preprocessing and cache construction. Reward solved
certified rankings relative to strong same-target baselines; report solve rate
before runtime so abstention cannot improve the score. Tiny microsecond timings
need larger evaluation batches and controlled execution before steering a search.

This is a proposed evaluator contract, not an implemented integration or a frozen
new score. An existing external counting checker could strengthen numerical
correctness, but it would still need an adapter for factor models and three-state
ranking. Biological usefulness needs a separate held-out affinity-assay evaluation
with a matched molecular system. Success on synthetic counting does not establish
that final biological gate.

[The independent external-grader review](notes/EXTERNAL_GRADERS.md) originally recommended
screening public MC2026/MC2025 Track 4 instances for nonnegative, unprojected
weighted counting, with exact-rational Ganak as an independent reference. MC2022
is an archived fallback. It distinguishes that proposed evaluator from external Lean
count checkers, UAI factor-model benchmarks and assay-based biological grading.
No reviewed tool is a turnkey grader for the full three-state affinity task.

The subsequent campaign-008 gate used unweighted Track 1 inputs to keep its adapter
within the existing integer proof. It is a completed narrow negative result;
weighted/projection extensions and biological validation were not completed and
are not scheduled in this project.
