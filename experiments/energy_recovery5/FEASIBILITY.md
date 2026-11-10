# Finite-energy recovery: feasibility, not a measured experiment

This is a fallback sensitivity study for the released UAI encoding. Full-precision molecular inputs paired with experimental labels take priority. No new protein conditioning, partition sum, sequence score or timing measurement was performed here. The work remains an exploratory `poc`.

The static inspector and `metadata_inspection.json` record raw ZIP/member identities, lexical energy precision and label-based Cartesian counts. The existing independently sealed campaign004 audit supplies the prior energy/factor compatibility evidence; this note does not replace that audit.

## What is available

Use the already selected `2rfe_prepped_00012` case, all 21 F338 residue templates and the other source-first selectors. There are 885,801 Cartesian assignments across 63 state slots; the largest slot is ARG complex, with 146,880 assignments. This is small enough for bounded direct log-domain enumeration. These are metadata counts, not positive-support counts or new inference results. Reusing the frozen panel prevents choosing a sensitivity case after seeing its answer.

The archive includes finite `emat.complex.txt`, `emat.protein.txt` and `emat.ligand.txt` entries for every unary and pairwise energy factor: 261,326 printed entries for this pilot. Text has approximately two significant decimal digits, such as `9.2e+00`, rather than full precision. A half-unit interval at the last printed decimal place is therefore often much wider than the LEU–ARG score gap seen in campaign004. No ranking change has been computed.

The existing campaign004 grader checked the sign, temperature and factor mapping across all 14 archived cases. Its compatibility checks cover 4,661,625 energy entries; 696,477 correspond to source zero weights. Of these, 695,547 are certainly finite-energy binary64 underflows at the printed precision, while 930 straddle its underflow boundary. This is not evidence that original full-precision energies can be recovered.

## Exact mapping to preserve

1. Parse the raw `.uai`, `.uai.query`, `.uai.sum` and conversion summary. Keep source state order complex/protein/ligand from the declared sum groups, not an inferred filename convention.
2. `residue_id_to_conformationVariable_id[state]` maps ordered local energy positions to UAI conformation variables. Each singles row starts with that local position and supplies one entry for each of its conformers.
3. A pair row begins `left:conformer`; remaining entries run through all earlier positions and all their conformers in ascending local order. Reorder its two coordinates to match the actual UAI factor scope. Check every table size and require a unique energy entry for each unary/pairwise factor coordinate.
4. Selector/conformer compatibility factors remain exact 0/1. They have no energy-table replacement. Preserve all labeled conformers, including additional final indices; no dummy designation follows from index alone.
5. Use only `.emat.<state>.txt` members already checked against the UAI factors. The separately archived `.rigid.txt` files are distinct inputs and cannot be substituted without a new equivalence audit.
6. Keep the declared `T=298.15 K`, `R=0.0019891 kcal/(mol K)`, with no added offset or normalization. Existing source factors contain no omitted scalar or cross-state factor. This establishes a factor-level encoding convention, not absolute physical standard-state calibration.

The [paper's equation 3](https://proceedings.mlr.press/v216/pezeshki23a/pezeshki23a.pdf) defines the energy-factor product, and its [supplement section 2.0.3](https://ics.uci.edu/~dechter/publications/r274-supplemental.pdf) describes the released molecular design and sum-file format. A new independent decoder should verify the mapping rather than trust this implementation description.

## Proposed targets, requiring a prospective freeze

Keep three distinct targets and do not call any of them recovered original physical energies:

- **Released source:** retain literal zero weights and all positive source weights; this is the existing campaign004 numerical target.
- **Zero-restored hybrid:** preserve every positive source weight exactly and replace only finite-energy source zeros by positive Boltzmann factors whose energies lie in the printed-energy intervals. This isolates the effect of omitted underflow contributions. It is a new target, not exact equivalence to the released UAI.
- **Rounded-energy box:** replace all energy factors by Boltzmann factors from their printed intervals. A midpoint reconstruction is only one member of that box and should never substitute for a robustness bound.

For printed lexeme `e`, let `q` be its final decimal-place unit and assume round-to-nearest printing. The closed interval `[e-q/2,e+q/2]` includes either endpoint tie convention. This is a conditional uncertainty model: the original printer and generation path have not been reconstructed, and matching the UAI values to these intervals does not prove the rounding convention or energy provenance. Wider intervals may be necessary if source inspection disproves the assumption.

For each retained conformation assignment `x`, sum the lower and upper energies separately, retaining exact selector compatibility. Monotonicity gives

`exp(-sum(E_hi(x))/RT) <= weight(x) <= exp(-sum(E_lo(x))/RT)`.

Summing these positive bounds gives `Z_lo <= Z <= Z_hi`. Consequently

`logK_lo = logZ_C_lo - logZ_P_hi - logZ_L_hi`

and

`logK_hi = logZ_C_hi - logZ_P_lo - logZ_L_lo`.

The unchanged protein term cancels exactly when comparing two panel templates. Use that cancellation in pairwise bounds instead of needlessly widening them. A pair is robust only if its difference interval excludes zero. Overlapping intervals mean unresolved under this uncertainty model, not a demonstrated rank reversal. A reversal needs a concrete common energy assignment inside the same global box, evaluated independently.

For zero-restored hybrid bounds, sum omitted assignments separately from source-supported assignments. This avoids subtracting nearly equal totals when bounding the underflow correction; use `log1p(Z_omitted/Z_source)` or a directed equivalent. Every finite energy contributes mathematically positive weight, even if its numerical exponential would underflow. A zero-support simplifier cannot delete those entries from this target.

## Numerical and resource requirements

Do not use ordinary binary64 exponentiation to rebuild finite weights. Accumulate energy sums and partition sums with directed outward rounding, or provide a proven rounding-error enclosure. Decimal 90/120 agreement alone is a cross-check, not a certified interval. Large finite energies near `1e15` require adequate exponent range or an explicit bounded tail; silently turning these exponentials back into exact zero defeats the purpose.

A practical bounded pilot could allow one direct enumeration per state/endpoint at 90 and 120 digits, cap every state at one million assignments and 60 seconds, total wall at 300 seconds and memory at 512 MiB. Those are proposed limits, not observed costs. Enumerating at most 146,880 assignments per state makes this plausible; failure must stay recorded. No performance winner or larger-problem coverage claim is justified by this sensitivity study.

The independent grader should freeze the target definitions, intervals, exact panel, tolerances, stopping rules and all code/input hashes before evaluation. Useful outcomes are either a bound proving the released-source ordering survives finite-energy underflow restoration, a demonstrated permitted reversal, or an honest unresolved result with the interval widths reported. None establishes experimental affinity accuracy, native BBK* superiority, an ETH implementation or an improved biological design.

## Status

Only static inspection is complete. No recovery model or scientific experiment has been executed. New prepared full-precision molecular inputs found by the parent investigation take priority over this fallback.
