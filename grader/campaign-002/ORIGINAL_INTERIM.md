# Original campaign 002: interim independent audit

**The frozen artifact is intact and the represented computations are auditable; the native comparator has an unintended scheduler-memory cap.** Keep the original 15 `invalid_output` rows. They cannot establish host-RAM exhaustion, the declared process-RSS boundary, or native-solver infeasibility. Broad performance judgment is deferred until a versioned correction and fresh matched matrix are audited.

This is an interim finding on original bundle `f14285`, execution manifest `49ee3a`, under prospective grader freeze `64ed2a`. Full identities are stored in the audit JSON files. The grader first received these original outputs after the rubric froze. The parent disclosed the memory-unit suspicion before the audit; the grader then independently inspected the original code and obtained official version-pinned sources. That causal audit is post-exposure and is not a blinded discovery.

## Integrity and prospectivity

All **3,178 files / 152,769,638 bytes** in the original bundle match their recorded sizes and SHA-256 hashes. The grader's three frozen payload files remain unchanged. The original manifest and all trial rows pass the frozen schemas. All **828 planned IDs** reconcile exactly with both the JSONL ledger and per-trial raw records, without duplicates, missing rows, identity changes, or mismatched manifest hashes. The execution manifest timestamp is `2026-11-06T12:40:16.489699+00:00`; the earliest measured trial starts at `12:40:17.449257+00:00`.

The original outcomes are **471 success, 24 unverified accuracy, 126 planned skip, 108 predicted table cap, 78 unsupported conversion, 15 invalid output, and 6 timeout**. These are trial counts, not independent proteins. The cohort has **42 unchanged baseline states, six published computational protein extensions, and eleven synthetic controls**, with 67 representations. The baseline runs only the high profile; the new cases run both profiles. Do not describe this as a complete crossing of every model and profile.

The six extensions reproduce the frozen rule when independently extracting all 35 raw matrix links from the archived author HTML and sorting by declared positions and PDB ID. All 42 baseline hashes match their mapping. Preparation/finalization ledgers disclose prior evidence and static changes before measured runs. Timestamps and local hash inventories are provenance evidence, not a trusted external timestamp service.

## Semantics and structure

Independent code, without importing the converters or simplifier, checks all **67 representations**: domains, factor entries/scopes, primal edges, components, recorded-order induced width, largest table, and the declared two-array-plus-input workspace estimate. All eight serialized reductions reproduce entry-for-entry. Additive splits are checked as exact identities of the stored binary64 values using `Fraction`; constants and one-axis reductions preserve hard zeros. Every original variable/domain remains in the sum.

Independent source reads check all **75,264 selected CPD pair entries**, every selected BKB unary, and each template term, including coordinate coverage, duplicate selected coordinates, first-AA selection, domain encounter order, and hard zeros. The target follows the archived author converter: `Etmp + BKB + pair`; `SELF` is not added again. Only literal `1.0E38` is mapped to zero weight. All other finite first-column energies remain finite stored logs, even when ordinary exponentiation would underflow. This audit checks selected source coordinates exhaustively; nonselected full-pair completeness remains supported by the preserved worker bitset audit rather than a second complete grader reconstruction.

The six new inputs have **23–30 listed positions and 10–25 nontrivial rotamer variables**. Their represented graphs become complete graphs on the nontrivial variables after removing constant/singleton dependencies. Removing singleton edges reduces reported width but leaves largest dense joined-table sizes unchanged. The smallest new case, 1FYN, has 15,805,440 declared assignments and a 126,443,520-byte largest dense table under the recorded order; the other five have predictions above 512 MiB. These are dense-representation/order results, not lower bounds for every exact algorithm. No sparse published-protein family was obtained. Synthetic forests, grids, constant and separable controls must retain their separate role.

The protein extensions are arbitrary source-first fixed-AA, **single-state beta=1 numerical energy targets**. They are not experimental affinities, paired binding ensembles, a physical-temperature calibration, sequence optimization, or biological prediction evidence.

## References and resources

All **471 original success values** independently recompare against their frozen references, with maximum absolute log error **1.85e-13**, inside the prospective tolerance. This reaggregation is not a fresh reference computation: baseline references include the previous independent audit, and synthetic references are separately generated analytic/transfer calculations. The 24 no-oracle completions remain `unverified_accuracy` in the original ledger. Fresh high-precision grader checks are pending and will be labeled post-exposure; they will not silently replace original status rows.

