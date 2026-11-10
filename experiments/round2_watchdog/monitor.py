"""Watch only an owned subprocess group; sampled RSS is not an instantaneous ceiling."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import psutil


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def _cpu_children():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _kill_group(process, sig):
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def supervise(command, *, cwd, env, stdout_path, stderr_path, rss_ceiling_bytes,
              wall_timeout_seconds, sample_interval_seconds=.01):
    if min(rss_ceiling_bytes, wall_timeout_seconds, sample_interval_seconds) <= 0:
        raise ValueError("Positive resource limits and sampling interval required")
    started_at = utcnow()
    start = time.perf_counter()
    cpu_start = _cpu_children()
    baseline, peak, samples, errors = None, 0, 0, 0
    trigger, killed, reason, overshoot = None, None, None, 0
    stdout_path, stderr_path = Path(stdout_path), Path(stderr_path)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                                   start_new_session=True)
        owner = psutil.Process(process.pid)
        while True:
            elapsed = time.perf_counter() - start
            try:
                with owner.oneshot():
                    rss = owner.memory_info().rss
                for descendant in owner.children(recursive=True):
                    try:
                        rss += descendant.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.ZombieProcess):
                        pass
                baseline = rss if baseline is None else baseline
                peak = max(peak, rss)
                samples += 1
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                rss = 0
            except psutil.AccessDenied:
                errors += 1
                rss = 0
            if process.poll() is not None:
                break
            if rss > rss_ceiling_bytes:
                reason, trigger = "rss_limit", elapsed
                overshoot = max(overshoot, rss - rss_ceiling_bytes)
            elif elapsed >= wall_timeout_seconds:
                reason, trigger = "timeout", elapsed
            if reason:
                _kill_group(process, signal.SIGTERM)
                killed = time.perf_counter() - start
                try:
                    process.wait(timeout=.2)
                except subprocess.TimeoutExpired:
                    _kill_group(process, signal.SIGKILL)
                    process.wait(timeout=2)
                break
            time.sleep(sample_interval_seconds)
        returncode = process.wait()
    return {
        "started_at_utc": started_at, "finished_at_utc": utcnow(),
        "exit_code": returncode, "signal": signal.Signals(-returncode).name if returncode < 0 else None,
        "wall_seconds": time.perf_counter() - start,
        "cpu_seconds": max(0., _cpu_children() - cpu_start),
        "termination_reason": reason, "rss_baseline_bytes": baseline,
        "sampled_peak_rss_bytes": peak, "rss_samples": samples,
        "sampling_errors": errors, "sample_interval_seconds": sample_interval_seconds,
        "limit_trigger_seconds": trigger, "kill_seconds": killed,
        "overshoot_bytes": overshoot,
        "scope": "Sum of sampled worker and live descendants RSS; shared pages can be counted multiple times; exited descendants and between-sample peaks can be missed.",
        "cpu_scope": "Sequential per-trial delta of resource.getrusage(RUSAGE_CHILDREN), user plus system CPU, after child is reaped.",
        "instantaneous_ceiling_guaranteed": False,
    }


def validate_controls(output_dir, *, python=sys.executable):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    env = {key: os.environ[key] for key in ("PATH", "TMPDIR", "LANG") if key in os.environ}
    cases = [
        ("completion", "print('watchdog-control-complete')", 256*1024**2, 2., None),
        ("rss", "import time; a=bytearray(96*1024*1024); time.sleep(2)", 48*1024**2, 3., "rss_limit"),
        ("timeout", "import time; time.sleep(2)", 256*1024**2, .1, "timeout"),
    ]
    results = []
    for name, source, rss, timeout, expected in cases:
        record = supervise([python, "-c", source], cwd=output_dir, env=env,
                           stdout_path=output_dir/(name+".stdout.txt"),
                           stderr_path=output_dir/(name+".stderr.txt"),
                           rss_ceiling_bytes=rss, wall_timeout_seconds=timeout)
        record.update({"control_id": name, "expected_reason": expected,
                       "passed": record["termination_reason"] == expected and
                       (record["exit_code"] == 0 if expected is None else record["exit_code"] != 0)})
        results.append(record)
    result = {"recorded_at_utc": utcnow(), "kind": "nonmeasurement_watchdog_control",
              "all_passed": all(x["passed"] for x in results), "controls": results,
              "limitations": "Tests verify sampled detection/termination on these controls. They do not guarantee an instantaneous RSS ceiling or catch every transient peak."}
    (output_dir/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    if not result["all_passed"]:
        raise RuntimeError("Watchdog control failed")
    return result
