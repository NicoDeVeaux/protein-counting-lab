#!/usr/bin/env python3
"""Compile proofs, audit axioms, and exercise the compiled Lean certificate checker."""

import argparse
import csv
import itertools
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
THEOREMS = (
    "check_sound", "add_sound", "mul_sound", "sum_sound", "product_sound",
    "three_state_sound", "three_state_rank_sound", "repeated_bounds",
)


def expected(row):
    anl, anu, adl, adu, bnl, bnu, bdl, bdu = row
    return (
        0 <= anl <= anu and 0 < adl <= adu
        and 0 <= bnl <= bnu and 0 < bdl <= bdu
        and anl * bdl > bnu * adu
    )


def run(args, **kwargs):
    return subprocess.run(args, cwd=HERE, text=True, capture_output=True,
                          timeout=60, **kwargs)


def assert_ok(result):
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--certificates", type=Path,
                        help="Additional rows: eight whitespace-separated naturals.")
    parser.add_argument("--witness-csv", type=Path,
                        help="Controller WITNESSES.csv with named endpoint columns.")
    args = parser.parse_args()
    version = run(["lean", "--version"])
    assert_ok(version)
    if "version 4.35.0," not in version.stdout:
        raise RuntimeError("Expected the pinned Lean 4.35.0 toolchain")

    with tempfile.TemporaryDirectory(prefix="rank6-lean-") as temp:
        build = run(["lean", "-o", f"{temp}/Certificate.olean", "Certificate.lean"])
        assert_ok(build)
        if "sorryAx" in build.stdout or "Lean.ofReduceBool" in build.stdout:
            raise RuntimeError("Forbidden proof axiom")
        reports = []
        for theorem in THEOREMS:
            suffix = (" depends on axioms: [propext, Quot.sound]"
                      if theorem == "repeated_bounds"
                      else " does not depend on any axioms")
            reports.append(f"'CertifiedRank.{theorem}'{suffix}")
        if build.stdout.splitlines() != reports:
            raise RuntimeError("Missing or unexpected proof axiom report")

        rows = list(itertools.product(range(3), repeat=8))
        rng = random.Random(6006)
        for _ in range(1000):
            row = []
            for pair in range(4):
                x, y = rng.getrandbits(256), rng.getrandbits(256)
                row.extend(sorted((x, y)))
            rows.append(tuple(row))
        # Overflow, exact equality, one-unit gaps, inverted endpoints, zero denominators.
        big = 10 ** 100
        rows.extend([
            (big + 1, big + 1, big, big, big, big, big, big),
            (big, big, big, big, big, big, big, big),
            (4, 4, 1, 1, 2, 2, 1, 1),
            (4, 3, 1, 1, 2, 2, 1, 1),
            (4, 4, 0, 1, 2, 2, 1, 1),
        ])
        if args.certificates:
            for line in args.certificates.read_text().splitlines():
                values = tuple(map(int, line.split()))
                if len(values) != 8 or min(values) < 0:
                    raise ValueError("Certificate rows require eight naturals")
                rows.append(values)
        if args.witness_csv:
            with args.witness_csv.open(newline="") as stream:
                for row in csv.DictReader(stream):
                    rows.append(tuple(int(row[k]) for k in (
                        "aNL", "aNU", "aDL", "aDU", "bNL", "bNU", "bDL", "bDU")))

        sys.path.insert(0, str(HERE.parents[2]))
        from experiments.certified_rank6.core import RatioBounds, certificate_gt
        for index, row in enumerate(rows):
            actual = certificate_gt(RatioBounds(*row[:4]), RatioBounds(*row[4:]))
            if actual != expected(row):
                raise RuntimeError(f"Python checker disagreement at row {index}")

        invalid = ["", "1 2", "-1 2 1 2 1 2 1 2", "x 2 1 2 1 2 1 2"]
        payload = "\n".join(" ".join(map(str, row)) for row in rows)
        payload += "\n" + "\n".join(invalid) + "\n"
        checked = run(["lean", "--run", "Main.lean"], input=payload,
                      env={**os.environ, "LEAN_PATH": temp})
        assert_ok(checked)
        answers = checked.stdout.splitlines()
        want = ["accepted" if expected(row) else "rejected" for row in rows]
        want.extend(["invalid"] * len(invalid))
        if answers != want:
            mismatch = next((i for i, (a, b) in enumerate(zip(answers, want))
                             if a != b), min(len(answers), len(want)))
            raise RuntimeError(f"Lean checker disagreement at row {mismatch}")

        source = (HERE / "Certificate.lean").read_text()
        before = "b.numerator.hi * a.denominator.hi < a.numerator.lo * b.denominator.lo"
        if source.count(before) != 1:
            raise RuntimeError("Mutation target changed")
        mutant = Path(temp) / "Mutant.lean"
        mutant.write_text(source.replace(before, before.replace(" < ", " ≤ ")))
        failed = run(["lean", str(mutant)])
        if failed.returncode == 0 or "error:" not in failed.stdout:
            raise RuntimeError("Non-strict certificate mutant did not break proof")

    print(version.stdout.strip())
    print(build.stdout.strip())
    print(f"checker_rows={len(rows)} accepted_rows={sum(map(expected, rows))} "
          f"malformed_rows={len(invalid)} lean_python_disagreements=0 "
          "nonstrict_mutant=proof_failure")


if __name__ == "__main__":
    main()
