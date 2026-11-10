"""Enumerate a fixed rigid energy model without evaluating molecular geometry."""

import math

import numpy as np


def enumerate_state(matrix, domains, rt, *, cap=1_000_000, batch_size=8192):
    """Return a partition log and minimum energy for explicit conformer domains."""
    if len(domains) != len(matrix.domains):
        raise ValueError('Position count mismatch')
    domains = tuple(tuple(d) for d in domains)
    for domain, size in zip(domains, matrix.domains):
        if not domain or len(set(domain)) != len(domain):
            raise ValueError('Empty or repeated conformer domain')
        if any(not isinstance(rc, int) or not 0 <= rc < size for rc in domain):
            raise ValueError('Conformer outside source domain')
    rt = np.longdouble(str(rt))
    if not np.isfinite(rt) or rt <= 0:
        raise ValueError('RT must be finite and positive')
    if batch_size < 1:
        raise ValueError('Batch size must be positive')
    count = math.prod(map(len, domains))
    if count > cap:
        raise ValueError('State Cartesian assignment cap exceeded')
    singles = np.asarray(matrix.one_body, dtype=np.longdouble)
    pairs = np.asarray(matrix.pairwise, dtype=np.longdouble)
    constant = np.longdouble(matrix.constant)
    if not (np.all(np.isfinite(singles)) and np.all(np.isfinite(pairs))
            and np.isfinite(constant)):
        raise ValueError('Nonfinite energy input')
    arrays = [np.asarray(d, dtype=np.int64) for d in domains]
    shifted_log_sum = np.longdouble(-np.inf)
    minimum = np.longdouble(np.inf)
    underflow_terms = 0
    for start in range(0, count, batch_size):
        indexes = np.arange(start, min(start + batch_size, count), dtype=np.int64)
        assignments = []
        for domain in reversed(arrays):
            assignments.append(domain[indexes % len(domain)])
            indexes //= len(domain)
        assignments.reverse()
        energy = np.full(len(assignments[0]), constant, dtype=np.longdouble)
        for pos, rc in enumerate(assignments):
            energy += singles[matrix.one_body_offsets[pos] + rc]
            for prior in range(pos):
                pair_index = pos * (pos - 1) // 2 + prior
                offset = (matrix.pairwise_offsets[pair_index]
                          + matrix.domains[prior] * rc + assignments[prior])
                energy += pairs[offset]
        batch_minimum = np.min(energy)
        logs = -(energy - batch_minimum) / rt
        with np.errstate(under='ignore'):
            weights = np.exp(logs)
        underflow_terms += int(np.count_nonzero(weights == 0))
        batch_log_sum = np.log(np.sum(weights, dtype=np.longdouble))
        if batch_minimum < minimum:
            shifted_log_sum -= (minimum - batch_minimum) / rt
            minimum = batch_minimum
        else:
            batch_log_sum -= (batch_minimum - minimum) / rt
        shifted_log_sum = np.logaddexp(shifted_log_sum, batch_log_sum)
    log_z = shifted_log_sum - minimum / rt
    return {'assignments': count, 'log_z': float(log_z),
            'minimum_energy': float(minimum), 'gmec_log_weight': float(-minimum / rt),
            'log_effective_conformations': float(shifted_log_sum),
            'batch_exp_underflows': underflow_terms,
            'longdouble_mantissa_bits': int(np.finfo(np.longdouble).nmant)}


def binding_score(states, key):
    if set(states) != {'complex', 'protein', 'ligand'}:
        raise ValueError('Expected complete three-state result')
    values = [float(states[s][key]) for s in ('complex', 'protein', 'ligand')]
    if not all(math.isfinite(x) for x in values):
        raise ValueError('Nonfinite partition or minimum-energy score')
    return math.fsum((values[0], -values[1], -values[2]))


def relative_scores(mutant, wild_type):
    if set(mutant) != {'complex', 'protein', 'ligand'} or set(wild_type) != set(mutant):
        raise ValueError('Expected complete WT and mutant three-state results')
    signs = {'complex': 1, 'protein': -1, 'ligand': -1}
    gmec = math.fsum(version_sign * sign * states[state]['gmec_log_weight']
                     for states, version_sign in ((mutant, 1), (wild_type, -1))
                     for state, sign in signs.items())
    correction = math.fsum(version_sign * sign * states[state]['log_effective_conformations']
                           for states, version_sign in ((mutant, 1), (wild_type, -1))
                           for state, sign in signs.items())
    ensemble = math.fsum((gmec, correction))
    if not all(math.isfinite(x) for x in (gmec, correction, ensemble)):
        raise ValueError('Nonfinite relative score')
    return {'delta_log_k_ensemble': ensemble, 'delta_log_k_gmec': gmec,
            'delta_log_k_ensemble_correction': correction}
