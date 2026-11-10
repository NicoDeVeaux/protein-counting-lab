"""Prospective synthetic panel from grader/campaign-006/PROTOCOL.md."""

import random

from .core import Candidate, Factor, Model


CASE_NAMES = ("uniform8", "concentrated8", "concentrated12", "shared12",
              "independent_dense8", "independent_dense12", "near_tie8", "exact_tie8")


def chain(n, scalar=1, gauge=0, uniform=False):
    factors = [Factor((), (scalar,))]
    for variable in range(n):
        values = (1, 1) if uniform else (1, 9)
        if gauge & (1 << variable):
            values = values[::-1]
        factors.append(Factor((variable,), values))
    for variable in range(n - 1):
        scope = variable, variable + 1
        base = (1, 1, 1, 1) if uniform else (9, 1, 1, 9)
        values = tuple(base[((a ^ ((gauge >> variable) & 1)) << 1)
                            | (b ^ ((gauge >> (variable + 1)) & 1))]
                       for a in (0, 1) for b in (0, 1))
        factors.append(Factor(scope, values))
    return Model(n, tuple(factors))


def dense(n, seed):
    rng = random.Random(seed)
    factors = [Factor((v,), tuple(rng.randint(1, 9) for _ in range(2)))
               for v in range(n)]
    factors += [Factor((a, b), tuple(rng.randint(1, 9) for _ in range(4)))
                for a in range(n) for b in range(a + 1, n)]
    return Model(n, tuple(factors))


def make_case(name):
    if name not in CASE_NAMES:
        raise ValueError("unknown frozen case")
    n = 12 if name.endswith("12") else 8
    if name.startswith("independent_dense"):
        seed = 602 if n == 12 else 601
        return tuple(Candidate(chr(65 + candidate),
                               *(dense(n, seed + 100 * candidate + 10 * state)
                                 for state in range(3))) for candidate in range(3))
    if name == "exact_tie8":
        target = chain(n)
        return tuple(Candidate(chr(65 + i), target, target, target) for i in range(3))
    if name == "near_tie8":
        target = chain(n)
        return tuple(Candidate(chr(65 + i), chain(n, 1_000_000 + i), target, target)
                     for i in range(3))
    shared = name in ("shared12", "uniform8")
    uniform = name == "uniform8"
    return tuple(Candidate(chr(65 + i), chain(n, scalar, uniform=uniform),
                           chain(n, gauge=0 if shared else 2 * i + 1, uniform=uniform),
                           chain(n, gauge=0 if shared else 2 * i + 2, uniform=uniform))
                 for i, scalar in enumerate((1, 2, 8)))


def input_profile(candidates):
    models = {m.key: m for c in candidates for m in c.models}
    coefficients = [v for m in models.values() for f in m.factors for v in f.values]
    return {"unique_states": len(models), "state_uses": 3 * len(candidates),
            "binary_variables_per_state": max(m.n for m in models.values()),
            "factor_entries": len(coefficients),
            "coefficient_bits": max(v.bit_length() for v in coefficients),
            "coefficient_bits_sum": sum(max(1, v.bit_length()) for v in coefficients),
            "auxiliary_variables": 0}
