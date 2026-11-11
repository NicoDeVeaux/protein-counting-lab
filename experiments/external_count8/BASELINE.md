# Native exact baseline

Campaign 008 uses the official Ganak 2.9.0 Apple Silicon CLI release, with
integer arithmetic, one thread and probabilistic caching disabled. The release
archive and executable identities are recorded in `baseline-provenance.json`.
The executable is a native Mach-O ARM64 binary; its dynamic dependencies are
Apple's system C++ and system libraries. No emulator or cloud solver is involved.

The fixed flags are:

```text
--mode 0 --prob 0 --threads 1 --seed 8008 --verb 0 --arjunverb 0 --fast
```

The [official documentation](https://github.com/meelgroup/ganak) describes mode 0
as integer counting and `--prob 0` as deterministic cache behavior. The executable's
own help and output confirm these settings. The `--fast` flag is selected for all
cases before observing external answers: the pinned source only reduces Arjun
preprocessing budgets and does not re-enable probabilistic hashing. It is
documented for short instances. No approximate fallback is selected.

`baseline.py` decodes the exact decimal count and requires both zero epsilon and
zero delta in the native result. It also rejects projected/weighted output,
conflicting satisfiability status, missing counts, and ambiguous multiple results.
The adapter retains errors and timeouts. It times native startup, CNF parsing,
preprocessing, counting and decoding; it does not use Ganak's rounded printed time
as the benchmark duration. Executable integrity checking is a preparation step.

The wheel `pyganak==2.9.0` was investigated but is not used. Its unweighted
`Counter` returns arbitrary-precision integers, yet its constructor exposes no
deterministic-cache option and its configuration defaults to probabilistic
hashing. Exact integer arithmetic alone would not satisfy this campaign's
deterministic-reference contract. `WeightedCounter` uses MPFR and returns a float,
so it is unsuitable as an exact rational reference here.

Tiny preflight controls include a formula with an unused declared variable
(count 4) and a zero-variable formula containing an empty clause (count 0).
Neither comes from the external cohort. Full source revision, artifact hashes,
fixed flags and source links are retained in the provenance record. Ganak's
repository is MIT-licensed apart from separately attributed Flow Cutter code;
third-party binary artifacts are downloaded separately rather than redistributed
as original project software.
