"""Run bounded post hoc variants on the four distinct failed input models."""

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

from experiments.round2_watchdog.monitor import supervise

root = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", default="experiments/established/diagnostics/results")
parser.add_argument("--tests-only", action="store_true")
args = parser.parse_args()
output = root / args.output_dir
output.mkdir()
if args.tests_only:
    env={key:os.environ[key] for key in ("PATH","TMPDIR","LANG") if key in os.environ}
    env.update({"OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1","VECLIB_MAXIMUM_THREADS":"1"})
    record=supervise([sys.executable,"-m","pytest","-q","tests/test_established_pyagrum_v2.py"],cwd=root,env=env,stdout_path=output/"tests.stdout.txt",stderr_path=output/"tests.stderr.txt",rss_ceiling_bytes=536870912,wall_timeout_seconds=20)
    (output/"test_monitor.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record),flush=True)
    sys.exit(0 if record["exit_code"]==0 else 1)
manifest = json.loads((root/"runs/campaign-002/manifest.json").read_text())
failures = []
for path in sorted((root/"runs/campaign-002/raw").glob("*.result.json")):
    record = json.loads(path.read_text())
    if record.get("status") == "adapter_error" and record.get("exception_message") == "std::bad_alloc":
        failures.append({"original_result_path": str(path.relative_to(root)), "model_id":record["model_id"]})
paths = {m["model_id"]: next(r["files"][0]["path"] for r in m["representations"] if r["representation_id"] == "original") for m in manifest["models"]}
cases = sorted({f["model_id"] for f in failures})
source_evidence = []
for path in ("src/agrum/base/graphicalModels/inference/scheduler/scheduledInference_inl.h", "src/agrum/base/graphicalModels/inference/scheduler/scheduler_inl.h"):
    url = "https://raw.githubusercontent.com/agrumery/aGrUM/3.3.2/" + path
    with urllib.request.urlopen(url,timeout=30) as response: blob=response.read()
    source_evidence.append({"url":url,"sha256":hashlib.sha256(blob).hexdigest(),"source_path":path})
preparation = {"recorded_at":datetime.now(timezone.utc).isoformat(),"kind":"posthoc_outcome_selected_adapter_diagnostic",
               "selection":"Every distinct input among all15 retained std::bad_alloc adapter failures, original representation; no campaign rows replaced.",
               "original_failures":failures,"cases":cases,"variants":["as-written","default","128","1024"],
               "resource_limits":{"rss_ceiling_bytes":536870912,"wall_timeout_seconds":20,"sample_interval_seconds":.01},
               "source_evidence":source_evidence}
(output/"diagnostic_plan.json").write_text(json.dumps(preparation,indent=2)+"\n")
env={key:os.environ[key] for key in ("PATH","TMPDIR","LANG") if key in os.environ}
env.update({"OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1","VECLIB_MAXIMUM_THREADS":"1"})
observations=[]
for index,model_id in enumerate(cases):
    for variant in preparation["variants"]:
        stem=f"{index:02d}-{variant}"
        path=output/(stem+".json")
        command=[sys.executable,"-m","experiments.established.diagnostics.quota_variant",paths[model_id],"--quota",variant,"--output",str(path)]
        monitor=supervise(command,cwd=root,env=env,stdout_path=output/(stem+".stdout.txt"),stderr_path=output/(stem+".stderr.txt"),rss_ceiling_bytes=536870912,wall_timeout_seconds=20)
        record={"model_id":model_id,"variant":variant,"monitor":monitor}
        if path.exists(): record["diagnostic"]=json.loads(path.read_text())
        observations.append(record)
        result=record.get("diagnostic",{}).get("result",{})
        print(json.dumps({"model_id":model_id,"variant":variant,"status":result.get("status",monitor["termination_reason"]),"log_z":result.get("log_z"),"sampled_peak_rss_bytes":monitor["sampled_peak_rss_bytes"]}),flush=True)
(output/"all_results.json").write_text(json.dumps({"plan":preparation,"observations":observations},indent=2)+"\n")
