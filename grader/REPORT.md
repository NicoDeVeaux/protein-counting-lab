# Independent verdict

**Informative exploratory work, with one numerical claim requiring qualification.** The study produces a validated discrete-model artifact and useful feasibility measurements. It establishes neither an ETH-derived speedup nor improved biological prediction. Rubric `4403e5` remained unchanged; bundle `506449` was audited after freezing. The detailed machine-readable judgment is in [verdict.json](verdict.json).

## Findings

| Question | Judgment |
|---|---|
| Is the computational artifact trustworthy? | Yes, for the published discrete representation and fixed source-first sequences. |
| Are the exact calculations consistent? | Yes, within the prospective floating tolerance. |
| Do all stored bounds strictly enclose the reference? | No. All pass a tolerance-relaxed check. |
| Was a sparse-graph advantage demonstrated? | No; the tested elimination forms a full joint table in every model. |
| Is there ETH-specific progress? | A verified negative feasibility audit of one literal parameter schedule. |
| Was biological improvement tested? | No; computational models and experimental labels are unpaired. |

All **1,342 frozen files** match their hashes, and all **410 planned trials** are present without driver failures. Independent reconstruction checks all **35,459 converted entries**, source factor/variable coverage, conditioning domains, and source zeros. The declared selection rule reproduces from the frozen repository tree. The resulting artifact covers **42 states, 14 cases, and 9 PDB IDs**; it is one sequence per case, not sequence optimization or a benchmark of measured affinity.

A separate raw-weight product/sum enumeration agrees with all **284 exact trial outputs**, with maximum log difference **1.71e-13**, below the prospective tolerance. Independent 80-digit Decimal checks cover **20 models and 30,284 configurations**, evaluating both original weights and stored-log factors. The 14 modeled log K-star identities also recompute correctly. This validates numerical computation within these discrete models; it does not validate the energy model against molecules.

The original statement that all 126 bounds “contain” the chosen reference is too strong if read literally. **30/126 stored intervals miss the chosen floating VE value**, although every interval passes the predefined tolerance-relaxed test. In the 80-digit subset, **42/60 intervals miss the converted-model reference**, by at most **1.36e-14 log units**. These tiny errors do not defeat the exploratory numerical result, but they do defeat strict enclosure. The honest result is **126/126 tolerance-relaxed checks**, with no interval certificate. The frozen claim/output should remain preserved alongside this correction.

## What the timings actually show

These conditioned models have only **1–8 variables** and **10–10,054,800 configurations**. Every recorded elimination has induced width `n-1` for the represented scopes, and its largest table contains the full joint grid. This is not evidence that sparse graphical structure was exploited. Nor does it prove intrinsic interaction complexity: constant or separable tables might permit preprocessing, which was not tested.

VE has the faster kernel median on **22/42** models; batch enumeration wins on **20/42**. The median of model-level batch/VE kernel ratios is **1.04**, with a largest ratio of **12.47**. The corresponding median wall ratio is **1.01**. VE's largest model median kernel is **0.098 s**; batch enumeration's is **1.003 s**. The larger local VE advantage comes with materialization: maximum process RSS is about **122 MB**, versus at most **46 MB** for batch enumeration.

This is a useful local implementation/time–memory comparison, with three original repeats per exact timed method. It is not a general algorithmic speedup, a comparison with established state-of-the-art solvers, or a scalability boundary. Process startup, shared workstation load, related cases, and preparation outside timing scope limit interpretation. Timings were independently reaggregated, not rerun.

## ETH and biological scope

The literal Section 4 parameter transcription matches the archived manuscript. An independent integer search over square-root blocks, separately within every ceiling-log interval, verifies the first passing `lambda` values:

| beta | First lambda passing the four necessary gates |
|---|---:|
| 1 | 10,909,384,704 |
| 2 | 17,045,913,600 |
| 3 | 26,011,238,400 |

Even `r >= 2` first occurs at `lambda = 521,284`. For beta 1, the minimum integer Boolean-variable count in the first joint passing interval is `2**10909384703 + 1`. This is a useful, cheap reason to defer the literal schedule as a practical implementation route. It is not all-hypothesis feasibility, a runtime crossover, a protein reduction, a theorem check, or a restriction on optimized schedules and other routines. Novelty of this calculation is modest; its value is avoiding an unjustified implementation investment.

Independent extraction matches **all 63 measured labels**, including **29 missing errors**, in the 2025 supplement. The package inventory and script references support the stated reproduction gap: prepared PDBs, numerical score tables, and energy matrices needed for a direct matched-input replay are absent from that package. This does not prove they are unavailable elsewhere. The labels belong to five related pockets and are not paired with this UAI cohort. They support a preparation artifact, not a biological positive or null result.

## Recommended next experiment

**Do not implement the full ETH-to-protein pipeline on this evidence.** If the objective is only to demonstrate the literal Section 4 schedule at practical sizes, no further experiment is justified.

For computational usefulness, a small prospective conventional study is justified. Before inference, select public instances by predicted intermediate-table memory, domain counts, and represented width—not compressed archive size. Include both simplifiable/sparse and dense cases if available; document any algebraic simplification. Freeze a modest local time/memory budget and retain failures. Compare the current methods with at least one established inference/counting implementation under the same target and accuracy contract. Measure preprocessing, inference, memory, and the accuracy–cost frontier separately. The question should be whether a usable resource regime exists, not whether a chosen method wins an aggregate ratio. If the available models cannot vary the relevant structure or exceed the current trivial regime, stop with the artifact rather than manufacture a speedup study.

For biological prediction, first obtain one reproducible molecular preparation and energy model paired with relevant measured variants. Then freeze a comparison of computation accuracy versus prediction error/ranking, without retuning the physical model on the held-out labels. Until that prerequisite exists, no biological epsilon-sweep experiment is justified. More exact counting can preserve, improve, or worsen model predictions; this study does not distinguish those outcomes.

Audit procedures, post-exposure choices, and limitations are recorded in [POSTEXPOSURE.md](POSTEXPOSURE.md), [audit_results.json](audit_results.json), [spotcheck_results.json](spotcheck_results.json), and [summary_checks.json](summary_checks.json). No frozen worker inputs, results, or rubric were modified; no later parent plots/reports were used.
