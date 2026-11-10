"""Finite integer factor models; no floating-point decisions."""

from dataclasses import dataclass, field
from fractions import Fraction
import heapq
from itertools import product
from math import prod


@dataclass(frozen=True, order=True)
class Factor:
    scope: tuple[int, ...]
    values: tuple[int, ...]

    def __post_init__(self):
        if type(self.scope) is not tuple or type(self.values) is not tuple:
            raise ValueError("factor scopes and tables must be immutable tuples")
        if any(type(v) is not int for v in self.scope):
            raise ValueError("factor variables must be integers")
        if tuple(sorted(set(self.scope))) != self.scope:
            raise ValueError("factor scope must be strictly increasing")
        if len(self.values) != 1 << len(self.scope):
            raise ValueError("table size does not match binary scope")
        if any(type(v) is not int or v < 0 for v in self.values):
            raise ValueError("weights must be nonnegative integers")

    def value(self, assignment):
        index = 0
        for variable in self.scope:
            index = 2 * index + assignment[variable]
        return self.values[index]


@dataclass(frozen=True)
class Model:
    n: int
    factors: tuple[Factor, ...]
    _key: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.n) is not int or self.n < 0:
            raise ValueError("invalid variable count")
        if type(self.factors) is not tuple or any(not isinstance(f, Factor) for f in self.factors):
            raise ValueError("model factors must be an immutable tuple of Factors")
        if any(v < 0 or v >= self.n for f in self.factors for v in f.scope):
            raise ValueError("factor variable outside model")
        object.__setattr__(self, "_key", (self.n, tuple(sorted(self.factors))))

    @property
    def key(self):
        # Equality compares complete tables, rather than a digest or a display name.
        return self._key


class PartitionBounds:
    """A disjoint prefix frontier bounds every assignment exactly once."""

    def __init__(self, model):
        self.model = model
        self.compiled = []
        for factor in model.factors:
            k = len(factor.scope)
            levels = []
            for assigned in range(k + 1):
                width = 1 << (k - assigned)
                levels.append(tuple((min(factor.values[j:j + width]),
                                     max(factor.values[j:j + width]))
                                    for j in range(0, len(factor.values), width)))
            self.compiled.append((factor.scope, levels))
        self.heap = []
        self.lower, self.upper = self.prefix_bounds(())
        if self.lower != self.upper:
            heapq.heappush(self.heap, (self.lower - self.upper, (), self.lower, self.upper))
        self.expansions = 0
        self.bound_evaluations = 1
        self.exact_leaf_evaluations = int(model.n == 0)
        self.resolved_assignments = (1 << model.n) if self.lower == self.upper else 0

    def prefix_bounds(self, prefix):
        low = high = 1
        for scope, levels in self.compiled:
            index = assigned = 0
            for variable in scope:
                if variable >= len(prefix):
                    break
                index = 2 * index + prefix[variable]
                assigned += 1
            a, b = levels[assigned][index]
            low *= a
            high *= b
        completions = 1 << (self.model.n - len(prefix))
        return low * completions, high * completions

    def refine(self, limit=1):
        if type(limit) is not int or limit < 0:
            raise ValueError("invalid refinement budget")
        used = 0
        while used < limit and self.heap:
            _, prefix, old_low, old_high = heapq.heappop(self.heap)
            children = []
            for value in (0, 1):
                child = prefix + (value,)
                low, high = self.prefix_bounds(child)
                children.append((low, high))
                self.exact_leaf_evaluations += int(len(child) == self.model.n)
                if low != high:
                    heapq.heappush(self.heap, (low - high, child, low, high))
                else:
                    self.resolved_assignments += 1 << (self.model.n - len(child))
            low = sum(a for a, _ in children)
            high = sum(b for _, b in children)
            if not old_low <= low <= high <= old_high:
                raise AssertionError("prefix refinement must tighten bounds")
            self.lower += low - old_low
            self.upper += high - old_high
            self.expansions += 1
            self.bound_evaluations += 2
            used += 1
        return used


@dataclass(frozen=True)
class Ticket:
    generation: int
    key: tuple
    revision: int


