from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
import random

from experiments.eth_schedule.run import ceil_log2, ceil_sqrt, parameters


def test_ceil_logs_at_power_boundaries():
    for exponent in range(1, 200):
        value = 1 << exponent
        assert ceil_log2(value) == exponent
        assert ceil_log2(value + 1) == exponent + 1
        if exponent > 1:
            assert ceil_log2(value - 1) == exponent


def test_integer_parameters_against_independent_decimal_formulas():
    rng = random.Random(20261106)
    samples = [rng.randrange(5, 10**15) for _ in range(150)]
    samples += [n * n + delta for n in (3, 100, 10000, 104448)
                for delta in (-1, 0, 1)]
    with localcontext() as context:
        context.prec = 80
        for lam in samples:
            nu = 1
            while 2**nu < lam:
                nu += 1
            for beta in (1, 2, 3):
                expected_r = int((Decimal(lam).sqrt() / Decimal(nu**2)).to_integral_value(rounding=ROUND_FLOOR))
                expected_q = int((Decimal(lam) / Decimal(128 * nu)).to_integral_value(rounding=ROUND_FLOOR))
                expected_r_degree = (beta + 3) * int(Decimal(lam).sqrt().to_integral_value(rounding=ROUND_CEILING))
                result = parameters(lam, beta)
                assert (result["nu"], result["r"], result["Q"], result["R"]) == (nu, expected_r, expected_q, expected_r_degree)


def test_ceil_sqrt_at_large_square_boundaries():
    for value in (2, 100, 104448, 10**30):
        square = value * value
        assert ceil_sqrt(square - 1) == value
        assert ceil_sqrt(square) == value
        assert ceil_sqrt(square + 1) == value + 1
