# Structure and resource study

This local exploratory study measures conventional partition-sum computation. It includes 42 unchanged baseline models, six larger published protein-design models, and eleven explicitly synthetic controls. There are 67 measured representations and 828 scheduled trials per run: three methods, three fresh repeats, and the declared resource profiles. The baseline uses only the high profile.

The independent verdict is **useful conventional feasibility evidence**: integrity and audited numerics pass; local memory findings are supported; broad solver timing and biological improvement claims are unsupported. Read the final report in `grader/campaign-002/REPORT.md`.

The larger proteins are arbitrary source-first fixed-AA, single-state numerical targets at dimensionless beta=1. This is neither sequence design nor calibrated binding-affinity prediction. Their interactions remain complete among nontrivial rotamer variables after exact simplification. The synthetic sparse and separable models demonstrate mechanisms separately.

| Recorded status | Original | Corrected |
|---|---:|---:|
| Passed frozen numerical reference | 471 | 484 |
| Completed without adequate frozen reference | 24 | 24 |
| Predeclared enumeration skip | 126 | 126 |
| Table-policy rejection | 108 | 108 |
| Linear-weight conversion rejection | 78 | 78 |
| Invalid output / allocation exception | 15 | 0 |
| Timeout | 6 | 8 |
| **Total** | **828** | **828** |

These are trial counts, including repeats and multiple representations, not independent biological samples. Both ledgers remain unchanged. A completed unverified output is not a validated success.

## Correction and provenance

The independent grader froze its protocol before the first measured run. The original comparator adapter passed `1` to a native memory-setting API whose Python documentation described gigabytes. Independent inspection of the pinned C++ implementation showed MiB units. All fifteen allocation exceptions therefore occurred under an unintended 1 MiB scheduler quota; they are not evidence of exhaustion at the declared process-RSS ceilings.

Version 2 passes 1024 MiB, using the same locked pyagrum 3.3.2 runtime and the unchanged external budgets. The full original trial matrix was repeated, with disclosed knowledge of the original outcomes and selected diagnostics. All fifteen formerly exceptional rows passed their numerical reference in the rerun. Four other rows changed between completion and timeout; all are retained. One initial manifest-schema rejection occurred before any corrected trial; its catalog and partial freeze are archived.

The corrected run uses `a042ab`, under adaptive amendment `e587cf`. Its combined review bundle is `c12e4a`; the original bundle is `f14285`. Full SHA-256 values are stored in the manifests. The combined bundle checks 6,199 files and preserves both runs, source matrices, conversion audits, exact-algebra records, diagnostic evidence, and validation logs. The final independent audit seals 29 audit artifacts under `095f16` in `grader/campaign-002/audit_manifest.json`.

## Reading the results

Custom VE operates in the log domain. Batched enumeration streams assignments. The established comparator reconstructs log Z through conditional exact Shafer-Shenoy marginal queries; all queries are timed. This adapter is not a native one-query partition-sum API. Its 78 conversion rejections protect the same-target contract when ordinary probability weights would underflow or lose too much accuracy; they do not prove that the target is unsolvable.

The low/high profiles specify 16/128 MiB named-table caps, 128/512 MiB process-RSS ceilings, and 10/20-second wall limits. Table-policy rejection, sampled RSS enforcement, and native scheduler quotas are distinct. The 10 ms RSS sampler can miss transient peaks and double-count shared pages; worker lifetime high-water checks supplement it. Neither provides an instantaneous universal memory guarantee.

The frozen static workspace estimate is labeled "conservative" in its metadata, but the grader found it is not an upper bound on live numeric arrays. For original 1FYN it predicts 252,905,192 bytes while the kernel records 268,710,632 bytes of live arrays. Observed process peaks are higher still. This label is preserved as original evidence and corrected here explicitly.

Exact simplification leaves 1FYN's largest named table unchanged at 126,443,520 bytes, while observed process peaks fall from about 455–496 MB to 207–208 MB. This is a useful local representation/memory observation, despite the absence of a controlled timing advantage. It is not a universal memory guarantee or evidence that the other five proteins became tractable.

Fresh-process wall times include startup, prepared JSON loading and monitoring. Raw-source preparation and serialization are excluded. Recorded algebra-preparation times also omit derived artifact serialization. Three repeats provide descriptive local measurements; observed variability and timeouts limit speed claims.

No ETH algorithm, novel counting method, improved affinity prediction, or biological validation is demonstrated here. The independent report determines which numerical, representation, and resource observations are useful.

The grader subsequently computed a separate 90-digit Decimal reference for 1FYN from the original stored-log model. Exact hard-zero propagation reduced 15,805,440 declared assignments to 263,088 assignments with positive support. The reference includes an explicit negligible-tail bound (about 1.10e-127 relative mass); its arithmetic is not outward-rounded. Completed values in both campaigns agree within 8.82e-14 in log Z. This is post-exposure accuracy evidence, and the original `unverified_accuracy` labels remain intact.

The timing audit blocks broad performance conclusions: 104 of 167 complete three-repeat cells have wall max/min above 2, and 56 above 5. Early and late trials also differ substantially. The experiment does not identify a generally faster solver. Exact support propagation before dense inference is a concrete follow-up hypothesis; the grader's reference calculation is not a controlled performance trial.

## Evidence and reproduction

- Independent report: `grader/campaign-002/REPORT.md` (with its machine-readable audit files).
- Corrected ledger and summary: `runs/campaign-002-amendment-001/`.
- Combined sealed bundle: `runs/campaign-002-amendment-001-review/bundle_manifest.json`.
- Original retained ledger: `runs/campaign-002/`.
- Amendment and premeasurement catalog correction: `prepared/campaign-002/`.
- Figure: `outputs/campaign-002-v2.png` and `.svg`; derived after measurements and separate from the sealed execution bundle.
- Relevant correction validation: `prepared/campaign-002/amendment-001-tests.txt` — 69 passed. The retained earlier full preflight reports 154 passed in its authorized runtime; these test sets overlap.

The dedicated Python environment is `experiments/established/.venv/bin/python`, from the lockfile in that directory. The original inference implementation and all original execution files remain preserved. Process monitoring requires macOS permissions outside this session's restrictive sandbox.

To reproduce into a **new** run directory, use the versioned driver, without overwriting any existing evidence:

```sh
experiments/established/.venv/bin/python scripts/campaign_round2_v2.py freeze --run-dir runs/campaign-002-reproduction-001
experiments/established/.venv/bin/python scripts/campaign_round2_v2.py run --run-dir runs/campaign-002-reproduction-001
experiments/established/.venv/bin/python scripts/campaign_round2_v2.py summarize --run-dir runs/campaign-002-reproduction-001
```

Use the unchanged amended catalog to retain the frozen reference map. The freeze verifies original target representations, trial identities and external budgets, and hashes the catalog evidence. The independent audit separately verified that the measured correction preserved every reference. The raw data and original baseline artifacts must remain available; the locked environment alone is insufficient. A new run has a new provenance manifest and must not replace either stored campaign.
