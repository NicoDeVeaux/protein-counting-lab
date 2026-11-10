# Archived KRas–c-Raf rigid-energy inputs

**The archived rigid matrices are usable as full-precision binary64 discrete inputs.** A restricted Python decoder reproduces every native Java getter value, and source-defined residue-conformer labels reproduce every retrospective matrix domain. No partition sums, sequence scores, affinity predictions or scientific timing measurements were computed in this investigation.

This replaces the rounded-UAI recovery proposal as the more useful next experiment. It remains a new discrete target. It is not a reproduction of the authors' continuous-minimized BBK* scores.

## Inputs and numerical identity

Inputs are the parent-retrieved Harvard Dataverse archives `data/campaign-005/kras2020/rasDesigns.zip` and `OSPREY.zip`. Their full hashes, member hashes, configurations and source-derived labels appear in `kras_metadata.json`. Retrieval URLs and dataset provenance remain in the parent's `data/campaign-005/kras2020/` records.

`java_matrix.decode(bytes)` reads the Java serialization stream as data; it executes no Java serialization hooks. It supports only the archived `EnergyMatrix`, `TupleMatrixDouble`, `AbstractTupleMatrix`, boxed Double/Number and primitive int/double arrays with their expected class identities. Unknown classes, custom serialization, non-null higher terms, non-null tuple trees, embedded reference-energy objects, invalid offsets, nonfinite energy entries and trailing/truncated data are rejected.

The independent native cross-check uses the archived compiled `OSPREY3-master-3.1-beta1.jar` with an allowlisted Java object filter, a 256 MiB heap and no additional dependency downloads. Its getters provide a canonical binary64 digest for the constant, all singles and all pairs in source-defined order. The Python getters reproduce those digests for **126 rigid matrices and 484,084 energy entries**. All constants are zero, higher terms are absent and pruning intervals are infinite. The stored `native_matrix_check.tsv` binds every native matrix result to its archive member. Three parser tests pass, including the complete native identity check and malformed-stream rejection.

The energy convention is

`E(rc) = constTerm + sum_i oneBody[i,rc_i] + sum_(i>j) pairwise[i,rc_i,j,rc_j]`.

The exact source indexes are `oneBodyOffsets[i]+rc_i` and `pairwiseOffsets[i*(i-1)/2+j]+numConfAtPos[j]*rc_i+rc_j`. Native getter identity checks both coordinate orderings, not just the flattened table lengths.

The archived `BoltzmannCalculator.constRT` delegates to `PoissonBoltzmannEnergy.constRT`, whose Java expression is `1.9891/1000.0 * 298.15`. Its binary64 value has hexadecimal representation `0x1.2fa4456f1ff36p-1`; preserve that value when defining a same-source Boltzmann target.

## Sequence and conformer mapping

The archive has 41 retrospective matrix directories: 34 core configurations and seven `.null` variants. All 123 retrospective rigid state matrices match the label reconstruction. An additional prospective `T182` matrix triple decodes, but the expected corresponding `T182.cfs` is absent; that mapping failure is retained and must not be silently folded into retrospective coverage.

The safe configuration parser accepts only literal top-level assignments to `mol`, `strand_defs` and `strand_flex`; it does not execute the author configuration files. The original script constructs protein from `strand0`, ligand from `strand1`, and complex from `[protein,ligand]`.

Source-defined ordering is important:

1. Positions follow PDB residue order within each strand, then protein before ligand in the complex. Configuration dictionary ordering is not the position order.
2. Library templates are an insertion-preserving set of the actual wild-type template followed by the explicitly allowed templates. Duplicates are removed without sorting.
3. Each library template contributes its archived Lovell rotamers in order; templates with zero tabulated rotamers contribute one RC. Library PRO contributes two pucker RCs.
4. Added wild-type coordinate conformers come after the library RCs. The prepared retrospective PDB has blank chain identifiers and no alternate conformers, so exactly one such conformer is reconstructed per position.

The inspector rejects explicit model/chain/alternate ambiguity. Every reconstructed state domain equals its serialized matrix domain. `positions[].conformer_labels` identifies the AA template at every matrix index, and `template_counts` gives each per-template domain count. To determine a fixed-sequence Cartesian count, multiply those counts across its positions; this is metadata and not inference. The same AA may have both library and added WT conformers; they are distinct modeled states and neither is discarded as a duplicate.

The mapping is supported by archived source and exact domain-count checks. A native Java `SimpleConfSpace` label reconstruction has not been run. The final independent grader should assess this remaining mapping qualification separately from the stronger bitwise energy-array identity check.

## Energy and interpretation limits

The author's script constructs a minimizing energy calculator and reference energies, then copies its conformation-energy calculator to a non-minimizing calculator for rigid matrix generation. `EnergyPartition.Traditional.makeSingle` incorporates `eref.getOffset` into the calculated interactions; those adjustments are already in the matrix numbers. A null serialized `eRefMat` therefore does not mean the energy values are unreferenced. Do not add another reference correction, normalization or offset.

The minimized matrices store fragment lower-bound information for continuous conformation search. Adding their entries does not recreate the full minimized conformation energy or the author's final BBK* affinity prediction. Only the archived **rigid** matrix is proposed as a direct pairwise discrete model here. The prepared molecular inputs and full precision fix the earlier source-input gap; they do not establish a calibrated dissociation constant, identical continuous ensembles or experimental predictive accuracy.

Commands used for the static check are `python3 -m experiments.energy_recovery5.inspect_kras`, `javac` against the archived jar, `java -Xmx256m` running `NativeMatrixCheck`, and `python3 -m unittest experiments.energy_recovery5.test_java_matrix -v`. No native force-field calculation, molecular minimization, BBK* search, partition sum or assay-label comparison was executed here. Parent scoring must follow the campaign005 grader freeze and activation rules.
