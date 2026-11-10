#!/usr/bin/env python3
"""Check the cache model and guard mutants with a pinned local TLC jar."""

import argparse
import hashlib
from itertools import product
from pathlib import Path
import re
import subprocess
import tempfile

PIN = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
HERE = Path(__file__).resolve().parent


def expected(identity, generation, revision, nested, prop, workers):
    if prop == "Encloses":
        return identity
    if prop == "MatchingIdentity":
        return identity
    if prop == "Fresh":
        return generation
    if prop == "CurrentRevision":
        return revision or workers == 1
    if prop == "NoWidening":
        return nested or revision or workers == 1
    raise ValueError(prop)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--jar", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.jar.read_bytes()).hexdigest() != PIN:
        raise SystemExit("TLC jar digest differs from pinned v1.7.4")
    rows = []
    with tempfile.TemporaryDirectory(prefix="certified-rank-tlc-") as directory:
        tmp = Path(directory)
        for workers in (2, 1):
            for i, g, r, n in product((False, True), repeat=4):
                for prop in ("Encloses", "MatchingIdentity", "Fresh", "CurrentRevision", "NoWidening"):
                    cfg = tmp / "BoundCache.cfg"
                    cfg.write_text("SPECIFICATION Spec\nCHECK_DEADLOCK FALSE\nCONSTANTS\n"
                                   + f"Workers = 1..{workers}\n"
                                   + f"GuardIdentity = {str(i).upper()}\n"
                                   + f"GuardGeneration = {str(g).upper()}\n"
                                   + f"GuardRevision = {str(r).upper()}\n"
                                   + f"GuardNested = {str(n).upper()}\nINVARIANT {prop}\n")
                    # TLC configs do not accept set expressions: substitute an enumerated set.
                    cfg.write_text(cfg.read_text().replace(f"1..{workers}",
                                   "{" + ",".join(str(i) for i in range(1, workers + 1)) + "}"))
                    result = subprocess.run(
                        ["java", "-Xmx256m", "-XX:+UseParallelGC", f"-Djava.io.tmpdir={tmp}",
                         "-cp", str(args.jar.resolve()), "tlc2.TLC", "-workers", "1",
                         "-metadir", str(tmp / "states"), "-config", str(cfg), "BoundCache"],
                        cwd=HERE, capture_output=True, text=True, timeout=30,
                    )
                    output = result.stdout + result.stderr
                    holds = result.returncode == 0 and "No error has been found" in output
                    violates = (f"Invariant {prop} is violated" in output)
                    want = expected(i, g, r, n, prop, workers)
                    match = holds if want else violates
                    traces = re.findall(r"State \d+: <([^>]+)>", output)
                    states = re.search(r"([\d,]+) distinct states found", output)
                    row = (workers, int(i), int(g), int(r), int(n), prop,
                           "holds" if want else "violates", "holds" if holds else
                           "violates" if violates else "error", states.group(1) if states else "?",
                           "; ".join(traces), match)
                    rows.append(row)
                    print(" ".join(map(str, row[:-1])), flush=True)
                    if not match:
                        print(output[-2500:])
    mismatches = sum(not row[-1] for row in rows)
    if args.report:
        text = "# TLC cache checks\n\nAll 16 guard combinations, 5 properties and 2 worker counts.\n\n"
        text += "| Workers | Identity | Generation | Revision | Nested | Property | Expected | Observed | States | Trace actions |\n"
        text += "|---|---|---|---|---|---|---|---|---|---|\n"
        text += "\n".join("| " + " | ".join(map(str, row[:-1])) + " |" for row in rows)
        text += f"\n\nrows={len(rows)} mismatches={mismatches}\n"
        args.report.write_text(text)
    print(f"rows={len(rows)} mismatches={mismatches}")
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
