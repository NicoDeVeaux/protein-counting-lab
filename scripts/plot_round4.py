"""Render the complete campaign004 source-score panel and every cold worker cost."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("ve", "batch")
ARMS = ("simplified", "propagated")
COLORS = {"simplified": "#326b98", "propagated": "#18836e"}
COVERAGE = [
    ("accepted score", "#69aa91"),
    ("correct undefined ratio", "#bcc4cc"),
    ("incorrect / invalid", "#cc6570"),
    ("incomplete / unverified", "#e4bb66"),
    ("score passes; panel rejected", "#a6bfce"),
]


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path):
    return {"path": str(path), "sha256": sha256(path)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_run(run_dir):
    require((run_dir / "summary.json").is_file(), "No completed summary; do not plot a running or stopped campaign")
    require((run_dir / "completion.json").is_file(), "A completed measurement ledger is required")
    manifest = read(run_dir / "manifest.json")
    require(manifest["campaign"] == "004", "Expected campaign004")
    require(sha256(run_dir / "manifest.json") == (run_dir / "manifest.sha256").read_text().split()[0], "Execution seal mismatch")
    root = Path(manifest["root"])
    summary = read(run_dir / "summary.json")
    records = lines(run_dir / "panels.jsonl")
    queries = lines(run_dir / "queries.jsonl")
    states = lines(run_dir / "states.jsonl")
    variants = manifest["pilot"]["sequences"]
    planned = manifest["panels"]
    require(len(variants) == len({row["sequence_id"] for row in variants}) == 21, "Expected the complete 21-template pilot")
    require(len(planned) == 12 and [row["panel"] for row in records] == planned, "Missing, duplicate, extra or reordered panels")
    require({(row["method"], row["arm"], row["repeat"]) for row in planned} ==
            {(method, arm, repeat) for method in METHODS for arm in ARMS for repeat in range(3)}, "Incomplete paired method matrix")
    expected_queries = [(panel["panel_id"], sequence) for panel in planned for sequence in panel["query_order"]]
    require([(row["panel_id"], row["sequence_id"]) for row in queries] == expected_queries, "Query matrix mismatch")
    require(queries == [query for record in records for query in record["query_results"]], "Panel and query ledgers disagree")
    require(len(states) == len(manifest["slots"]) == 756, "State matrix count mismatch")
    require([{key: row[key] for key in slot} for slot, row in zip(manifest["slots"], states)] == manifest["slots"], "State matrix identity mismatch")
    require(summary["panels"] == len(records) and summary["planned_queries"] == len(queries) and
            summary["planned_state_slots"] == len(states), "Summary matrix counts disagree")
    require(summary["panel_statuses"] == [row["status"] for row in records], "Summary panel statuses disagree")
    require(summary["correct_scores"] == sum(row["validation"]["status"] == "success" for row in queries), "Summary accepted-score count mismatch")

    reference_path = root / manifest["reference_artifact"]["path"]
    require(sha256(reference_path) == manifest["reference_artifact"]["sha256"], "Independent reference hash mismatch")
    reference = read(reference_path)
    require(reference["case_id"] == manifest["pilot"]["case_id"] and
            reference["source_hashes"]["archive_sha256"] == manifest["pilot"]["archive"]["sha256"], "Reference source identity mismatch")
    by_index = {row["panel_index"]: row for row in reference["rows"]}
    require(len(by_index) == len(reference["rows"]) == len(variants), "Reference panel incomplete")
    scores = []
    for variant in variants:
        row = by_index[variant["panel_index"]]
        score = row["scores"]["stored_binary64_log"]
        require(row["label"] == variant["label"] and score == manifest["references"][variant["sequence_id"]]["score"], "Normalized reference differs from its independent source")
        status = score["status"]
        require(status in {"finite", "zero numerator", "undefined", "unresolved"}, "Unknown reference score status")
        if status == "finite":
            require(Decimal(score["logKstar"]).is_finite(), "A finite score contains a nonfinite value")
        scores.append({"sequence_id": variant["sequence_id"], "label": variant["label"],
                       "panel_index": variant["panel_index"], "status": status,
                       "logKstar": score.get("logKstar"), "reference": score})

    inputs = {run_dir / name for name in ("manifest.json", "manifest.sha256", "summary.json", "completion.json",
                                         "panels.jsonl", "queries.jsonl", "states.jsonl")}
    inputs.add(reference_path)
    preparation_path = root / manifest["preparation_manifest"]["path"]
    require(sha256(preparation_path) == manifest["preparation_manifest"]["sha256"], "Preparation seal mismatch")
    inputs.update((preparation_path, preparation_path.with_suffix(".sha256")))
    for record in records:
        for artifact in record["artifacts"]:
            path = root / artifact["path"]
            require(sha256(path) == artifact["sha256"], "Panel artifact hash mismatch: " + str(path))
            inputs.add(path)
        monitor = record["monitor"]
        if monitor is not None:
            require(math.isfinite(monitor["wall_seconds"]) and monitor["wall_seconds"] >= 0, "Invalid worker wall observation")
            rss = record.get("whole_peak_rss_bytes")
            require(isinstance(rss, int) and rss >= monitor["sampled_peak_rss_bytes"], "Incomplete whole-worker RSS observation")
    ordered = sorted(records, key=lambda row: (METHODS.index(row["panel"]["method"]), row["panel"]["repeat"], ARMS.index(row["panel"]["arm"])))
    return manifest, summary, ordered, queries, states, scores, sorted(inputs)


def coverage_code(query, panel_status):
    status = query["validation"]["status"]
    if status == "success":
        return 0 if panel_status == "complete" else 4
    if status == "correct_undefined":
        return 1
    if status in {"wrong_answer", "wrong_target_or_cache", "invalid_score_output"}:
        return 2
    return 3


def top_code(record):
    ranking = record["ranking"]
    cells = [ranking["top_k"].get(str(k), {}) for k in (1, 3, 5)]
    if not ranking.get("full_declared_panel"):
        return "subset"
    if any(cell.get("status") == "wrong" for cell in cells):
        return "wrong"
    if any(cell.get("boundary_uncertain") or cell.get("observed_boundary_uncertain") or
           cell.get("status") != "compatible_with_reference_envelope" for cell in cells):
        return "uncertain"
    return "OK"


def clean_axis(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0, labelsize=9)
    ax.set_axisbelow(True)


def plot_scores(ax, scores):
    finite = [float(row["logKstar"]) for row in scores if row["status"] == "finite"]
    low, high = (min(finite), max(finite)) if finite else (0, 1)
    span = max(high - low, 1)
    ax.set_xlim(low - .08 * span, high + .28 * span)
    for y, row in enumerate(scores):
        if y % 2 == 0:
            ax.axhspan(y - .5, y + .5, color="#f4f6f7", zorder=0)
        if row["status"] == "finite":
            value = float(row["logKstar"])
            color = "#815b99" if row["label"] in {"HIP", "HIE", "HID"} else "#326b98"
            ax.scatter(value, y, s=35, color=color, zorder=3)
            ax.annotate(f"{value:.4f}", (value, y), xytext=(7, 0), textcoords="offset points", va="center", fontsize=8.5, color="#38434e")
        else:
            label = {"zero numerator": "K* = 0; logK* = −∞", "undefined": "undefined: zero denominator",
                     "unresolved": "reference unresolved"}[row["status"]]
            ax.text(.03, y, label, transform=ax.get_yaxis_transform(), va="center", fontsize=9, color="#946a33")
    ax.set_ylim(len(scores) - .5, -.5)
    ax.set_yticks(range(len(scores)), [row["label"] + (" · baseline" if i == 0 else "") for i, row in enumerate(scores)])
    ax.set_xlabel("Independent reference logK* (natural log units)", fontsize=10)
    ax.grid(axis="x", color="#dfe4e8", lw=.7)
    ax.set_title("A   All source templates, in source order", loc="left", fontsize=12, weight="bold", pad=36)
    clean_axis(ax)


def plot_coverage(ax, records, scores, rectangle):
    for x, record in enumerate(records):
        by_id = {row["sequence_id"]: row for row in record["query_results"]}
        for y, score in enumerate(scores):
            code = coverage_code(by_id[score["sequence_id"]], record["status"])
            ax.add_patch(rectangle((x - .47, y - .46), .94, .92, facecolor=COVERAGE[code][1], edgecolor="white", lw=.3))
        pairs = record["ranking"]["pairwise"]
        ax.text(x, len(scores) + .25, top_code(record), ha="center", va="center", fontsize=8, weight="bold")
        ax.text(x, len(scores) + 1.15, f"{pairs['wrong']}/{pairs['checked']}", ha="center", va="center", fontsize=7.8)
    ax.set_xlim(-.6, len(records) - .4)
    ax.set_ylim(len(scores) - .5, -.5)
    ax.set_xticks(range(len(records)), [f"{row['panel']['method'].upper()}\nR{row['panel']['repeat'] + 1} {'B' if row['panel']['arm'] == 'simplified' else 'P'}" for row in records])
    ax.xaxis.tick_top()
    ax.set_yticks([])
    ax.tick_params(length=0, labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.axvline(5.5, color="#65727d", lw=1)
    ax.set_title("B   Every query validation across all 12 workers", loc="left", fontsize=12, weight="bold", pad=36)
    ax.text(-.7, len(scores) + .25, "top-1/3/5", ha="right", va="center", fontsize=8)
    ax.text(-.7, len(scores) + 1.15, "wrong / resolved pairs", ha="right", va="center", fontsize=8)


def plot_cost(ax, records, field, title, ylabel):
    groups = [(method, repeat) for method in METHODS for repeat in range(3)]
    positions = [0, 1, 2, 4, 5, 6]
    values = []
    for x, (method, repeat) in zip(positions, groups):
        pair = {row["panel"]["arm"]: row for row in records if row["panel"]["method"] == method and row["panel"]["repeat"] == repeat}
        coordinates = []
        for arm, offset in (("simplified", -.13), ("propagated", .13)):
            row = pair[arm]
            monitor = row["monitor"]
            value = None if monitor is None else (monitor["wall_seconds"] if field == "wall" else row["whole_peak_rss_bytes"] / 2**20)
            if value is None:
                ax.text(x + offset, .05, "skip", transform=ax.get_xaxis_transform(), rotation=90, ha="center", color="#946a33", fontsize=8)
                continue
            values.append(value)
            coordinates.append((x + offset, value))
            marker = "o" if arm == "simplified" else "D"
            face = COLORS[arm] if row["status"] == "complete" else "white"
            ax.scatter(x + offset, value, s=43, marker=marker, facecolor=face, edgecolor=COLORS[arm], linewidth=1.3, zorder=3)
            label_offset = ((-5 if arm == "simplified" else 5), 7) if field == "wall" else (0, 10 if arm == "simplified" else -16)
            align = ("right" if arm == "simplified" else "left") if field == "wall" else "center"
            ax.annotate(f"{value:.3f}" if field == "wall" else f"{value:.1f}", (x + offset, value), xytext=label_offset,
                        textcoords="offset points", ha=align, fontsize=8, color=COLORS[arm])
            if row["status"] != "complete":
                ax.annotate(row["status"], (x + offset, value), xytext=(0, -12), textcoords="offset points", ha="center", fontsize=6.5)
        if len(coordinates) == 2:
            ax.plot(*zip(*coordinates), color="#c5cdd3", lw=1, zorder=1)
    ax.set_xlim(-.6, 6.65)
    ax.set_ylim(0, max(values, default=1) * 1.3)
    ax.set_xticks(positions, [f"{'VE' if method == 've' else 'Batch'}\nrepeat {repeat + 1}" for method, repeat in groups])
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, loc="left", fontsize=12, weight="bold", pad=10)
    ax.grid(axis="y", color="#e1e6e9", lw=.7)
    clean_axis(ax)


def render(run_dir, output, overwrite=False):
    manifest, summary, records, queries, states, scores, inputs = load_run(run_dir)
    destinations = [output.with_suffix(suffix) for suffix in (".png", ".svg", ".provenance.json")]
    require(overwrite or not any(path.exists() for path in destinations), "Derived figure already exists; choose a new output stem or --overwrite")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Rectangle

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none"})
    fig = plt.figure(figsize=(16, 14), facecolor="white")
    fig.text(.07, .97, "Three-state source score: full template panel and measured costs", fontsize=21, weight="bold", va="top")
    pilot = manifest["pilot"]
    fig.text(.07, .936, f"Campaign 004 · {pilot['case_id'].split('_prepped')[0]} / residue {pilot['residue']} · 21 source templates · one computational case", fontsize=12)
    fig.text(.07, .908, "Stored binary64 log target; source zeros retained. HIP, HIE and HID remain distinct. Decimal 90/120 references.\n"
             f"{summary['correct_scores']}/{summary['planned_queries']} query scores pass; {summary['correct_undefined']} correct undefined ratios; all {summary['planned_state_slots']} state slots retained.",
             fontsize=10.5, color="#42505c", linespacing=1.5, va="top")
    plot_scores(fig.add_axes([.115, .425, .345, .40]), scores)
    plot_coverage(fig.add_axes([.585, .425, .35, .40]), records, scores, Rectangle)
    fig.legend(handles=[Patch(facecolor=color, label=label) for label, color in COVERAGE],
               loc="center", bbox_to_anchor=(.74, .346), ncol=2, frameon=False, fontsize=8.5, handlelength=1.1)
    plot_cost(fig.add_axes([.115, .15, .345, .16]), records, "wall", "C   All paired cold-worker wall observations", "Wall time (seconds)")
    plot_cost(fig.add_axes([.585, .15, .35, .16]), records, "rss", "D   All paired whole-worker RSS observations", "Observed peak RSS (MiB)")
    fig.legend(handles=[Line2D([], [], color=COLORS[arm], marker="o" if arm == "simplified" else "D", ls="", label=label)
                        for arm, label in (("simplified", "B: baseline — exact algebra"), ("propagated", "P: pruned — exact hard-zero propagation + algebra"))],
               loc="center", bbox_to_anchor=(.52, .102), ncol=2, frameon=False, fontsize=10)
    cache_counts = Counter(row["panel_id"] for row in states if row["raw"].get("cache_hit"))
    cache_range = [cache_counts[row["panel"]["panel_id"]] for row in records]
    cache_label = str(cache_range[0]) if min(cache_range) == max(cache_range) else f"{min(cache_range)}–{max(cache_range)}"
    pair_errors = sum(row["ranking"]["pairwise"]["wrong"] for row in records)
    pair_uncertain = sum(row["ranking"]["pairwise"]["uncertain_reference"] + row["ranking"]["pairwise"]["uncertain_observed"] for row in records)
    epsilon = manifest["scientific_choices"]["accuracy"]["rank_score_envelope"]
    fig.text(.07, .075, f"Numerical rank envelope ±{epsilon:.3g} log units; {pair_errors} wrong resolved pair orders and {pair_uncertain} uncertain pair comparisons across worker repeats.\n"
             f"Exact same-target cache reuse: {cache_label} of 63 state slots per worker; conditioning and transformations remain charged. Repeats are not independent proteins.",
             fontsize=9.1, color="#42505c", linespacing=1.5, va="top")
    fig.text(.07, .045, "RSS = controller maximum of sampled process-tree RSS and worker high-water before/after result writing; transient peaks may be missed.\n"
             "Source-encoding arithmetic diagnostics only; no experimental-affinity, biological-prediction or BBK*/AOBB comparison claim.",
             fontsize=9, color="#52606b", linespacing=1.5, va="top")
    fig.text(.07, .008, f"Derived after measurement · execution seal {sha256(run_dir / 'manifest.json')[:6]} · full hashes in provenance", fontsize=8, color="#6a7680")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destinations[0], dpi=180, facecolor="white")
    fig.savefig(destinations[1], facecolor="white")
    plt.close(fig)
    provenance = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "campaign": "004",
        "kind": "postmeasurement_derived_visualization", "source_run_directory": str(run_dir),
        "renderer": {"matplotlib": matplotlib.__version__, "backend": "Agg"},
        "inputs": [identity(path) for path in inputs], "script": identity(Path(__file__).resolve()),
        "outputs": [identity(path) for path in destinations[:2]],
        "reference_scores": scores,
        "panels": [{"panel": row["panel"], "status": row["status"], "wall_seconds": row["monitor"]["wall_seconds"] if row["monitor"] else None,
                    "whole_peak_rss_bytes": row.get("whole_peak_rss_bytes"), "cached_state_slots": cache_counts[row["panel"]["panel_id"]],
                    "accepted_scores_under_panel_policy": row["accepted_scores_under_panel_policy"], "ranking": row["ranking"]} for row in records],
        "coverage_status_counts": dict(Counter(row["validation"]["status"] for row in queries)),
        "all_21_templates_12_panels_252_queries_756_slots_reconciled": True,
        "score_target": "sum exp(stored binary64 math.log weights); source-represented zeros retained",
        "rank_policy": "Frozen raw-score/reference-envelope checks; no ranking from rounded displayed values",
        "wall_scope": "Fresh whole panel process: startup, archive parse, conditioning, transformations, inference/cache, result writing and reaping",
        "rss_scope": "Controller whole_peak_rss_bytes: maximum of sampled process-tree RSS and before/after-result worker high-water; not an instantaneous ceiling",
        "replication_scope": "Three cold paired repetitions of one computational case; no independent biological replication",
        "biological_accuracy_tested": False, "domain_comparator_executed": False}
    with destinations[2].open("w" if overwrite else "x") as stream:
        stream.write(json.dumps(provenance, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"outputs": [str(path) for path in destinations], "templates": len(scores), "panels": len(records)}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=ROOT / "runs/campaign-004")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/campaign-004")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing derived figure outputs")
    args = parser.parse_args()
    render(args.run_dir.resolve(), args.output.resolve(), args.overwrite)


if __name__ == "__main__":
    main()
