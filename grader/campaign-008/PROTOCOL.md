# Campaign 008 prospective external benchmark protocol

Frozen by the independent grader on 2026-11-11 before exact reference counts or
performance measurements. This is one bounded external gate for the existing
prefix-bound producer and Lean construction checker, not a new solver claim.

## Question and frozen cohort rule

Can certified partial counting decide an ordering on external, nontrivial inputs
at least twice as fast as the fastest matched exact baseline, including producer
preprocessing, certificate generation, model binding and verification costs?

Use the organizers' MC2026 public Track 1 archive. Retain the archive URL, digest,
byte size, retrieval date and complete member catalog. Do not use exact answers,
solver success or timings to select instances. The source is external to all
previous synthetic development, but public competition instances are not secret
holdouts and family-level independence is not assumed without provenance.

Parse and inventory every candidate before selection. Eligible ordinary CNFs have
at most 256 declared variables, 2,000 source clauses, six distinct variables per
non-tautological clause and 50,000 explicit factor-table entries after semantics-
preserving literal deduplication/tautology handling. Preserve unused declared
variables. Reject malformed files and unsupported weighted or projected semantics
explicitly; a filename/track label alone does not establish their absence.

Sort eligible normalized member paths lexicographically, shuffle with Python
`random.Random(8008)`, and select the first 12. Freeze the resulting source-byte
hashes and the entire eligibility/exclusion table before computing any reference
counts. If fewer than 12 are eligible, report that feasibility result; do not
relax criteria based on outcomes. A metadata-only prospective amendment may be
made before any exact counts/timings and must preserve this original protocol.

Pair consecutive selected instances into six disjoint numerical queries. Query
`(A,B)` asks whether `Z_A / 2^n_A` is greater than, less than or equal to
`Z_B / 2^n_B`. This normalization removes a domain-size-only raw-count advantage.
These are artificial probability-ordering tasks built from external CNFs, not
biological measurements or a reproduction of official competition scoring.

## Methods and correctness contract

Run all three methods on every query:

1. The unchanged campaign-006 prefix-bound producer, adapted to this two-model
   query, followed by the campaign-007 Lean construction checker. At each step
   choose the refinable model with the largest normalized interval width
   `(upper-lower)/2^n`, breaking ties in A/B order, and refine at most 16 prefixes.
   Use at most 4,096 total prefix expansions per query. Stop on a strict interval
   separation, a proven exact tie, exhaustion, or the resource budget.
2. An established exact counter, preferably Ganak with verified unweighted integer
   arithmetic and probabilistic caching explicitly disabled. A Python API is
   eligible only if its deterministic, lossless arithmetic and cache behavior
   have been established for the pinned version. MPFR approximation or default
   probabilistic counting does not satisfy this method.
3. The existing exact native-to-the-model variable-elimination baseline, with a
   prospective maximum intermediate table of 262,144 entries. Retain table-cap
   failures explicitly rather than silently switching algorithms or dropping rows.

Every strict comparison uses exact integer cross multiplication. A certified
method may claim a direction only after both model-bound certificates are
accepted and the submitted interval endpoints strictly separate after exact
normalization. Equal point estimates or overlapping intervals cannot establish
a tie. A tie is solved only with exact, equal normalized values. Unresolved and
timeout outcomes are safe but are not solved decisions.

Keep each method's cache cold between invocations. The exact counter and VE must
solve both members of a query within their timed invocation; they may not reuse
precomputed reference answers. Reference counts may be retained separately for
auditing after the cohort is sealed. Record the provenance and arithmetic mode
of each exact reference; unresolved references remain unresolved. A candidate
that disagrees with exact references or whose certificate/translation fails
invalidates a positive performance claim.

## Resource and timing budgets

Use three repetitions, rotating the fixed method order by repetition. Run
measurement workers sequentially while Lean builds, solver installation,
independent audits and other campaign computation are idle. Use one solver
thread and a 10-second hard wall limit per query/method invocation. Retain crashes,
memory limits, table-cap failures, malformed outputs and timeouts as outcomes.
The complete measurement campaign has a 900-second wall cap; if reached, retain
completed rows and mark the remainder not run rather than selecting a subset.

Build and audit a native Lean checker once before measurement, pinning the proof
and CLI source bytes and executable digest. Report compilation/build costs
separately. The primary certified-method timing includes input loading and
translation, actual prefix search, certificate serialization, full expected-model
binding, native checker process startup/parsing/checking, and final comparison.
Do not accept self-reported producer timings as the whole measurement. The
currently interpreted `lean --run` bridge may be reported as a separate diagnostic;
it must not be mixed with the native-checker primary measurements.

Exact-baseline timing includes input parsing, solver startup/work, count decoding
and the normalized comparison. File download and one-time executable preparation
are excluded consistently and reported separately. Retain per-stage timing where
instrumented, total times, source coefficient/table sizes, expansion counts,
certificate nodes/bytes, outcomes, raw counts/bounds and every repetition.

Seal the selected cohort, translator, search policy, benchmark runner, baseline
wrappers, native checker sources/binary identity and this protocol before timing.
Any implementation fix that can alter outcomes or performance needs a new sealed
version and a complete rerun, with failed evidence preserved.

## Independent checks and continuation gate

The grader independently checks DIMACS semantics and the factor/tree translation
on tiny exact controls: unused variables, no clauses, empty clauses, tautologies,
duplicate literals/clauses, sign/index errors, zero/one counts and large integers.
Do not use the implementation's interval arithmetic as its own oracle. Check
every claimed strict decision, every accepted certificate's binding and endpoints,
and the timing summaries against raw records. Verify native checker behavior
against the prior interpreted checker on identical certificate bytes.

The gate passes only with at least two nontrivial strict queries that are correct
and have certified-method median total time at most half that of the fastest
matched exact baseline which solves the same query. Both individual directions
need exact reference support. Initial root-exact controls are trivial and cannot
pass the gate. A baseline timeout or VE table cap alone does not establish a
2x speedup; classify such a row separately as a possible solve-rate result.

Report all six queries and all methods, including exact ties, unresolved results,
timeouts and unconfirmed references. A positive result must be repeatable and
survive translation/certificate controls. If the prefix method has no such
advantage, the supported conclusion is to archive this verified prototype and
stop investing in this particular search method. No biological, ETH-derived or
general solver improvement follows from a narrow pass.
