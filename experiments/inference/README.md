# Conventional inference harness

This implements standard variable elimination, independent scalar and batched exhaustive enumeration, and best-first prefix enumeration with omitted-mass bounds. It is not an ETH algorithm.

## Model interface

```json
{
  "schema_version": 1,
  "model_id": "source-case-id",
  "kind": "published_computational_model",
  "log_base": "e",
  "domains": [2, 3],
  "factors": [
    {"scope": [0], "log_values": [0.0, -1.0]},
    {"scope": [1, 0], "log_values": [[0.0, -2.0], [-3.0, 0.0], [-1.0, null]]}
  ],
  "metadata": {"source_url": "...", "weight_convention": "natural log Boltzmann weight"}
}
```

Factor axes follow `scope` order. Flat arrays use C ordering. `null` or `"-inf"` means a zero weight. Scalars have an empty scope. Variables absent from all factors still contribute their domain size to Z. Higher-arity factors require explicit opt-in.

`condition_model(model, {variable: value})` fixes an assignment and reindexes remaining variables. It does not sum or maximize over the conditioned variables. `log_kstar` combines three existing log partition functions; it does not solve the outer sequence optimization.

## Running

From the repository root:

```sh
uv run --with numpy python -m experiments.inference model.json --method eliminate --max-table-bytes 67108864
uv run --with numpy python -m experiments.inference model.json --method brute --max-states 1000000
uv run --with numpy python -m experiments.inference model.json --method batch --max-states 11000000 --max-batch-bytes 67108864
uv run --with numpy python -m experiments.inference model.json --method bounded --epsilon 0.1 --max-nodes 100000
uv run --with numpy --with pytest python -m pytest -q tests/test_inference.py
uv run --with numpy python -m experiments.inference.controls --family chain --variables 8 --domain-size 3 --seed 7 --output /tmp/synthetic-chain.json
```

Do not use timing outputs as benchmark evidence until a manifest and grading rubric have been frozen.

## Evidence boundary

- Variable elimination and enumeration are exact sum-product algorithms evaluated in float64 log arithmetic. They are not interval-certified numerical proofs.
- The table guard bounds each dense table, including input factors. It does not cap process RSS. Reported live array bytes exclude Python objects, allocator behavior, and parsing overhead.
- Batched enumeration uses mixed-radix state indices and direct factor lookups, independently of elimination. Its batch guard budgets indices, coordinate arrays, weights, and one factor lookup array. Input factors, interpreter/library memory, and NumPy-internal scratch space are outside that estimate. Scalar enumeration is a correctness reference rather than the intended performance baseline.
- CLI records model loading time separately from inference kernel time and the Python process's peak RSS. A parent runner must use a fresh process to interpret peak RSS per trial and capture startup/end-to-end time separately.
- `logical_entry_operations` is an accounting quantity, not a measured CPU instruction or FLOP count.
- The prefix bound replaces each incomplete factor by its largest compatible log weight and multiplies by the number of remaining assignments. The frontier partitions all unevaluated assignments. Thus lower = evaluated mass and upper = lower + the sum of frontier mass bounds.
- `epsilon_met` means the omitted mass divided by the upper bound is at most epsilon. In exact arithmetic this implies lower/Z >= 1-epsilon. Its floating-point arithmetic is explicitly not outward-rounded interval arithmetic.
- A small epsilon for one fixed-sequence model is not a bound on errors in molecular energy functions, continuous configuration integrals, experimental binding affinity, or sequence optimization.

Synthetic generators require explicit seeds and label graph families and Gaussian log-weight semantics. They are correctness/scaling controls, not evidence about protein-model accuracy.
