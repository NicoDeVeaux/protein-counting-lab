# Campaign 003 amendment 001: static preparation before final measurement freeze

Date: 2026-11-06 UTC. This additive amendment changes the freeze sequence in `PROTOCOL.md`; it does not edit or replace any frozen file. The unchanged grader freeze and this amendment's precise time and hashes are bound in `AMENDMENT-001.json`.

The parent reported, before requesting this clarification, that no campaign003 protein preparation or inference had run; only synthetic implementation/unit work had occurred. The grader has not inspected campaign003 code, controls, derived data, preprocessing or results. This attestation is reported by the parent, not independently established by the grader. The campaign remains an adaptive follow-up to campaign002.

## Permitted sequence

Static preparation by an already declared algorithm is admissible **after an immutable preparation manifest and before the final execution manifest**. This resolves the need to calculate derived hashes and checkable support/algebra evidence before binding them into the final manifest. It supersedes only the requirement that the complete execution manifest precede target preprocessing. Every other protocol gate remains in force.

1. Freeze the preparation manifest described below before any protein preparation. Record its SHA256 and creation time; preserve it unchanged.
2. Run only the frozen static conversion/support-propagation/algebra/structural preparation. Record every attempted input, command, exit status, start/end time, observed resource behavior, resulting artifact/hash and proof check in an append-only preparation ledger. Retain failed and partial artifacts. Include all six targets and both arms; no case may disappear or be excluded because preparation is ineffective, large or fails.
3. Freeze the final execution manifest before timed protein inference. It binds the preparation manifest/ledger, all resulting derived artifacts, mappings, proofs, counts and static predictions, plus the unchanged prospective trial plan and contracts. Then execute cold pipeline measurements from the original-model boundary as required by the protocol.

Static preparation may calculate domain maps, hard-zero fixed points, exact algebra certificates, before/after structure, state products, order-dependent table estimates and artifact hashes. Such observations are disclosed preparation evidence, not measured speedup evidence. They may trigger only an already frozen static rejection/skip rule. They may not select a preferred subset, alter an algorithm/resource policy/reference/schedule, or determine which arm receives measurement. No protein partition-function inference or outcome-selected pilot is authorized by this clarification. Synthetic correctness work remains separately labeled and logged.

## Required preparation-manifest fields

The preparation manifest may use a compact JSON shape rather than the final inherited manifest schema. These fields must be concrete, hashed and sufficient to execute the plan without making outcome-dependent choices:

| Field | Required content |
|---|---|
| Identity | Campaign `003`, phase `preparation`, UTC freeze time, grader `FREEZE.json` and amendment identities. |
| Inputs/cohort | All six exact original model IDs, file paths and SHA256 values from the grader freeze; raw-source/provenance links; both baseline-simplified and hardzero-pruned+simplified arms. No wildcard or optional protein subset. |
| Implementation | Code/config hashes for parsing, propagation, simplification, order/structure estimation, evidence generation, workers and compared methods; exact deterministic algorithms, settings, versions/dependencies, thread policy and environment. Decide optional established comparator inclusion now. |
| Controls | Frozen identities, mechanisms, generators/explicit factors, seeds and independent reference procedure; separately identify premeasurement correctness and measured controls. Preserve prior synthetic/unit exposure in the ledger. |
| Numerical/references | The unchanged numerical and exact-zero contract; fixed reference identities/hashes/provenance, including prior independent 1FYN evidence and explicit missing-reference status for other proteins. No inferred new oracle. |
| Resources | Finite static preparation row/total time and RSS policies; finite measured row/total budgets; table/allocation and enumeration-state policies; enforcement, watchdog sampling and descendant accounting; cold endpoint and phase-clock definitions. Static preparation and measurement budgets must be distinguished. |
| Complete plan | Every measured trial ID with model, arm, method, profile, accuracy contract, repeat, paired block and exact order; seed, repetitions, warmup/cache policy and concurrency. The list may be a separately hashed enumerated file. All planned identities survive skips and failures. |
| Adaptation/ledger | Pre-freeze exposure and prior work, permitted preparation commands, append-only ledger location/schema, amendment rule, and an attestation that no campaign003 protein preparation/inference preceded this preparation freeze. |

A configuration or proof-artifact field may be absent only if it does not exist yet and is explicitly listed as a final binding output; it cannot conceal a later methodological choice. Source inputs, code/configuration, inclusion, reference/accuracy rules, resource policies and complete measured identities/order must already be fixed.

## Final binding and changes

The final execution manifest may add **only** observed preparation statuses/ledger entries and static outputs: derived artifact paths/hashes, domain maps, support/algebra evidence, structure/counts/order estimates and their associated validation. It must retain the original plan, references, budgets and every row identity. Independently verify that final and preparation manifests agree on all prospective fields. A static skip status follows the predeclared rule; it is not permission to remove the row.

If preparation reveals a bug or unmet requirement, preserve the attempt and obtain a numbered, exposed amendment before changing the code/plan. No silent replacement of the preparation manifest or artifact is allowed. Any additional preparation or diagnostics and their selection effects remain visible. Amendments may support a useful exploratory result without being mislabeled as untouched confirmatory evidence.

Cold measured rows must redo their arm's original-model load, propagation where applicable, simplification/order selection, solver ingestion, inference and valid output within the common row watchdog. Static prepared artifacts cannot make either arm's preprocessing free. Report static preparation separately; include measured preprocessing in end-to-end time and whole-pipeline memory. Timing drift, exact same-target proof, original-domain mappings, complete failure accounting, fixed accuracy and restrained interpretation retain their original gates.
