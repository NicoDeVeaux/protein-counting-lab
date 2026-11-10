# Protein counting experiments

Exploratory experiments on discrete protein design: partition functions, ensemble affinity scores, exact preprocessing, numerical references, and independent grading. This repository preserves useful results and negative findings from five local CPU campaigns.

The latest study uses full-precision rigid energy matrices from the published c-Raf/Ras archive. All 78 state calculations for 13 admitted variants pass independent high-precision references. Ensemble counting reverses two pairwise variant rankings and changes no mutation-effect directions. A small model-transfer comparison does not establish improved biological prediction.

| Study | Result |
|---|---|
| Initial inference pilot | Conventional finite-model inference and numerical checks; no demonstrated biological improvement. |
| [Campaign 002](CAMPAIGN-002.md) | Established-solver comparison, adapter correction and retained reruns; broad timing claims rejected. |
| [Campaign 003](CAMPAIGN-003.md) | Exact hard-zero propagation helps one supplied model; larger cases remain bounded negative results. |
| [Campaign 004](CAMPAIGN-004.md) | Full three-state ranking for 21 residue templates; baseline remains best, no general pruning win. |
| [Campaign 005](CAMPAIGN-005.md) | Counting changes prioritization in a full-precision rigid model; assay/model mismatch prevents direct biological validation. |

The independent grader freezes criteria before fresh measurements and checks saved outputs separately from experiment implementations. This is research code, not a production solver or evidence of an ETH breakthrough.

## Why the ETH result did not produce a speedup here

**We did not implement or benchmark the new ETH-refuting algorithm.** An early feasibility audit rejected one literal proof parameter schedule as a practical starting point; the subsequent experiments used conventional enumeration, variable elimination and exact preprocessing. This archive therefore contains no negative performance benchmark of the new algorithm.

The released [manuscript](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/paper.pdf) covers exact counting of fixed-width CNF solutions, and its common counting routine accepts rational-algebra factors. A decision-versus-counting distinction is not the explanation. The [Lean scope note](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/lean/docs/378.md) documents a weaker subexponential bound than the sharper paper bound; neither supplies a demonstrated practical protein counter.

- **Asymptotic scale:** in the audited Section 4 schedule, four necessary conditions first pass at `n = 2^10909384703 + 1` Boolean variables for beta=1. This is a parameter-feasibility threshold, not a measured runtime crossover or a lower bound on improved implementations. A new check of the appendix's literal tensor schedule also finds an unusably late first positive recursion parameter. More CPUs or GPUs do not repair those literal schedules.
- **The relevant size:** `n` counts encoded Boolean variables, not conformations. Fifty positions with ten conformers have `10^50` conformations but only 200 binary choice bits before validity/weight auxiliaries. A huge conformational space is not automatically the theorem's large-n regime.
- **A weighted-model bridge remains:** finite-domain choices, Boltzmann weights, precision, intermediate coefficients and encoding overhead need an explicit analysis. The common weighted product-sum interface makes this a real open route, but we did not build that adapter.
- **Our biological bottleneck remains:** the final 78 state calculations were already cheap; their model and assays were mismatched. Faster sums alone would not establish better affinity predictions. Larger conventional cases remain unsolved under our budgets, which also does not establish an ETH-derived opportunity.

The current explanation is an implementation, finite-scale and model-validation gap. Better constructions or extracted subroutines remain possible. [Detailed checks and qualifications](notes/ETH_AND_OPEN_LANES.md) include reproducible arithmetic checks without downloading the bulk data.

## Lanes left open

Checked on 2026-11-10; these assessments distinguish completed work from proposed experiments.

| Lane | Evidence and current assessment | Next useful gate |
|---|---|---|
| Literal proof schedules plus larger hardware | Poor practical starting point: old Section 4 and new appendix parameter checks fail at realistic sizes. This says nothing universal about other implementations. | Derive an explicit finite operation/bit-memory budget before implementing a full counter. |
| Instance-specific layouts or simplified algebraic subroutines | Mathematically open: the paper exposes a general product-sum routine. No practical gain demonstrated here. | Construct and verify a small layout, bound every interpolation/measurement cost, and compare with same-target VE before expanding. |
| Weighted encoding and precision | Useful, inexpensive prerequisite rather than a demonstrated speedup. | Count actual bits, auxiliaries and coefficient sizes; propagate errors through three-state ratios and rankings. |
| Structure, shared-state reuse and certified rank-aware stopping | Best supported engineering lane: propagation helped one source model and identical-state reuse was validated. Adaptive ranking remains untested; finite positive weights require tail bounds. | Match a native/domain baseline, retain preprocessing costs, and resolve useful rankings with valid enclosures rather than demanding unnecessary partition precision. |
| Assay-matched energies and flexibility | Highest priority for biological usefulness: campaign 005 changes two model orders but has no matched-assay validation or established biological winner. | Prepare the measured molecular system, freeze model/assay identities, and compare ensemble versus same-model GMEC on held-out measurements. |

The checks are preconditions and error-budget arithmetic, not a new solver benchmark. See [the checked roadmap](notes/ETH_AND_OPEN_LANES.md) for what would justify revisiting each lane.

## Code and data

Code, tests, reports and figures live in Git. Bulk results and licensed inputs are attached to the [data release](https://github.com/NicoDeVeaux/protein-counting-lab/releases/tag/v2026.11.10). From a clone:

```sh
python3 publication.py verify --code-only
python3 publication.py download
python3 publication.py verify
```

The downloader verifies the compressed SHA-256 and every extracted file. It restores data into this working tree; skip downloading if you only want to read the code and results summaries.

For the latest model's core checks:

```sh
uv sync --frozen --group dev
uv run --group dev pytest -q tests/test_rigid_affinity5.py
uv run python -m unittest experiments.energy_recovery5.test_java_matrix
```

Earlier campaigns also require upstream inputs excluded from the mirror. Their pinned URLs, checksums and exclusion reasons are in [UPSTREAM_ARTIFACTS.json](UPSTREAM_ARTIFACTS.json); `python3 publication.py fetch-upstream --path PATH` downloads an explicitly selected direct source. See [RUNNING.md](RUNNING.md) and the campaign guides. Existing measured output locations are intentionally not overwritten.

## Publication boundaries

This is a privacy-redacted export. Original scientific outputs are retained, but local paths, private policy references and signed download URL query strings were removed. Historical freeze hashes describe original workspace bytes and must not be mistaken for checksums of edited public metadata. [PUBLICATION_MANIFEST.json](PUBLICATION_MANIFEST.json) records original/export hashes and omissions; [PUBLICATION.md](PUBLICATION.md) explains verification.

No new scientific measurements were made for publication. Read the independent [campaign-005 verdict](grader/campaign-005/REPORT.md) and [result figure](outputs/campaign-005-v2.png) for the substantive findings and qualifications.

Original software is MIT-licensed. Data and attributed transcriptions retain the terms described in [THIRD_PARTY.md](THIRD_PARTY.md). Please cite the original papers and datasets when using their material.

This is written by an AI agent (model name unavailable) on Nico DeVeaux's behalf.