class BoundCache:
    """Accept only current, nested results from a trusted bound producer."""

    def __init__(self):
        self.generation = 0
        self.entries = {}

    def register(self, key, lower, upper):
        if key in self.entries:
            raise ValueError("duplicate model registration")
        self._validate(lower, upper)
        self.entries[key] = (0, lower, upper)

    @staticmethod
    def _validate(lower, upper):
        if type(lower) is not int or type(upper) is not int or not 0 <= lower <= upper:
            raise ValueError("invalid integer enclosure")

    def begin(self, key):
        return Ticket(self.generation, key, self.entries[key][0])

    def commit(self, ticket, result_key, lower, upper):
        self._validate(lower, upper)
        current = self.entries.get(ticket.key)
        if (result_key != ticket.key or ticket.generation != self.generation or current is None
                or ticket.revision != current[0]):
            return False
        revision, old_lower, old_upper = current
        if not old_lower <= lower <= upper <= old_upper:
            return False
        self.entries[ticket.key] = (revision + 1, lower, upper)
        return True

    def restart(self):
        self.generation += 1
        self.entries.clear()

    def bounds(self, key):
        return self.entries[key][1:]


@dataclass(frozen=True)
class Candidate:
    name: str
    complex: Model
    protein: Model
    ligand: Model

    @property
    def models(self):
        return self.complex, self.protein, self.ligand


@dataclass(frozen=True)
class RatioBounds:
    numerator_lower: int
    numerator_upper: int
    denominator_lower: int
    denominator_upper: int

    def valid(self):
        return (all(type(v) is int for v in self.endpoints())
                and 0 <= self.numerator_lower <= self.numerator_upper
                and 0 < self.denominator_lower <= self.denominator_upper)

    def endpoints(self):
        return (self.numerator_lower, self.numerator_upper,
                self.denominator_lower, self.denominator_upper)


def certificate_gt(a, b):
    """The same natural-number predicate is compiled and proved in Lean."""
    return (a.valid() and b.valid()
            and a.numerator_lower * b.denominator_lower
            > b.numerator_upper * a.denominator_upper)


def ratio_bounds(candidate, bounds):
    (cl, cu), (pl, pu), (ll, lu) = (bounds[m.key] for m in candidate.models)
    return RatioBounds(cl, cu, pl * ll, pu * lu)


class RankController:
    def __init__(self, candidates):
        self.candidates = tuple(candidates)
        if not self.candidates or len({c.name for c in self.candidates}) != len(self.candidates):
            raise ValueError("a nonempty panel with distinct names is required")
        self.cache = BoundCache()
        self.producers = {}
        self.uses = sum(len(c.models) for c in self.candidates)
        for candidate in self.candidates:
            for model in candidate.models:
                key = model.key
                if key not in self.producers:
                    producer = self.producers[key] = PartitionBounds(model)
                    self.cache.register(key, producer.lower, producer.upper)
        self.expansions = 0
        self.certification_calls = 0

    def bounds(self):
        return {key: self.cache.bounds(key) for key in self.producers}

    def ratios(self):
        bounds = self.bounds()
        return [ratio_bounds(c, bounds) for c in self.candidates]

    def refine(self, key, budget):
        ticket = self.cache.begin(key)
        producer = self.producers[key]
        used = producer.refine(budget)
        if not self.cache.commit(ticket, producer.model.key, producer.lower, producer.upper):
            raise AssertionError("sequential producer result unexpectedly stale")
        self.expansions += used
        return used

    def certificate(self):
        ratios = self.ratios()
        if any(r.denominator_upper == 0 for r in ratios):
            return "undefined_zero_denominator", None, []
        witnesses = []
        for i, ratio in enumerate(ratios):
            if not ratio.valid():
                continue
            wins = []
            for j, other in enumerate(ratios):
                if i == j:
                    continue
                self.certification_calls += 1
                if not certificate_gt(ratio, other):
                    break
                wins.append(ratio.endpoints() + other.endpoints())
            else:
                return "certified_top1", self.candidates[i].name, wins
        if all(r.valid() and r.numerator_lower == r.numerator_upper
               and r.denominator_lower == r.denominator_upper for r in ratios):
            scores = [Fraction(r.numerator_lower, r.denominator_lower) for r in ratios]
            maximum = max(scores)
            tied = [i for i, value in enumerate(scores) if value == maximum]
            if len(tied) > 1:
                return "exact_top_tie", None, witnesses
        return "unresolved", None, witnesses

    def run(self, method="adaptive", max_expansions=20000, batch=16,
            epsilon=Fraction(1, 100)):
        if method not in ("adaptive", "fixed"):
            raise ValueError("unknown refinement method")
        if type(max_expansions) is not int or max_expansions < 0 or batch <= 0:
            raise ValueError("invalid budget")
        if not 0 < epsilon < 1:
            raise ValueError("relative tolerance must lie in (0,1)")
        while True:
            if any(r.denominator_upper == 0 for r in self.ratios()):
                status, winner, witnesses = "undefined_zero_denominator", None, []
                break
            if method == "adaptive":
                status, winner, witnesses = self.certificate()
                if status in ("certified_top1", "exact_top_tie"):
                    break
            bounds = self.bounds()
            if method == "fixed":
                eligible = [key for key, (low, high) in bounds.items()
                            if (high - low) * epsilon.denominator
                            > low * epsilon.numerator]
                if not eligible:
                    status, winner, witnesses = self.certificate()
                    break
            else:
                ratios = self.ratios()
                # Remove candidates already strictly dominated by a certified lower bound.
                active = [i for i, value in enumerate(ratios)
                          if not any(certificate_gt(other, value)
                                     for j, other in enumerate(ratios) if i != j)]
                eligible = list(dict.fromkeys(m.key for i in active
                                              for m in self.candidates[i].models
                                              if bounds[m.key][0] < bounds[m.key][1]))
            eligible = [key for key in eligible if self.producers[key].heap]
            if not eligible or self.expansions >= max_expansions:
                status, winner, witnesses = self.certificate()
                break
            # Relative width avoids prioritizing a state solely because of its scale.
            key = max(eligible, key=lambda k: Fraction(bounds[k][1] - bounds[k][0],
                                                       max(1, bounds[k][1])))
            self.refine(key, min(batch, max_expansions - self.expansions))
        return {"method": method, "status": status, "winner": winner,
                "expansions": self.expansions,
                "bound_evaluations": sum(p.bound_evaluations for p in self.producers.values()),
                "exact_leaf_evaluations": sum(p.exact_leaf_evaluations
                                              for p in self.producers.values()),
                "resolved_assignments": sum(p.resolved_assignments
                                            for p in self.producers.values()),
                "unique_states": len(self.producers), "state_uses": self.uses,
                "certification_calls": self.certification_calls,
                "max_endpoint_bits": max(p.prefix_bounds(())[1].bit_length()
                                         for p in self.producers.values()),
                "tolerance_met": all((p.upper - p.lower) * epsilon.denominator
                                     <= p.lower * epsilon.numerator
                                     for p in self.producers.values()),
                "all_partitions_exact": all(p.lower == p.upper for p in self.producers.values()),
                "witnesses": witnesses,
                "bounds": [{"lower": lo, "upper": hi}
                           for lo, hi in self.bounds().values()]}


