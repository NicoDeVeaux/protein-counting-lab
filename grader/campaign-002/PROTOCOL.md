# Campaign 002: prospective independent grading protocol

Status: frozen when the adjacent `FREEZE.json` is written. Work class: exploratory research (`poc`); these files specify an audit, not production software. Scope: local CPU inference/counting on explicitly represented finite nonnegative factor models. No result, implementation, or campaign-002 measurement was read to write this protocol.

## Exposure and independence

The grader read the canonical shared policy, repository `AGENTS.md`, and prior campaign `grader/REPORT.md`. The prior report is adaptive evidence: 42 conditioned models with 1–8 variables; full-joint materialization in the recorded elimination; strict-bound rounding failures despite tolerance checks; no established solver comparison. This follow-up is therefore not an independent replication of a hypothesis invented before that evidence. A fresh grader context is a procedural separation, not a guarantee against bias. The protocol must remain unchanged after freeze. Later changes use numbered, dated, hashed amendments stating exposure and the effect on confirmatory status. Earlier frozen campaign files must remain unchanged.

The experiment worker may prepare data, install/check solvers, inspect static model structure, and run correctness controls before the final execution manifest freezes. Preparation outputs must be retained and labeled. Preparation timing or resource behavior cannot silently determine the reported measured cohort: all attempted preparation cases and reasons for exclusions enter a ledger. Any pilot inference on a proposed measured protein model must be disclosed before manifest freeze, including observed output, time, memory, and its effect on selection. Pure conversion, algebraic validation, and small synthetic correctness controls may precede freeze. The grader does not inspect campaign-002 implementations or measurements until the parent explicitly delivers a frozen bundle.

## Questions and acceptable outcomes

1. What computation do the publicly available, fixed-sequence protein models actually represent, before and after justified simplification?
2. Within fixed local budgets, which predeclared model/method/resource cells produce a sufficiently accurate partition function, and where do representation size, conversion, timeout, or memory cause failure?
3. Where paired cases are valid and timing differences are large enough to resolve, how do preprocessing, inference, total wall time, and RSS compare with an established inference/counting implementation?

A validated negative feasibility result, a coverage gap, or an obstruction caused by represented factor tables can be useful. No speedup, winner, broad scaling law, or biological result is required. A model that cannot be represented or converted within budget is a retained result, not an invisible exclusion.

## Two freezes and the audit bundle

This protocol and its JSON schemas freeze first. The worker then freezes one complete execution manifest, conforming to `manifest.schema.json`, before any reported timed inference. The manifest supplies the exact model IDs, source/derived hashes and provenance, fixed sequences and conditioning, method versions/configuration, static strata, all resource limits, repetitions and schedule, accuracy contracts, and deterministic selection rule. A manifest cannot refer to a future wildcard cohort. Every planned trial has a stable ID. The trial Cartesian product may be stored as an enumerated hashed file, but its exact rows must be part of the freeze. Skips must have planned trial records.

Deliver the manifest, source/converted data, preparation ledger, converters, simplification evidence, static estimators, implementations/wrappers, dependency/version inventory, commands/environment, raw stdout/stderr, case-level trial records, and a complete hash inventory. Retain all failures and post-freeze edits. Implementation fixes after freeze require a versioned amendment and a new result family; retain original outputs. State which measurements predate each fix. Do not overwrite a run to hide it.

## Cohort and prospective stratification

Keep the original 42-model cohort unchanged as a named baseline, with frozen identities and any mapping to new derived representations. Larger published fixed-sequence models may be added using a source-first/static rule based on structure and predicted resource cost. Separate published computational protein models from synthetic controls and experimental affinity measurements. Source/archive size is not a structural or memory stratum.

For every attempted model record the original and simplified variable count, domain-cardinality vector, factor scopes/arities and table entries, connected components, represented primal edges/density, factor graph cycles where computed, elimination heuristic/order, induced width under that order, largest predicted intermediate entries/bytes, and joint configuration count or its logarithm. A heuristic induced width is an order-dependent upper bound, not a proof of treewidth. Predict broadcast/product workspaces in addition to the final intermediate. Count original dense factor storage separately.

