# Prefreeze scientific implementation review

Reviewed `core.py`, `scripts/campaign5_prepare.py`, `scripts/campaign5_worker.py`, the frozen grader protocol and `panel_plan.first.json`. This review executed one synthetic counterexample only; no protein score, partition sum or assay association was evaluated. Sealed `experiments/energy_recovery5/READY.json` inputs were not changed.

## Confirmed finding

The initial `relative_scores` implementation loses a small ensemble correction when an absolute partition log has a large common offset. Reproduction uses one position, zero unary energies, `constant=1e16`, `RT=1`: wild-type complex has one conformer, mutant complex has two, and all free states have one zero-energy conformer. The expected relative ensemble score is `ln(2)`; the initial code returns zero for both ensemble score and ensemble correction. `enumerate_state` correctly retains `log_effective_conformations=ln(2)`, but conversion of `log_z` to binary64 discards it before subtraction.

The finding was sent to the parent before activation. A suitable correction computes the relative ensemble correction directly from the signed effective-conformation logs across all six state/version slots, computes the GMEC change with a single signed sum, then adds the two. A regression must verify the synthetic result and preserve the ordinary same-target cases. This does not claim that the admitted protein panel exhibits the problem; no such outcomes were inspected.

## Correct behavior found

- Matrix access uses the correct source pair index and lower-position RC stride, including noncontiguous conditioned domains.
- Mixed-radix batches cover each allowed Cartesian assignment exactly once. The running minimum rescaling preserves the shifted log-sum across batches with increasing or decreasing minima.
- The same enumeration returns the same-domain minimum-energy comparator; it does not substitute continuous pairwise lower-bound matrices.
- Preparation conditions every other position to its prepared wild-type template. Each variant is normalized against its own exact configuration's wild type, avoiding direct comparison of raw scores from different flexible spaces.
- Mutation templates are matched uniquely by residue identity, retaining every conformer of that template, including added wild-type conformers. Ambiguous protonation mappings are excluded rather than selected by score.
- The plan records all 1,394 variant/configuration pairs, representing 41 label variants and 34 canonical configurations. Thirteen unique variants are eligible, with 78 WT/mutant/state slots and 3,677,224 planned assignments. The deterministic minimum-count configuration and prefix-cap rules match the protocol.
- Each state checks its Cartesian cap. No inference cache reuse is claimed; repeated unchanged free-state calculations count as actual scheduled work.

## Qualifications and nonblocking robustness points

- The state timer starts after writing its attempt journal. Total elapsed timing starts before activation checks and includes those writes; state and total timing scopes differ.
- RSS is a worker-lifetime high-water observation after each state, not instantaneous enforcement. A controlling process must retain incomplete ledgers if the worker exits early.
- `relative_scores` was outside the slot exception handler at review time. An exception during query scoring could leave all state rows but no final query/completion record; controller reconciliation must treat that as an incomplete attempt, not silently omit the variant.
- `np.longdouble(str(rt))` interprets a decimal string. Bind the exact source binary64 RT as a sufficiently precise decimal when claiming the same constant; a shortest round-trip decimal has a negligible but nonzero difference on platforms with wider long-double arithmetic.
- Stable log-sum arithmetic and reported underflow counts are numerical evidence, not outward-rounded certificates. Precision, discarded-tail allowance and independent reference error must be reported. The count only covers exponential underflow within batches, not loss in every possible subsequent floating-point operation.
- The source reconstruction of residue-conformer labels is supported by all serialized domain matches. Native Java energy getter identity is stronger than that label check; a native conformation-space label recreation was not part of this review.
- The study is explicitly a model-transfer mechanistic pilot. These implementation checks do not establish exact assay/model biological compatibility or calibration of absolute dissociation constants.

No code changes were made by this reviewer. The parent owns the correction, final checks and execution freeze.
