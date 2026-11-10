# Exact ranking certificate

Run `sh formal/campaign-006/lean/check.sh` from the repository root. Lean 4.35.0
is pinned in `lean-toolchain`; only Lean's bundled `Std` is imported. Builds and
the deliberate mutant use a temporary directory.

`Certificate.lean` proves that an accepted strict certificate orders every pair
of nonnegative integer ratios enclosed by its intervals, with positive actual
denominators. It also proves interval addition, multiplication, finite sums,
finite products, three-state denominator composition, and repeated contribution
bounds. `check_sound`, `three_state_rank_sound`, and the composition lemmas are axiom-free;
`repeated_bounds` uses only Lean's standard `propext` and `Quot.sound` axioms.

`Main.lean` runs that proved Boolean checker. Each input line contains eight
naturals:

```
a_numerator_lower a_numerator_upper a_denominator_lower a_denominator_upper b_numerator_lower b_numerator_upper b_denominator_lower b_denominator_upper
```

It returns `accepted`, `rejected`, or `invalid`. Acceptance requires ordered
endpoints, strictly positive lower denominators, and
`a_numerator_lower * b_denominator_lower > b_numerator_upper * a_denominator_upper`.
For `C/(P*L)`, the numerator interval is the complex interval and the denominator
interval is the product of the protein and ligand intervals. Division and
floating point arithmetic are unnecessary for this certificate.

The runner checks the compiler's axiom report, compares the executable and Python
checker with an independent integer predicate on an exhaustive small grid plus fixed large-integer
cases, and verifies that changing strict `<` to non-strict `≤` breaks the proof.
Additional real controller witnesses can be passed with `--certificates FILE`
or `--witness-csv experiments/certified_rank6/results/WITNESSES.csv`.

The theorem concerns this Lean checker. It does not prove Python's implementation,
the Python frontier's coverage of assignments, the model parser, or biological
energy accuracy. The Python producer and controller require independent tests.
Sum/product lemmas justify the arithmetic composition once the factor enclosure
and disjoint-prefix coverage assumptions have been established. Lean's kernel,
runtime and integer/IO implementations remain trusted.
