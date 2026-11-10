# Independent grading protocol

Prepared **2026-11-06 11:50:01 UTC**, before experimental outputs were inspected. This is exploratory (`poc`) work. The evaluator owns only `grader/`; workers own implementations. Procedural independence reduces opportunities for outcome-driven grading but does not eliminate bias.

The frozen criteria are in [rubric.json](rubric.json), with its byte-level SHA-256 in [rubric.sha256](rubric.sha256). The machine-readable verdict format is [verdict.schema.json](verdict.schema.json). Never overwrite the frozen rubric: record any amendment separately with time, rationale, original digest, and whether results were visible.

## What can be learned

Evaluate five distinct claims: a validated benchmark artifact, a useful measurement (including a negative result), a computational improvement over a named comparator, biological evidence against measured outcomes, and ETH-specific progress. A study can support one without supporting the others. No combined score or arbitrary speedup/correlation threshold decides success.

Exactness within a published or synthetic energy model establishes computational correctness. Biological prediction requires measured outcomes and an independent comparison with appropriate uncertainty. A small retrospective dataset may support a preliminary, narrowly stated biological observation; new experiments and a publication-scale study are not required.

Conventional inference is established prior art. An ETH-specific claim must identify and verify an actual manuscript component. Reproducing a restricted lemma is useful when labeled, but does not establish the integrated routine, the SAT theorem, a practical speedup, or improved biology. We do not independently validate the manuscript's theorem by grading this campaign.

The prospective literal-schedule audit is admissible as negative-feasibility evidence. Check exact arithmetic, source transcription, and minimality across ceiling-log boundaries. Passing four necessary gates is not passing all construction hypotheses or finding a runtime crossover. Failure concerns that literal schedule, not all optimized variants.

## After receipt of a frozen bundle

1. Verify the rubric digest and bundle manifest/hashes; record receipt time, files exposed, implementation snapshot, environment, run manifests, and amendments.
2. Check provenance and objective semantics, including all bound/unbound states, units, offsets, encoding multiplicities, and conversion error.
3. Independently recompute tractable values and analytic boundaries. Cover successes, failures, and limiting cases. Record commands, evidence, and exactly what was not rerun.
4. Assess fair timing and resource boundaries, matched accuracy, uncertainty, case selection, and censored/failed/skipped trials. Preserve original outputs when making diagnostics.
5. Produce `verdict.json` conforming to the schema and a concise report. Tie each finding to evidence and rubric criteria; retain nulls, failures, and limitations.

Criterion states are `pass`, `partial`, `fail`, `not_tested`, and `not_applicable`. Claim conclusions are `supported`, `partially_supported`, `not_supported`, `inconclusive`, and `not_tested`. An absent experiment is not a negative result. A failed correctness gate blocks an affected speedup claim, but may itself be an informative failure.

No paid compute or remote publication is authorized. Do not inspect `experiments/` or results before the parent supplies the frozen bundle. Clarification and diagnostic reruns after receipt are logged; they do not retroactively become prospective.

Primary references reviewed before freezing: [Viricel et al. 2016](https://doi.org/10.1007/978-3-319-44953-1_46), [Pezeshki et al. 2022](https://proceedings.mlr.press/v180/pezeshki22a.html), and the [October 25 ETH manuscript](https://github.com/openai/math/tree/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026). Exact local source hashes and the limited pages read are recorded in the rubric.