Use these fixed descriptive bins, before and after simplification:

| Axis | Bins/required labels |
|---|---|
| Represented graph | edgeless; pairwise forest; pairwise cyclic; at least one factor of arity >2 (also report actual arity and density) |
| Algebra | unchanged; exact constant/scope reduction; exact separability/decomposition; multiple reductions; unverified/approximate simplification (distinct target) |
| Largest predicted intermediate in float64 | <1 MiB; 1–128 MiB inclusive; >128–512 MiB inclusive; >512 MiB; unknown/infeasible to derive |
| Domain | maximum cardinality <=16; 17–64; >64; always retain the full cardinality vector and log joint size |
| Variables | <=8; 9–32; >32 |

The final manifest must identify intended occupied cells and uncovered cells; a full Cartesian crossing is not required. Claims must be restricted to occupied cells and observed ranges. The existence of a dense listed scope does not establish intrinsic interaction complexity if its values permit reduction. Conversely, do not call a model sparse merely because it has few stored factors or a small compressed download.

Synthetic controls are allowed only to fill documented structural gaps in available published models or to test correctness/limits. Freeze their generator, seed, sizes, weights, and intended mechanism. Include analytically solvable examples (independent variables, trees, and constant/separable high-arity factors where relevant) and a nontrivial loopy/dense control if comparing structure. Preserve genuine hard zeros and very small positive weights in dedicated numerical controls. Do not pool synthetic cases into the protein success rate or use them as evidence of protein scaling. Keep preparation/correctness controls and measured synthetic controls separately labeled.

## Algebra and conversion contract

Define the target as `log Z = log(sum_x product_a w_a(x_scope))` with finite nonnegative source weights and the declared fixed-sequence conditioning. `log Z = -inf` means exactly zero mass; it must not mean floating underflow. Preserve zeros, domain/state mappings, factor order, scope-axis order, conditioning rules, and every scale offset. Report native-source semantics if different. Invalid negative/NaN weights or ill-formed domains are conversion failures.

Check source tokens/values against derived data independently: variable/factor counts; scopes; domain sizes; table shapes; all entries where feasible (otherwise a frozen exhaustive hashing/checking method plus deterministic stratified samples); zeros; small positive extrema; and state assignments. Document whether source decimal lexemes, binary64 weights, or another representation define the audited target. Preserve raw source text. Detect positive source entries that parse/convert to zero, and factors/products that overflow or underflow ordinary arithmetic. A positive entry lost to zero disqualifies that conversion from a claim of semantic equivalence. Use a log/scaled representation or report an unsupported conversion failure. Products may underflow in an ordinary-weight diagnostic without invalidating a separately verified log-space computation.

Factor rescaling must restore offsets in log Z. Independently validate scale restoration and parser/axis conventions on small enumerated controls and chosen real factor entries. A comparator that requires positive-only factors cannot silently remove zeros or add epsilon. Native solver output scales/normalizations must be checked.

Exact constant or separable reduction needs a checkable algebraic identity under the declared source semantics, domain multiplicities, and offsets. Numeric rank or a floating tolerance alone is not an exact certificate. A tolerance-based rewrite is an approximation with its own target/error budget; validate its effect on Z and do not mix its timings into exact same-target comparisons. Charge simplification and representation conversion to their declared preprocessing scope, report them separately, and preserve both before/after structure. Validate the reduced and unreduced models against independent enumeration or high precision where feasible; otherwise provide the identity check rather than assuming equality from matching solver outputs.

## Methods and correctness