All **126 skips** are the frozen batch-enumeration rule for more than 20 million assignments. All **87 custom join rejections** have a proposed dense join above the table cap; the other **21 table rejections** are native-wrapper clique preflight policy. These are not observed OS allocation failures. The profile caps are 16/128 MiB for named table allocations and 128/512 MiB for process RSS, with 10/20-second trial timeouts.

Independent scalar `exp/log` reconstruction reproduces the **72 positive-entry underflow rejections** and **six roundtrip-tolerance rejections**. Their status correctly protects the same-target contract; they do not prove exact zero mass or mathematical impossibility. Rejection is specific to this linear-weight adapter/representation.

All six timeouts are external watchdog timeouts. No original trial is classified `rss_limit`; completed success/unverified trials satisfy sampled RSS and reported worker high-water checks. Monitor access-error counts are zero. The 10 ms process-tree sampler and worker lifetime high-water have explicitly limited scopes: transient or exited-descendant peaks can be missed, shared pages can be counted twice, and an instantaneous ceiling is not guaranteed. The nonmeasurement watchdog controls test completion, sampled RSS termination, and timeout. A table cap remains distinct from process RSS.

End-to-end subprocess wall time includes interpreter startup, imports, prepared-model loading, worker output and process reaping. Offline raw-source acquisition/conversion, artifact serialization and complete preparation are excluded. The stored `preparation_seconds` covers model loading, static analyses and exact reduction before writing artifacts. Therefore `one_off_wall_plus_algebra_seconds` is not a complete raw-source-to-result cost.

## Independently confirmed scheduler-unit confound

The installed Python 3.3.2 docstring says the parameter is in gigabytes. The official C++ [ScheduledInference declaration](https://raw.githubusercontent.com/agrumery/aGrUM/3.3.2/src/agrum/base/graphicalModels/inference/scheduler/scheduledInference.h) specifies megabytes, its [forwarder](https://raw.githubusercontent.com/agrumery/aGrUM/3.3.2/src/agrum/base/graphicalModels/inference/scheduler/scheduledInference_inl.h) passes that value through, and the [Scheduler implementation](https://raw.githubusercontent.com/agrumery/aGrUM/3.3.2/src/agrum/base/graphicalModels/inference/scheduler/scheduler_inl.h) multiplies it by 1,048,576. The actual unit is MiB.

The original adapter computes `max(1, ceil(table_cap / 1_000_000_000))` and passes **1 in both profiles**. Its variable, comment, README and output metadata call that gigabytes, but the scheduler receives a **1 MiB** cap. It is separate from the wrapper table policy and external process limits. The fifteen generic adapter errors contain `std::bad_alloc`, at observed process RSS of about **39–46 MiB**. Preserve `invalid_output` as the original raw classification and annotate the native allocation-policy exception; do not recast these as declared RSS failures.

The parent separately authorized outcome-selected diagnostics on all four distinct failing inputs. Independent inspection of those 16 diagnostic rows shows: all four as-written variants fail; all four default and all four 1024-MiB variants complete; the 128-MiB variant completes three and fails one. These diagnostics support the unit-confound diagnosis. They are posthoc and must not supply replacement campaign rows, a universal memory limit, or a confirmatory performance estimate.

## Current gate judgment

| Gate | Interim judgment |
|---|---|
| Integrity/prospectivity | Pass for the original frozen bundle and complete ledger; subsequent correction is explicitly adaptive. |
| Semantics/numerics | Conversion and exact-reduction audits pass; original validated outputs agree with frozen references; fresh numerical coverage remains pending. |
| Representation/coverage | Useful bounded obstruction and clear synthetic mechanisms; no sparse larger published-protein coverage, no >64-domain family or high-order-factor family. |
| Resource/comparison | Resource policies are auditable; native scheduler confound defeats broad original comparison. Corrective matched run required. |
| Interpretation/usefulness | A validated representation/data artifact and bounded diagnostic are useful; no winner is needed. Broader conclusions remain deferred. |

There is no ETH implementation or theorem-to-program test here. Exact counting or faster inference does not establish better biological prediction. Preserve both original and corrected evidence, including failures, and mark all post-exposure adaptations.

Machine-readable evidence: `original_integrity_audit.json`, `original_semantics_audit.json`, `original_selection_audit.json`, `original_resource_audit.json`, `installed_quota_docstring.json`, and the independently archived official sources in `primary_sources/`. No original input, implementation, result, or frozen grader payload was edited.
