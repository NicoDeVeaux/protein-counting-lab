# Project conclusion

Closed on 2026-11-11. **Stop active work on this project as a route to faster,
biologically useful ensemble calculations.** The completed studies do not justify
another implementation campaign, more proof polishing or a hardware upgrade.
Keep the repository as a reproducible research archive and the verified bound
checker as a reusable prototype.

This is a resource-allocation decision. We have not proved that every related
algorithm fails, and we did not implement or benchmark the ETH-derived algorithm.

## Evidence behind the decision

| Question | Completed evidence | Conclusion |
|---|---|---|
| Did the ETH result supply a practical method here? | Literal proof-schedule checks have astronomical size prerequisites; no finite competitive adapter was established. | No practical opportunity demonstrated. These checks do not rule out other constructions. |
| Did conventional inference improve broadly? | Hard-zero propagation helped one source model; later comparisons did not establish a general pruning advantage. | Preserve the local finding, without a general acceleration claim. |
| Did adaptive ranking beat established inference? | Campaign 006 saved refinements on three nontrivial synthetic cases, but direct exact VE was faster on every nontrivial case. | A scheduling improvement over our fixed-precision policy did not become a solver advantage. |
| Did the verified approach transfer externally? | Campaign 008 resolved 0/6 external CNF probability-ordering queries at 4,096 expansions; native Ganak resolved 2/6. All certificates checked. | The prespecified continuation gate failed. Correct evidence was too weak to answer the queries. |
| Did ensemble counting improve biological prediction? | Campaign 005 passed independent numerical references for 78 state calculations across 13 variants, with two ensemble/GMEC pair-order reversals. Molecular model and assay were mismatched. | Numerical correctness and changed rankings did not establish a biological winner. |

Sources: [ETH feasibility checks](notes/ETH_AND_OPEN_LANES.md), independent reports
for [campaign 003](grader/campaign-003/REPORT.md),
[campaign 004](grader/campaign-004/REPORT.md),
[campaign 005](grader/campaign-005/REPORT.md),
[campaign 006](grader/campaign-006/REPORT.md) and
[campaign 008](grader/campaign-008/REPORT.md).

Campaign 008 was expansion-limited, not wall-limited. It does not reject the
method family at equal used time: larger caps, stronger bounds and other search
policies remain untested. We are choosing to stop without running those
sensitivities. Unknown exact answers on four external queries remain unknown;
neither timeouts nor quick unresolved returns count as successful solutions.

## What is worth retaining

[Campaign 007](CAMPAIGN-007.md) provides the clearest reusable component: Lean
recomputes partition enclosures from nonnegative-integer factor trees and a binary
split certificate, and proves the bound construction sound. A corollary composes
checked bounds into a strict three-state comparison. Independent tests exercise
translation, actual producer exports, malformed certificates and proof mutants.
Campaign 008 also measured native checking with its costs included.

This component could serve a future, better producer. It has no demonstrated
speedup, novelty or biological-accuracy claim. The original table translation,
model binding, JSON parser, compiler and runtime remain explicit trust boundaries;
the complete application is not kernel-proved. The synthetic benchmark and grader
are also useful examples of separating correctness from performance.

## Final state and reproduction

- No further campaign, formal extension, molecular preparation or hardware
  purchase is scheduled. A generic model-counting project in Frontier would be a
  separate effort; there is no Frontier integration in this repository.
- Frozen protocols, source seals, raw measured records, negative findings and
  independent reports are retained. Closeout changes only documentation and its
  publication inventory; it does not rerun or replace measurements.
- Earlier bulk data remains in the linked [data release](https://github.com/NicoDeVeaux/protein-counting-lab/releases/tag/v2026.11.10).
  It need not be restored to read the findings or run the small synthetic checks.
- Campaign-008 source CNFs, full converted certificates and native binaries are
  excluded from the public mirror. Recorded source URLs, hashes, build metadata
  and the [reproduction guide](experiments/external_count8/README.md) describe the
  acquisition and rebuild requirements. Public records alone cannot replay those
  original local certificate payloads; redistribution terms were not established.

Check the Git inventory without downloading bulk data:

```sh
python3 -B publication.py verify --code-only
```

For the retained verifier, see [campaign 007's commands](CAMPAIGN-007.md#reproduce).
For measured tasks, budgets and baselines, see [BENCHMARK.md](BENCHMARK.md).
Historical redaction and seal limitations remain in [PUBLICATION.md](PUBLICATION.md).

## Reopening requires new evidence

Reconsider only when there is a concrete new input: a practical finite algorithm
with an explicit cost budget, a materially stronger certificate producer already
competitive on external instances with checking costs charged, or an independently
prepared assay-matched benchmark with a committed biological collaborator. Each
would require a new prospective evaluation. Mathematical possibility, more
available compute or another proof lemma alone is insufficient.

This is written by an AI agent (model name unavailable) on Nico DeVeaux's behalf.
