from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import resource
import sys
import time

from .core import InferenceLimit, batched_brute_force, bounded_mass, brute_force, load_model, variable_elimination


def safe_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "nan"
        return "-inf" if value < 0 else "inf"
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description="Conventional partition inference; not an ETH implementation")
    parser.add_argument("model", type=Path)
    parser.add_argument("--method", choices=["eliminate", "brute", "batch", "bounded"], default="eliminate")
    parser.add_argument("--order", choices=["natural", "min-fill", "min-weight"], default="min-fill")
    parser.add_argument("--max-table-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--max-states", type=int, default=1_000_000)
    parser.add_argument("--batch-states", type=int, default=65_536)
    parser.add_argument("--max-batch-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--epsilon", type=float, default=0.1)
    parser.add_argument("--max-nodes", type=int, default=100_000)
    parser.add_argument("--max-frontier-nodes", type=int, default=100_000)
    parser.add_argument("--time-limit-seconds", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-higher-arity", action="store_true")
    args = parser.parse_args()
    load_start = time.perf_counter()
    model = load_model(args.model, allow_higher_arity=args.allow_higher_arity)
    loading_seconds = time.perf_counter() - load_start
    record = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "model_id": model.model_id, "model_sha256": model.source_sha256,
        "kind": model.kind, "variables": len(model.domains), "factors": len(model.factors),
        "state_count": str(model.n_states), "metadata": dict(model.metadata),
        "loading_seconds": loading_seconds,
    }
    try:
        if args.method == "eliminate":
            result = variable_elimination(model, order=args.order, max_table_bytes=args.max_table_bytes,
                                          time_limit_seconds=args.time_limit_seconds)
        elif args.method == "brute":
            result = brute_force(model, max_states=args.max_states, time_limit_seconds=args.time_limit_seconds)
        elif args.method == "batch":
            result = batched_brute_force(model, max_states=args.max_states, batch_states=args.batch_states,
                                         max_batch_bytes=args.max_batch_bytes,
                                         time_limit_seconds=args.time_limit_seconds)
        else:
            result = bounded_mass(model, epsilon=args.epsilon, max_nodes=args.max_nodes,
                                  max_frontier_nodes=args.max_frontier_nodes,
                                  time_limit_seconds=args.time_limit_seconds)
    except InferenceLimit as exc:
        result = {"status": exc.reason, "method": args.method, "metrics": exc.metrics}
    except ArithmeticError as exc:
        result = {"status": "numerical_failure", "method": args.method,
                  "error": str(exc), "error_type": type(exc).__name__}
    record.update(result)
    record["kernel_elapsed_seconds"] = result.get("metrics", {}).get("elapsed_seconds")
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    record["process_peak_rss_bytes"] = int(rss if sys.platform == "darwin" else rss * 1024)
    record["peak_rss_scope"] = "current Python process, including loading and libraries"
    text = json.dumps(safe_json(record), indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
