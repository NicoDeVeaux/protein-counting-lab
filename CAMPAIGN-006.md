# Campaign 006: certified adaptive ranking

This laptop experiment makes the certified-stopping lane concrete for exact
discrete surrogate models. It implements no ETH-derived algorithm and uses no
new molecular inputs or experimental affinity measurements.

The [benchmark guide](BENCHMARK.md) defines the question and prospective gates.
The [independent verdict](grader/campaign-006/REPORT.md) includes every case,
failure control and limitation. The [design](experiments/certified_rank6/DESIGN.md)
explains how the prefix bounds, controller, cache and native baselines work.

## Result

Three nontrivial cases meet the frozen adaptive-work gate while the fixed method
also reaches its required partition precision:

| Case | Adaptive / fixed expansions | Adaptive / fixed / exact VE milliseconds |
|---|---:|---:|
| concentrated8 | 144 / 576 | 4.586 / 10.202 / 1.062 |
| concentrated12 | 528 / 2,016 | 19.869 / 48.168 / 1.852 |
| shared12 | 176 / 672 | 6.590 / 12.527 / 1.114 |

Adaptive stopping certifies all seven strict winners and identifies the exact tie.
Fixed 1% partition precision leaves both the near tie and exact tie unresolved.
Dense12 reaches a valid winner with fewer adaptive expansions, but the fixed
method exhausts its budget before reaching 1% partition precision; that comparison
has a different stopping outcome. All eight cases and all four methods remain in
[the complete results](experiments/certified_rank6/results-v2/RESULTS.csv).

Native exact Python variable elimination is faster in every nontrivial case.
These results support spending only the partition precision needed for a ranking;
they do not establish an overall solver improvement. Known scalar/gauge structure
in the easy chain cases further limits generalization. A stronger producer and
external held-out models are the next meaningful gate.

## Validation and evidence

The [prospective protocol](grader/campaign-006/PROTOCOL.md), construction amendment
and source seal precede timing. The first run overlapped formal checking and is
retained as a diagnostic. A [prospective operational amendment](grader/campaign-006/AMENDMENT-002.md)
specified exactly one complete rerun after those processes finished. All timing
conclusions use that second run; scientific source and case choices stayed fixed.

Both 96-invocation collections pass independent exact-oracle audits. The grader
checks 282 returned intervals and 78 accepted witnesses per collection, all strict
winners, input-bit inventories and the 32 reported medians. Its adversarial tests
reject twelve source mutants. The source audit found and fixed two checker edge
cases before measurement.

The [Lean checker](formal/campaign-006/lean/README.md) proves eight theorems about
integer interval composition and strict three-state ranking. A combined executable
comparison covers 17,647 rows, including independent grader cases and 78 actual
benchmark witnesses, with no disagreements. The central ranking theorems are
axiom-free; the repeated-contribution lemma uses standard `propext` and `Quot.sound`.
The arithmetic proof assumes valid enclosing partition bounds. Python's frontier
coverage is independently tested rather than formally proved.

The [TLC checks](formal/campaign-006/tla/README.md) cover all 16 combinations of
four cache guards, five properties and one/two-job controls: 160 expected outcomes,
zero mismatches. Actual Lean and TLA MCP calls succeeded. The cache model concerns
serialized delivery and in-memory reset, not threaded execution, durable process
recovery, malicious workers or numeric enclosure validity.

Reproduce the Python checks with the commands in [README.md](README.md).
Lean needs the pinned 4.35.0 toolchain; TLC needs the pinned v1.7.4 jar. No historical
bulk data is needed. To generate a new benchmark run, use a **fresh** destination:

```sh
python3 -B scripts/campaign6_benchmark.py --output /tmp/new-certified-rank-run
```

The runner verifies its prospective source seal. It can overwrite files in an
existing output directory, so do not point it at retained evidence. Reproduction
on another host is a new measurement and must not replace the saved results.
