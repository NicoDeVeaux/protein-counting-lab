"""Enumerate exact dyadic matrix energies and independent Decimal references."""

import hashlib
import itertools
import json
import math
import platform
import resource
import signal
import time
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from zipfile import ZipFile

from decode_matrix import matrix


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent


def limit(signum, frame):
    raise TimeoutError("Independent reference wall budget exhausted")


def energies(model, domains):
    values = [model["constant"]]
    unary, pairs = [], []
    for i, domain in enumerate(domains):
        row = [model["one_body"][model["one_offsets"][i] + rc] for rc in domain]
        unary.append(row)
        values.extend(row)
    for i in range(len(domains)):
        for j in range(i):
            base = model["pair_offsets"][i * (i - 1) // 2 + j]
            row = [model["pairwise"][base + model["counts"][j] * ri + rj]
                   for ri in domains[i] for rj in domains[j]]
            pairs.append((i, j, len(domains[j]), row))
            values.extend(row)
    assert all(math.isfinite(value) for value in values)
    scale = max(value.as_integer_ratio()[1].bit_length() - 1 for value in values)

    def integer(value):
        numerator, denominator = value.as_integer_ratio()
        return numerator << (scale - (denominator.bit_length() - 1))

    constant = integer(model["constant"])
    unary = [[integer(value) for value in row] for row in unary]
    pairs = [(i, j, width, [integer(value) for value in row]) for i, j, width, row in pairs]
    result = []
    for conf in itertools.product(*(range(len(domain)) for domain in domains)):
        value = constant + sum(row[rc] for row, rc in zip(unary, conf))
        value += sum(row[width * conf[i] + conf[j]] for i, j, width, row in pairs)
        result.append(value)
    return result, 1 << scale


def reference(payload, domains, precision, rt):
    model = matrix(payload)
    numbers, denominator = energies(model, domains)
    minimum = min(numbers)
    with localcontext() as context:
        context.prec = precision
        exponent_denominator = denominator * rt.numerator
        cutoff = 80 * exponent_denominator
        weight_sum = Decimal(0)
        omitted = 0
        for value in numbers:
            scaled_gap = (value - minimum) * rt.denominator
            if scaled_gap >= cutoff:
                omitted += 1
            else:
                weight_sum += (-Decimal(scaled_gap) / Decimal(exponent_denominator)).exp()
        log_effective = weight_sum.ln()
        minimum_over_rt = Decimal(minimum * rt.denominator) / Decimal(exponent_denominator)
        logz = log_effective - minimum_over_rt
        tail_bound = Decimal(omitted) * Decimal(-80).exp().next_plus()
        assert weight_sum >= 1
        assert -Decimal("1e-50") <= log_effective <= Decimal(len(numbers)).ln() + Decimal("1e-50")
        return {
            "precision": precision,
            "cartesian": len(numbers),
            "finite_support": len(numbers),
            "emin_numerator": str(minimum),
            "emin_denominator": str(denominator),
            "emin_decimal": str(Decimal(minimum) / Decimal(denominator)),
            "log_effective_decimal": str(log_effective),
            "logz_decimal": str(logz),
            "exponential_terms_evaluated": len(numbers) - omitted,
            "tail_terms_omitted": omitted,
            "tail_logz_error_upper_bound": str(tail_bound),
            "tail_rule": "Exact integer comparison E-Emin>=80RT; each omitted term<=exp(-80), Zshifted>=1, so log error<=N_omitted*exp(-80).",
        }


def query_scores(rows, rt):
    by = {(row["version"], row["state"]): row["reference"] for row in rows}
    with localcontext() as context:
        context.prec = 90
        results = {}
        for version in ("wild_type", "mutant"):
            energy = Fraction(0)
            correction = Decimal(0)
            for state, sign in (("complex", 1), ("protein", -1), ("ligand", -1)):
                row = by[version, state]
                energy += sign * Fraction(int(row["emin_numerator"]), int(row["emin_denominator"]))
                correction += sign * Decimal(row["log_effective_decimal"])
            value = -energy / rt
            gmec = Decimal(value.numerator) / Decimal(value.denominator)
            results[version] = {"gmec_fraction": value, "gmec": gmec, "correction": correction,
                                "ensemble": gmec + correction}
        delta_gmec = results["mutant"]["gmec_fraction"] - results["wild_type"]["gmec_fraction"]
        delta_gmec = Decimal(delta_gmec.numerator) / Decimal(delta_gmec.denominator)
        delta_correction = results["mutant"]["correction"] - results["wild_type"]["correction"]
        return {"wild_type_ensemble": str(results["wild_type"]["ensemble"]),
                "mutant_ensemble": str(results["mutant"]["ensemble"]),
                "wild_type_gmec": str(results["wild_type"]["gmec"]),
                "mutant_gmec": str(results["mutant"]["gmec"]),
                "delta_gmec": str(delta_gmec), "delta_correction": str(delta_correction),
                "delta_ensemble": str(delta_gmec + delta_correction)}


def main():
    activation_path = ROOT / "prepared/campaign-005/ACTIVATION.json"
    activation_bytes = activation_path.read_bytes()
    activation = json.loads(activation_bytes)
    review = json.loads((OUT / "ACTIVATION_REVIEW-002.json").read_text())
    assert hashlib.sha256(activation_bytes).hexdigest() == review["draft_sha256"]
    plan_path = ROOT / activation["plan"]
    plan = json.loads(plan_path.read_text())
    rt = Fraction.from_float(float.fromhex(activation["rt_hex"]))
    path = OUT / "reference_states.jsonl"
    assert not path.exists()
    started = time.monotonic()
    signal.signal(signal.SIGALRM, limit)
    rows, query_rows, precision_rows = [], [], []
    with ZipFile(ROOT / activation["archive"]) as archive, path.open("x") as journal:
        for query_index, query in enumerate(plan["selected_unique_variants"]):
            group = []
            for slot in query["slots"]:
                current = time.monotonic()
                row = {"variant": query["variant"], "configuration": query["config_member"],
                       "version": slot["version"], "state": slot["state"],
                       "matrix_member": slot["matrix_member"], "domains": slot["domains"]}
                remaining = 600 - (current - started)
                if remaining <= 0:
                    raise TimeoutError("Independent reference total wall budget exhausted")
                signal.setitimer(signal.ITIMER_REAL, min(120, remaining))
                try:
                    payload = archive.read(slot["matrix_member"])
                    assert hashlib.sha256(payload).hexdigest() == slot["matrix_sha256"]
                    row["reference"] = reference(payload, slot["domains"], 90, rt)
                    assert row["reference"]["cartesian"] == slot["assignments"]
                    row["status"] = "ok"
                except Exception as error:
                    row.update({"status": "failed", "error": repr(error)})
                    raise
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    row["wall_seconds"] = time.monotonic() - current
                    row["self_lifetime_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if platform.system() == "Darwin" else 1024)
                    journal.write(json.dumps(row) + "\n")
                    journal.flush()
                rows.append(row)
                group.append(row)
                print(json.dumps({"slots_completed": len(rows), "variant": row["variant"],
                                  "version": row["version"], "state": row["state"],
                                  "wall_seconds": row["wall_seconds"]}), flush=True)
            query_rows.append({"variant": query["variant"], "reference": query_scores(group, rt)})
            if query_index == 0:
                for precision in (60, 90):
                    for slot in query["slots"]:
                        current = time.monotonic()
                        signal.setitimer(signal.ITIMER_REAL, 120)
                        try:
                            value = reference(archive.read(slot["matrix_member"]), slot["domains"], precision, rt)
                        finally:
                            signal.setitimer(signal.ITIMER_REAL, 0)
                        precision_rows.append({"variant": query["variant"], "version": slot["version"],
                                               "state": slot["state"], "precision": precision,
                                               "reference": value, "wall_seconds": time.monotonic() - current})
    result = {"activation_sha256": hashlib.sha256(activation_bytes).hexdigest(),
              "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
              "completed_at_utc": datetime.now(timezone.utc).isoformat(),
              "method": "Independent raw Java decoder; exact integer-scaled dyadic energies; Decimal90 reference, explicit80RT tail bound; no experiment imports.",
              "rt_numerator": str(rt.numerator), "rt_denominator": str(rt.denominator),
              "state_slots": len(rows), "query_slots": len(query_rows),
              "wall_seconds": time.monotonic() - started,
              "state_rows_path": str(path.relative_to(ROOT)),
              "precision_checks": precision_rows, "query_references": query_rows,
              "worker_scores_read_before_references": False}
    (OUT / "references.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"complete": True, "state_slots": len(rows), "query_slots": len(query_rows),
                      "wall_seconds": result["wall_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
