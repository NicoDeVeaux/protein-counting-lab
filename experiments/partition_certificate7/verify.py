"""Bind model inputs, compile the proved checker, and verify certificate batches."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .core import check_binding


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "formal/campaign-007/lean"
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


@dataclass(frozen=True)
class Verification:
    status: str
    lower: int | None = None
    upper: int | None = None


class LeanVerifier:
    """Keep one audited proof build for multiple JSON-line verification batches."""

    def __enter__(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="partition7-lean-")
        self.env = {**os.environ, "LEAN_PATH": self._temporary.name}
        try:
            version = self._run(["lean", "--version"])
            if "version 4.35.0," not in version:
                raise RuntimeError("expected the pinned Lean 4.35.0 toolchain")
            self.axiom_report = self._run(
                ["lean", "-o", str(Path(self._temporary.name) / "PartitionCertificate.olean"),
                 "PartitionCertificate.lean"])
            if ("sorry" in self.axiom_report or "Lean.ofReduceBool" in self.axiom_report
                    or "PartitionCertificate.check_sound" not in self.axiom_report):
                raise RuntimeError("missing or forbidden checker proof report")
            for report in re.findall(r"depends on axioms: \[([^\]]*)\]", self.axiom_report):
                axioms = {name.strip() for name in report.split(",") if name.strip()}
                if not axioms <= STANDARD_AXIOMS:
                    raise RuntimeError("unexpected checker proof axioms")
        except BaseException:
            self._temporary.cleanup()
            raise
        return self

    def __exit__(self, *_):
        self._temporary.cleanup()

    def _run(self, command, input=None):
        result = subprocess.run(command, cwd=PROJECT, env=self.env, input=input,
                                text=True, capture_output=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout

    def raw_lines(self, lines):
        """Exercise the actual Lean decoder, including deliberately invalid input."""
        lines = list(lines)
        if not lines:
            return []
        if any("\n" in line or "\r" in line for line in lines):
            raise ValueError("each request must occupy exactly one line")
        output = self._run(["lean", "--run", "Main.lean"], input="\n".join(lines) + "\n")
        responses = output.splitlines()
        if len(responses) != len(lines):
            raise RuntimeError("Lean response count differs from request count")
        replies = []
        for response in responses:
            fields = response.split()
            if fields in (["rejected"], ["invalid"]):
                replies.append(Verification(fields[0]))
            elif (len(fields) == 3 and fields[0] == "accepted"
                  and all(field.isdecimal() for field in fields[1:])):
                lower, upper = map(int, fields[1:])
                if lower > upper:
                    raise RuntimeError("Lean returned reversed accepted endpoints")
                replies.append(Verification("accepted", lower, upper))
            else:
                raise RuntimeError("unexpected Lean checker response: " + response)
        return replies

    def raw_batch(self, certificates):
        return self.raw_lines(json.dumps(c, separators=(",", ":"), allow_nan=False)
                              for c in certificates)

    def verify_batch(self, requests):
        """Require the independent caller-supplied model before asking Lean."""
        requests = list(requests)
        indices = [i for i, (model, cert) in enumerate(requests) if check_binding(model, cert)]
        replies = [Verification("binding_mismatch") for _ in requests]
        checked = self.raw_batch(requests[i][1] for i in indices)
        for index, reply in zip(indices, checked):
            cert = requests[index][1]
            if reply.status == "accepted" and (reply.lower, reply.upper) != (cert["lower"], cert["upper"]):
                raise RuntimeError("accepted endpoints differ from submitted claim")
            replies[index] = reply
        return replies
