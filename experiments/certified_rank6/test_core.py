"""Executable boundary controls, separate from the independent campaign audit."""

from fractions import Fraction
from itertools import product
import random
import unittest

from .core import (BoundCache, Candidate, Factor, Model, PartitionBounds, RankController,
                   RatioBounds, certificate_gt, enumerate_partition, variable_elimination)
from .fixtures import chain


class ExactBoundsTests(unittest.TestCase):
    def test_frontier_encloses_and_terminates(self):
        rng = random.Random(5601)
        for n in range(1, 6):
            factors = [Factor((v,), tuple(rng.randrange(6) for _ in range(2))) for v in range(n)]
            factors += [Factor((a, a + 1), tuple(rng.randrange(6) for _ in range(4)))
                        for a in range(n - 1)]
            model = Model(n, tuple(factors))
            exact = enumerate_partition(model)
            bounds = PartitionBounds(model)
            while True:
                self.assertLessEqual(bounds.lower, exact)
                self.assertGreaterEqual(bounds.upper, exact)
                if not bounds.refine():
                    break
            self.assertEqual((bounds.lower, bounds.upper), (exact, exact))
            self.assertEqual(variable_elimination(model)[0], exact)

    def test_empty_scalar_and_free_variables(self):
        for model, expected in ((Model(0, ()), 1), (Model(3, ()), 8),
                                (Model(2, (Factor((), (7,)),)), 28)):
            bounds = PartitionBounds(model)
            self.assertEqual((bounds.lower, bounds.upper), (expected, expected))
            self.assertEqual(variable_elimination(model)[0], expected)

    def test_cache_rejects_restart_reorder_key_and_widening(self):
        cache = BoundCache()
        key = chain(2).key
        other = chain(2, scalar=2).key
        cache.register(key, 1, 100)
        old = cache.begin(key)
        self.assertTrue(cache.commit(old, key, 2, 90))
        self.assertFalse(cache.commit(old, key, 3, 80))
        self.assertFalse(cache.commit(cache.begin(key), key, 0, 101))
        self.assertFalse(cache.commit(cache.begin(key), other, 3, 80))
        cache.restart()
        cache.register(other, 1, 100)
        self.assertFalse(cache.commit(old, key, 3, 80))
        same_key_ticket = cache.begin(other)
        cache.restart()
        cache.register(other, 1, 100)
        self.assertFalse(cache.commit(same_key_ticket, other, 3, 80))

    def test_model_identity_reuses_full_tables_only(self):
        original = chain(3)
        reordered = Model(3, tuple(reversed(original.factors)))
        changed = chain(3, scalar=2)
        self.assertEqual(original.key, reordered.key)
        self.assertNotEqual(original.key, changed.key)
        panel = [Candidate("A", original, reordered, original),
                 Candidate("B", changed, original, original)]
        controller = RankController(panel)
        self.assertEqual(len(controller.producers), 2)
        result = controller.run()
        self.assertEqual((result["status"], result["winner"]), ("certified_top1", "B"))

    def test_undefined_denominator_zero_numerator_tie_and_budget(self):
        zero = Model(1, (Factor((0,), (0, 0)),))
        one = Model(1, (Factor((0,), (1, 1)),))
        result = RankController([Candidate("A", one, zero, one)]).run()
        self.assertEqual(result["status"], "undefined_zero_denominator")
        result = RankController([Candidate("A", zero, one, one),
                                 Candidate("B", one, one, one)]).run()
        self.assertEqual(result["winner"], "B")
        tied = RankController([Candidate("A", one, one, one),
                               Candidate("B", one, one, one)]).run()
        self.assertEqual(tied["status"], "exact_top_tie")
        uncertain = chain(3)
        result = RankController([Candidate("A", uncertain, uncertain, uncertain),
                                 Candidate("B", chain(3, 2), uncertain, uncertain)]).run(max_expansions=0)
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["expansions"], 0)

    def test_certificate_exact_cross_products_and_invalid_intervals(self):
        for al, au, dl, du, bl, bu, el, eu in product(range(3), repeat=8):
            a, b = RatioBounds(al, au, dl, du), RatioBounds(bl, bu, el, eu)
            accepted = certificate_gt(a, b)
            if accepted:
                self.assertGreater(Fraction(al, du), Fraction(bu, el))
        self.assertFalse(certificate_gt(RatioBounds(1, 2, 0, 1), RatioBounds(0, 1, 1, 1)))


if __name__ == "__main__":
    unittest.main()
