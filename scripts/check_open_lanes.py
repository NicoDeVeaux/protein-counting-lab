#!/usr/bin/env python3
"""Reproduce bounded arithmetic checks; no SAT solver or biological data required."""

import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.eth_schedule.run import ceil_log2, first_all_necessary_gates, first_r_gate


def checks():
    first_r = first_r_gate()['lambda']
    first_joint = first_all_necessary_gates(1)['lambda']
    assert first_r == 521284
    assert first_joint == 10909384704

    appendix = []
    for label, size in [('10^3', 10**3), ('10^6', 10**6),
                        ('10^12', 10**12), ('10^100', 10**100)]:
        lam = ceil_log2(size)
        u0 = lam // (128*1024)
        assert u0 == 0
        appendix.append({'size_label': label, 'ceil_log2_size': lam, 'literal_root_u': u0})

    # Only the sufficient conditions named here imply this bound.
    min_r, min_R = 2, 32
    min_Q = 6*min_R
    min_log2_D_squared = 4*min_Q
    assert min_Q == 192 and min_log2_D_squared == 768

    positions, conformers = 50, 10
    binary_bits = positions*ceil_log2(conformers)
    one_hot_bits = positions*conformers
    assert binary_bits == 200 and one_hot_bits == 500

    # Six constituent logZ errors per WT-normalized effect, twelve per pair.
    assumed_pair_gap = 0.03
    eta_limit = assumed_pair_gap/12
    assert math.isclose(eta_limit, 0.0025)
    return {
        'scope': 'Arithmetic/precondition checks only; no new solver, timing or biological experiment.',
        'literal_section4': {
            'first_lambda_r_ge_2': first_r,
            'first_lambda_four_gates_beta1': first_joint,
            'first_boolean_n_expression': f'2^{first_joint-1} + 1',
            'qualification': 'Necessary gates only, not a runtime crossover or universal lower bound.'},
        'conditional_retuning_bound': {
            'assumptions': ['r>=2', 'R>=32', '6R<=Q', 'D=r^(2Q)',
                            '2(b+w)D^2<=M<=b*n', 'b,w>=1'],
            'conclusion': 'n > 2^769',
            'qualification': 'Does not constrain layouts dropping these sufficient conditions or alternative algorithms.'},
        'literal_tensor_appendix': {
            'epsilon': '1/131072', 'root_u': 'floor(ceil(log2(s))/131072)',
            'examples': appendix, 'first_nonzero_root_u_size_expression': '2^131071 + 1',
            'qualification': 'First positive parameter only; all other hypotheses/costs untested. Not a crossover.'},
        'encoding_illustration': {
            'positions': positions, 'states_per_position': conformers,
            'conformations_expression': '10^50', 'binary_choice_bits_before_auxiliaries': binary_bits,
            'one_hot_choice_bits_before_auxiliaries': one_hot_bits,
            'qualification': 'Hypothetical arithmetic; validity, factor and weight encoding costs are additional.'},
        'ranking_error_illustration': {
            'assumed_log_score_gap': assumed_pair_gap,
            'required_uniform_absolute_logZ_error_strictly_below': eta_limit,
            'upper_relative_Z_factor_minus_one': math.expm1(eta_limit),
            'qualification': 'Requires valid error enclosures; triangle bound only, no speedup or physical-accuracy claim.'}}


if __name__ == '__main__':
    print(json.dumps(checks(), indent=2))