def enumerate_partition(model):
    return sum(prod(f.value(x) for f in model.factors)
               for x in product((0, 1), repeat=model.n))


def variable_elimination(model):
    """Exact min-neighbour binary elimination, charging factor table work."""
    factors = list(model.factors)
    operations = 0
    remaining = set(range(model.n))
    while remaining:
        def cost(variable):
            return len(set(v for f in factors if variable in f.scope for v in f.scope))
        variable = min(remaining, key=lambda v: (cost(v), v))
        selected = [f for f in factors if variable in f.scope]
        factors = [f for f in factors if variable not in f.scope]
        scope = tuple(sorted({v for f in selected for v in f.scope} - {variable}))
        values = []
        for assignment in product((0, 1), repeat=len(scope)):
            x = dict(zip(scope, assignment))
            value = 0
            for bit in (0, 1):
                x[variable] = bit
                value += prod(f.value(x) for f in selected)
                operations += len(selected)
            values.append(value)
        factors.append(Factor(scope, tuple(values)))
        remaining.remove(variable)
    return prod(f.values[0] for f in factors), operations


def exact_panel(candidates, method):
    if method not in ("enumeration", "ve"):
        raise ValueError("unknown exact method")
    cache = {}
    work = 0
    for candidate in candidates:
        for model in candidate.models:
            if model.key not in cache:
                if method == "ve":
                    value, used = variable_elimination(model)
                else:
                    value, used = enumerate_partition(model), 1 << model.n
                cache[model.key] = value
                work += used
    scores = []
    for candidate in candidates:
        c, p, l = (cache[m.key] for m in candidate.models)
        if not p or not l:
            return {"method": method, "status": "undefined_zero_denominator", "winner": None,
                    "unique_states": len(cache), "work": work}
        scores.append(Fraction(c, p * l))
    winners = [c.name for c, value in zip(candidates, scores) if value == max(scores)]
    return {"method": method, "status": "certified_top1" if len(winners) == 1 else "exact_top_tie",
            "winner": winners[0] if len(winners) == 1 else None,
            "unique_states": len(cache), "work": work,
            "max_endpoint_bits": max(value.bit_length() for value in cache.values())}
