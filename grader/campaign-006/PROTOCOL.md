# Campaign 006 prospective protocol

Frozen by the independent grader on 2026-11-10 before performance measurements.
This is a laptop proof of concept on synthetic discrete models. It tests whether
exact partition enclosures can stop once a strict top-1 affinity rank is proved.
It tests neither the ETH algorithm nor biological predictive accuracy.

## Contract

Each binary factor table contains nonnegative integers, with exact integer
arithmetic throughout the producer and certificate checker. Main-panel weights
are strictly positive. For each candidate, K = Z_C / (Z_P Z_L). A result may name
a strict winner only when its lower affinity bound exceeds every other upper
bound. Partition bounds must enclose the independent exhaustive partition, remain
ordered and tighten monotonically. Exhaustion must return the exact partition.
Bounds with invalid order, negative entries, missing states or nonpositive lower
denominator bounds cannot certify. Ties, budget exhaustion and invalid
denominators remain explicit outcomes. A result is a certificate only for the
exact discrete model identified in its input, including every factor entry.

Caching may reuse only identical complete model targets. Labels alone are not
identities. Distinct factors with identical labels must not share evidence.
Any asynchronous orchestration must reject mismatched identities and stale
generations before its result can influence a certificate.

## Frozen panel and methods

There are three candidates per primary case:

| Case | Variables per state | Required construction |
|---|---:|---|
| uniform8 | 8 | All entries in each factor are equal; root bounds are exact. |
| concentrated8 | 8 | Unary bias (1,9), chain pair factors (9,1,1,9); complex scalar factors 1,2,8. |
| concentrated12 | 12 | The same positive construction at the larger size. |
| shared12 | 12 | The positive chain construction; every candidate shares the complete protein and ligand targets; complex scalars 1,2,8. |
| independent_dense8 | 8 | Every pair is an edge; independent tables of integers 1..9, seed 601 with fixed candidate/state offsets. |
| independent_dense12 | 12 | The same dense construction, seed 602. |
| near_tie8 | 8 | A common positive chain target; complex scalars M,M+1,M+2, M=1,000,000; equal denominator values. |
| exact_tie8 | 8 | Identical complete complex, protein and ligand targets for all candidates. |

The deterministic generator, offsets, tie-breaking, variable order, refinement
quantum and implementation source are sealed by their SHA-256 hashes before any
timing. The construction fixes biological and optimization choices; the source
seal fixes remaining executable details. Any necessary recipe change is a
prospective amendment, never an outcome-driven replacement of a panel case.

Run adaptive strict top-1 stopping, fixed relative partition precision 1/100,
native exact variable elimination and full exhaustive enumeration on every case.
Fixed precision uses the same producer and exact certificate checker. Its stopping
criterion is (upper-lower) <= lower/100 for every required unique state; unresolved
rankings after that precision are reported rather than rounded into winners.
Use one content-identity cache per method invocation, including the exact
baselines; discard caches between invocations. Retain preprocessing and controller
costs. Report any deliberate stronger dependency cancellation separately.

The adaptive and fixed-precision methods have 20,000 prefix expansions per case,
with the actual used count recorded. No state has more than 2^12 assignments.
Time-limit an individual method invocation to 30 seconds and the campaign to ten
minutes; record a timeout instead of removing its case. Three complete repeats
use a fixed method order rotated by repetition. Report individual times and
medians, peak memory where measured, unique-state counts, prefix expansions,
exact-leaf counts, certificate status and oracle agreement. Wall time includes
model construction, identity hashing, bounds preparation, scheduling, caching and
certificate checking. Keep oracle validation outside timed regions.

## Independent checks and interpretation

The grader computes Z by an independent assignment-product implementation and
uses Fraction for affinity. Check every returned partition interval and every
claimed strict winner. Include tiny exhaustive/random grids and deterministic
controls for zero numerator, zero denominator, exact ties, zero budget, wrong
model identity, stale generation and malformed interval endpoints. Where no
asynchronous code exists, mark the stale-generation control inapplicable instead
of inventing concurrency. Show deliberate endpoint/cross-product/identity mutants
are rejected. A failed control invalidates any performance headline.

Lean should prove the integer cross-product soundness contract for all natural
endpoints and true partition values, with explicit enclosure/positivity premises.
Audit its axioms and show a changed inequality breaks a proof or concrete harness.
This proves a mathematical checker model, not the Python interpreter or floating
physical energies. Test the executable Python checker against the same cases.
TLC checks the finite scheduling/cache model if the implementation has such
interleavings; report the modeled scope and positive/negative control rows.

Report all eight primary cases and all failures. Initial exactness in uniform or
identical-model controls is a trivial result. A useful adaptive-work result needs
at least two other cases with a valid strict winner, at most half the fixed-method
expansions and at most 80% of its median wall time. Calling the method a solver
speedup additionally requires beating the matched exact VE baseline on those
cases with preprocessing charged. Otherwise distinguish saved refinement work
from an actual overall speedup. Near ties and ties are expected stress cases;
an unresolved answer is safe but is not a solved ranking. No panel aggregate may
hide failures, timeouts or unresolved cases.

Successful proofs without a useful performance result are a valid negative
engineering outcome. Proposed extensions must remain clearly separate from
completed checks. No old campaign data, model energy files or assay measurements
are needed for this campaign.
