# Deferred bound-cache checks

`BoundCache.tla` models the new Python [cache](../../../experiments/certified_rank6/core.py)
at its actual API boundaries: `begin` (line147), atomic serialized `commit`
(line150), and in-memory `restart` followed by registration (line162).
It explores delayed result delivery to two distinct complete model identities,
with one or two jobs and at most one API reset. Every worker submits at most one
job. The actual benchmark controller runs sequentially.

The producer's arithmetic is trusted here. A computed enclosure is sound for its
declared result key and refines its ticket's snapshot; delivery can mix up result
keys. Each guard independently checks result identity, in-memory generation,
current revision, or nesting inside the current cache enclosure. These assumptions
are essential: a claimed key does not authenticate an untrusted worker, and
monotone bounds alone do not prove they enclose the true partition.

The checker evaluates all 16 guard combinations against all 5 properties with both
worker counts:160 rows, zero mismatches. With all guards enabled, the two-job
model has 13,786 reachable states and every property holds. Removing the identity
guard permits an enclosure for target B to replace A's. Removing the generation
guard permits a ticket created before an API reset to commit afterwards. Removing
the revision guard permits replay. Disabling revision and nesting guards permits
an older, wider result to undo progress. The one-job controls show that the last
two failures require competing results in this finite model. Nesting is redundant
with the revision guard under the monotone-producer and bounded-job assumptions;
this does not establish redundancy for arbitrary future producers or lifecycles.

Run with a local [TLC v1.7.4 jar](https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4):

```sh
python3 -B formal/campaign-006/tla/check.py --jar /path/to/tla2tools.jar
```

The runner verifies the pinned digest, caps the JVM heap at 256 MB, uses one TLC
worker, limits each invocation to 30 seconds and puts metadata in temporary storage.
Expected failures must reproduce; a missing counterexample fails the run.
[RESULTS.md](RESULTS.md) retains the complete expected/observed table.

The installed `tlaplus-mcp` 0.2.1 was also launched through `mcporter` 0.16.1 with
a task-local configuration. It checked this actual model with all guards enabled
and reproduced four negative controls. [MCP_TRACES.md](MCP_TRACES.md) preserves the
full counterexample states without machine paths. The Lean MCP also successfully
reported the ranking theorem diagnostics and axiom audit. Neither required a
machine-wide configuration change.

An initial model transcription accidentally made its ghost-history checks guards
on transitions; the required negative controls exposed14 unexpected passes. That
model was rejected and corrected before the 160-row result reported here. The
executable cache tests and grader's source mutants independently exercise identity,
reset, replay and widening on Python.

This is bounded safety checking, not a proof of Python thread safety, durable
restart handling, liveness, arbitrary repeated jobs or the numeric bound producer.
`commit` is modeled atomically because calls are serialized. It contains no lock
for concurrent Python threads. An operating-system process reconstruction resets
the generation to zero; it is outside the modeled in-memory API reset.
