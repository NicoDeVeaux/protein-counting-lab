"""Keep zero denominators and unresolved rank boundaries explicit."""

import math

STATES = ("complex", "protein", "ligand")


def number(value):
    result = -math.inf if value in ("-inf", "-Infinity") else float(value)
    if math.isnan(result) or result == math.inf:
        raise ValueError("A score must be finite or negative infinity")
    return result


def score_ratio(logs):
    if not all(state in logs for state in STATES):
        return {"status": "incomplete", "log_k": None}
    c, p, l = (number(logs[state]) for state in STATES)
    if any(math.isnan(value) or value == math.inf for value in (c, p, l)):
        return {"status": "invalid", "log_k": None}
    if p == -math.inf or l == -math.inf:
        return {"status": "undefined_zero_denominator", "log_k": None}
    if c == -math.inf:
        return {"status": "zero_numerator", "log_k": "-inf"}
    return {"status": "finite", "log_k": math.fsum((c, -p, -l))}


def ranking_check(observed, reference, epsilon=3e-8):
    eligible = {key:number(value) for key,value in reference.items()}
    available = {key:number(observed[key]) for key in eligible if key in observed}
    complete = len(available) == len(eligible)
    pairs = {"checked": 0, "wrong": 0, "uncertain_reference": 0, "uncertain_observed": 0}
    keys = sorted(available)
    for index, left in enumerate(keys):
        for right in keys[index+1:]:
            a, b = eligible[left], eligible[right]
            if a == b or (math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 2*epsilon):
                pairs["uncertain_reference"] += 1
                continue
            x, y = available[left], available[right]
            if x == y or (math.isfinite(x) and math.isfinite(y) and abs(x-y) <= 2*epsilon):
                pairs["uncertain_observed"] += 1
                continue
            pairs["checked"] += 1
            pairs["wrong"] += (a > b) != (x > y)
    top = {}
    ordered = sorted(eligible, key=lambda key:eligible[key], reverse=True)
    for k in (1,3,5):
        if k > len(ordered):
            continue
        if not complete:
            top[str(k)] = {"status": "incomplete_panel"}
            continue
        threshold = eligible[ordered[k-1]]
        if math.isfinite(threshold):
            required = {key for key,value in eligible.items() if value > threshold+2*epsilon}
            allowed = {key for key,value in eligible.items() if value >= threshold-2*epsilon}
        else:
            required = {key for key,value in eligible.items() if math.isfinite(value)}
            allowed = set(eligible)
        observed_order = sorted(available, key=lambda key:available[key], reverse=True)
        selected = set(observed_order[:k])
        boundary_uncertain = len(allowed) > k
        observed_uncertain = False
        if k < len(observed_order):
            left, right = (available[key] for key in observed_order[k-1:k+1])
            observed_uncertain = left == right or (math.isfinite(left) and math.isfinite(right) and left-right <= 2*epsilon)
        compatible = required <= selected <= allowed
        status = "compatible_with_reference_envelope" if compatible else "wrong"
        if observed_uncertain and not boundary_uncertain:
            status = "unresolved_observed_boundary"
        top[str(k)] = {"status": status,
                       "boundary_uncertain": boundary_uncertain,
                       "observed_boundary_uncertain": observed_uncertain,
                       "required": sorted(required), "allowed": sorted(allowed), "observed": sorted(selected)}
    return {"eligible_variants": len(eligible), "available_variants": len(available), "full_panel": complete,
            "score_envelope": epsilon, "pairwise": pairs, "top_k": top,
            "assurance": "Tolerance-based ranking compatibility; not a rigorous interval certificate."}
