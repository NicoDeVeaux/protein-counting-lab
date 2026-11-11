"""Build the unchanged proved checker once; time native verification separately."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from experiments.partition_certificate7.core import check_binding
from experiments.partition_certificate7.verify import Verification


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "formal/campaign-007/lean"
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
LAKEFILE = '''name = "campaign8_checker"
version = "0.1.0"
defaultTargets = ["checker8"]

[[lean_lib]]
name = "PartitionCertificate"

[[lean_exe]]
name = "checker8"
root = "Main"
'''


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _run(command, directory, timeout=180):
    result = subprocess.run(command, cwd=directory, capture_output=True, text=True,
                            timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result


def build_checker(build_dir):
    """Use a fresh local directory; executable paths are runtime-only metadata."""
    start = time.perf_counter()
    directory = Path(build_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError("native checker build directory must be empty")
    source_sha256 = {}
    for name in ("PartitionCertificate.lean", "Main.lean", "lean-toolchain"):
        data = (SOURCE / name).read_bytes()
        (directory / name).write_bytes(data)
        source_sha256[(SOURCE / name).relative_to(ROOT).as_posix()] = _sha(data)
    (directory / "lakefile.toml").write_text(LAKEFILE)
    toolchain = _run(["lean", "--version"], directory).stdout.strip()
    if "version 4.35.0," not in toolchain:
        raise RuntimeError("expected the pinned Lean 4.35.0 toolchain")
    audit_start = time.perf_counter()
    proof = _run(["lean", "PartitionCertificate.lean"], directory).stdout
    expected = [f"'PartitionCertificate.{name}' depends on axioms: {axioms}"
                for name, axioms in AXIOMS.items()]
    if proof.splitlines() != expected:
        raise RuntimeError("missing or unexpected native checker proof audit: " + proof)
    audit_seconds = time.perf_counter() - audit_start
    compile_start = time.perf_counter()
    _run(["lake", "build", "checker8"], directory)
    compile_seconds = time.perf_counter() - compile_start
    executable = directory / ".lake/build/bin/checker8"
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise RuntimeError("native checker executable was not built")
    for name in ("PartitionCertificate.lean", "Main.lean", "lean-toolchain"):
        original = (SOURCE / name).read_bytes()
        if (directory / name).read_bytes() != original:
            raise RuntimeError("native build source differs from original: " + name)
    binary = executable.read_bytes()
    binary_sha256 = _sha(binary)
    return {"executable": str(executable), "executable_name": executable.name,
            "build_seconds": time.perf_counter() - start,
            "audit_seconds": audit_seconds, "compile_seconds": compile_seconds,
            "source_sha256": source_sha256, "binary_sha256": binary_sha256,
            "binary_bytes": len(binary), "toolchain": toolchain,
            "proof_report": proof, "lakefile_sha256": _sha(LAKEFILE.encode())}


def check_lines(executable, lines, timeout=60):
    """Run one native process; include its startup, parsing and checking in timing."""
    lines = list(lines)
    if not lines:
        return []
    if any("\n" in line or "\r" in line for line in lines):
        raise ValueError("each request must occupy exactly one line")
    result = subprocess.run([str(executable)], input="\n".join(lines) + "\n",
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    outputs = result.stdout.splitlines()
    if len(outputs) != len(lines):
        raise RuntimeError("native checker response count differs from input count")
    replies = []
    for output in outputs:
        fields = output.split()
        if fields in (["invalid"], ["rejected"]):
            replies.append(Verification(fields[0]))
        elif (len(fields) == 3 and fields[0] == "accepted"
              and all(value.isdecimal() for value in fields[1:])):
            lower, upper = map(int, fields[1:])
            if lower > upper:
                raise RuntimeError("native checker returned reversed endpoints")
            replies.append(Verification("accepted", lower, upper))
        else:
            raise RuntimeError("unexpected native checker output: " + output)
    return replies


def check_certificates(executable, requests, timeout=60):
    """Bind complete models and invoke an already built native checker."""
    requests = list(requests)
    indices = [i for i, (model, cert) in enumerate(requests) if check_binding(model, cert)]
    replies = [Verification("binding_mismatch") for _ in requests]
    lines = (json.dumps(requests[i][1], separators=(",", ":"), allow_nan=False)
             for i in indices)
    checked = check_lines(executable, lines, timeout)
    for index, reply in zip(indices, checked):
        certificate = requests[index][1]
        if (reply.status == "accepted"
                and (reply.lower, reply.upper) != (certificate["lower"], certificate["upper"])):
            raise RuntimeError("native checker accepted different endpoints")
        replies[index] = reply
    return replies
