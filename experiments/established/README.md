# Established exact-inference comparator

This adapter uses **pyagrum 3.3.2** and its C++ Shafer-Shenoy MRF engine. It is not an ETH implementation, a native partition-function API benchmark, or a certified interval solver.

The public `evidenceProbability()` method returns normalized evidence probability and returns 1 with no evidence. Treating it as a partition function would be incorrect. The adapter instead selects a complete feasible assignment using the largest positive conditional marginal at each variable, accumulates its conditional log probability, and reconstructs `log Z = log W(assignment) - log P(assignment)`. This requires one conditional inference query per variable; all query costs are included.

## Runtime

From the repository root:

```sh
uv sync --project experiments/established --frozen --group dev
uv run --project experiments/established --frozen python -m experiments.established MODEL.json --max-table-bytes 134217728 --output RESULT.json
uv run --project experiments/established --frozen --group dev pytest -q tests/test_established_pyagrum.py
```

The dedicated lock preserves the earlier root environment. It pins pyagrum 3.3.2 and NumPy 2.5.4; CPython 3.13 is required. The same environment can run all comparison methods and the parent RSS watchdog.

## Representation and arithmetic

Scalar factors become explicit log offsets. Identical scopes are merged in log space; each factor is shifted by its maximum before exponentiation. Singleton and isolated variables remain in the sum. Source hard zeros remain zero. Any positive entry that becomes zero is rejected as `conversion_underflow`; exp/log roundtrip diagnostics exceeding a total 1e-9 log-unit threshold are rejected as `conversion_accuracy_limit`. These diagnostics are floating estimates, not rigorous error certificates.

An all-zero scalar or merged factor proves zero partition mass directly. An incompatible-evidence result proves zero only in the conservative normal-positive-product regime; otherwise it is reported as numerical failure or unresolved zero support. A finite result can still fail the campaign's independent reference check, particularly when linear message products underflow. No state is silently pruned to avoid this.

## Resource and timing scope

Before constructing the inference engine, the adapter uses the package's `JunctionTreeGenerator` on the native MRF. The resulting maximum clique table is a **wrapper preflight policy**, not a native solver failure or an RSS guarantee. The actual engine tree is also reported. The 3.3.2 binding only accepts integer gigabytes for `setMaxMemory`, so its scheduler setting is rounded up to at least 1 GB and recorded. External process RSS and wall-time limits must be enforced by the parent driver.

Records separate JSON loading, numerical factor conversion, package import, native network/tree preprocessing, conditional-inference kernel, total adapter time, and process peak RSS. Parent wall time additionally includes interpreter/import startup. Process RSS includes libraries and input data; estimated clique bytes describe one table only.

Primary sources and installed distribution metadata are recorded in `sources.json`. No published-model measurements were executed during adapter preparation; tests use synthetic correctness controls only.
