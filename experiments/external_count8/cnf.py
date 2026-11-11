"""Strict unweighted DIMACS input and an exact binary-factor translation."""

from dataclasses import dataclass
from itertools import product

from experiments.certified_rank6.core import Factor, Model


@dataclass(frozen=True)
class Cnf:
    n: int
    clauses: tuple


def parse_dimacs(text):
    header = None
    clauses, pending = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        fields = line.split()
        if fields[0] == "c":
            if fields[1:3] in (["p", "weight"], ["p", "show"], ["p", "ind"]):
                raise ValueError("weighted/projected directives are outside this cohort")
            if fields[1:2] == ["t"] and fields[2:] != ["mc"]:
                raise ValueError("unsupported counting task directive")
            continue
        if fields[0] == "p":
            if header is not None or len(fields) != 4 or fields[1] != "cnf":
                raise ValueError("invalid or duplicate DIMACS header")
            n, count = map(int, fields[2:])
            if n < 0 or count < 0:
                raise ValueError("negative DIMACS header")
            header = n, count
            continue
        if header is None:
            raise ValueError("clause before header")
        for token in fields:
            literal = int(token)
            if literal == 0:
                clauses.append(tuple(pending))
                pending.clear()
            else:
                if abs(literal) > header[0]:
                    raise ValueError("literal outside declared variable range")
                pending.append(literal)
    if header is None or pending or len(clauses) != header[1]:
        raise ValueError("missing header, unterminated clause or clause-count mismatch")
    return Cnf(header[0], tuple(clauses))


def normalized_clauses(cnf):
    for clause in cnf.clauses:
        literals = set(clause)
        if any(-v in literals for v in literals):
            continue
        yield tuple(sorted(literals, key=lambda v: (abs(v), v)))


def input_inventory(cnf):
    clauses = tuple(normalized_clauses(cnf))
    arities = [len(c) for c in clauses]
    return {"variables": cnf.n, "clauses": len(cnf.clauses),
            "nontrivial_clauses": len(clauses), "max_clause_arity": max(arities, default=0),
            "factor_entries": sum(1 << k for k in arities) if max(arities, default=0) <= 20 else None}


def eligibility(cnf):
    inventory = input_inventory(cnf)
    reasons = []
    if cnf.n > 256:
        reasons.append("variables_above_256")
    if len(cnf.clauses) > 2000:
        reasons.append("clauses_above_2000")
    if inventory["max_clause_arity"] > 6:
        reasons.append("clause_arity_above_6")
    if inventory["factor_entries"] is None or inventory["factor_entries"] > 50000:
        reasons.append("factor_entries_above_50000")
    return inventory, reasons


def to_model(cnf):
    factors = []
    for clause in normalized_clauses(cnf):
        scope = tuple(abs(v) - 1 for v in clause)
        signs = tuple(v > 0 for v in clause)
        values = tuple(int(any(bool(bit) == sign for bit, sign in zip(assignment, signs)))
                       for assignment in product((0, 1), repeat=len(scope)))
        factors.append(Factor(scope, values))
    return Model(cnf.n, tuple(factors))
