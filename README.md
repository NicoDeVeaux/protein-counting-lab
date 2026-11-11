# Protein counting experiments

**Status: exploratory work completed; active research stopped on 2026-11-11.**
We found no demonstrated solver speedup or improvement in biological prediction
that warrants another campaign. The Lean-checked partition-bound certificates are
retained as a reusable prototype. [CONCLUSION.md](CONCLUSION.md) records the final
decision, evidence, limits and conditions for reopening.

Exploratory experiments on discrete protein design: partition functions, ensemble affinity scores, exact preprocessing, numerical references, and independent grading. This repository preserves local CPU campaigns, verified checks and negative findings.

The latest biological study uses full-precision rigid energy matrices from the published c-Raf/Ras archive. All 78 state calculations for 13 admitted variants pass independent high-precision references. Ensemble counting reverses two pairwise variant rankings and changes no mutation-effect directions. A small model-transfer comparison does not establish improved biological prediction.

[Campaign 006](CAMPAIGN-006.md) tests certified adaptive ranking on small synthetic integer models. Lean checks the ranking arithmetic; TLC checks a bounded cache model. Adaptive stopping reduces work on three nontrivial cases, while exact variable elimination remains faster on every nontrivial case. [BENCHMARK.md](BENCHMARK.md) explains the task, scoring, baselines and requirements for a discovery loop.

[Campaign 007](CAMPAIGN-007.md) strengthens that certificate path: Lean now recomputes and proves the partition-bound construction from a model and binary split certificate. The Python table translation remains independently tested rather than proved. This is a verification follow-up, with no new speedup claim.

The [external continuation gate, campaign 008](CAMPAIGN-008.md), failed: the 4,096-expansion configuration resolved none of six MC2026 probability-ordering queries. Native Ganak resolved two; four timed out. The verified checker worked, but the bounds were too weak. A full-time-budget or stronger-producer comparison remains unmeasured; neither is scheduled.

| Study | Result |
|---|---|
| Initial inference pilot | Conventional finite-model inference and numerical checks; no demonstrated biological improvement. |
| [Campaign 002](CAMPAIGN-002.md) | Established-solver comparison, adapter correction and retained reruns; broad timing claims rejected. |
| [Campaign 003](CAMPAIGN-003.md) | Exact hard-zero propagation helps one supplied model; larger cases remain bounded negative results. |
| [Campaign 004](CAMPAIGN-004.md) | Full three-state ranking for 21 residue templates; baseline remains best, no general pruning win. |
| [Campaign 005](CAMPAIGN-005.md) | Counting changes prioritization in a full-precision rigid model; assay/model mismatch prevents direct biological validation. |
| [Campaign 006](CAMPAIGN-006.md) | Exact ranking certificates and safe adaptive stopping work on a laptop; refinement savings do not beat native exact VE. |
| [Campaign 007](CAMPAIGN-007.md) | Lean checks factor bounds, completion counts and split coverage; a supplied Python enclosure is no longer a premise of the new bound theorem. |
| [Campaign 008](CAMPAIGN-008.md) | External MC2026 gate fails: 0/6 certified decisions at the expansion cap, versus 2/6 for native exact Ganak; no speedup established. |

The independent grader freezes criteria before fresh measurements and checks saved outputs separately from experiment implementations. This is research code, not a production solver or evidence of an ETH breakthrough.

## Why the ETH result did not produce a speedup here

**We did not implement or benchmark the new ETH-refuting algorithm.** An early feasibility audit rejected one literal proof parameter schedule as a practical starting point; the subsequent experiments used conventional enumeration, variable elimination and exact preprocessing. This archive therefore contains no negative performance benchmark of the new algorithm.

The released [manuscript](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/paper.pdf) covers exact counting of fixed-width CNF solutions, and its common counting routine accepts rational-algebra factors. A decision-versus-counting distinction is not the explanation. The [Lean scope note](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/lean/docs/378.md) documents a weaker subexponential bound than the sharper paper bound; neither supplies a demonstrated practical protein counter.

- **Asymptotic scale:** in the audited Section 4 schedule, four necessary conditions first pass at `n = 2^10909384703 + 1` Boolean variables for beta=1. This is a parameter-feasibility threshold, not a measured runtime crossover or a lower bound on improved implementations. A new check of the appendix's literal tensor schedule also finds an unusably late first positive recursion parameter. More CPUs or GPUs do not repair those literal schedules.
- **The relevant size:** `n` counts encoded Boolean variables, not conformations. Fifty positions with ten conformers have `10^50` conformations but only 200 binary choice bits before validity/weight auxiliaries. A huge conformational space is not automatically the theorem's large-n regime.
- **A weighted-model bridge remains:** finite-domain choices, Boltzmann weights, precision, intermediate coefficients and encoding overhead need an explicit analysis. The common weighted product-sum interface makes this a real open route, but we did not build that adapter.
- **Our biological bottleneck remains:** the final 78 state calculations were already cheap; their model and assays were mismatched. Faster sums alone would not establish better affinity predictions. Larger conventional cases remain unsolved under our budgets, which also does not establish an ETH-derived opportunity.

