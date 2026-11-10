# Campaign004 independent reference

Classification: exploratory `poc`. This package uses only the Python standard library. It neither imports experiment preprocessing/inference code nor reads conditioned targets to define its reference. The CLI is for parent-controlled execution after the preparation freeze:

```sh
uv run python -m experiments.three_state_reference \
  --archive data/raw/uai23/2rfe_prepped_00012_3_0_3_3_F2_N0_E0_e0_t0e+00_KstarMAP.zip \
  --output runs/campaign-004/preparation/references.json \
  --max-assignments 1000000 --state-seconds 60 --total-seconds 300 --memory-mib 512
```

The entire source-ordered panel runs once under this policy. Labels are never filtered by energy, support, runtime or reference result. The chosen source is fixed elsewhere by the minimum sum of existing source-first state Cartesian counts. This package does not choose a case after computation. It selects the first query selector with at least two non-`DUMMY` labels, takes all its non-`DUMMY` labels in source order, and fixes every other query selector to its first non-`DUMMY` label. `HIP`, `HIE` and `HID` remain separate labels.

## Stable Python API and JSON contract

`load_archive(path)` independently reads ZIP/UAI/query/sum/summary and hashes the archive and every original member. `panel_specs(archive)` returns fixed panel identities. `condition_state(archive, sequence, state, scalar_owners=None)` returns the independently sliced state plus source-offset proof. Sequence keys are original selector integers. State names are `complex`, `protein`, `ligand`; their order is fixed. `reference_state(target, limits, total_deadline=None)` performs both precision passes. `reference_panel(archive, limits, scalar_owners=None)` preserves every planned state row. `score_states(states, semantics)` applies the zero rules. `verify_conditioning(archive, sequence, state, model_json, scalar_owners=None)` compares a decoded unpruned target JSON against every independent source entry, factor/scalar and metadata map; it returns `status: pass|fail` without importing the external writer. Explicit scalar owners are a map from original factor index to state name; unsupported implicit scalar/selector-only ownership is an error.

Top-level JSON keys include `case_id`, `source_hashes.archive_sha256`, `source_hashes.members`, `planned_panel`, `planned_state_rows`, `rows`, `limits`, `elapsed_seconds`, and `environment`. Each `rows[]` entry has `panel_index`, `selector`, `label`, `sequence` (string original-selector IDs), `states` keyed by state name, and `scores` keyed by numerical semantics.

A successful state has `status: "reference-passing success"`, `values[semantics].Z` and `.logZ` as decimal strings at 120 digits, `passes[]` at 90 and 120 digits, `precision_120_minus_90_logZ`, `conversion_logZ_differences`, `positive_assignments`, `conditioning_proof`, and elapsed/RSS observations. Each defined score also records its two precision passes, `precision_120_minus_90_logKstar`, and `logKstar_minus_source_binary64`. Failure rows retain identity, status, reason and completed passes. Cap failures never cause panel replacement. The primary production-method comparison is `values.stored_binary64_log.logZ` and `scores.stored_binary64_log.logKstar`. The other two targets disclose conversion effects.

All hashes in JSON are full SHA-256 identities. `conditioning_proof` records original state variables, original conformer-domain maps, every source factor owner, every retained source table index, each decimal lexeme, binary64 hex value, and stored logarithm hex value. Its hash is over canonical JSON of those fields. It does not use the production target's hash as an independent reference identity.

## Source and conditioning proof

Let the original table scope be `(v0,...,vr)` with domain sizes `(d0,...,dr)`. The decoder's table index is `(((a0*d1+a1)*d2+a2)...*dr+ar)`: the last scope variable changes fastest. Every retained table entry is obtained through that expression using the original domains, including when selectors and conformation variables occur in asymmetric scope order. No factor is transposed or normalized. Every source factor is owned by exactly one state from its non-selector scope. A factor that crosses state groups, or whose scope gives no state owner, is rejected unless an explicit scalar assignment supplies the latter owner. Scalars remain multiplicative table entries, including sequence-dependent selector-only factors with explicit owners. There are no discarded offsets.

For shared sequence `s`, each state variable retains **all** original conformer indices whose exact summary label equals `s` at its original residue ID. This is a bijection from each retained local assignment to its corresponding original assignment. In particular, a final source conformer mapped to a real baseline label is retained; it is never inferred to be `DUMMY`, UFO, or zero by ordinal position. Distinct mapped conformers preserve multiplicity even if their factor values coincide. The decoder requires a complete metadata label map and accounts for absent selectors through explicit state membership. A missing conformation domain is recorded as unsupported rather than replaced by a feasible dummy witness.

