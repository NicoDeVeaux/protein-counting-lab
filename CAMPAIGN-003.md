# Exact hard-zero propagation follow-up

This exploratory local study compares the same conventional solvers before and after exact support propagation on all six published CPD numerical targets. The baseline cold-loads the original model and applies the existing exact algebraic simplifier. The treated arm cold-loads the same model, removes only domain values without hard-zero constraint support, and applies that same simplifier. Every measured result includes its own transformation costs.

The completed independent audit supports a **local 1FYN feasibility, cost and VE memory benefit**, with all five larger targets still unsuccessful under these policies. It verifies all 8,031 bundle hashes, all 324 rows, 137,976 factor-entry identities and all 119 reference-covered outputs. The final audit seal is `d2084f`; see `grader/campaign-003/REPORT.md` and `AUDIT_SEAL.json` for qualifications.

Only explicit negative infinity forbids an assignment. Finite values remain positive weights even when ordinary exponentiation would underflow. Duplicate-scope boolean constraints are aligned and intersected; numerical factors remain separate. Arc consistency does not imply global feasibility. Domain maps, deletion witnesses, factor restrictions and exact algebra records are archived.

The 324 planned trials comprise six published models at low/high profiles and six labeled synthetic controls at the high profile, two arms, three methods and three fresh repeats. All 324 rows are retained: **119 frozen-reference passes, 60 enumeration-state-policy rejections, 78 conversion rejections, 63 table-policy rejections and four timeouts**. No row has an unverified partition value; the five proteins without an independent oracle did not produce a completed value.

## Observed result

| Published target | Baseline Cartesian assignments | After exact propagation |
|---|---:|---:|
| 1FYN | 15,805,440 | 476,280 |
| 1BK2 | 48,157,200,000 | 1,064,448,000 |
| 1MJC | 1,040,153,273,083,072,512,000 | 37,922,254,747,820,352,000 |
| 1PIN | 530,811,773,856,000 | 127,598,984,100,000 |
| 1SHG | 41,479,796,736,000,000 | 59,962,291,200,000 |
| 1CSK | 296,339,963,841,331,200 | 13,607,447,319,244,800 |

These are products of retained domain sizes, **not positive-support counts**. The separate prior 1FYN audit enumerated 263,088 globally nonzero assignments.

For 1FYN, the named largest table falls from 126,443,520 bytes to 3,810,240 bytes. Under the low profile, baseline VE is table-rejected in all three repeats; propagated VE completes correctly in all three. Under the high profile, all three complete in both arms: measured cold wall times are approximately **0.39–0.51 s baseline versus 0.13–0.18 s propagated**, and whole-process observed peaks are approximately **206–207 MB versus 42 MB**. In-memory propagation/algebra/target-check preparation costs about 9–17 ms for these runs, already included in the cold result.

Propagated 1FYN enumeration also passes in all six low/high repeats. Baseline enumeration has two completions and four timeouts; do not drop censored rows or report infinite speedup. Enumeration's measured memory does not improve: roughly 67 MB propagated versus 64–65 MB baseline. The reduction benefits depend on the method.

The other five targets still exceed these dense-table and enumeration policies. Even 1SHG's roughly 692-fold domain-product reduction leaves about 60 trillion assignments. The linear-weight pyagrum adapter rejects all six protein targets in both arms. No new protein identity becomes solved, no physical affinity prediction is tested, and no ETH-derived algorithm or novel propagation method is demonstrated.

The separate independent report in `grader/campaign-003/REPORT.md` determines which semantic, numerical and measurement conclusions are supported. Absolute timings are local observations from three repeats; the study does not establish a general solver ranking.

## Protocol and retained corrections

The independent protocol froze as `004d54`. Amendment 001 (`e5a507`) clarified the preparation sequence: fix source inputs, algorithms/configuration, references, budgets and complete schedule before static preparation, then bind derived artifacts before timed inference. Preparation manifest `996bf1` preceded all 24 static preparation attempts. The 1FYN reference known from campaign002 is prospective here. The five other protein references remain absent.

Two execution freezes failed before any timed trial: an inherited `selection_rule` object shape and a descriptive algebra label outside the inherited enum. Both failed catalogs, partial directories, error records and the complete schema diagnostic are preserved. Amendments 002 (`8c625a`) and 003 (`6871f7`) disclose format-only corrections. The original descriptions remain present; enum labels are derived from already bound exact-algebra proof kinds. The complete corrected fixture passes the unchanged full schema before launch. Numerical implementations, prepared numerical models, references, all 324 identities/order and all budgets remain unchanged from preparation freeze.