Include at least one established, independently implemented inference/counting package with a public version/source and documented applicable algorithm. Freeze a version/commit, build/environment, algorithm, order/settings, wrapper, numeric representation, and any adapter. A wrapper is acceptable; another call into the custom kernel under a new name is not. Basic array arithmetic alone is not an established solver comparator. If no applicable established solver can be installed or can represent the models, retain that finding and limit the study to representation/feasibility; do not claim a valid established-solver comparison.

Match target, conditioning, source semantics, simplification status, accuracy, and resource profile. Record algorithmic differences and adapter restrictions. Exact, heuristic approximate, and certified approximate methods belong to separate accuracy contracts. A faster approximate answer is not an exact speedup. A failed comparator cannot make a numerator/denominator timing ratio infinite or establish an unconditional winner.

Before reported measurements, freeze and pass controls that independently exercise parser ordering, conditioning, scale offsets, zeros, very small positive weights, and a nonsymmetric multi-variable factor. Use analytic solutions and a direct enumerator implemented separately from the compared elimination/contraction paths. Use at least 80 decimal digits for selected numerical controls and a prespecified real subset selected by static features (smallest, largest enumerable, smallest positive entry, any algebraically reduced case). Freeze reference selection and validation coverage. Shared parser/reference lineage must be disclosed; agreement of methods that share a bug is weak evidence.

Default exact acceptance is equality of zero-mass classification and absolute log-Z difference <= `1e-8 + 64*eps64*max(1, abs(reference_log_z), sum_abs_restored_log_offsets)`. The manifest may tighten this rule before measurements; relaxing it requires a prospective amendment with justification. The floating slack addresses arithmetic comparison and is not a proof of exact real arithmetic. Report the actual error and reference uncertainty. At least one comparator/reference must be validated independently; agreement among unverified solvers alone does not establish accuracy. If a large case lacks an adequate independent reference, label it `unverified_accuracy`; retain feasibility but do not count it as validated success.

For any approximate contract, predeclare an absolute log error or relative-Z target, confidence/failure semantics if stochastic, and reference precision. Convert log error to multiplicative error using `expm1` where useful. Report all measured errors, not only a success threshold. Interval claims must distinguish strict containment from tolerance-relaxed overlap. Strict certificates require directed rounding/validated error propagation or a documented theorem with checked assumptions; tolerance alone cannot certify enclosure.

## Resources and measurement

All inference uses local CPU. Freeze machine/OS, dependency inventory, thread counts/environment, concurrency, warm-up policy, repetitions, RNG seeds, order/randomization, and per-case trial schedule. Prefer one timed trial at a time and one native thread; report deviations. At least three measured fresh-process repeats per feasible deterministic cell are required for paired runtime claims. One trial is sufficient to retain a resource/representation failure; a static rejection needs no expensive repeated allocation. Cache state is declared; warm and cold measurements remain separate.

Freeze table/allocation caps (normally 128 MiB and/or 512 MiB, binary units), per-trial wall timeout (finite, at most 300 seconds), and a finite total campaign time budget. The exact feasible matrix is the parent's premeasurement choice. A table cap is a policy for a named allocation estimate, not a total memory ceiling. Specify bytes/element, original inputs, intermediates, broadcasts, temporary buffers, and estimate conservatism. A static `predicted_table_cap` skip is distinct from an attempted allocation failure.

For each resource profile also freeze an explicit total process/descendant RSS ceiling and enforcement plan. Where an external watchdog can reliably observe/terminate over-limit trials, use it and record sampling interval, process-tree accounting, trigger/kill times and overshoot. Validate the watchdog on a dedicated nonmeasurement control. On macOS or another host where an address-space/OS limit is not equivalent to RSS, name it accurately. If a practical hard RSS enforcement cannot be made reliable, declare `observed_only` prospectively, bound trial time and table allocations, report sampled peak RSS as a lower bound with sampling limitations, and make no claim that an RSS budget was guaranteed. Do not substitute an allocation cap for RSS.

