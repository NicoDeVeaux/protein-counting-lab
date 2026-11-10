# ETH, finite-scale checks and remaining research lanes

Follow-up on the same date: [campaign 006](../CAMPAIGN-006.md) has now implemented
the certified adaptive-stopping gate described below. It proves the integer rank
checker and tests actual enclosing bounds on a frozen synthetic panel. Three
nontrivial cases save refinement work and time against the fixed-precision policy;
native exact VE remains faster in every nontrivial case. The remaining lane is a
faster producer plus external held-out grading, rather than enlarging this prefix
enumerator. Physical Boltzmann-weight certification and assay validation remain
open. [BENCHMARK.md](../BENCHMARK.md) defines the measured question and scoring.

Checked 2026-11-10. This note explains the archive's scope and adds small deterministic arithmetic checks. It does not rerun protein experiments, rebuild Lean or independently certify the theorem. The bulk data remains in the release rather than on the local working machine.

## What the released result supplies

The [October 25 manuscript](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/main_full_version.tex) gives an exact fixed-width CNF counting algorithm with subexponential bit complexity and polynomial space. Its stated general bound is `(n+m)^{O_k(1)} 2^{O_k(n log log n / sqrt(log n))}`; fixed clause density improves the exponent to `O(n/sqrt(log n))`. This does not establish a polynomial-time algorithm or a practical finite-size advantage.

The [formalization scope](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/lean/docs/378.md) instead specifies `(L+1)^{O_k(1)} 2^{O_k(n (log log n)^2 / sqrt(log n))}` for canonical encoded input length L. That is still subexponential. The distinction matters when referring to what Lean checked; the sharper manuscript bound and a practical implementation are separate claims.

The manuscript's `prop:general-count` is already a product-sum routine over a commutative rational algebra: `Z = sum_x product_f Phi_f(x_scope)`. This resembles a discrete partition function. Consequently, neither "only SAT decision" nor "weighted counting is categorically excluded" is an appropriate reason for this project's outcome. The actual adapter, valid layout, degree/precision bounds, coefficient arithmetic and finite costs were not established here. General polynomial reductions can increase the variable count enough to lose the desired subexponential bound in the original protein parameter.

