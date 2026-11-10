# Operational rerun after resource contention

Recorded after the first benchmark finished and before the second benchmark starts
on 2026-11-10. The original source seal and scientific protocol remain unchanged.

The first 96 invocations overlapped with a TLC model-checking matrix. Retain them
under `experiments/certified_rank6/results/` as a correctness and contention
diagnostic; do not use their times for the performance conclusion. Perform exactly
one complete rerun in a fresh `results-v2/` directory after TLC, Lean and the
independent computational audits have finished. Use all second-run measurements
for the timing conclusion, including unfavorable outcomes. Do not choose the faster
run or alter the source, cases, budgets, order, repeats or scoring criteria.

The timed region starts inside an already imported Python worker. It includes
model construction, model identity work, producer preprocessing, scheduling,
caching, arithmetic and certificate checking. Python process startup/imports,
serialization, separate input inventory and independent validation are excluded
consistently for every method. Three repetitions on one laptop do not establish
portable performance or formal statistical significance. Other host activity is
not controlled by this experiment.
