import itertools
import math
from types import SimpleNamespace

import pytest

from experiments.rigid_affinity5.core import enumerate_state, relative_scores


def matrix(domains, single, pair=(), constant=0.0):
    one_offsets, pair_offsets = [], []
    one_count = pair_count = 0
    for pos, size in enumerate(domains):
        one_offsets.append(one_count)
        one_count += size
        for prior in range(pos):
            pair_offsets.append(pair_count)
            pair_count += size * domains[prior]
    assert one_count == len(single) and pair_count == len(pair)
    return SimpleNamespace(domains=domains, one_body=single, pairwise=pair,
                           one_body_offsets=one_offsets, pairwise_offsets=pair_offsets,
                           constant=constant)


def test_asymmetric_pair_offsets_noncontiguous_domains_and_batch_boundaries():
    m = matrix((2, 3, 2), [2, -1, 4, 5, -3, 6, 8],
               list(range(6)) + [9, 2, -7, 3] + [4, -2, 1, 0, -3, 8], 7)
    domains = [(1,), (0, 2), (0, 1)]
    energies = []
    for a, b, c in itertools.product(*domains):
        energies.append(7 + m.one_body[a] + m.one_body[2+b] + m.one_body[5+c]
                        + m.pairwise[2*b+a] + m.pairwise[6+2*c+a]
                        + m.pairwise[10+3*c+b])
    expected = math.log(math.fsum(math.exp(-e / 3) for e in energies))
    for batch in (1, 3, 8):
        result = enumerate_state(m, domains, 3, batch_size=batch)
        assert result['assignments'] == 4
        assert result['minimum_energy'] == min(energies)
        assert result['log_z'] == pytest.approx(expected, abs=1e-13)


def test_huge_energy_offsets_do_not_underflow_partition():
    result = enumerate_state(matrix((2,), [1e6, 1e6]), [(0, 1)], 1)
    assert result['log_z'] == pytest.approx(-1e6 + math.log(2), abs=1e-9)
    assert result['log_effective_conformations'] == pytest.approx(math.log(2), abs=1e-12)


def test_degeneracy_changes_ensemble_but_not_minimum():
    one = enumerate_state(matrix((1,), [0]), [(0,)], 1)
    two = enumerate_state(matrix((2,), [0, 0]), [(0, 1)], 1)
    wt = dict.fromkeys(['complex', 'protein', 'ligand'], one)
    mutant = {'complex': two, 'protein': one, 'ligand': one}
    scores = relative_scores(mutant, wt)
    assert scores['delta_log_k_ensemble'] == pytest.approx(math.log(2))
    assert scores['delta_log_k_gmec'] == 0
    assert scores['delta_log_k_ensemble_correction'] == pytest.approx(math.log(2))


def test_denominator_sign_and_state_scalar():
    one = enumerate_state(matrix((1,), [0]), [(0,)], 2)
    shifted = enumerate_state(matrix((1,), [0], constant=6), [(0,)], 2)
    wt = dict.fromkeys(['complex', 'protein', 'ligand'], one)
    mutant = {'complex': one, 'protein': shifted, 'ligand': one}
    scores = relative_scores(mutant, wt)
    assert scores['delta_log_k_ensemble'] == 3
    assert scores['delta_log_k_gmec'] == 3
    assert scores['delta_log_k_ensemble_correction'] == 0


def test_relative_score_preserves_multiplicity_under_huge_common_offset():
    free = enumerate_state(matrix((1,), [0]), [(0,)], 1)
    bound_one = enumerate_state(matrix((1,), [0], constant=1e16), [(0,)], 1)
    bound_two = enumerate_state(matrix((2,), [0, 0], constant=1e16), [(0, 1)], 1)
    wild_type = {'complex': bound_one, 'protein': free, 'ligand': free}
    mutant = {'complex': bound_two, 'protein': free, 'ligand': free}
    result = relative_scores(mutant, wild_type)
    assert result['delta_log_k_ensemble'] == pytest.approx(math.log(2), abs=1e-14)
    assert result['delta_log_k_ensemble_correction'] == pytest.approx(math.log(2), abs=1e-14)
    assert result['delta_log_k_gmec'] == 0


@pytest.mark.parametrize('domains,cap', [([()], 2), ([(0, 0)], 2), ([(2,)], 2), ([(0, 1)], 1)])
def test_invalid_domains_and_caps(domains, cap):
    with pytest.raises(ValueError):
        enumerate_state(matrix((2,), [0, 1]), domains, 1, cap=cap)


def test_invalid_temperature_and_energy():
    with pytest.raises(ValueError):
        enumerate_state(matrix((1,), [0]), [(0,)], 0)
    with pytest.raises(ValueError):
        enumerate_state(matrix((1,), [math.inf]), [(0,)], 1)
