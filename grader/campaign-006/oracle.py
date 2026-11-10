"""Independent assignment-product oracle; no experiment arithmetic is imported."""

from fractions import Fraction
from itertools import product


def partition(n, factors):
    total = 0
    for values in product((0, 1), repeat=n):
        mass = 1
        for scope, table in factors:
            index = 0
            for variable in scope:
                index = 2 * index + values[variable]
            mass *= table[index]
        total += mass
    return total


def affinity(complex_z, protein_z, ligand_z):
    if protein_z == 0 or ligand_z == 0:
        return None
    return Fraction(complex_z, protein_z * ligand_z)


def strict_winner(scores):
    if any(score is None for score in scores.values()):
        return None
    winners = [name for name, score in scores.items()
               if all(name == other or score > value
                      for other, value in scores.items())]
    return winners[0] if len(winners) == 1 else None


def claims_are_sound(bounds, true_z):
    return (type(bounds[0]) is int and type(bounds[1]) is int
            and 0 <= bounds[0] <= true_z <= bounds[1])


def cross_order_is_true(a, b):
    return (a[1] > 0 and a[2] > 0 and b[1] > 0 and b[2] > 0
            and affinity(*a) > affinity(*b))
