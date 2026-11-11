# Campaign 008: the external continuation gate failed

The current certified prefix-search configuration resolved **none of six external
ordering queries**. Ganak resolved two; four exceeded the query time budget.
Exact Python VE hit its intermediate-table cap on all six. The prespecified
continuation gate failed, so the supported next step is to archive this
4,096-expansion configuration as a verified prototype.

This is a bounded local experiment on inputs from the
[Model Counting Competition 2026](https://mccompetition.org/2026/mc_description.html).
It is not an official competition result, biological validation or a benchmark of
the ETH paper's algorithm. The [independent report](grader/campaign-008/REPORT.md)
contains the full assessment and its limits.

## Frozen question and inputs

Each query compares two CNFs' satisfying-assignment probabilities:
`Z_A / 2^n_A` versus `Z_B / 2^n_B`. These artificial numerical comparisons test
whether partial, checked bounds can settle an ordering before full exact counts
are available. Normalization avoids giving a larger declared domain an automatic
raw-count advantage.

The official Track 1 public archive contained 100 inputs. Static syntax and size
limits admitted 24: at most 256 variables, 2,000 source clauses, six distinct
variables per non-tautological clause and 50,000 explicit factor entries.
Seed 8008 selected 12 eligible inputs before any exact counting or timing, then
paired adjacent selections into six queries. The complete
[cohort and exclusion catalog](experiments/external_count8/COHORT.json) retains
every source hash and selection detail. Family-level independence was not
established; these public inputs were external to our prior synthetic development.

The [prospective protocol](grader/campaign-008/PROTOCOL.md) and
[operational amendment](grader/campaign-008/AMENDMENT-001.md) preceded measurement.
An initial metadata-only selection shuffled all members before filtering; it was
corrected to the protocol's eligible-first shuffle before any external count or
timing. Five members exceeded an acquisition decompression cap, but their headers
already violated the declared eligibility limits; that cap did not change the
eligible cohort. No outcome-based exclusions or replacement queries were used.

## Results

All 54 invocations were recorded, with consistent outcomes across three repetitions.
The measurement campaign took 160.94 seconds. Every method had a 10-second hard
query limit. The prefix method additionally had a 4,096-expansion cap; VE could
materialize at most 262,144 entries in an intermediate table.

| Query | Official instance IDs | Certified result; median total seconds | Ganak result; median total seconds |
|---|---|---|---|
| Q01 | 003 / 021 | Unresolved; 0.234 | Timeout; 9.877 |
| Q02 | 087 / 053 | Unresolved; 0.961 | Timeout; 9.885 |
| Q03 | 051 / 049 | Unresolved; 0.418 | Timeout; 9.879 |
| Q04 | 001 / 101 | Unresolved; 0.435 | A greater; 0.106 |
| Q05 | 023 / 047 | Unresolved; 0.337 | Timeout; 9.883 |
| Q06 | 097 / 055 | Unresolved; 1.055 | B greater; 0.104 |

[Complete summary CSV](experiments/external_count8/results-v1/RESULTS.csv) and
[all raw measurements](experiments/external_count8/results-v1/RAW_RESULTS.json)
retain every repetition, table-cap result, partial exact count and timeout.
Returning an unresolved answer quickly is not a time-to-solution advantage.

The gate required at least two correct nontrivial strict decisions with median
total time at most half that of the fastest matched exact baseline. There were
zero qualifying decisions. All certified runs stopped at the expansion cap;
none used the full wall budget. This is not a matched-used-time rejection of the
entire algorithm family. A higher-cap sensitivity study remains unmeasured and
must not replace this failed primary result.

## What failed and what still worked

Both lower partition bounds remained zero in every query, so the intervals could
not strictly separate. Every query spent all 4,096 expansions and produced 8,194
cut nodes across its two models. Valid certificates are insufficient when their
bounds remain too weak to answer the question.

The verification component worked. Native checking, including model binding,
serialization, process startup and checking, took median 0.076--0.452 seconds per
query. Certificate payloads ranged from about 32 to 321 kB. These costs were
included in total query time. The one-off native Lean build/audit took 6.593
seconds and is reported separately. Download/install time was not measured and
is excluded; no per-query proof compilation was hidden in the timings.

The baseline was the official native ARM64 Ganak 2.9.0 executable in integer mode
with probabilistic caching disabled, one thread, fixed seed and a prespecified
fast preprocessing profile. Every accepted count had an explicit zero-error,
zero-failure-probability output declaration. The Python wrapper was rejected as a
baseline because its exposed interface did not disable probabilistic caching.
[Baseline provenance](experiments/external_count8/baseline-provenance.json) pins the
release, binary, source and arguments; [build metadata](experiments/external_count8/NATIVE_BUILD.json)
pins the native Lean checker built from unchanged campaign-007 sources.

The native process verifies both partition enclosures. The host makes the exact
normalized cross-product comparison using the previously tested arithmetic
predicate. Its mathematical formula has a Lean proof; the complete host program,
DIMACS translation and JSON decoding are not kernel-proved.

## Independent validation and interpretation

The grader verified all 54 records and 18 summary medians, replayed all 36 saved
certificates through the native checker, and performed 129,456 source-clause,
factor-table and decision-tree assignment comparisons. Seven source instances had
consistent exact reference counts from Ganak and any available VE results; five
remained unconfirmed within the budgets. Unknown references were never treated
as zero or used to assert an ordering.

The result supports pausing this prefix configuration. It does not establish that
more computation, another variable order, stronger bounds or another search policy
would fail. Such work would be a new experiment. Keep the proved checker as a
reusable component; there is currently no measured external benefit that justifies
expanding this particular configuration or polishing more proofs around it.

The [reproduction guide](experiments/external_count8/README.md) describes the
source/binary seals and local data requirements. Raw CNFs and their converted
factor/certificate payloads are not mirrored because redistribution terms were
not established. Public metadata, code, result counts/bounds and hashes are kept
separately. Earlier release data and historical campaign files are unchanged.
