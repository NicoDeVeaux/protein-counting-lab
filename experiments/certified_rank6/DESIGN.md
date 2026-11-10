# Exact discrete ranking prototype

This campaign uses synthetic binary factor models with explicit integer weights.
It has no molecular energy conversion, measured affinities, floating-point
partition sums or implementation of the ETH paper's counting algorithm.

For each prefix of an assignment, every factor supplies its minimum and maximum
over table entries compatible with that prefix. Multiplying those nonnegative
extrema and the number of remaining assignments bounds the prefix's partition
contribution. A disjoint frontier covers the whole assignment space. Replacing
one prefix by its two children tightens the summed bounds; exact subtrees can be
closed without evaluating every leaf. The heap selects the largest absolute
subtree gap. This producer is tested against independent exhaustive calculations;
the producer itself is **not** proved correct in Lean.

The controller combines three partition intervals into a numerator interval
`[cL,cU]` and denominator interval `[pL*lL,pU*lU]`. It declares A above B only if
both denominator lower bounds are positive and
`aNL*bDL > bNU*aDU`. This comparison uses exact integer multiplication, with no
division or logarithms. The Lean project proves the mathematical comparison's
soundness under its explicit enclosure assumptions. Agreement tests connect that
checker model to Python; they do not verify the Python interpreter.

The adaptive method discards candidates already strictly dominated by a valid
interval comparison. Among the remaining states it refines the largest relative
partition gap `(upper-lower)/upper`, in batches of 16 prefix expansions. It stops
when every comparison needed for a strict top-1 is certified, an exact top tie is
established, or the expansion budget is exhausted. It makes no top-k claim.
Fixed precision uses the same producer, refines every distinct required state
until `(upper-lower) <= lower/100` or budget exhaustion, then invokes the same
rank checker. A fixed-precision rank can remain unresolved.

The cache identity is the full variable count and sorted immutable factor tables,
including scopes and scalar factors. It uses exact equality rather than trusting
a short digest or candidate name. All methods, including enumeration and exact
variable elimination, reuse identical complete states within an invocation and
start with cold caches. Shared-state cases are synthetic representation controls,
not evidence for a particular protein-design workload.

`BoundCache.begin` and `commit` expose a deferred-result interface. A commit must
match its ticket's complete model key, in-memory generation and per-state revision,
and tighten the current enclosure. The actual benchmark delivers results
sequentially from the trusted local producer. The TLA+ model explores delayed
delivery and API-reset orderings at these boundaries. `restart()` is an in-memory
reset; generations are not persisted across process reconstruction. The cache has
no multi-thread lock, persistence protocol or untrusted-worker proof checker.
Nested bounds alone do not establish numerical soundness.

The native baseline eliminates one binary variable at a time, choosing the
smallest current factor neighbourhood with variable-index tie breaking. It uses
the same exact weights and complete-target reuse. Enumeration sums every explicit
assignment independently for each distinct state. Neither baseline is required to
use the prefix search. Enumeration's assignment count, VE's multiplication count
and prefix expansions are different work units and are not compared as if equal.
The `certification_calls` diagnostic counts comparisons within a complete-winner
certificate attempt; candidate-pruning comparisons are timed but not included in
that counter.

Each timed worker includes model construction, canonical identities and hashing,
bounds preparation, scheduling, caching and the final certificate check. Python
startup/imports, output serialization, input inventory and independent oracle
validation are excluded. Each invocation runs in a new process. Three repeats
rotate the fixed method order; individual times and medians are retained. These
small laptop timings support engineering gates, not general asymptotic claims.

`factor_entries`, `coefficient_bits_sum` and `coefficient_bits` inventory the
explicit integer tables after identical-state reuse. They exclude scope/index and
container overhead. `max_endpoint_bits` records the largest partition upper-bound
bit length at initialization for prefix methods (subsequent upper bounds can only
decrease), or the largest exact partition bit length for exact baselines. There
is no Boolean weighted-counting reduction here; the reported auxiliary-variable
count is zero because the models are used directly. This inventory does not bound
the encoding size of a physical-energy or ETH-derived implementation.

Reproduce small controls with:

```sh
python3 -B -m unittest experiments.certified_rank6.test_core
python3 -B grader/campaign-006/audit.py
```

The prospective source seal must match before `scripts/campaign6_benchmark.py`
runs. Existing results remain versioned; use `--output` for a fresh destination.
The independent protocol and its amendments define which run is used for the
reported performance gate.
