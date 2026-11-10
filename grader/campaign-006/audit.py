"""Independent end-to-end and adversarial checks for the actual Python controller."""

from fractions import Fraction
from itertools import product
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.certified_rank6 import core
from oracle import affinity, partition, strict_winner


def raw(model):
    return tuple((factor.scope, factor.values) for factor in model.factors)


def z(model):
    return partition(model.n, raw(model))


def within(producer, expected):
    assert type(producer.lower) is int and type(producer.upper) is int
    assert 0 <= producer.lower <= expected <= producer.upper


def prefix_z(model, prefix):
    total = 0
    for tail in product((0, 1), repeat=model.n - len(prefix)):
        assignment = prefix + tail
        mass = 1
        for scope, table in raw(model):
            index = 0
            for variable in scope:
                index = index * 2 + assignment[variable]
            mass *= table[index]
        total += mass
    return total


def producer_checks():
    models = refinements = prefixes = 0
    rng = random.Random(60601)
    for n in range(6):
        for trial in range(24):
            minimum = trial % 2
            factors = [core.Factor((), (rng.randrange(minimum, 5),))]
            factors += [core.Factor((i,), tuple(rng.randrange(minimum, 5) for _ in range(2)))
                        for i in range(n)]
            factors += [core.Factor((i, j), tuple(rng.randrange(minimum, 5) for _ in range(4)))
                        for i in range(n) for j in range(i + 1, n)]
            model = core.Model(n, tuple(factors))
            producer = core.PartitionBounds(model)
            expected = z(model)
            within(producer, expected)
            for length in range(n + 1):
                for prefix in product((0, 1), repeat=length):
                    lower, upper = producer.prefix_bounds(prefix)
                    assert lower <= prefix_z(model, prefix) <= upper
                    prefixes += 1
            while producer.heap:
                previous = producer.lower, producer.upper
                assert producer.refine(1) == 1
                assert previous[0] <= producer.lower <= producer.upper <= previous[1]
                within(producer, expected)
                refinements += 1
            assert producer.lower == producer.upper == expected
            assert producer.refine(1) == 0
            models += 1
    return {"models": models, "prefixes": prefixes, "refinements": refinements}


def checker_checks():
    rng = random.Random(60602)
    rows = []
    accepted = 0
    for _ in range(10000):
        an, ad, bn, bd = [rng.randrange(1, 50) for _ in range(4)]
        a = core.RatioBounds(rng.randrange(an + 1), an + rng.randrange(10),
                             rng.randrange(1, ad + 1), ad + rng.randrange(10))
        b = core.RatioBounds(rng.randrange(bn + 1), bn + rng.randrange(10),
                             rng.randrange(1, bd + 1), bd + rng.randrange(10))
        claimed = core.certificate_gt(a, b)
        if claimed:
            assert Fraction(an, ad) > Fraction(bn, bd)
            accepted += 1
        rows.append(a.endpoints() + b.endpoints())
    good = core.RatioBounds(2, 2, 1, 1)
    invalid = [core.RatioBounds(3.0, 3, 1, 1), core.RatioBounds(True, True, 1, 1),
               core.RatioBounds(-1, 2, 1, 1), core.RatioBounds(2, 1, 1, 1),
               core.RatioBounds(1, 2, 0, 1), core.RatioBounds(1, 2, 2, 1)]
    for bad in invalid:
        assert not core.certificate_gt(good, bad)
        assert not core.certificate_gt(bad, good)
    equal = core.RatioBounds(1, 1, 1, 1)
    assert not core.certificate_gt(equal, equal)
    # These controls expose three tempting, unsound predicate mutations.
    a, b = core.RatioBounds(1, 100, 1, 1), core.RatioBounds(2, 2, 1, 1)
    assert not core.certificate_gt(a, b)
    assert a.numerator_upper * b.denominator_upper > b.numerator_lower * a.denominator_lower
    assert equal.numerator_lower * equal.denominator_lower >= equal.numerator_upper * equal.denominator_upper
    a, b = core.RatioBounds(3, 3, 100, 100), core.RatioBounds(2, 2, 1, 1)
    assert not core.certificate_gt(a, b)
    assert a.numerator_lower * a.denominator_upper > b.numerator_upper * b.denominator_lower
    rows.extend([equal.endpoints() * 2,
                 core.RatioBounds(1, 100, 1, 1).endpoints() + core.RatioBounds(2, 2, 1, 1).endpoints(),
                 a.endpoints() + b.endpoints()])
    return {"random_enclosures": 10000, "accepted": accepted,
            "invalid_endpoint_controls": len(invalid), "predicate_mutants_exposed": 3}, rows


