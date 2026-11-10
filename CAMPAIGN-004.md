# Three-state sequence-ranking pilot

The pilot computes the source-model score `log K* = log Z_complex - log Z_protein - log Z_ligand` across a fixed residue-template panel. The completed independent audit verifies the full ranking workflow for the released source encoding. Physical affinity and the unrounded physical partition functions remain unestablished.

All 14 existing source archives pass the formal decoder audit and source-first equivalence checks against the prior 42 state models, ignoring only the old explicit scalar-zero identity factors. The predeclared minimum-sum Cartesian-count rule selects `2rfe_prepped_00012`. Its first mutable selector is residue **F338**. The panel keeps all 21 source templates there and fixes every other selector to its source-first template. `HIP`, `HIE` and `HID` remain distinct protonation templates; these are not 21 different natural amino acids. Compatible additional conformers remain included; their coordinate origin is not inferred from an index.

## Results

Both baseline and pruned workflows finish **21/21 templates** in every VE and enumeration repeat. There is **no additional sequence coverage** from pruning on this small pilot. All 252 repeated scores, representing 21 unique templates, pass the frozen references. All 756 state slots reconcile, including 240 explicitly traced cache hits. Every panel reproduces all 210 pairwise orders and the reference top-1, top-3 and top-5 membership. The smallest adjacent gap is approximately 0.03206 log units, above the numerical envelopes.

| Highest source-model scores | Natural-log K* |
|---|---:|
| LEU — declared baseline | 32.069211 |
| ARG | 32.030782 |
| LYS | 29.475048 |
| ASN | 27.704647 |
| ILE | 26.766135 |

No tested alternative beats the declared baseline in this model. The LEU–ARG gap is approximately 0.03843 natural-log units. Numerical separation is not evidence of physical significance or an experimental improvement. These scores must not be converted into calibrated molar Kd values without establishing the missing physical conventions and model validity.

| Full-panel worker wall range, three fresh repeats | Baseline | Pruned |
|---|---:|---:|
| VE | 0.168–0.184 s | 0.189–0.197 s |
| Batched enumeration | 0.224–0.233 s | 0.185–0.194 s |

Pruned VE is slower in this record, with both arm orders observed. Pruned enumeration runs are shorter, but the frozen random seed places the pruned arm first in all three enumeration pairs; order confounds that comparison, so it does not establish a pruning speedup. No extra favorable repeats were added. Observed whole-worker peaks are approximately 74–76 MB across all paths; this pilot shows no meaningful memory-capacity expansion. All paths are far below the common 20-second/512 MiB panel limits. These are local measurements, not a general solver ranking.

The independent raw-source oracle evaluates every original panel state at 90 and 120 decimal digits. It separately evaluates exact source-decimal weights, exact source-binary64 weights and the ideal target represented by stored binary64 logarithms. The last is the measured methods' primary target. Maximum recorded absolute errors are approximately **6.58e-14 per log Z** and **8.33e-14 per log K***, inside the frozen 1e-8 and 3e-8 tolerances. All 21 ratios are finite; no denominator is zero. This is numerical validation, not an outward-rounded interval certificate.

The completed independent assessment is in `grader/campaign-004/REPORT.md` and `verdict.json`, with audit seal `352888`. Its verdict is a verified source-encoding ranking, equal coverage, no material memory benefit and no general timing win. The physical-affinity gate is not established. This guide incorporates the audit's source, numerical and measurement qualifications; the grader did not review this later narrative or the parent plots.

## What is timed

Each fresh panel worker reads and parses the original source archive once, conditions all 21 queries, applies its declared transformations, verifies numerical target fingerprints and computes all three states and the ratio. Both arms use the same exact algebraic simplifier. The pruned arm additionally uses exact hard-zero propagation. Only source-represented zeros remove support; no finite stored log weight is discarded.

Identical transformed state targets are cached within a panel using exact numerical fingerprints. Cache origins and values are checked independently by the controller. This reuses the unchanged free-state result across the panel. Conditioning, transformations and fingerprint checks still run for every query. There is no cache across fresh workers or repeats, and no OS cache flush. Cached solver statistics are not presented as fresh solver time.

Startup, parsing, conditioning, transformations, inference, progress/result serialization and process reaping are inside each outer row watchdog. The worker reserves 0.5 seconds for closeout, and source loading has a five-second phase deadline. VE uses a 16 MiB estimated solver-array policy and the wall limit; enumeration enforces a 20-million-assignment guard per state. Every observed state product is below that guard. Neither policy bounds total panel assignments or whole-worker memory; the latter has a separate 512 MiB RSS policy.

