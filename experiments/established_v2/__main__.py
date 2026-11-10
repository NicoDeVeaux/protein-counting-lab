from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import resource
import sys
import time

from experiments.inference import load_model
from .pyagrum_adapter import run_pyagrum


def safe_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return "-inf" if value < 0 else "inf"
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description="pyagrum exact inference through conditional marginals; not an ETH implementation")
    parser.add_argument("model", type=Path)
    parser.add_argument("--max-table-bytes", type=int, default=128 * 1024 * 1024)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    loading = time.perf_counter()
    model = load_model(args.model)
    load_seconds = time.perf_counter() - loading
    record = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
              "model_id": model.model_id, "model_sha256": model.source_sha256,
              "kind": model.kind, "variables": len(model.domains), "factors": len(model.factors),
              "state_count": str(model.n_states), "loading_seconds": load_seconds,
              "metadata": dict(model.metadata), "python": platform.python_version(),
              "solver_package_version": importlib.metadata.version("pyagrum")}
    try:
        result = run_pyagrum(model, max_table_bytes=args.max_table_bytes)
    except Exception as error:
        result = {"status": "adapter_error", "method": "pyagrum_conditional_normalizer",
                  "exception": type(error).__name__, "exception_message": str(error)}
    record.update(result)
    for field in ("conversion_seconds", "dependency_import_seconds", "preprocessing_seconds", "kernel_elapsed_seconds"):
        record[field] = result.get("metrics", {}).get(field, 0.0)
    record["adapter_total_seconds"] = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    record["process_peak_rss_bytes"] = int(rss if sys.platform == "darwin" else rss * 1024)
    text = json.dumps(safe_json(record), indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