The execution manifest also rewrites descriptive accuracy-contract text relative to the preparation manifest and adds provenance/inventory records beyond the literal field-only wording of the format amendments. The numerical validator code was fixed before preparation; targets, references, resource policies and trial order remain identical. These wording/provenance differences remain disclosed procedural deviations. No postmeasurement amendment erases them.

Final measured manifest `6a9215` and all failures live in `runs/campaign-003-amendment-003/`. The sealed review bundle `19ed41` checks 8,031 files, including unchanged prior evidence. Later plots, this guide and independent audit outputs remain separate from measured evidence.

## Resources and validation

- Low: 16 MiB named-table policy, 128 MiB process RSS, 10-second whole-row timeout.
- High: 128 MiB named-table policy, 512 MiB process RSS, 20-second whole-row timeout.
- Each measured preparation phase has a three-second signal deadline; native calls may defer signal handling. The outer row watchdog remains active.
- Static preparation: 20 seconds/512 MiB per row, 180 seconds total; no partition inference. Measurements: 900-second total budget, one worker at a time.
- Enumeration guard: 20 million transformed Cartesian assignments, checked **after cold preparation**, so skipped inference still pays preparation cost.
- Three rounds with shuffled model/profile and method blocks, adjacent randomized arm pairs; seed 2026110603. Fresh processes; no OS cache flush or warmup inference.
- Wall/CPU clocks cover original loading, propagation, algebra, target fingerprinting, aggregate method call and valid result JSON encoding/write. Legacy internal CPU subdivisions are unavailable; internal wall phases retain their scope.
- External RSS sampling requests a 10 ms sleep interval; achieved cadence is not verified. Worker lifetime high-water through result serialization supplements it. Later stdout and sidecar creation have sampler coverage only. Transient peaks can be missed, and an instantaneous ceiling is not guaranteed. Ledger/summary peak fields are sampler-only; memory ranges in this guide use the maximum of sampled and both worker high-water readings.
- Preflight: **118 tests passed**, including 85 support tests, cold pipeline/clock/hash/deadline checks, synthetic reference checks and driver accounting. Additional metadata schema checks are retained separately. No old source or measured result was overwritten.

This is numerical validation within the unchanged absolute-log tolerance, not an outward-rounded interval certificate. The static two-largest-array workspace estimate is a heuristic, not an upper bound or total RSS prediction.

Controller ingestion, artifact hashing and numerical reference validation occur after each worker's row clock. The 134.74-second sum of row wall times excludes those costs; the 136.42-second campaign total includes them. Method-call and internal wall phases are nested, and their times must not be added together.

The final method-version metadata says `unknown` for pyagrum because of a distribution-name lookup mismatch. All 108 native worker records identify installed distribution 3.3.2, consistent with the pinned runtime. The incorrect manifest field remains preserved and disclosed.

## Evidence and reproduction

- `grader/campaign-003/REPORT.md` and `verdict.json`: independent assessment.
- `runs/campaign-003-review/bundle_manifest.json`: sealed evidence inventory.
- `prepared/campaign-003/preparation_manifest.json`: prospective static plan.
- `prepared/campaign-003/preparation.jsonl`: all 24 static attempt records.
- `prepared/campaign-003/catalog.amendment-003.json`: unchanged targets with corrected schema metadata.
- `runs/campaign-003-amendment-003/`: complete raw measured ledger, stdout/stderr, sidecars, environment and schedule.
- `outputs/campaign-003.png` and `.svg`: derived result figures.

Use the dedicated locked Python at `experiments/established/.venv/bin/python`. To reproduce the measured stage into a new directory, retaining all existing evidence:

```sh
experiments/established/.venv/bin/python scripts/campaign_round3.py freeze --catalog prepared/campaign-003/catalog.amendment-003.json --run-dir runs/campaign-003-reproduction-001
experiments/established/.venv/bin/python scripts/campaign_round3.py run --run-dir runs/campaign-003-reproduction-001
experiments/established/.venv/bin/python scripts/campaign_round3.py summarize --run-dir runs/campaign-003-reproduction-001
```

The freeze checks the original preparation plan and all frozen implementation hashes. Its original sources and prepared evidence must remain available. Process-tree monitoring requires the same macOS permissions used by the recorded experiment. A new measured run has a new manifest and must not replace the preserved rows.
