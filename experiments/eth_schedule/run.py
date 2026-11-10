"""Check necessary gates in the ETH manuscript's literal parameter schedule."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from math import isqrt, log10
from pathlib import Path
import platform
import time


def ceil_log2(value: int) -> int:
    if value < 1:
        raise ValueError("value must be positive")
    return (value - 1).bit_length()


def ceil_sqrt(value: int) -> int:
    root = isqrt(value)
    return root + (root * root < value)


def parameters(lam: int, beta: int = 1) -> dict:
    if lam < 2 or beta < 1:
        raise ValueError("lambda >= 2 and beta >= 1 are required")
    nu = ceil_log2(lam)
    r = isqrt(lam // nu**4)
    q = lam // (128 * nu)
    degree = (beta + 3) * ceil_sqrt(lam)
    gates = {
        "r_at_least_2": r >= 2,
        "Q_greater_than_R": q > degree,
        "R_at_least_32": degree >= 32,
        "six_R_at_most_Q": 6 * degree <= q,
    }
    return {"lambda": lam, "nu": nu, "beta": beta, "r": r,
            "Q": q, "R": degree, "necessary_gates": gates,
            "all_necessary_gates_pass": all(gates.values())}


def first_r_gate() -> dict:
    certificate = []
    for nu in range(1, 256):
        low, high = (1 << (nu - 1)) + 1, 1 << nu
        candidate = max(low, 4 * nu**4)
        exists = candidate <= high
        certificate.append({"nu": nu, "lambda_low": low,
                            "lambda_high": high,
                            "candidate": candidate if exists else None})
        if exists:
            return {"lambda": candidate, "certificate": certificate}
    raise RuntimeError("search range exhausted")


def first_all_necessary_gates(beta: int) -> dict:
    """Search exact ceil-log intervals; the inequalities reduce to a root interval."""
    if beta < 1:
        raise ValueError("beta must be positive")
    certificate = []
    for nu in range(1, 256):
        low, high = (1 << (nu - 1)) + 1, 1 << nu
        low = max(low, 4 * nu**4)
        coefficient = 128 * nu * 6 * (beta + 3)
        # With t=ceil(sqrt(lambda)), Q>=6R requires lambda>=coefficient*t.
        # Since lambda<=t^2, t>=coefficient is necessary.
        t = max(ceil_sqrt(low), coefficient, (31 // (beta + 3)) + 1)
        candidate = max(low, (t - 1) ** 2 + 1, coefficient * t)
        exists = candidate <= min(high, t * t)
        certificate.append({"nu": nu, "lambda_low_after_r_gate": low,
                            "lambda_high": high, "minimum_root_t": t,
                            "coefficient": coefficient,
                            "candidate": candidate if exists else None})
        if exists:
            record = parameters(candidate, beta)
            if not record["all_necessary_gates_pass"]:
                raise AssertionError("candidate failed necessary gates")
            return {**record, "certificate": certificate,
                    "minimum_N_expression": f"2**{candidate - 1}+1",
                    "approx_log10_minimum_N": (candidate - 1) * log10(2)}
    raise RuntimeError("search range exhausted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    source_path = Path(manifest["source_path"])
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_digest != manifest["source_sha256"]:
        raise ValueError("frozen manuscript source hash mismatch")
    started = time.perf_counter()
    observations = []
    for n in manifest["boolean_variable_counts"]:
        lam = ceil_log2(n)
        observations.append({"N": str(n), **parameters(lam, 1)})
    result = {
        "experiment_id": manifest["experiment_id"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_sha256": source_digest,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "interpretation": "Necessary gates only; not full feasibility, a runtime benchmark, a theorem check, or a lower bound on optimized variants.",
        "observations": observations,
        "first_r_gate": first_r_gate(),
        "first_all_necessary_gates": [first_all_necessary_gates(b) for b in manifest["betas"]],
        "elapsed_seconds": time.perf_counter() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "observations": len(observations)}))


if __name__ == "__main__":
    main()
