# Hard-zero support propagation

`propagate_model(model, simplify=False)` returns a restricted `Model` and a deletion ledger. It implements conventional generalized arc consistency: intersect hard-zero constraints with identical scopes, then repeatedly remove values with no remaining support in an incident constraint. The numeric factors remain separate.

Only stored `-inf` entries forbid assignments. All finite logs are preserved, including values whose exponentials would underflow. There is no energy cutoff, approximate pruning, or claim of a new algorithm.

For each variable, `retained_original_indices[v]` maps the output's domain back to the function input's domain. Variables remain present, including singletons and isolated variables. Restriction copies all retained numeric entries without arithmetic. If propagation proves a zero partition sum, the output instead keeps the variable count using dummy singleton domains and a scalar `-inf`; the ledger distinguishes these dummy indices from feasible assignments.

The ledger records every deletion with the constraint and domains that justify it, scope intersections, per-factor original axis indices and slicing shapes, configuration counts, structure estimates and in-memory preprocessing time. Scalar factors have empty axis mappings. Factor indices refer to the restriction stage before optional algebra; canonical-zero replacements are marked separately. Exact algebra from the immutable `experiments.structure` namespace is optional and separately timed. Loading and serialization are excluded from this function's timer and must be charged by the caller.

An arc-consistent cyclic model can still be globally inconsistent. `arc_consistent` is not a satisfiability certificate. Domain mappings are relative to each invocation's input, not automatically composed through earlier preprocessing stages.

This is an exploratory conventional inference component. It makes no ETH, affinity-prediction or biological-validation claim. The independent grader evaluates the campaign evidence separately.
