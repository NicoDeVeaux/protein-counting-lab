# Partition certificates and their soundness

Run from the repository root:

```sh
sh formal/campaign-007/lean/check.sh
```

Lean 4.35.0 is pinned. Only its bundled libraries are used; there are no Mathlib
or downloaded proof dependencies. Compilation, the executable checker and proof
mutants use temporary build directories. Additional valid exported JSON-lines
certificates can be passed with `--certificates FILE`.

## What is proved

`PartitionCertificate.lean` proves eleven theorems. The proof follows the actual
checker construction:

1. A decision-tree factor's conditional minimum/maximum encloses every assignment
   agreeing with the assigned prefix.
2. Products of those factor enclosures bound the assignment weight.
3. A uniform weight enclosure multiplied by `2^remaining` encloses the sum of all
   completions. The semantic partition recursively assigns each remaining variable
   false and true and adds both branches.
4. A binary split certificate covers this partition by construction. A leaf uses
   the conditional product bound; a split verifies both children and adds their
   intervals. A split beyond the model's variable count is rejected.
5. An accepted supplied interval exactly matches the recomputed cut interval and
   therefore encloses the semantic partition. The theorem has **no premise that
   the supplied enclosure is valid**.
6. Accepted factors use only declared variable indices; the value of such a model
   is independent of environment entries outside that declared range.
7. `checked_greater_sound` composes six accepted partition certificates and a
   positive-denominator cross-product comparison into the strict ordering of the
   actual three-state ratios. This corollary also requires no supplied-enclosure
   premise.

The last corollary checks `C_A/(P_A*L_A) > C_B/(P_B*L_B)` without division. Its
executable `checkedGreater` requires all six state certificates, positive lower
denominator products and `cA_lower*(pB_lower*lB_lower) >
cB_upper*(pA_upper*lA_upper)`. It rejects ties and undefined denominators. The
JSON-lines entry point verifies individual state certificates; the reproduction
runner separately exercises the composed Lean predicate on six concrete cases.

The checker does not enumerate global assignments to establish a bound. It visits
the supplied cut and the small factor trees at its leaves. A root-leaf certificate
can represent many assignments through its completion multiplier. Larger cuts can
still be expensive; this is a verification advance, not a solver-speedup claim.

## Wire format and executable

`Main.lean` reads one JSON object per line, containing exactly these five fields:

```json
{"n":1,"factors":[["b",0,["c",2],["c",5]]],"cut":[0,0],"lower":7,"upper":7}
```

- A factor is `["c",weight]` or `["b",variableIndex,falseBranch,trueBranch]`.
  All weights and indices are naturals, and every index must be less than `n`.
- A cut is `0` for a leaf or `[falseBranch,trueBranch]` for a split. Depth starts
  at zero, so each split fixes the next binary variable.
- `lower` and `upper` must exactly equal the checker-computed interval. Even a
  numerically valid but different, wider interval is rejected by this format.
- Output is `accepted LOWER UPPER`, `rejected`, or `invalid`. Values are printed
  as full exact decimal integers. `invalid` covers malformed JSON/shape/natural
  values; `rejected` covers a parsed certificate failing the mathematical checks.

For the example above, the result is `accepted 7 7`. Replacing the cut by `0` and
claiming bounds `4` and `10` is also valid. Dropping a child, splitting past depth
one, changing a bound or using variable index one fails.

To batch input without the reproduction harness, compile `PartitionCertificate.lean`
to a temporary `PartitionCertificate.olean`, set `LEAN_PATH` to that directory,
and run `lean --run Main.lean` from this pinned project directory. The Python
binding in `experiments/partition_certificate7/` manages this for its callers.

## Trust boundary and negative controls

The universal proof concerns the Lean definitions and the supplied parsed model.
It does not prove Python, the original factor-table-to-tree translation, external
file authenticity, JSON parsing, compilation, native execution or IO. The Python
boundary binds `n` and every encoded factor to an expected immutable model before
requesting verification. That binding and translation are independently tested;
they are not kernel-proved.

Lean's JSON parser normalizes duplicate object keys before the field-shape check.
Consequently the raw CLI theorem concerns the normalized parsed model, not a claim
that the original JSON text had unique keys. The host API supplies canonical JSON
with one copy of each field. A wrapper accepting arbitrary raw JSON must reject
duplicates before relying on unique-key syntax. Trailing non-JSON content is
rejected. Resource exhaustion can still fail verification rather than return an
acceptance; there is no unbounded-input availability guarantee.

The axiom audit expects only Lean's standard `propext` and `Quot.sound`, with the
exact dependency set checked for each theorem. It rejects missing/unexpected
reports and thus `sorryAx`, native-evaluation axioms or any other added axiom.

Three source mutants must fail Lean compilation: omitted completion count,
omitted right split branch, and minimum substituted for the upper bound. The
executable controls include unknown variables, missing/extra fields, truncated
cuts, excessive split depth, incorrect endpoints, shared factor variables, large
integers, zero weights and six composed ranking cases. Independent bridge/oracle
results belong to the separate campaign-007 grader report.
