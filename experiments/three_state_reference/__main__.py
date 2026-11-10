"""Run the frozen independent reference for every source-ordered panel label."""

import argparse
import json
import time
from pathlib import Path

from .core import ReferenceLimits, load_archive, reference_panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-assignments", type=int, default=1_000_000)
    parser.add_argument("--state-seconds", type=float, default=60)
    parser.add_argument("--total-seconds", type=float, default=300)
    parser.add_argument("--memory-mib", type=int, default=512)
    parser.add_argument("--scalar-owners", type=Path, help="JSON map of source factor ID to explicit state owner")
    args = parser.parse_args()
    limits = ReferenceLimits(args.max_assignments, args.state_seconds, args.total_seconds, args.memory_mib)
    if min(vars(limits).values()) <= 0:
        parser.error("all resource limits must be positive")
    started = time.perf_counter()
    scalar_owners = {int(k): v for k, v in json.loads(args.scalar_owners.read_text()).items()} if args.scalar_owners else None
    archive = load_archive(args.archive)
    result = reference_panel(archive, limits, scalar_owners, started_monotonic=started)
    result["command"] = __import__("sys").argv
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
