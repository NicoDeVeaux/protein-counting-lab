# External graders and benchmarks

Checked against primary sources on 2026-11-10. This is a source review and a
proposed next gate, not an executed external benchmark. No solver was installed,
dataset downloaded, or external optimization run launched for this review.

Screen MC2026 Track 4 first, then MC2025 Track 4, for nonnegative, unprojected
weighted-counting instances. Use deterministic exact-rational Ganak as an external
numerical gate; MC2022 remains an archived fallback with verified licensing.
For biological usefulness, use held-out,
assay-matched SKEMPI systems; ProteinGym is the stronger ready-made scoring option
if a suitable binding assay is available. These are separate objectives.

The [campaign-006 protocol](../grader/campaign-006/PROTOCOL.md) is an internal
correctness and performance test on eight synthetic cases. It is useful for
development but too small and public to serve as the sole objective for a closed
optimization loop. A separate agent is still an internal grader; an external
benchmark needs independently chosen instances, references and evaluation rules.

No reviewed package is a turnkey external grader for this repository's exact
three-state affinity-ranking problem. The strongest options cover different
parts of that problem:

| External resource | What it supplies | What remains |
|---|---|---|
| [Model Counting Competition 2026](https://mccompetition.org/2026/mc_description.html), [2025](https://mccompetition.org/2025/mc_description.html), and archived [2022](https://mccompetition.org/2022/mc_description.html), plus [Ganak](https://github.com/meelgroup/ganak) | Public counting instances and an established independent counter with exact rational arithmetic and a nonprobabilistic mode. | Classify weights/projection before selecting a compatible cohort; validate the parser/adapter and build the interval/ranking evaluator. A counter is an oracle/baseline, not itself a ranking grader. |
| [UAI 2022 PR benchmarks](https://uaicompetition.github.io/uci-2022/results/benchmarks/) | External finite factor graphs and separate tuning/final suites. PR is exactly a sum of products of factors. | Support actual domains and decimal factors. The [official score](https://uaicompetition.github.io/uci-2022/results/evaluation-criteria/) evaluates point-estimate log error, not sound enclosures or three-state rankings; exact references must be established separately. |
| [count-catcher](https://github.com/leansolving/count-catcher) | An external Lean checker producing count theorems from D4/CPOG certificates; an archived, licensed subset of MC2022 instances. | Current counting is unweighted. A protein-factor encoding and weighted extension are separate work. The supplied reproduction stack targets x86-64 Linux, with substantial dependencies. |
| [OSPREY / BBK*](https://pmc.ncbi.nlm.nih.gov/articles/PMC6074059/) | An established domain algorithm using affinity bounds to prune sequence spaces and order designs. | Run the same conformational spaces and energy model, including preparation costs. An OSPREY result is a model-based computational comparison, not an assay truth label. |
| [SKEMPI 2.0](https://life.bsc.es/pid/skempi2/default/index) | Measured mutation effects on binding, with structures and affinity/thermodynamic records. | A dataset rather than a packaged evaluator. Prepare the measured system and define assay-matched splits, uncertainty and ranking metrics before scoring. |
| [ProteinGym](https://github.com/OATML-Markslab/ProteinGym) | Existing external scoring code and experimental variant-effect assays, including rank metrics. | Select genuinely relevant binding assays; DMS fitness is not automatically equilibrium affinity. Molecular preparation and the prediction adapter remain necessary. |

Mutable repository links describe the versions inspected on the date above.
Before an actual campaign, freeze full source revisions, dependency locks,
executable/checker digests and dataset hashes in its prospective manifest.
This source review is not a reproducible executable release seal.

## First practical gate: independent weighted-counting evaluation

### Recent public downloads are available

On 2026-11-10 the organizers' public shares returned directory listings without
a user login. HEAD requests for both Track 4 archives returned HTTP 200 with
`application/x-tar`. Only metadata was fetched; the archives were not downloaded.

| Year | Public share | Archives listed |
|---|---|---|
| 2026 | [MCC2026_Public](https://nextcloud.liu.se/s/STzdpXNgZDZaPRo) | Tracks 1, 2B, 3, 4 and 5B; Track 4 is 74,352,640 bytes. |
| 2025 | [MC2025_Public](https://nextcloud.liu.se/s/2zbn4APWnjLxRLo) | Tracks 1, 3, 4 and 5B; Track 4 is 45,424,640 bytes. |

The original recommendation to start with 2022 was unnecessarily conservative.
Availability is distinct from compatibility with our current arithmetic. The
[2026 results slides, slide 17](https://mccompetition.org/assets/files/2026/MC2026_awards.pdf)
explicitly say Track 4 contained MC, PMC and WMC instances, with no PWMC instances
received. Its title alone therefore must not exclude the entire track. Screen
the actual metadata for ordinary nonnegative WMC. The
[2025 page](https://mccompetition.org/2025/mc_description.html) says weighted
counting was subsumed by Track 4, so screen that collection next.

The separate 2026 link labelled `Private Instances` redirected this anonymous
check to Microsoft sign-in. That does not restrict the accessible public share.
The contest's public/private split describes its evaluation process; a new search
still needs a protected family-level holdout. Recent archive contents, exact
reference counts and redistribution terms have not yet been audited here.

Freeze eligibility by semantics, source family and static size before measuring
our method; retain hard cases as explicit timeouts. The
[2026 rules](https://mccompetition.org/2026/mc_description.html) allow 3,600 seconds
and 32 GB, while Track 1F uses the same unweighted instances with a 120-second
limit. That is a useful bounded solver gate, but does not test weighted affinity.
The official webpage strikes out precision category B although the results slides
still show it; use a clearly frozen exact category A for this proposed evaluator.
These are external counting problems, not biological affinity measurements.

### Archived fallback and independent reference

The organizers' [archived competition set](https://zenodo.org/records/10012860)
contains all four tracks, with CC BY 4.0 recorded in the
[repository metadata](https://zenodo.org/api/records/10012860). The
[weighted-track archive](https://zenodo.org/api/records/10012860/files/mc2022-track2-wmc_competition.tar/content)
is 21,473,280 bytes. The archive includes the original public even-numbered
instances and the odd-numbered final-evaluation instances, which are now public
too. Neither split is a secret holdout today. Preserve original attribution and
instance hashes; freeze a new family-level split for a new search.

For an independent exact rational reference, the current Ganak documentation
supports this combination of CLI options:

```sh
ganak --mode 1 --prob 0 instance.cnf
```

This command has not been run here. `--mode 1` selects rational arithmetic;
`--prob 0` disables probabilistic caching. Specify both polarities' weights.
The Python `WeightedCounter` wrapper instead uses MPFR and returns a floating
approximation; it should not silently replace this exact oracle. Native Apple
Silicon availability/build cost for the CLI remains untested. Ganak's repository
identifies its software license as MIT. [Ganak usage and weight modes](https://github.com/meelgroup/ganak/blob/master/README.md).

The adapter can represent each CNF clause as a zero/one factor and each variable's
two literal weights as a unary factor. Parse finite decimal weights as exact
rationals, never through binary64. Positive denominator scaling can turn these
unary factors into integer tables, but the total scale must be retained when
recovering Z. Independently test that translation on tiny enumerated formulas,
including unused variables, tautological clauses, repeated literals, zeros and
unsatisfiable formulas. Account for auxiliary bits, table sizes, preprocessing,
coefficient growth and external oracle cost. This is a proposed adapter, not a
verified reduction already present in campaign 006.

MC2026's signed-weight Track 2B is outside the current natural-number/nonnegative
proof; complex-weight Track 5B also needs different arithmetic and an appropriate
objective. Projected counting changes the target and cannot be supported by
discarding the projection directive. These are track-specific restrictions,
not a reason to reject the recent public collections as a whole.
[MC2026 tracks and format](https://mccompetition.org/2026/mc_description.html).

The fixed evaluator should validate every claimed interval against its independent
reference and every claimed strict winner by exact cross multiplication. A false
certificate fails the candidate. An unresolved answer or timeout gets no solved
credit, even if returned quickly. Report solved counts first, then runtime against
the established counter/native VE on equally solved targets; give unresolved cases
the fixed timeout penalty if a scalar optimization objective is required. Freeze
that objective prospectively. Artificial triples of counting instances may test
ratio arithmetic, but must be labelled synthetic ranking tasks.

There is also an external execution harness,
[tlyphed/copperbench](https://github.com/tlyphed/copperbench), used for reproducible
solver experiments. It generates Slurm jobs and requires a patched `runsolver`;
it is not a count-certificate checker or a ready macOS evaluator. This is distinct
from an unrelated hardware-design benchmark with the same name. The competition
report's cited archived result/setup records could not be retrieved in this check,
so their expected-count tables have not been accepted as an oracle here.

For optimization, expose development cases and keep a distinct family-level final
holdout outside candidate inputs. Freeze the grader, references, parser and resource
limits outside the candidate's editable repository. Limit feedback from final
evaluation; repeated querying turns a holdout into training data. Do not optimize
only against our slower fixed-precision prefix baseline or reward early abstention.

## Stronger formal gate: inspect the actual external trust boundary

The [October 26, 2026 count-catcher paper](https://arxiv.org/html/2610.36196v1)
checks formula/circuit equivalence and the circuit's count, then returns a Lean
theorem. Weighted counting is explicitly future work. Its native evaluation trusts
Lean's compiler/runtime and introduces native-evaluation axioms; this differs from
the current campaign's kernel-checked checker-soundness theorem. An encoding lemma
is still needed to connect CNF to the intended objects. The paper also reports a
wrong printed count in CPOG's C checker and two unproved lemmas in its archived
Lean dependencies; an external label alone does not establish correctness.

The [artifact instructions](https://github.com/leansolving/count-catcher#installation)
require x86-64 Linux because of the supplied D4/PaToH dependency and caution that
Apple Silicon emulation is too slow for full reproduction. Short stages still use
several GiB. The repository includes 44 MC2022 formulas with certificates below
100 MB and identifies their license as CC BY 4.0. The code is Apache-2.0 with
separate upstream notices. This is a useful later certificate gate, not a cheap
drop-in replacement on this laptop.

The older [CPOG release](https://github.com/rebryant/cpog/releases/tag/v1.2.0)
does ship a Lean checker, but its [actual CLI](https://github.com/rebryant/cpog/blob/v1.2.0/VerifiedChecker/Main.lean)
labels `--count` as **unweighted**. Its exact weighted C implementation must not
be described as a released Lean-verified weighted executable. Keep the
[reported normalization bug](https://github.com/rebryant/cpog/issues/3) as a
regression if testing that version. The release pins Lean 4.4.0-rc1 and a Lake
dependency manifest, so it needs a separate build from campaign 006.

## Biological gate: held-out, assay-matched SKEMPI systems

For claims about binding, prefer a small predeclared set of SKEMPI complexes with
adequate same-assay WT/mutant measurements and a tractable prepared molecular
model. SKEMPI's official [download page](https://life.bsc.es/pid/skempi2/database/index)
supplies CSV records and cleaned structures; its [terms](https://life.bsc.es/pid/skempi2/info/terms)
are CC BY 4.0. It supplies observations, not an automatic scorer. Freeze chain and
mutation identities, constructs, assay conditions, temperature, replicate/censoring
rules and molecular preparation. Keep test complexes or families out of tuning.

Compare ensemble ranking with the same-model minimum-energy baseline, and compare
runtime with native K*/BBK* where the exact same prepared target is supported.
Use within-assay ranking with uncertainty, and signed mutation-effect accuracy;
do not pool incompatible assays or rank all records across unrelated complexes.
This is a proposed biological protocol, not evidence that a faster counter improves
affinity prediction. OSPREY's GPL-v2 software and any upstream model artifacts retain
their own licenses. [OSPREY source and license](https://github.com/donaldlab/OSPREY3).

If a ready-made biological scorer is the priority, ProteinGym already provides
Spearman, NDCG and top-k evaluation code, with aggregation by protein and selection
category. It is MIT-licensed at repository level. Select binding assays using its
reference metadata, preserve each original dataset's attribution, and interpret
the assay phenotype literally. Scoring saved predictions is cheap; producing
matched ensemble energies is the expensive missing part. Its full data/model-score
downloads are large and were not fetched here. [Official scoring documentation](https://github.com/OATML-Markslab/ProteinGym#results).

An additional recent package, [EpiGym](https://github.com/tubic/EpiGym), ships a
portable evaluator and measured multi-mutation/epistasis datasets, including a
SKEMPI binding auxiliary dataset. It addresses a different target from top-1
affinity ranking. Its task definitions, split validity and per-source licenses
would need a separate audit before adoption; it is a candidate, not the selected
external gate.
