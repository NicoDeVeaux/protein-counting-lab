"""Pinned native Ganak baseline; exact integer arithmetic and deterministic cache."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess
import time


VERSION = "2.9.0"
BINARY_SHA256 = "50de92712514b9655065cb6fe3a0fdc759f6ba2bb94c109f7fd3dc6107d030b2"
FLAGS = ("--mode", "0", "--prob", "0", "--threads", "1", "--seed", "8008",
         "--verb", "0", "--arjunverb", "0", "--fast")


def verify_binary(binary):
    """Run before measurement; never silently substitute another executable."""
    actual = hashlib.sha256(Path(binary).read_bytes()).hexdigest()
    if actual != BINARY_SHA256:
        raise ValueError("Ganak executable differs from the pinned native ARM release")
    return actual


def parse_output(stdout):
    """Reject approximate, projected, ambiguous or non-deterministic output."""
    counts = re.findall(r"^c s exact arb int ([0-9]+)\s*$", stdout, re.MULTILINE)
    guarantees = re.findall(r"^c s pac guarantees epsilon: (\S+) delta: (\S+)\s*$",
                            stdout, re.MULTILINE)
    kinds = re.findall(r"^c s type (\S+)\s*$", stdout, re.MULTILINE)
    statuses = re.findall(r"^s (SATISFIABLE|UNSATISFIABLE)\s*$", stdout, re.MULTILINE)
    if len(counts) != 1 or guarantees != [("0", "0")] or kinds != ["mc"] or len(statuses) != 1:
        raise ValueError("missing or ineligible Ganak exact/deterministic result")
    count = int(counts[0])
    if (statuses[0] == "UNSATISFIABLE") != (count == 0):
        raise ValueError("Ganak satisfiability status conflicts with its integer count")
    return count


def _text(value):
    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""


def count_file(binary, path, timeout_seconds=10.0):
    """Charge process startup, native parsing/preprocessing/solve and output decoding."""
    if timeout_seconds <= 0:
        return {"status": "timeout", "seconds": 0.0, "count": None}
    start = time.perf_counter()
    try:
        result = subprocess.run([str(binary), *FLAGS, str(path)], capture_output=True,
                                text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as failure:
        return {"status": "timeout", "count": None,
                "seconds": time.perf_counter() - start,
                "stdout": _text(failure.stdout), "stderr": _text(failure.stderr)}
    record = {"status": "error", "count": None, "returncode": result.returncode,
              "stdout": result.stdout, "stderr": result.stderr}
    if result.returncode == 0:
        try:
            record["count"] = str(parse_output(result.stdout))
            record["status"] = "exact"
        except ValueError as failure:
            record["error"] = str(failure)
    record["seconds"] = time.perf_counter() - start
    return record


def count_query(binary, paths, timeout_seconds=10.0):
    """Solve both members under one total budget without reference-answer reuse."""
    paths = list(paths)
    if len(paths) != 2:
        raise ValueError("a probability-ordering query needs exactly two CNFs")
    start = time.perf_counter()
    members = []
    for path in paths:
        remaining = timeout_seconds - (time.perf_counter() - start)
        record = count_file(binary, path, remaining)
        members.append(record)
        if record["status"] != "exact":
            return {"status": record["status"], "counts": None, "members": members,
                    "seconds": time.perf_counter() - start}
    return {"status": "exact", "counts": [record["count"] for record in members],
            "members": members, "seconds": time.perf_counter() - start}