Controller parsing, artifact hashing and reference validation are outside each worker row clock and inside the campaign clock. All 12 measured panels plus controller work take about 2.56 seconds; recorded per-panel controller validation totals about 0.103 seconds. Static preparation/reference work takes about 8.79 seconds separately, with reference construction approximately 5.65 seconds. Molecular structure preparation and energy generation are excluded because the source encodings are supplied inputs.

RSS observations use the maximum of sampled process-tree RSS and worker lifetime high-water before/after final JSON writing. Per-query high-water readings are cumulative worker values, not isolated query memory. Sampling requests a 10 ms sleep; achieved cadence is not proved and transient peaks can be missed. Later timing-sidecar/stdout allocation has sampling coverage only. No instantaneous memory ceiling is claimed.

## Interpretation limits

- The authoritative `.uai.sum` file specifies one numerator state and two denominator states, agreeing with the archived metadata. A plain joint Markov partition function would multiply the three state sums and is not the K* ratio.
- The source declares unnormalized Boltzmann conversions at 298.15 K with its supplied gas constant. Every source factor and selector mapping is accounted for. Ambiguous scalar/selector-only or cross-state factors cause rejection rather than silent omission.
- Some source Boltzmann factors have already underflowed to literal zero. They remain zero in all paths. Rounded archived energy text cannot restore the original unrounded physical model reliably. Correctness here concerns the represented source target.
- The bounded comparator audit found no validated drop-in BBK*/AOBB-K* implementation for these exact fixed UAI factors. OSPREY's API requires conformational-space and energy-calculator integration that was not implemented. This pilot makes no domain-solver superiority claim.
- The separately collected 2025 experimental specificity dataset has 63 affinity labels but missing prepared molecular inputs, energy matrices and same-target score tables. It is not this pilot's biological validation set. No experimental correlation or predictive accuracy improvement is measured.

## Frozen evidence and reproduction

The fresh grader protocol is `8f2343`. Preparation manifest `500936` binds case/panel rules, actual panel identities, code/tests, reference procedure, resources and exact schedule before new protein conditioning. Execution manifest `96d122` binds all resulting targets/references before measurement, carrying the scientific choices unchanged. The review bundle `1e4e8e` inventories 8,428 files including unchanged prior evidence. Later plots, this guide and independent audit outputs are separate.

The final audit rehashes all 8,428 bundle files, including all 8,031 prior campaign files, and seals 15 audit artifacts separately. Prospectivity receives a qualified pass: source grammar, labels and a numeric prefix were inspected before the preparation freeze, as disclosed; formal audits, conditioning and reference enumeration follow that freeze in the stored chronology. Local timestamps and seals cannot certify the absence of undisclosed historical work.

Preflight: **136 tests passed** in the dedicated locked Python environment. Synthetic development failures, including an incomplete fixture and an initially wrong test interpreter, preceded preparation; they are not erased or labeled measured results. No measured panel was retried and no implementation changed after preparation freeze.

- `prepared/campaign-004/preparation_manifest.json`: prospective choices and code hashes.
- `prepared/campaign-004/preparation.jsonl`: all 17 static/reference stage attempts.
- `prepared/campaign-004/independent_target_verification.json`: independent original-source entry checks for all 63 conditioned states.
- `prepared/campaign-004/references.json`: both precision passes and all three numerical target interpretations.
- `runs/campaign-004/manifest.json`, `panels.jsonl`, `queries.jsonl`, `states.jsonl`: complete planned and observed identities, values, cache origins and evidence.
- `runs/campaign-004-review/bundle_manifest.json`: sealed evidence inventory.
- `data/campaign-004/comparator_audit/REPORT.md`: official-source comparator and biological-input feasibility audit.
- `outputs/campaign-004.png` and `.svg`: derived result figures.

The dedicated interpreter is `experiments/established/.venv/bin/python`; package versions are declared at freeze, rather than independently logged at every import. The original preparation and execution entry point is `scripts/execute_round4.py`. It intentionally refuses to overwrite an existing freeze or measured run. Reproduction requires a new, explicitly versioned run location and matching manifests; copying only output scores is insufficient. Process-tree monitoring requires the macOS permissions used by the recorded experiment. No remote publication or paid/cloud compute was used.
