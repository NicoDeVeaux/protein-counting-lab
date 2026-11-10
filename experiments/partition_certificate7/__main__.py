"""Generate and check one small certificate without historical datasets."""

import argparse
import json

from experiments.certified_rank6.fixtures import CASE_NAMES, make_case
from .core import build_certificate
from .verify import LeanVerifier


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--case", choices=CASE_NAMES, default="concentrated8")
    parser.add_argument("--candidate", choices=("A", "B", "C"), default="A")
    parser.add_argument("--state", choices=("complex", "protein", "ligand"), default="complex")
    parser.add_argument("--expansions", type=int, default=16)
    args = parser.parse_args()
    candidate = next(c for c in make_case(args.case) if c.name == args.candidate)
    model = getattr(candidate, args.state)
    certificate = build_certificate(model, args.expansions)
    with LeanVerifier() as verifier:
        result, = verifier.verify_batch([(model, certificate)])
    print(json.dumps({"case": args.case, "candidate": args.candidate, "state": args.state,
                      "status": result.status, "lower": result.lower, "upper": result.upper,
                      "certificate_bytes": len(json.dumps(certificate, separators=(",", ":")).encode())}))
    if result.status != "accepted":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