Every conformation excluded by the metadata rule must have an independently read exact-zero source-factor witness when the shared selectors are fixed. The witness factor may involve that conformation variable and selectors only, so its zero applies regardless of every other conformation assignment. Without such a witness the decoder rejects the target. This proves excluded assignments contribute zero, and establishes equality with the raw conditioned state sum. It does not require assuming metadata labels are sufficient constraints. The proof records every removed index and its source factor/table offset.

The independent source-semantics gate must separately establish physical meaning, including whether any auxiliary encoding has a physical interpretation. Conditioning itself does not establish that interpretation. The package does not claim that an appended source state is a physical rotamer or that source weights recover an unrounded physical model.

## Arithmetic proof and uncertainty

The direct loop visits every assignment in the conditioned Cartesian product. It skips an assignment only after reading a source-represented exact-zero table entry; no positive threshold or support propagation is used. Every other assignment contributes the product of every owned factor, including scalars. Thus a completed pass with zero positive assignments proves combinatorial zero for the represented target. A pass that hits a cap supplies no zero proof.

Three declared targets are evaluated in the same pass:

* `source_binary64`: sum of products of exact `Decimal.from_float(float(source_lexeme))` values.
* `source_decimal_lexeme`: sum of products of exact decimal lexemes, as a text-rounding diagnostic.
* `stored_binary64_log`: sum of products of `exp(Decimal.from_float(math.log(float(source_lexeme))))` for every positive source value. This is the ideal real-valued target represented by the production's stored binary64 logarithms, evaluated with Decimal arithmetic.

Literal source zero is preserved for all three. A positive decimal that becomes binary64 zero during parsing is explicitly rejected as adapter underflow. Existing literal source zeros cannot be restored by guessing. At each declared precision the exp/product/sum/log operations round in Decimal; their target definitions above are ideal mathematical targets. Conversion deltas compare the 120-digit log results. Both passes must agree within `1e-10` log units, including exact support. This is numerical evidence, **not** directed rounding or an interval certificate. No interval/tail-bound claim is made.

For each semantics, `logKstar = logZ_complex - logZ_protein - logZ_ligand` is formed only with positive denominator sums. A zero complex numerator with positive denominators gives `-Infinity`; any zero denominator, including `0/0`, gives `undefined` with no numeric score. This is a source-encoding diagnostic until the independent gate validates compatible state normalization and physical interpretation.

## Resource and test policy

Defaults are one million Cartesian assignments per state/pass, 60 seconds for both precision passes of a state, 300 seconds for the full batch including archive load, and a 512 MiB observed-RSS policy. `getrusage` reports lifetime high-water RSS. The worker checks it every 256 assignments and between targets, rejecting after observation; it is not an enforced instantaneous memory ceiling. A parent watchdog may enforce a stricter outer bound. No retries or fallback oracle are performed. Parsing and conditioning are charged in batch time; state elapsed time is the enumeration/reference phase. JSON serialization is outside the internal batch timer and should be included by the parent's outer observation.

Frozen synthetic tests are in `tests/test_three_state_reference_round4.py`. They cover analytic three-state ratios, asymmetric scope indexing and selector sharing with different state-local variable IDs, explicit scalar restoration and rejected ambiguous/cross-state ownership, true tiny-positive factors, literal zero and adapter underflow, duplicate real-conformer multiplicity, distinct protonation labels, zero numerator, either zero denominator, `0/0`, and fixed failure ledgers under caps. Synthetic fixtures are separate from protein archives.

## Pre-freeze exposure record

Implementation grammar inspection read the selected raw archive's member names, complete `UAI.query`, complete `UAI.sum`, complete `uai_conversion_summary.txt`, the first 3,500 characters of `UAI`, and the first 7,000 characters of the design TOML. The inspection included summary conformer labels and UAI header/initial selector-constraint entries. It did not condition a protein target or perform weighted protein inference/reference enumeration. The parent explicitly authorized this read-only grammar inspection before preparation freeze and will disclose it in the ledger. No new experiment implementation or inference kernels were read. Formal all-case source audits and protein reference execution remain deferred until the preparation freeze notice.
