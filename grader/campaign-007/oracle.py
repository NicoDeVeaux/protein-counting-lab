"""Independent finite-table oracle and prospectively seeded controls."""

from dataclasses import dataclass
from itertools import product
import random


@dataclass(frozen=True)
class Table:
    scope: tuple
    values: tuple


@dataclass(frozen=True)
class Target:
    n: int
    factors: tuple


def weight(target, assignment):
    result = 1
    for factor in target.factors:
        row = 0
        for variable in factor.scope:
            row = (row << 1) | assignment[variable]
        result *= factor.values[row]
    return result


def partition(target):
    return sum(weight(target, assignment)
               for assignment in product((0, 1), repeat=target.n))


def tree_value(tree, assignment):
    if tree[0] == "c":
        return tree[1]
    return tree_value(tree[3] if assignment[tree[1]] else tree[2], assignment)


def parsed_weight(factors, assignment):
    value = 1
    for factor in factors:
        value *= tree_value(factor, assignment)
    return value


def compatible_contribution(target, prefix):
    return sum(weight(target, prefix + suffix)
               for suffix in product((0, 1), repeat=target.n - len(prefix)))


def factor_tree(factor):
    def build(scope, values):
        if not scope:
            return ["c", values[0]]
        midpoint = len(values) // 2
        return ["b", scope[0], build(scope[1:], values[:midpoint]),
                build(scope[1:], values[midpoint:])]
    return build(factor.scope, factor.values)


def table_cut_bounds(target, cut, prefix=()):
    if cut != 0:
        left = table_cut_bounds(target, cut[0], prefix + (0,))
        right = table_cut_bounds(target, cut[1], prefix + (1,))
        return left[0] + right[0], left[1] + right[1]
    lower = upper = 1
    for factor in target.factors:
        choices = []
        for row, value in enumerate(factor.values):
            valid = True
            for position, variable in enumerate(factor.scope):
                bit = (row >> (len(factor.scope) - position - 1)) & 1
                if variable < len(prefix) and bit != prefix[variable]:
                    valid = False
                    break
            if valid:
                choices.append(value)
        lower *= min(choices)
        upper *= max(choices)
    count = 1 << (target.n - len(prefix))
    return lower * count, upper * count


def wire_certificate(target, cut):
    lower, upper = table_cut_bounds(target, cut)
    return {"n": target.n, "factors": [factor_tree(f) for f in target.factors],
            "cut": cut, "lower": lower, "upper": upper}


def deterministic_targets():
    large = 2 ** 140 + 7
    return [
        ("zero_variables_empty", Target(0, ())),
        ("zero_variables_zero_scalar", Target(0, (Table((), (0,)),))),
        ("zero_variables_scalar", Target(0, (Table((), (17,)),))),
        ("unused_variables", Target(4, ())),
        ("zero_factor", Target(3, (Table((1,), (0, 0)),))),
        ("constant_factor", Target(4, (Table((0, 3), (5, 5, 5, 5)),))),
        ("sparse_scope", Target(5, (Table((1, 4), (0, 2, 11, 3)),))),
        ("repeated_factor", Target(3, (Table((0, 2), (1, 7, 2, 4)),) * 2)),
        ("large_coefficients", Target(3, (
            Table((), (large,)), Table((0, 2), (large, 1, 0, large + 1))))),
        ("chain", Target(4, tuple(Table((i, i + 1), (1, 4, 2, 7))
                                 for i in range(3)))),
        ("dense", Target(4, tuple(Table((i, j), (3, 0, 5, 2))
                                 for i in range(4) for j in range(i + 1, 4)))),
    ]


def seeded_targets():
    rng = random.Random(7007)
    for index in range(60):
        n = index % 6
        factors = []
        for _ in range(rng.randrange(7)):
            arity = rng.randrange(min(3, n) + 1)
            scope = tuple(sorted(rng.sample(range(n), arity)))
            values = tuple(rng.randrange(10) for _ in range(1 << arity))
            factors.append(Table(scope, values))
        yield f"seed7007_{index:02d}", Target(n, tuple(factors))


def full_cut(n):
    return 0 if n == 0 else [full_cut(n - 1), full_cut(n - 1)]


def partial_cut(n, splits):
    """Breadth-first control cuts independent of the candidate's scheduling."""
    if n == 0 or splits == 0:
        return 0
    root = [0, 0]
    frontier = [(root, 0, 1), (root, 1, 1)]
    used = 1
    while frontier and used < splits:
        parent, side, depth = frontier.pop(0)
        if depth < n:
            parent[side] = child = [0, 0]
            frontier.extend(((child, 0, depth + 1), (child, 1, depth + 1)))
            used += 1
    return root


def cut_nodes(cut):
    return 1 if cut == 0 else 1 + cut_nodes(cut[0]) + cut_nodes(cut[1])
