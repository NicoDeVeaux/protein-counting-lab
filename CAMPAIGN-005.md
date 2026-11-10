# Full-precision rigid ensemble transfer pilot

The new study obtains prepared molecular inputs and full-precision binary64 energy matrices from the [Lowegard2020 Harvard Dataverse archive](https://doi.org/10.7910/DVN/VHIRNM), then compares an explicitly discrete ensemble model with its own minimum-energy-conformation baseline. It advances beyond the rounded, underflowed UAI inputs. It does not establish improved biological prediction.

The [primary paper](https://doi.org/10.1371/journal.pcbi.1007447) supplies a prepared structure, design configurations, rigid/minimized state matrices and archived native outputs. The present experiment evaluates **rigid** matrices only. Pairwise minimized matrices are lower bounds and are not treated as energies of fully minimized conformations. Reference-energy adjustments are already incorporated in the stored entries; no external reference correction is added. All evaluated scalar terms are retained.

The direct matched-assay gate **fails**. The prepared model includes Ras G12D, lacks a nucleotide/Mg entry, has Ras C118 and Raf C81, and models only part of the Raf construct. The 2020 titration assay uses nucleotide-loaded Ras and stabilizing substitutions. Earlier retrospective observations include v-Ha-Ras relative radioactivity and incompletely mapped dissociation measurements. These are model/assay differences, not proof that the original study is incorrect. This follow-up is explicitly a **model-transfer mechanistic pilot**, not a direct matched-system affinity validation.

## Fixed panel and results

The grader froze the original 34 BBK design configurations, per-state cap of one million Cartesian assignments, metadata-only duplicate choice and total assignment prefix rule before new scores. Every one of the 41 published variants is tested for input eligibility against every configuration: **1,394 candidate pairs**. **13 variants** qualify, giving **78 WT/mutant state slots and 3,677,224 assignments**. Twenty-six excluded variants exceed the state cap; two have no exact supported template in a compatible design. Their records remain in `prepared/campaign-005/panel_plan.json`. No null/EWAK configuration fills a primary-input gap.

Each mutant is normalized to its own wild type under the same design, since designs use different flexible shells:

`delta_log_K = (logZ_C - logZ_P - logZ_L)_mutant - (logZ_C - logZ_P - logZ_L)_WT`.

The GMEC baseline substitutes `-E_min/RT` for each log partition. The ensemble correction is the six signed terms `logZ + E_min/RT`, accumulated separately to preserve small contributions under large common offsets. This is a log effective conformer count correction, not Shannon entropy.

- All **13 queries and 78 states** complete in the single scheduled run, with no retries or inference-cache reuse.
- Counting changes **two of 78 pairwise variant orders**, with 76 concordant and none numerically unresolved.
- Counting changes **no mutation's predicted improvement/worsening direction** relative to its own WT.
- The ensemble correction ranges from **−1.37749** to **+0.42856** natural-log units. K84R has the largest negative correction; N71E has the largest positive correction.
- N71R and F61W have positive model effects in both approaches; all other admitted variants have negative model effects. This is not a mutation recommendation.

The reversed pairs are N64A/K84R and N64K/K84R: GMEC prefers K84R, while ensemble scoring prefers the other variant. All three have negative effects relative to their own WT in both methods, so these reversals do not identify an improved binder.

`outputs/campaign-005-analysis.json` contains every point, correction, direction and pairwise order. `outputs/campaign-005-v2.png` and `.svg` visualize the results. The first figure is retained; v2 moves an annotation that obscured one point, without changing data.

## Separate empirical context

Eight admitted variants have S2 relative-binding observations attributed to Fridman2000. The recovered original paper describes retained radioactive v-Ha-Ras binding to bead-linked GST-RBD, not equilibrium Kd. Five other admitted variants have printed Kd values, but their original assay/construct row mapping remains unresolved. They are listed individually and do not enter a pooled correlation. Missing measurement errors remain unknown.

For the eight relative-binding observations, the prespecified descriptive transfer comparison gives:

| Method | Spearman rho | Nominal exact permutation p | Variant-bootstrap 95% interval |
|---|---:|---:|---:|
| Rigid ensemble | 0.6667 | 0.0831 | −0.1053 to 1.0000 |
| Same-model GMEC | 0.6190 | 0.1150 | −0.2000 to 1.0000 |

The paired bootstrap interval for the correlation difference is **0.0000 to 0.3784**. These are 40,320 exact permutations and 10,000 paired variant resamples with the frozen seed; no constant bootstrap resample occurred. Printed-value ties use average ranks rather than artificial strict source ranks. Small, correlated, size-selected observations and model transfer limit inference; these numbers do not establish an ensemble advantage. No fitting, calibrated molar prediction or fresh native BBK*/EWAK* execution is performed.

## Numerical and resource evidence

The restricted Python decoder agrees bit for bit with archived OSPREY Java getters on **126 rigid matrices and 484,084 unary/pair entries**. Independently, the grader decodes every original core rigid/minimized matrix and reconstructs every core conformer map from archived source, the rotamer library and prepared coordinates. Source reconstruction is not molecular geometry or energy regeneration.

The completed independent audit verifies all **78 state outputs and 13 normalized query scores** against references computed from original source bytes without importing experiment scoring code. It sums binary64 input energies exactly as scaled dyadic integers and evaluates Decimal references at 90 digits, with separate 60/90-digit passes on the smallest complete WT/mutant case. Maximum absolute errors are **1.59e-14 per log partition** and **1.39e-14 per normalized query score**, inside the frozen allowances. The largest independently bounded omitted reference tail is **8.07e-30**; the smallest-case 60/90 discrepancy is **5.10e-59**. These numerical checks do not repair model/assay differences. The full verdict is in `grader/campaign-005/REPORT.md`; final seal `71b732` binds 26 audit artifacts separately from the measurement bundle.

Measured worker wall is about **0.300 seconds**; the outer controller interval is about **0.384 seconds**. Observed worker lifetime RSS peaks at **169,607,168 bytes**, below the frozen 512 MiB policy. The worker observes its own lifetime high-water after each state, not instantaneous total-system memory. No performance comparison is claimed. Aggregate source discovery/manual-development preparation time was not enclosed in a watchdog or consistently recorded, so compliance with the protocol's total preparation ceiling is not established. The short scoring interval does not represent end-to-end biological preparation cost. Independent reference computation takes approximately 8.74 seconds separately.

All input energy entries are finite. The floating-point implementation records **3,012,982 batch-relative exponential underflows**; these are numerical tail losses rather than structural zeros, support pruning or literal source underflow. Independent high-precision references and explicit tail bounds verify the declared numerical allowances. Observed `numpy.longdouble` has 52 mantissa bits on this machine, so no extra extended precision is claimed. This is not an exact-arithmetic certificate merely because all assignments are visited.

## Provenance and reproduction

Grader protocol `546cc5` precedes fresh scores. Amendment `6df454` prospectively defines the model-transfer endpoint after publication-column exposure. Activation `da1315` binds 34 files, the fixed slot plan, exact source RT, environment, tests and budgets; review `660516` checks its exact bytes before the single execution. An earlier activation review is preserved and explicitly superseded after two files were added before scoring.

Review bundle `4c5b85` seals **125 files and 146,646,865 bytes**, including all new source/preparation/measurement/analysis artifacts and the separate contextual-statistics review. It excludes the later parent guide and final independent audit, which are sealed separately. Every bundle file rehashes correctly.

Published S2 computational columns and one archived BBK WT row were seen during preparation. Input-family/size rules predate that parent exposure; the mechanistic amendment follows it and precedes every fresh rigid score. No blind retrospective analysis is claimed. Prefreeze synthetic failures exposed two large-offset cancellation issues and a test-runner collection problem; all records are retained, and final verification passes **10 core checks plus three decoder checks**.

Primary artifacts are:

- `data/campaign-005/kras2020/`: checksum-verified original archives, metadata and retrieval provenance.
- `data/campaign-005/source_discovery/REPORT.md`: bounded candidate/assay search, literal S2 extraction and source manifest `8ac18d`.
- `experiments/energy_recovery5/READY.json`: decoder/native identity handoff `f3f7bd`.
- `prepared/campaign-005/ACTIVATION.json`, `analysis_plan.json` and `panel_plan.json`: frozen scientific choices and complete exclusions.
- `runs/campaign-005/`: raw startup, attempts, 78 state results, 13 query results and completion records.
- `runs/campaign-005-control/`: outer invocation, return status and raw stdout/stderr.
- `outputs/campaign-005-analysis.json`: prespecified analysis; code was separately frozen before execution.

The dedicated interpreter is `experiments/established/.venv/bin/python`. The entry point is `python -m scripts.campaign5_worker prepared/campaign-005/ACTIVATION.json` from the repository root. It refuses to overwrite its output directory. Reproduction needs a new versioned activation/output path; never overwrite this evidence. Earlier campaign files are preserved. All work is local CPU; no author contact, paid/cloud compute or remote publication occurred.

The next biological-validation requirement is a model prepared for the exact measured molecular system, with its assay-linked sequence/background/nucleotide identities and reproducible energy generation. Faster or more exact counting alone cannot supply that missing model.
