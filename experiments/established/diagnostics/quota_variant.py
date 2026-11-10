"""Post hoc scheduler-unit diagnostic; do not replace campaign results."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import resource
import sys
import time
import traceback

import psutil
import pyagrum as gum

from experiments.established.pyagrum_adapter import run_pyagrum
from experiments.inference import load_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--quota", choices=["as-written", "default", "128", "1024"], required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    events = []
    original = gum.ShaferShenoyMRFInference

    class TracedEngine:
        def __init__(self, mrf):
            self.engine = original(mrf)

        def __getattr__(self, name):
            target = getattr(self.engine, name)
            if name not in ("junctionTree", "makeInference", "posterior"):
                return target

            def traced(*values):
                events.append({"phase": name, "event": "start", "rss": psutil.Process().memory_info().rss})
                result = target(*values)
                events.append({"phase": name, "event": "complete", "rss": psutil.Process().memory_info().rss})
                return result
            return traced

        def setMaxMemory(self, value):
            forwarded = value if args.quota == "as-written" else None if args.quota == "default" else int(args.quota)
            events.append({"phase": "setMaxMemory", "wrapper_requested": value, "forwarded": forwarded})
            if forwarded is not None:
                self.engine.setMaxMemory(forwarded)

    gum.ShaferShenoyMRFInference = TracedEngine
    model = load_model(args.model)
    started = time.perf_counter()
    record = {"kind": "posthoc_diagnostic_outcome_selected_not_campaign_replacement",
              "recorded_at": datetime.now(timezone.utc).isoformat(),
              "model_path": args.model, "model_id": model.model_id,
              "model_sha256": model.source_sha256, "quota_variant": args.quota,
              "original_adapter_sha256": hashlib.sha256(open("experiments/established/pyagrum_adapter.py", "rb").read()).hexdigest()}
    try:
        record["result"] = run_pyagrum(model, max_table_bytes=134217728)
    except Exception as error:
        record["result"] = {"status": "diagnostic_exception", "exception": type(error).__name__, "message": str(error),
                            "traceback": traceback.format_exc()}
    record["elapsed_seconds"] = time.perf_counter() - started
    record["events"] = events
    record["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    from pathlib import Path
    Path(args.output).write_text(json.dumps(record, indent=2, default=lambda x: str(x))+"\n")


if __name__ == "__main__":
    main()
