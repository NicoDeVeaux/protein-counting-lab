"""Independent DIMACS semantics and exact tiny-model reference calculations."""

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class CNF:
    n: int
    clauses: tuple


def parse_dimacs(text):
    header = None
    tokens = []
    projections = []
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "c":
            if fields[1:3] == ["p", "weight"]:
                raise ValueError("weighted directive in ordinary CNF")
            if fields[1:3] == ["p", "show"]:
                if fields[-1] != "0":
                    raise ValueError("unterminated projection")
                projections.append(tuple(map(int, fields[3:-1])))
            if fields[1:2] == ["t"] and fields[2:] != ["mc"]:
                raise ValueError("nonordinary counting type")
            continue
        if fields[0] == "p":
            if header is not None or len(fields) != 4 or fields[1] != "cnf":
                raise ValueError("invalid or duplicate header")
            header = tuple(map(int, fields[2:]))
            if min(header) < 0:
                raise ValueError("negative dimensions")
            continue
        if header is None:
            raise ValueError("clauses precede header")
        tokens.extend(map(int, fields))
    if header is None:
        raise ValueError("missing header")
    n, expected = header
    if any(sorted(p) != list(range(1, n + 1)) for p in projections):
        raise ValueError("nontrivial projection")
    clauses = []
    pending = []
    for literal in tokens:
        if literal == 0:
            clauses.append(tuple(pending))
            pending.clear()
        elif abs(literal) > n:
            raise ValueError("literal outside declared range")
        else:
            pending.append(literal)
    if pending or len(clauses) != expected:
        raise ValueError("clause count or termination mismatch")
    return CNF(n, tuple(clauses))


def normalized_clauses(cnf):
    result = []
    for clause in cnf.clauses:
        literals = set(clause)
        if any(-literal in literals for literal in literals):
            continue
        result.append(tuple(sorted(literals, key=lambda v: (abs(v), v))))
    return tuple(result)


def value(cnf, assignment):
    return int(all(any((assignment[abs(literal) - 1] == 1) == (literal > 0)
                       for literal in clause) for clause in cnf.clauses))


def exact_count(cnf):
    if cnf.n > 24:
        raise ValueError("independent enumeration is a tiny-control oracle")
    return sum(value(cnf, assignment) for assignment in product((0, 1), repeat=cnf.n))


def expected_factor_tables(cnf):
    result = []
    for clause in normalized_clauses(cnf):
        scope = tuple(sorted({abs(literal) - 1 for literal in clause}))
        rows = []
        for bits in product((0, 1), repeat=len(scope)):
            assigned = dict(zip(scope, bits))
            rows.append(int(any((assigned[abs(literal) - 1] == 1) == (literal > 0)
                                for literal in clause)))
        result.append((scope, tuple(rows)))
    return tuple(sorted(result))


def probability_order(count_a, n_a, count_b, n_b):
    delta = count_a * (1 << n_b) - count_b * (1 << n_a)
    return "A" if delta > 0 else "B" if delta < 0 else "tie"


def interval_order(low_a, high_a, n_a, low_b, high_b, n_b):
    if not (0 <= low_a <= high_a <= 1 << n_a and 0 <= low_b <= high_b <= 1 << n_b):
        raise ValueError("invalid probability enclosure")
    if low_a * (1 << n_b) > high_b * (1 << n_a):
        return "A"
    if low_b * (1 << n_a) > high_a * (1 << n_b):
        return "B"
    if low_a == high_a and low_b == high_b:
        return probability_order(low_a, n_a, low_b, n_b)
    return "unresolved"
