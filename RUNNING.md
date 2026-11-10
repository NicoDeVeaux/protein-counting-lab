# Reproducing and extending the experiments

This is an exploratory research workspace, not a production solver or an implementation of the ETH algorithm.

## Roles and evidence

- `grader/` belongs to the independent evaluator. Its rubric was frozen before measured results and must not be silently changed.
- `data/` preserves raw published inputs, conversion checks, and experimental labels. The UAI models and experimental labels describe different proteins and must not be paired as prediction/measurement examples.
- `experiments/inference/` implements conventional log-domain variable elimination, exhaustive references, and approximate best-first search.
- `experiments/eth_schedule/` checks necessary gates in one literal manuscript parameter schedule. It does not execute the counting algorithm or establish a runtime crossover.
- `runs/campaign-001/` contains the prospective manifest and all 410 trial records. `runs/eth-schedule-001/` contains the separate prospective schedule experiment.
- `runs/review-001/bundle_manifest.json` identifies the exact files supplied to the grader. Later diagnostics are separate and do not overwrite original evidence.

The initial cohort contains 14 source-first sequences, 42 bound/unbound state models, and 9 distinct PDB IDs. It was selected by availability and source archive size before inference results. These conditioned models contain only 1–8 variables; they do not represent full sequence optimization.

## Check the implementation and source conversion

Run from this directory:

```sh
uv sync --frozen --group dev
uv run --group dev pytest -q tests experiments/eth_schedule/test_schedule.py
uv run python scripts/acquire_validate.py
```

The first campaign used Python 3.13.11 and NumPy 2.5.4 on arm64 macOS. Each measured trial used a fresh subprocess, one numerical-library thread, and randomized trial order. JSON records distinguish loading, inference kernel time, subprocess wall time, and process peak RSS. Downloading and preparing raw inputs is outside the timed interval.

## Start another conventional inference campaign

First have the evaluator approve the prospective question, input selection, methods, and interpretation. Then use a new output directory; existing frozen campaigns are never overwritten:

```sh
uv run python scripts/campaign.py freeze --run-dir runs/campaign-002
uv run python scripts/campaign.py run --run-dir runs/campaign-002
uv run python scripts/campaign.py summarize --run-dir runs/campaign-002
```

This repeats the initial question and settings. A different experiment needs its own prospective manifest and an explicit amendment or new protocol. The driver verifies recorded source and input hashes before execution and summarization.

Do not rerun acquisition scripts over the frozen workspace: they can update derived inputs or retrieval timestamps. Use a separate working copy for reacquisition and compare its source hashes. Acquisition commands and exact URLs are documented in `data/README.md` and the manifests.

## Numerical boundaries

"Exact" describes summing the specified finite model without truncating its states. It does not mean exact real arithmetic. All inference implementations use float64, and the source models already contain represented zeros from their original conversion.

The best-first bounds are sound in ideal arithmetic, but their floating endpoints are not outward-rounded interval certificates. The original campaign compares them with a predeclared numerical tolerance. `runs/review-001/strict_bound_diagnostic.json` separately records strict floating-reference misses; it does not modify the original trial results.

No measured-affinity prediction improvement, global sequence optimum, novel inference algorithm, or ETH-derived practical speedup is established by the first campaign.