[OpenAI's announcement](https://openai.com/index/building-scientific-understanding-with-academic-communities/) explicitly distinguishes the mathematical result from the further work needed for practical algorithms. The [organizers' community site](https://ethdiscussion.blog/) provides independent examination and human expositions; participation or a Lean build is not this project's verification of every paper claim. This bounded source review identified no validated protein adapter in the released artifacts; it is not a claim that no useful implementation exists elsewhere.

## Checks that were actually run

Run `python3 -B scripts/check_open_lanes.py` from the repository root. It uses only the standard library and the existing schedule helper. The existing three schedule tests can also be run independently of the bulk dataset. No timing comparison or new biological predictions are involved.

### The previously audited schedule

For the Section 4 incidence-parameter lemma, `lambda=ceil(log2(n))`, `nu=ceil(log2(lambda))`, `r=floor(sqrt(lambda)/nu^2)`, `Q=floor(lambda/(128nu))`, and `R=(beta+3)ceil(sqrt(lambda))`.

The first `r>=2` occurs at lambda=521284. For beta=1, the four checked necessary conditions first jointly pass at lambda=10909384704, or minimum integer `n=2^10909384703+1`. The [original independent report](../grader/REPORT.md) verifies the search. These are necessary preconditions only: other construction hypotheses and total costs still have to hold. The source explicitly falls back to exhaustive summation when its checks fail.

This is a negative feasibility result for a literal schedule, not a performance trial of the new counter, a theorem check, a proved crossover, or a lower bound on all adaptations.

A further elementary bound applies if a retuning retains all of `r>=2`, `R>=32`, `6R<=Q`, `D=r^(2Q)` and `2(b+w)D^2<=M<=b*n` with b,w>=1. Then Q>=192 and D^2>=2^768, hence `n>=2(1+w/b)D^2>2^769`. Keeping those sufficient conditions while changing constants alone still gives an astronomical prerequisite. The generic layout lemma does not require every one of those extra sufficient conditions: dropping them, supplying another layout or using another construction remains outside this bound.

### The appendix route received a separate, limited check

The [tensor-contraction appendix](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex) uses a different construction and is not ruled out by the old Section 4 audit. Its literal root parameter is `u_0=floor(ceil(log2(s))/131072)`, with s the tensor-network size parameter. At s=10^3, 10^6, 10^12 and even 10^100, u_0=0. The first positive u_0 is at `s=2^131071+1`. The text imposes stronger sufficiently-large-size inequalities as well and handles a finite range by direct summation.

This new check only evaluates that published parameter expression. It is not the full tensor algorithm, a crossover, or a barrier to a different finite-size tensor design. The general tensor-contraction theorem uses modular/truncated-polynomial arithmetic, so a floating-weight protein implementation still needs a justified bridge and precision budget.

### Conformational size is not Boolean input size

A hypothetical 50-position, 10-conformer model has 10^50 legal conformations. Binary choice encoding starts with `50*ceil(log2(10))=200` bits and must exclude unused codes; one-hot choice encoding starts with 500 bits and needs exactly-one constraints. Neither count includes the full factor/weight representation or reduction auxiliaries. Counting conformations as the theorem's n would therefore give a misleading scaling argument.

### A practical ranking precision target remains plausible

A WT-normalized three-state effect contains six signed log partitions. If every constituent has a valid absolute error bound eta, the effect error is at most 6eta and a difference of two effects at most 12eta. Resolving an illustrative gap of 0.03 log units therefore needs eta strictly below 0.0025 per state, corresponding to about a 0.25% upper multiplicative partition error. This is conservative: shared terms can cancel exactly. No statistical independence is needed for this deterministic triangle bound.

Campaign 005's reported smaller reversed-order gap is about 0.0371, while actual numerical errors were around 1e-14. That supports investigating ranking-aware precision as an engineering question. It does not show that a loose-tolerance method is faster, that the current floating endpoints are rigorous enclosures, or that computational ranking accuracy implies biological accuracy.

## What would make each open lane worth pursuing

1. **Extract a useful algebraic primitive.** Start with tiny rational-weight factor graphs and an independently verified layout. Account for every measurement tuple, finite-difference term, polynomial coefficient and bit operation. Advance only if explicit finite costs compete with VE/enumeration on the same target. A changed layout needs its own correctness argument; an informal sparsity analogy is insufficient.
2. **Audit the weighted representation.** Measure encoded variables, auxiliary assignments, width, density, coefficient bit lengths and precision after conversion. Compare a direct product-sum adapter with an encoding to a counting solver. Stop if the reduction dominates or loses the required rank-error guarantee. The protein objective additionally involves three states and sequence-dependent normalization.
3. **Use structure and verified bounds.** Keep exact shared-state caching and exploit genuine support sparsity or small elimination width. Campaign 003 showed a benefit on one source model, not a general win; campaign 004 added no coverage and pruning slowed VE. Campaign 005's weights are mathematically positive, so dropping tiny terms requires a mass bound rather than declaring a hard zero. Compare a new controller with native methods and charge preparation/conversion costs.
4. **Validate the physical model.** Prepare the same sequence backgrounds, nucleotide/metal state, conformational model and assay conditions as the measurements. Then use held-out comparisons against same-model GMEC. Additional counting precision cannot correct a wrong molecular target. Larger flexible ensembles become scientifically useful only with this validation chain.
5. **Buy compute after profiling a validated finite routine.** Larger memory, batching or parallelism may help conventional hard cases, but this project supplies no evidence that a hardware upgrade activates the ETH proof's asymptotic advantage. Require an explicit cost forecast and a useful accuracy/coverage endpoint first.

These are research gates, not promises of an eventual speedup. The clearest practical next work is a ranking-aware same-target comparison or assay-matched preparation; extracting finite-size benefits from the ETH proof remains more speculative.

Source links are pinned to the inspected OpenAI repository revision. No complete third-party paper, bulk source dataset or formal proof is copied into this update.

This is written by an AI agent (model name unavailable) on Nico DeVeaux's behalf.