Report separate clocks for source parsing/conversion, algebraic preprocessing/order search, solver ingestion, inference kernel, and end-to-end execution through valid result output. State which persistent artifact is reused and its preparation cost. Preserve raw wall and CPU time, units and clock definitions. Kernel timing excludes no hidden inference/order work. A solver with no reliable kernel boundary can still support end-to-end comparison. RSS is baseline and peak whole worker process plus relevant descendants, with phase scope, platform units, inherited inputs and sampling definition. On platforms where lifetime high-water includes preparation, do not label it kernel-only memory. Record external watchdog/startup costs separately if excluded from the scientific scope.

Timeouts are right-censored wall times; RSS/table failures are separate outcomes. A trial killed by the external monitor is not an accuracy result. A result returned just before a limit but not validated/output before the defined end point does not count as a completed end-to-end success. Distinguish numerical failure, wrong answer, unsupported conversion, static cap, allocation error, RSS kill, timeout, signal/crash, invalid output, skipped plan, and infrastructure error. Repeats/retries retain original rows and reasons. Every planned cell must reconcile with case-level trial records under `trial.schema.json`.

## Analysis and claim gates

Report every model/resource/method outcome and static stratum. Primary summaries are validated success counts and failure reasons by published/synthetic cohort, structure, algebra, domain, and resource profile. Show denominators, missingness, and exact occupied ranges. Prefer case-level absolute costs and accuracy-cost frontiers. Correlated states/PDBs are not independent biological samples; no population p-value is required or warranted from this convenience cohort.

Pairwise runtime/memory comparisons use matched completed correct trials under the same contract/profile. Report model-level medians, repeat variability, absolute values, paired ratios and timing scope. Do not mix kernel and end-to-end ratios. Aggregate ratios must specify geometric/median arithmetic, weights and their sensitivity; failures remain visible alongside the success-only aggregate. No statistical significance or superiority claim follows solely from a near-one aggregate on short trials. Startup/noise-limited measurements should be described as unresolved. If a predeclared bootstrap/interval is used, resample at the independent case/source level and state that convenience sampling limits generalization.

The grader will assess five gates separately, without a weighted winner score:

| Gate | Pass requires | Consequence of failure |
|---|---|---|
| Integrity/prospectivity | intact hashes, premeasurement manifest, amendments, complete planned-trial ledger | descriptive/exploratory only for affected evidence; identify exposure |
| Semantics/numerics | auditable conversions/reductions, controls, matched target and reference accuracy | no computational correctness/speedup claim for affected cells |
| Representation/coverage | before/after structure, static memory predictions, strata and gap disclosure | restrict claims; a documented obstruction may still be useful |
| Resource/comparison | established comparator when making comparative claims; clocks/RSS/caps/failures explicit and matched | feasibility-only or limited comparison; no invented success |
| Interpretation/usefulness | conclusion supported by case-level evidence and limits; actionable usable regime or reason to stop | state inconclusive result rather than inflate novelty |

The audit independently recomputes integrity, planned-row reconciliation, selected structure/memory predictions, conversion/underflow tests, and independent numerical controls; reaggregates all trial outcomes/timings; and checks claims against the gates. Full numerical reruns need not fit the audit budget, so record rerun coverage and remaining uncertainty. Report both numerical closeness and strict interval failures if bounds are present. Evaluate useful negative findings on evidence, not on whether a preferred method won.

No inference runtime or conventional counting method is an ETH implementation. An ETH claim needs a new explicit theorem-to-program mapping, checked assumptions and evidence, beyond this study. No improved biological affinity prediction, ranking, molecular validity, or scientific discovery follows from faster/more exact model inference. Such claims require a separately frozen matched molecular preparation/energy model and relevant held-out experimental labels, with no retuning on the holdout. Published protein models and unpaired experimental tables do not meet that requirement.

## Completion record

The final independent verdict records each gate, justified useful/negative findings, failures, amendments and exposure, validation coverage, unresolved uncertainty, and the exact audited bundle identity. Keep the original measured outputs and reports even when correcting their interpretation. Publication remains outside this authorization.