def cache_checks():
    cache = core.BoundCache()
    cache.register("model-a", 0, 100)
    ticket = cache.begin("model-a")
    assert cache.commit(ticket, "model-a", 1, 90)
    assert not cache.commit(ticket, "model-a", 2, 80), "replayed ticket must fail"
    ticket = cache.begin("model-a")
    assert not cache.commit(ticket, "model-a", 0, 95), "bounds may not widen"
    assert not cache.commit(ticket, "model-b", 2, 80), "wrong producer identity must fail"
    assert cache.bounds("model-a") == (1, 90)
    cache.restart()
    cache.register("model-a", 0, 100)
    assert not cache.commit(ticket, "model-a", 2, 80), "pre-restart ticket must fail"
    assert cache.bounds("model-a") == (0, 100)
    same_revision_ticket = cache.begin("model-a")
    cache.restart()
    cache.register("model-a", 0, 100)
    assert not cache.commit(same_revision_ticket, "model-a", 2, 80), "generation matters even when revision repeats"
    assert not cache.commit(core.Ticket(cache.generation, "model-b", 0), "model-b", 1, 99)
    for lo, hi in [(-1, 1), (2, 1), (0.0, 1), (False, 1)]:
        try:
            cache.commit(cache.begin("model-a"), "model-a", lo, hi)
        except ValueError:
            pass
        else:
            raise AssertionError("malformed cache interval accepted")
    return {"replay_restart_identity_nesting_controls": 6, "malformed_intervals": 4}


def controller_checks():
    one = core.Model(1, (core.Factor((0,), (1, 1)),))
    zero = core.Model(1, (core.Factor((0,), (0, 0)),))
    mixed = core.Model(1, (core.Factor((0,), (0, 1)),))
    c = core.Candidate
    single = core.RankController([c("single", one, mixed, one)])
    status, winner, _ = single.certificate()
    assert status != "certified_top1" and winner is None
    invalid = core.RankController([c("zero-denominator", one, zero, one), c("valid", one, one, one)])
    result = invalid.run()
    assert result["status"] == "undefined_zero_denominator" and result["winner"] is None
    numerator = core.RankController([c("zero-numerator", zero, one, one), c("positive", one, one, one)])
    assert numerator.run()["winner"] == "positive"
    tied = core.RankController([c("a", one, one, one), c("b", one, one, one)])
    assert tied.run()["status"] == "exact_top_tie"
    changed = core.Model(1, (core.Factor((0,), (1, 2)),))
    shared = core.RankController([c("a", one, one, one), c("b", changed, one, one)])
    assert len(shared.producers) == 2 and one.key != changed.key
    assert shared.run()["winner"] == "b"
    chain = core.Model(2, (core.Factor((0,), (1, 9)), core.Factor((0, 1), (9, 1, 1, 9))))
    limited = core.RankController([c("a", chain, chain, chain), c("b", chain, one, one)])
    limited_result = limited.run(max_expansions=0)
    assert limited_result["expansions"] == 0
    if limited_result["winner"] is not None:
        scores = {v.name: affinity(*(z(m) for m in v.models)) for v in limited.candidates}
        assert limited_result["winner"] == strict_winner(scores)
    return {"zero_singleton_tie_identity_budget_controls": 6}


def main():
    outcomes = {"producer": producer_checks(), "checker": None,
                "cache": cache_checks(), "controller": controller_checks()}
    outcomes["checker"], rows = checker_checks()
    if "--write-bridge" in sys.argv:
        path = Path(__file__).with_name("checker_cases.cert")
        path.write_text("".join(" ".join(map(str, row)) + "\n" for row in rows))
    for name, counts in outcomes.items():
        print(name, counts)
    print("independent_audit=pass")


if __name__ == "__main__":
    main()
