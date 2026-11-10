#!/usr/bin/env python3
"""Compile the partition proof, audit axioms and exercise its executable checker."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
AXIOMS = {
    "factor_bounds_sound": "[propext]",
    "model_bounds_sound": "[propext]",
    "compatible_parent": "[propext, Quot.sound]",
    "uniform_mass_bounds": "[propext, Quot.sound]",
    "leaf_bounds_sound": "[propext, Quot.sound]",
    "cut_bounds_sound": "[propext, Quot.sound]",
    "valid_factor_eval_congr": "[propext]",
    "valid_model_eval_congr": "[propext, Quot.sound]",
    "check_model_valid": "[propext]",
    "check_sound": "[propext, Quot.sound]",
    "checked_greater_sound": "[propext, Quot.sound]",
}


def run(command, **kwargs):
    return subprocess.run(command, cwd=HERE, text=True, capture_output=True,
                          timeout=60, **kwargs)


def require_success(result):
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--certificates", type=Path,
                        help="Additional valid JSON-lines exports; every row must be accepted.")
    args = parser.parse_args()
    version = run(["lean", "--version"])
    require_success(version)
    if "version 4.35.0," not in version.stdout:
        raise RuntimeError("Expected the pinned Lean 4.35.0 toolchain")

    c = lambda value: ["c", value]
    b = lambda index, left, right: ["b", index, left, right]
    basic = b(0, c(2), c(5))
    cases = []

    def case(n, factors, cut, lower, upper, accepted=True):
        row = {"n": n, "factors": factors, "cut": cut, "lower": lower, "upper": upper}
        cases.append((json.dumps(row), f"accepted {lower} {upper}" if accepted else "rejected"))

    case(0, [], 0, 1, 1)
    case(3, [], 0, 8, 8)
    case(1, [basic], 0, 4, 10)
    case(1, [basic], [0, 0], 7, 7)
    case(1, [basic], 0, 5, 10, False)
    case(1, [basic], [0, 0], 7, 8, False)
    case(0, [], [0, 0], 1, 1, False)
    case(0, [basic], 0, 2, 5, False)
    case(1, [basic], [[0, 0], 0], 7, 7, False)
    case(3, [b(1, c(4), c(6))], 0, 32, 48)
    case(3, [b(1, c(4), c(6))], [0, 0], 32, 48)
    case(3, [b(1, c(4), c(6))], [[0, 0], [0, 0]], 40, 40)
    case(1, [basic, b(0, c(3), c(7))], 0, 12, 70)
    case(1, [basic, b(0, c(3), c(7))], [0, 0], 41, 41)
    case(1, [b(0, c(3), b(0, c(0), c(7)))], 0, 0, 14)
    case(1, [b(0, c(3), b(0, c(0), c(7)))], [0, 0], 10, 10)
    case(200, [c(0)], 0, 0, 0)
    case(3, [c(10 ** 100)], 0, 8 * 10 ** 100, 8 * 10 ** 100)
    malformed = ["", "not json", "{}", "[]", '{"n":1} trailing']
    bad = {"n": 1, "factors": [basic], "cut": [0], "lower": 7, "upper": 7}
    malformed.append(json.dumps(bad))
    bad = {"n": -1, "factors": [], "cut": 0, "lower": 0, "upper": 0}
    malformed.append(json.dumps(bad))
    bad = {"n": 1, "factors": [["c", -1]], "cut": 0, "lower": 0, "upper": 0}
    malformed.append(json.dumps(bad))
    bad = {"n": 1, "factors": [], "cut": 0, "lower": 2, "upper": 2, "extra": 0}
    malformed.append(json.dumps(bad))
    cases.extend((row, "invalid") for row in malformed)
    if args.certificates:
        for line in args.certificates.read_text().splitlines():
            row = json.loads(line)
            cases.append((line, f"accepted {row['lower']} {row['upper']}"))

    with tempfile.TemporaryDirectory(prefix="partition7-proof-") as directory:
        build = run(["lean", "-o", directory + "/PartitionCertificate.olean",
                     "PartitionCertificate.lean"])
        require_success(build)
        expected = [f"'PartitionCertificate.{name}' depends on axioms: {axioms}"
                    for name, axioms in AXIOMS.items()]
        if build.stdout.splitlines() != expected:
            raise RuntimeError("Missing or unexpected axiom report: " + build.stdout)
        checked = run(["lean", "--run", "Main.lean"],
                      input="\n".join(line for line, _ in cases) + "\n",
                      env={**os.environ, "LEAN_PATH": directory})
        require_success(checked)
        answers = checked.stdout.splitlines()
        if answers != [expected for _, expected in cases]:
            raise RuntimeError("Executable certificate mismatch: " + checked.stdout)

        rank_probe = Path(directory) / "RankProbe.lean"
        rank_probe.write_text('''import PartitionCertificate
open PartitionCertificate
def scalar (weight : Nat) : State :=
  ⟨0, [.constant weight], .leaf, ⟨weight, weight⟩⟩
def forged : State := ⟨0, [.constant 1], .leaf, ⟨2, 2⟩⟩
def missing : State := ⟨0, [.constant 2], .split .leaf .leaf, ⟨2, 2⟩⟩
def main : IO Unit := do
  IO.println (checkedGreater (scalar 2) (scalar 1) (scalar 1)
    (scalar 1) (scalar 1) (scalar 1))
  IO.println (checkedGreater (scalar 1) (scalar 1) (scalar 1)
    (scalar 1) (scalar 1) (scalar 1))
  IO.println (checkedGreater (scalar 2) (scalar 0) (scalar 1)
    (scalar 1) (scalar 1) (scalar 1))
  IO.println (checkedGreater forged (scalar 1) (scalar 1)
    (scalar 1) (scalar 1) (scalar 1))
  IO.println (checkedGreater missing (scalar 1) (scalar 1)
    (scalar 1) (scalar 1) (scalar 1))
  IO.println (checkedGreater (scalar 1) (scalar 1) (scalar 1)
    (scalar 0) (scalar 1) (scalar 1))
''')
        ranked = run(["lean", "--run", str(rank_probe)],
                     env={**os.environ, "LEAN_PATH": directory})
        require_success(ranked)
        if ranked.stdout.splitlines() != ["true", "false", "false", "false", "false", "true"]:
            raise RuntimeError("Composed rank checker mismatch: " + ranked.stdout)

        source = (HERE / "PartitionCertificate.lean").read_text()
        mutants = {
            "omitted-completion-count": (
                "⟨bounds.lo * 2 ^ remaining, bounds.hi * 2 ^ remaining⟩",
                "⟨bounds.lo, bounds.hi⟩"),
            "omitted-right-branch": (
                "pure ⟨a.lo + b.lo, a.hi + b.hi⟩", "pure a"),
            "minimum-as-upper-bound": (
                "⟨min a.lo b.lo, max a.hi b.hi⟩", "⟨min a.lo b.lo, min a.hi b.hi⟩"),
        }
        for name, (before, after) in mutants.items():
            if source.count(before) != 1:
                raise RuntimeError("Mutation target changed: " + name)
            path = Path(directory) / "Mutant.lean"
            path.write_text(source.replace(before, after))
            broken = run(["lean", str(path)])
            if broken.returncode == 0:
                raise RuntimeError("Unsound proof mutant compiled: " + name)

    print(f"theorems={len(AXIOMS)} checker_rows={len(cases)} "
          f"malformed_rows={len(malformed)} rank_rows=6 proof_mutants={len(mutants)} disagreements=0")


if __name__ == "__main__":
    main()
