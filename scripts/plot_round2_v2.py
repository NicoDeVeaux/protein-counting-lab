"""Plot every planned outcome from the completed corrective campaign."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "runs/campaign-002-amendment-001"
DEFAULT_OUTPUT = ROOT / "outputs/campaign-002-v2"
METHODS = ("ve", "batch", "pyagrum")
METHOD_LABELS = ("VE (local)", "Enumeration (local)", "pyagrum v2")
PROFILES = ("low", "high")
COMPLETED = {"success", "unverified_accuracy"}
STATUS_STYLE = {
    "success": ("ok", "success: reference checked", "#92cfb0"),
    "unverified_accuracy": ("uv", "unverified accuracy", "#f4d277"),
    "planned_skip": ("skip", "planned / budget skip", "#d3d6da"),
    "predicted_table_cap": ("tab", "table / wrapper cap", "#a9cce6"),
    "rss_limit": ("rss", "RSS ceiling", "#e9a8bc"),
    "timeout": ("time", "wall timeout", "#b6a8dc"),
    "unsupported_conversion": ("conv", "conversion refused", "#eec39b"),
    "numerical_failure": ("num", "numerical failure", "#e48888"),
    "wrong_answer": ("wrong", "reference mismatch", "#d85f66"),
    "allocation_error": ("alloc", "allocation failure", "#ccae98"),
    "invalid_input": ("input", "invalid input", "#bbbc90"),
    "signal_or_crash": ("crash", "signal / crash", "#b5b5b5"),
    "invalid_output": ("out", "invalid output", "#acbcc4"),
    "infrastructure_error": ("infra", "infrastructure error", "#9c9c9c"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_complete_run(run_dir: Path):
    """Refuse incomplete, mismatched, duplicated, or silently filtered rows."""
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        raise ValueError(f"Completed summary required before plotting: {summary_path}")
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    summary = json.loads(summary_path.read_text())
    manifest_sha = digest(manifest_path)
    if summary.get("manifest_sha256") != manifest_sha:
        raise ValueError("Summary does not identify this manifest")
    if not manifest.get("amendment") or manifest.get("original_execution_manifest") is None:
        raise ValueError("Expected the corrective amendment manifest")
    adapter = next(m for m in manifest["methods"] if m["method_id"] == "pyagrum")
    if adapter["configuration"].get("adapter_version") != 2:
        raise ValueError("Expected corrected established adapter version 2")
    records = [json.loads(line) for line in (run_dir / "trials.jsonl").read_text().splitlines() if line.strip()]
    planned = {row["trial_id"]: row for row in manifest["planned_trials"]}
    actual = {row["trial_id"]: row for row in records}
    if len(planned) != len(manifest["planned_trials"]) or len(actual) != len(records):
        raise ValueError("Duplicate trial IDs")
    if set(planned) != set(actual):
        raise ValueError("Recorded trial IDs differ from the complete planned matrix")
    if summary.get("missing_trial_ids") or summary.get("unexpected_trial_ids"):
        raise ValueError("Summary reports a trial reconciliation failure")
    if summary.get("recorded_trials") != len(records) or summary.get("planned_trials") != len(planned):
        raise ValueError("Summary row counts do not match the raw records")
    keys = ("model_id", "representation_id", "method_id", "resource_profile_id", "accuracy_contract_id", "repeat")
    for trial_id, row in actual.items():
        if row.get("manifest_sha256") != manifest_sha:
            raise ValueError(f"Manifest mismatch in trial {trial_id}")
        if any(row.get(key) != planned[trial_id].get(key) for key in keys):
            raise ValueError(f"Planned metadata mismatch in trial {trial_id}")
        if row["status"] not in STATUS_STYLE:
            raise ValueError(f"Unrecognized status: {row['status']}")
        if row["status"] in COMPLETED:
            wall = row["timing"]["wall_seconds"]
            if not isinstance(wall, (int, float)) or not math.isfinite(wall) or wall < 0:
                raise ValueError(f"Invalid completed wall time in trial {trial_id}")
    if dict(Counter(row["status"] for row in records)) != summary.get("status_counts"):
        raise ValueError("Summary status counts differ from the raw records")
    return manifest, summary, records


def grouped_cells(records):
    cells = defaultdict(list)
    for row in records:
        key = tuple(row[k] for k in ("model_id", "representation_id", "method_id", "resource_profile_id"))
        cells[key].append(row)
    for key, rows in cells.items():
        rows.sort(key=lambda row: row["repeat"])
        if [row["repeat"] for row in rows] != [0, 1, 2]:
            raise ValueError(f"Expected all three distinct repeats for {key}")
    return cells


def model_rows(manifest, cohort):
    return [(model, rep) for model in manifest["models"] if model["cohort"] == cohort
            for rep in model["representations"]]


def row_label(model, rep):
    model_id = model["model_id"]
    if model["cohort"] == "published_protein_extension":
        name = model_id.split("__", 1)[0]
    else:
        name = model_id.removeprefix("synthetic-").replace("-n", " n=").replace("-q", " q=")
    representation = "original" if rep["representation_id"] == "original" else "simplified"
    return f"{name} / {representation}"


def time_label(rows):
    values = [row["timing"]["wall_seconds"] for row in rows if row["status"] in COMPLETED]
    if not values:
        return "—"
    label = f"{statistics.median(values):.2f} s"
    return label if len(values) == 3 else f"{label} ({len(values)}/3)"


def draw_matrix(ax, rows, cells, title, rectangle):
    for y, (model, rep) in enumerate(rows):
        for x, (profile, method) in enumerate((p, m) for p in PROFILES for m in METHODS):
            trials = cells[(model["model_id"], rep["representation_id"], method, profile)]
            ax.add_patch(rectangle((x + .025, y + .045), .95, .91,
                                   facecolor="#fafbfc", edgecolor="#d4d8dc", linewidth=.5))
            for repeat, trial in enumerate(trials):
                code, _, color = STATUS_STYLE[trial["status"]]
                left = x + .045 + repeat * .305
                ax.add_patch(rectangle((left, y + .07), .295, .43,
                                       facecolor=color, edgecolor="white", linewidth=.4))
                ax.text(left + .1475, y + .285, code, ha="center", va="center", fontsize=8.1)
            ax.text(x + .5, y + .73, time_label(trials), ha="center", va="center",
                    fontsize=8.2, color="#303841")
    ax.set_xlim(0, 6)
    ax.set_ylim(len(rows), 0)
    ax.set_xticks([i + .5 for i in range(6)], METHOD_LABELS * 2)
    ax.set_yticks([i + .5 for i in range(len(rows))], [row_label(m, r) for m, r in rows])
    ax.tick_params(axis="both", length=0, labelsize=9)
    ax.xaxis.tick_top()
    ax.axvline(3, color="#444c54", linewidth=1.0)
    ax.text(.25, 1.075, "LOW BUDGET", transform=ax.transAxes, ha="center", fontsize=9.5, weight="bold")
    ax.text(.75, 1.075, "HIGH BUDGET", transform=ax.transAxes, ha="center", fontsize=9.5, weight="bold")
    ax.set_title(title, loc="left", pad=53, fontsize=12, weight="bold")
    for spine in ax.spines.values():
        spine.set_visible(False)


def draw_baseline(ax, records, manifest):
    ids = {model["model_id"] for model in manifest["models"] if model["cohort"] == "original_42"}
    totals = []
    for y, method in enumerate(METHODS):
        rows = [row for row in records if row["model_id"] in ids and row["method_id"] == method]
        if any(row["resource_profile_id"] != "high" for row in rows):
            raise ValueError("Unexpected low-profile original-42 result")
        counts = Counter(row["status"] for row in rows)
        left = 0
        for status, (_, _, color) in STATUS_STYLE.items():
            count = counts[status]
            if count:
                ax.barh(y, count, left=left, height=.65, color=color, edgecolor="white", linewidth=.5)
                if count >= 5:
                    ax.text(left + count / 2, y, str(count), ha="center", va="center", fontsize=9)
                left += count
        totals.append(left)
    ax.set_title("Original 42 prepared states · high budget only", loc="left", fontsize=12, weight="bold", pad=9)
    ax.set_yticks(range(3), METHOD_LABELS)
    ax.set_ylim(2.6, -.6)
    ax.set_xlim(0, max(totals))
    ax.set_xlabel("Trial outcomes (42 states × 3 repeats per method; correlated descriptive counts)", fontsize=9)
    ax.tick_params(axis="both", labelsize=9, length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)


def render(run_dir: Path, output_stem: Path):
    manifest, summary, records = load_complete_run(run_dir)
    cells = grouped_cells(records)
    protein = model_rows(manifest, "published_protein_extension")
    synthetic = model_rows(manifest, "synthetic_measured")
    if not protein or not synthetic:
        raise ValueError("Both the published protein and synthetic cohorts are required")
    cohorts = {model["cohort"] for model in manifest["models"]}
    if cohorts != {"original_42", "published_protein_extension", "synthetic_measured"}:
        raise ValueError(f"Unexpected cohort would be omitted: {cohorts}")
    expected = {(model["model_id"], rep["representation_id"], method, profile)
                for model, rep in protein + synthetic for profile in PROFILES for method in METHODS}
    shown = expected | {key for key in cells if key[3] == "high" and key[0] in {
        model["model_id"] for model in manifest["models"] if model["cohort"] == "original_42"}}
    if shown != set(cells):
        raise ValueError("Figure would omit or invent planned cells")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "svg.fonttype": "none"})
    fig = plt.figure(figsize=(13, 17.5), facecolor="white")
    grid = fig.add_gridspec(3, 1, height_ratios=(len(protein), len(synthetic), 3.5), hspace=.45,
                           left=.285, right=.985, top=.81, bottom=.24)
    draw_matrix(fig.add_subplot(grid[0]), protein, cells,
                "Published computational protein models · one fixed sequence, β = 1 numerical target", Rectangle)
    draw_matrix(fig.add_subplot(grid[1]), synthetic, cells,
                "Synthetic structural controls · same partition target for each exact simplification", Rectangle)
    draw_baseline(fig.add_subplot(grid[2]), records, manifest)
    fig.text(.035, .975, "Partition-function calculations under fixed local budgets", fontsize=18, weight="bold", va="top")
    fig.text(.035, .947, f"Corrective full-matrix rerun · {summary['recorded_trials']} / {summary['planned_trials']} planned outcomes retained", fontsize=11)
    fig.text(.035, .918,
             "Each cell: three status tiles, left to right = stored repeats 0 / 1 / 2. Number below = median fresh-process wall time.\n"
             "Medians use completed calculations (ok + uv); a partial median shows n/3. — means none completed.\n"
             "Failures and skips retain their status tiles; their times are excluded from these descriptive medians.",
             fontsize=9.5, linespacing=1.5, color="#414a53", va="top")
    observed = set(row["status"] for row in records)
    mandatory = {"success", "unverified_accuracy", "planned_skip", "predicted_table_cap", "rss_limit",
                 "timeout", "unsupported_conversion", "numerical_failure"}
    handles = [Patch(facecolor=color, label=f"{code}: {label}")
               for status, (code, label, color) in STATUS_STYLE.items() if status in observed | mandatory]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(.033, .137), ncol=4,
               frameon=False, fontsize=9, columnspacing=1.9, handlelength=1.2, handletextpad=.5)
    profiles = {p["resource_profile_id"]: p for p in manifest["resource_profiles"]}
    resource_labels = [f"{profile}: {profiles[profile]['table_cap_bytes'] / 2**20:g} MiB table/allocation policy, "
                       f"{profiles[profile]['rss_ceiling_bytes'] / 2**20:g} MiB RSS ceiling, "
                       f"{profiles[profile]['wall_timeout_seconds']:g} s wall cap" for profile in PROFILES]
    fig.text(.035, .112, "  |  ".join(resource_labels), fontsize=8.5)
    fig.text(.035, .09,
             "Table policies differ by solver; they are not total-memory guarantees. RSS: 10 ms process-tree samples plus worker lifetime high-water; no instantaneous guarantee.\n"
             "Wall time includes process startup, JSON loading, solver work and monitoring; offline algebra preparation is excluded. No confidence intervals or significance tests.",
             fontsize=8.2, linespacing=1.5, color="#414a53", va="top")
    fig.text(.035, .049,
             "Scope: finite-state numerical targets only. Published computational models and synthetic controls are shown separately.\n"
             "β = 1 is an energy benchmark convention here, not an affinity measurement or a physical-temperature claim. No biological prediction or ETH claim is tested.",
             fontsize=8.4, linespacing=1.5, color="#414a53", va="top")
    fig.text(.035, .013, f"Source: {run_dir.relative_to(ROOT) if run_dir.is_relative_to(ROOT) else run_dir}  ·  manifest {digest(run_dir / 'manifest.json')[:6]}",
             fontsize=8, color="#66717b")
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    png, svg = output_stem.with_suffix(".png"), output_stem.with_suffix(".svg")
    fig.savefig(png, dpi=200, facecolor="white")
    fig.savefig(svg, facecolor="white")
    plt.close(fig)
    provenance = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_directory": str(run_dir),
        "inputs": [{"path": str(run_dir / name), "sha256": digest(run_dir / name)}
                   for name in ("manifest.json", "summary.json", "trials.jsonl")],
        "script": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__))},
        "outputs": [{"path": str(path), "sha256": digest(path)} for path in (png, svg)],
        "row_counts": {"planned": len(manifest["planned_trials"]), "recorded": len(records)},
        "median_scope": "Fresh subprocess wall time for success and unverified_accuracy rows only; n/3 shown if partial.",
        "all_repeat_statuses_shown": True,
        "no_inferential_or_biological_validation": True,
    }
    provenance_path = output_stem.with_suffix(".provenance.json")
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
    for path in (png, svg, provenance_path):
        print(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output-stem", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        render(args.run_dir.resolve(), args.output_stem.resolve())
    except (ValueError, KeyError, OSError, StopIteration) as error:
        parser.exit(1, f"Plot refused: {error}\n")


if __name__ == "__main__":
    main()