The current explanation is an implementation, finite-scale and model-validation gap. Better constructions or extracted subroutines remain possible. [Detailed checks and qualifications](notes/ETH_AND_OPEN_LANES.md) include reproducible arithmetic checks without downloading the bulk data.

## Disposition of the research lanes

Closed out on 2026-11-11. Mathematical possibilities remain, but there is no active
follow-up campaign. These are evidence requirements for reconsideration, not a
backlog.

| Lane | Evidence and disposition | Evidence needed to reconsider |
|---|---|---|
| Literal proof schedules plus larger hardware | Stop: audited Section 4 and appendix schedules are impractical at realistic sizes. This is not a universal barrier. | A different construction with a credible finite operation and memory budget. |
| Instance-specific layouts or simplified algebraic subroutines | Stop: no practical gain demonstrated; mathematically open. | An independently checked finite routine competitive with same-target conventional inference. |
| Weighted encoding and precision | Defer: exact integer bounds work, but physical-weight and reduction costs remain unestablished. | A concrete competitive solver that needs this adapter; an adapter alone would not establish a speedup. |
| Structure, shared-state reuse and certified rank-aware stopping | Retain the checker; stop the current producer. Synthetic work savings did not beat exact VE; the external gate failed. | A materially stronger producer with useful external decisions and total costs, including verification, competitive with exact baselines. |
| Assay-matched energies and flexibility | Close as a separate scientific dependency: two model-order reversals do not establish better affinity prediction. | An independently prepared matched molecular/assay benchmark and a committed biological collaborator. |

The ETH parameter checks remain preconditions and error-budget arithmetic. See
[the feasibility notes](notes/ETH_AND_OPEN_LANES.md) and [benchmark guide](BENCHMARK.md)
for the completed experiments and their scope.

The [external-grader review](notes/EXTERNAL_GRADERS.md) preserves other possible
evaluators. Campaign 008 completed a narrower unweighted external gate within the
existing integer proof. Weighted, projected and biological evaluations were not
completed and are not pending work in this project.

## Code and data

Code, tests, reports, figures and the small synthetic/external benchmark measurements live in Git. Earlier bulk results and licensed inputs are attached to the [data release](https://github.com/NicoDeVeaux/protein-counting-lab/releases/tag/v2026.11.10). Campaign 008 keeps its upstream CNFs and full converted certificates outside the mirror, with source URLs and hashes for reproduction. From a clone:

```sh
python3 publication.py verify --code-only
python3 publication.py download
python3 publication.py verify
```

The downloader verifies the compressed SHA-256 and every extracted file. It restores data into this working tree; skip downloading if you only want to read the code and results summaries.

Campaign 006 needs no bulk download or Python packages:

```sh
python3 -B -m unittest experiments.certified_rank6.test_core
python3 -B grader/campaign-006/audit.py
python3 -B grader/campaign-006/audit_mutants.py
python3 -B grader/campaign-006/audit_results.py experiments/certified_rank6/results-v2
sh formal/campaign-006/lean/check.sh
```

The last command needs the pinned Lean toolchain. The [formal check guides](CAMPAIGN-006.md) describe Lean and TLC reproduction. For campaign 005's molecular-model core checks:

```sh
uv sync --frozen --group dev
uv run --group dev pytest -q tests/test_rigid_affinity5.py
uv run python -m unittest experiments.energy_recovery5.test_java_matrix
```

Earlier campaigns also require upstream inputs excluded from the mirror. Their pinned URLs, checksums and exclusion reasons are in [UPSTREAM_ARTIFACTS.json](UPSTREAM_ARTIFACTS.json); `python3 publication.py fetch-upstream --path PATH` downloads an explicitly selected direct source. See [RUNNING.md](RUNNING.md) and the campaign guides. Existing measured output locations are intentionally not overwritten.

## Publication boundaries

This is a privacy-redacted export. Original scientific outputs are retained, but local paths, private policy references and signed download URL query strings were removed. Historical freeze hashes describe original workspace bytes and must not be mistaken for checksums of edited public metadata. [PUBLICATION_MANIFEST.json](PUBLICATION_MANIFEST.json) records original/export hashes and omissions; [PUBLICATION.md](PUBLICATION.md) explains verification.

The initial publication export did not recompute the historical campaigns. Later campaigns add separately sealed synthetic and external measurements and verification checks. Read the [external campaign-008 verdict](grader/campaign-008/REPORT.md), [synthetic campaign-006 verdict](grader/campaign-006/REPORT.md), or biological [campaign-005 verdict](grader/campaign-005/REPORT.md) and [result figure](outputs/campaign-005-v2.png), for findings and qualifications.

Original software is MIT-licensed. Data and attributed transcriptions retain the terms described in [THIRD_PARTY.md](THIRD_PARTY.md). Please cite the original papers and datasets when using their material.

This is written by an AI agent (model name unavailable) on Nico DeVeaux's behalf.
