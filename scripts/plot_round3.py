"""Show all campaign003 protein arms and outcomes without selecting timing winners."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT/"runs/campaign-003-amendment-003"
DEFAULT_OUTPUT = ROOT/"outputs/campaign-003"
METHODS = ("ve", "batch", "pyagrum")
METHOD_LABELS = ("VE (local)", "Enumeration (local)", "pyagrum v2")
ARMS = ("simplified", "propagated")
PROFILES = ("low", "high")
STYLE = {
    "success": ("ok", "reference-passing nonzero", "#8dccae"),
    "success_zero": ("Z0", "reference-passing exact zero", "#b4dfcd"),
    "unverified_accuracy": ("uv", "unverified accuracy", "#f2d16f"),
    "state_limit": ("states", "enumeration limit after cold preparation", "#d1d5da"),
    "planned_skip": ("skip", "budget / no-worker skip", "#c1c5ca"),
    "predicted_table_cap": ("table", "named table / wrapper policy", "#a7c9e2"),
    "unsupported_conversion": ("conv", "numerical conversion refused", "#edc196"),
    "timeout": ("time", "censored timeout", "#b6a5d8"),
    "rss_limit": ("rss", "RSS threshold exceeded", "#e8a5bb"),
    "wrong_answer": ("wrong", "reference mismatch", "#dc6870"),
    "numerical_failure": ("num", "numerical failure", "#e28b89"),
    "allocation_error": ("alloc", "allocation failure", "#c7a78f"),
    "invalid_input": ("input", "invalid input", "#bdbb90"),
    "invalid_output": ("out", "invalid output", "#aabac2"),
    "signal_or_crash": ("crash", "signal / crash", "#aab0b6"),
    "infrastructure_error": ("infra", "infrastructure error", "#959b9f"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_status(row):
    if row["status"] == "success" and row["output"].get("zero_mass"):
        return "success_zero"
    if row["status"] == "planned_skip" and row.get("raw_status") in {"state_limit", "integer_index_limit"}:
        return "state_limit"
    return row["status"]


def load_complete_run(run_dir):
    summary_path = run_dir/"summary.json"
    if not summary_path.is_file():
        raise ValueError("A completed summary is required; no plotting during partial measurements")
    manifest_path = run_dir/"manifest.json"
    manifest = json.loads(manifest_path.read_text())
    summary = json.loads(summary_path.read_text())
    manifest_sha = digest(manifest_path)
    if manifest.get("campaign") != "003" or summary.get("manifest_sha256") != manifest_sha:
        raise ValueError("Campaign/manifest identity mismatch")
    planned_list = manifest["planned_trials"]
    records = [json.loads(line) for line in (run_dir/"trials.jsonl").read_text().splitlines() if line.strip()]
    planned, actual = {r["trial_id"]:r for r in planned_list}, {r["trial_id"]:r for r in records}
    if len(planned) != len(planned_list) or len(actual) != len(records) or set(planned) != set(actual):
        raise ValueError("Full matrix reconciliation failed")
    if summary.get("planned_trials") != len(planned) or summary.get("recorded_trials") != len(records):
        raise ValueError("Summary counts disagree with raw ledger")
    if summary.get("missing_trial_ids") or summary.get("unexpected_trial_ids"):
        raise ValueError("Summary reports missing/unexpected identities")
    if summary.get("status_counts") != dict(Counter(r["status"] for r in records)):
        raise ValueError("Summary statuses disagree with raw ledger")
    keys = ("model_id", "representation_id", "method_id", "resource_profile_id", "accuracy_contract_id", "repeat", "block_id")
    for trial_id, row in actual.items():
        if row.get("manifest_sha256") != manifest_sha or any(row.get(k) != planned[trial_id].get(k) for k in keys):
            raise ValueError("Raw identity mismatch: "+trial_id)
        if display_status(row) not in STYLE:
            raise ValueError("Unknown status would be omitted: "+row["status"])
        wall = row["timing"]["wall_seconds"]
        if wall is not None and (not isinstance(wall, (int,float)) or not math.isfinite(wall) or wall < 0):
            raise ValueError("Invalid wall observation: "+trial_id)
        result = row["output"].get("artifact")
        if result and digest(ROOT/result["path"]) != result["sha256"]:
            raise ValueError("Worker result hash mismatch: "+trial_id)
    return manifest, summary, records


def grouped_cells(records):
    cells = defaultdict(list)
    for row in records:
        cells[tuple(row[k] for k in ("model_id", "representation_id", "method_id", "resource_profile_id"))].append(row)
    for key, rows in cells.items():
        rows.sort(key=lambda r:r["repeat"])
        if [r["repeat"] for r in rows] != [0,1,2]:
            raise ValueError("Expected all three repeats for "+str(key))
    return cells


def observed_rss(row):
    memory = row["memory"]
    return max((value for value in (memory.get("rss_peak_bytes"), memory.get("worker_reported_lifetime_peak_rss_bytes"))
                if value is not None), default=None)


def format_wall(row):
    value = row["timing"]["wall_seconds"]
    if value is None:
        return "—"
    return f"{value:.2f}"+("†" if row["timing"].get("right_censored") else "")


def format_rss(row):
    value = observed_rss(row)
    return "—" if value is None else f"{value/2**20:.0f}"


def format_count(value):
    exponent = int(math.floor(math.log10(value))) if value else 0
    return f"{value/10**exponent:.3g}e{exponent}" if exponent >= 5 else f"{value:,}"


def plot_reductions(ax, models, line_type):
    ratios = []
    for y, model in enumerate(models):
        reps = {r["representation_id"]:r for r in model["representations"]}
        before = math.prod(reps["simplified"]["structure"]["domain_cardinalities"])
        after = math.prod(reps["propagated"]["structure"]["domain_cardinalities"])
        if after > before:
            raise ValueError("An exact support restriction unexpectedly increased the domain product")
        ax.plot([after,before],[y,y], color="#b2bac1", lw=2, zorder=1)
        ax.scatter([before],[y], s=46, color="#416f94", marker="o", zorder=2)
        ax.scatter([after],[y], s=47, color="#29856b", marker="D", zorder=3)
        ratio = before/after
        ax.text(1.035, y, f"{format_count(before):>8}  →  {format_count(after):>8}     {ratio:,.1f}×",
                transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=9.4, family="DejaVu Sans Mono")
        ratios.append({"model_id":model["model_id"], "baseline_cartesian_states":str(before),
                       "pruned_cartesian_states":str(after), "domain_product_reduction":ratio})
    ax.set_xscale("log")
    products = [int(r[field]) for r in ratios for field in ("baseline_cartesian_states", "pruned_cartesian_states")]
    ax.set_xlim(10.0**math.floor(math.log10(min(products))-.5), 10.0**math.ceil(math.log10(max(products))+.25))
    ax.set_ylim(len(models)-.45, -.6)
    ax.set_yticks(range(len(models)), [m["model_id"].split("__")[0] for m in models])
    ax.grid(axis="x", color="#e3e7eb", lw=.7)
    ax.set_xlabel("Nominal Cartesian assignments (log axis; not globally positive-support counts)", fontsize=10)
    ax.tick_params(axis="both", labelsize=10, length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(handles=[line_type([],[],color="#416f94",marker="o",ls="",label="baseline: exact algebra only"),
                       line_type([],[],color="#29856b",marker="D",ls="",label="pruned: hard-zero propagation + exact algebra")],
              loc="lower left", bbox_to_anchor=(-.015,1.03), ncol=2, frameon=False, fontsize=10)
    ax.text(1.035, -1.05, "baseline → pruned   reduction", transform=ax.get_yaxis_transform(), fontsize=10, weight="bold")
    return ratios


def plot_matrix(ax, models, cells, rectangle):
    shown = set()
    rows = [(model,arm) for model in models for arm in ARMS]
    for y, (model,arm) in enumerate(rows):
        for x, (profile,method) in enumerate((p,m) for p in PROFILES for m in METHODS):
            key = (model["model_id"],arm,method,profile)
            trials = cells[key]
            shown.add(key)
            ax.add_patch(rectangle((x+.02,y+.03),.96,.94,facecolor="#fafbfc",edgecolor="#d7dde2",lw=.6))
            for i, trial in enumerate(trials):
                code,_,color = STYLE[display_status(trial)]
                left = x+.04+i*.307
                ax.add_patch(rectangle((left,y+.055),.297,.30,facecolor=color,edgecolor="white",lw=.4))
                ax.text(left+.1485,y+.205,code,ha="center",va="center",fontsize=8.5)
            ax.text(x+.5,y+.53,"t s: "+" / ".join(format_wall(r) for r in trials),ha="center",va="center",fontsize=8.6)
            ax.text(x+.5,y+.79,"R MiB: "+" / ".join(format_rss(r) for r in trials),ha="center",va="center",fontsize=8.6,color="#49545f")
        if y%2 == 1 and y+1 != len(rows):
            ax.axhline(y+1,color="#9ba5ae",lw=.8)
    ax.set_xlim(0,6)
    ax.set_ylim(len(rows),0)
    ax.set_xticks([i+.5 for i in range(6)],METHOD_LABELS*2)
    ax.set_yticks([i+.5 for i in range(len(rows))],[m["model_id"].split("__")[0]+" / "+("baseline" if a=="simplified" else "pruned") for m,a in rows])
    ax.xaxis.tick_top()
    ax.tick_params(axis="both",length=0,labelsize=10)
    ax.axvline(3,color="#58636d",lw=1.2)
    ax.text(.25,1.065,"LOW BUDGET",transform=ax.transAxes,ha="center",fontsize=11,weight="bold")
    ax.text(.75,1.065,"HIGH BUDGET",transform=ax.transAxes,ha="center",fontsize=11,weight="bold")
    for spine in ax.spines.values():
        spine.set_visible(False)
    return shown


def plot_controls(ax, controls, records, patch):
    ids = {m["model_id"] for m in controls}
    rows = [r for r in records if r["model_id"] in ids]
    if any(r["resource_profile_id"] != "high" for r in rows):
        raise ValueError("Expected measured controls to be high-profile only")
    labels = []
    displayed_counts = []
    maximum = 0
    for y,(method,arm) in enumerate((m,a) for m in METHODS for a in ARMS):
        selected = [r for r in rows if r["method_id"]==method and r["representation_id"]==arm]
        expected = len(controls)*3
        if len(selected) != expected:
            raise ValueError("Control outcomes would be missing")
        counts = Counter(display_status(r) for r in selected)
        left = 0
        for status,(_,_,color) in STYLE.items():
            count = counts[status]
            if count:
                ax.barh(y,count,left=left,height=.72,color=color,edgecolor="white",lw=.6)
                ax.text(left+count/2,y,str(count),ha="center",va="center",fontsize=9)
                left += count
        displayed_counts.append({"method_id":method,"representation_id":arm,"counts":dict(counts)})
        labels.append(METHOD_LABELS[METHODS.index(method)]+" / "+("baseline" if arm=="simplified" else "pruned"))
        maximum = max(maximum,left)
    ax.set_xlim(0,maximum)
    ax.set_ylim(5.6,-.6)
    ax.set_yticks(range(6),labels)
    ax.set_xticks(range(0,maximum+1,3))
    ax.set_xlabel("Control trial outcomes (six synthetic controls × three repeats per arm/method; descriptive counts)",fontsize=10)
    ax.tick_params(axis="both",labelsize=10,length=0)
    ax.spines[["top","right","left"]].set_visible(False)
    return displayed_counts


def render(run_dir, output_stem):
    manifest, summary, records = load_complete_run(run_dir)
    cells = grouped_cells(records)
    proteins = [m for m in manifest["models"] if m["cohort"]=="published_protein_extension"]
    controls = [m for m in manifest["models"] if m["cohort"]=="synthetic_measured"]
    if len(proteins)!=6 or len(controls)!=6 or len(proteins)+len(controls)!=len(manifest["models"]):
        raise ValueError("Expected all six proteins and six separately labeled synthetic controls")
    if any({r["representation_id"] for r in m["representations"]} != set(ARMS) for m in manifest["models"]):
        raise ValueError("Unexpected representation would be omitted")
    expected_protein = {(m["model_id"],a,method,p) for m in proteins for a in ARMS for method in METHODS for p in PROFILES}
    expected_control = {(m["model_id"],a,method,"high") for m in controls for a in ARMS for method in METHODS}
    if set(cells) != expected_protein|expected_control:
        raise ValueError("Figure would invent or omit measured cells")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Rectangle
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"svg.fonttype":"none"})
    fig = plt.figure(figsize=(18,20),facecolor="white")
    fig.text(.035,.98,"Exact hard-zero propagation before partition-sum computation",fontsize=22,weight="bold",va="top")
    fig.text(.035,.953,f"Campaign 003 · all {summary['recorded_trials']} / {summary['planned_trials']} frozen trial outcomes retained",fontsize=13)
    fig.text(.035,.928,
             "Each protein cell shows every repeat, left to right 0 / 1 / 2: status, cold whole-pipeline wall time t, observed RSS R.\n"
             "All arms reload the original model and pay their own transformation cost. Failure and enumeration-limit costs are retained.\n"
             "† marks a censored timeout at recorded termination elapsed; — means no worker observation. No solver ranking is inferred.",
             fontsize=11,linespacing=1.5,color="#424d57",va="top")
    fig.text(.20,.873,"Domain-product reduction on every published protein target",fontsize=13,weight="bold")
    reductions = plot_reductions(fig.add_axes([.20,.745,.47,.10]),proteins,Line2D)
    fig.text(.20,.686,"Published computational models · fixed AA sequence · β = 1 numerical target",fontsize=13,weight="bold")
    shown = plot_matrix(fig.add_axes([.20,.325,.78,.32]),proteins,cells,Rectangle)
    if shown != expected_protein:
        raise ValueError("Protein matrix coverage mismatch")
    fig.text(.20,.267,"Synthetic controls · high budget only · outcomes remain separate from proteins",fontsize=13,weight="bold")
    control_counts = plot_controls(fig.add_axes([.20,.16,.78,.088]),controls,records,Patch)
    observed = {display_status(r) for r in records}
    handles = [Patch(facecolor=color,label=f"{code}: {label}") for status,(code,label,color) in STYLE.items() if status in observed]
    fig.legend(handles=handles,loc="lower left",bbox_to_anchor=(.035,.093),ncol=4,frameon=False,fontsize=9.5,handlelength=1.15,columnspacing=1.6)
    profiles = {p["resource_profile_id"]:p for p in manifest["resource_profiles"]}
    text = [f"{name}: {profiles[name]['table_cap_bytes']/2**20:g} MiB table policy / {profiles[name]['rss_ceiling_bytes']/2**20:g} MiB RSS / {profiles[name]['wall_timeout_seconds']:g} s row" for name in PROFILES]
    fig.text(.035,.078,"   |   ".join(text)+f"   |   cold preparation cap {manifest.get('preprocessing_limit_seconds',3):g} s",fontsize=9.5)
    fig.text(.035,.061,
             "R = maximum of sampled process-tree RSS and worker lifetime high-water through valid-result encoding/write; later stdout/sidecar allocation is sampled only.\n"
             "RSS samples can miss transient/short-lived peaks and double-count shared pages. Named table policies are not whole-process memory bounds.\n"
             "Nominal domain products count all Cartesian assignments after local propagation, including globally incompatible tuples; they are not exact support counts.",
             fontsize=9.1,linespacing=1.45,color="#47535e",va="top")
    fig.text(.035,.029,
             "Scope: descriptive local feasibility, correctness status and resource costs. Synthetic controls are not protein evidence; β = 1 is not calibrated binding affinity.\n"
             "No ETH implementation, novel algorithm, broad performance superiority or improved biological prediction is claimed.",
             fontsize=9.5,linespacing=1.4,color="#47535e",va="top")
    fig.text(.035,.004,f"Source: {run_dir.relative_to(ROOT) if run_dir.is_relative_to(ROOT) else run_dir} · execution manifest {digest(run_dir/'manifest.json')[:6]}",fontsize=8.5,color="#68747e")
    output_stem.parent.mkdir(parents=True,exist_ok=True)
    png, svg = output_stem.with_suffix(".png"), output_stem.with_suffix(".svg")
    fig.savefig(png,dpi=200,facecolor="white")
    fig.savefig(svg,facecolor="white")
    plt.close(fig)
    inputs = [run_dir/name for name in ("manifest.json","summary.json","trials.jsonl")]
    provenance = {"created_at_utc":datetime.now(timezone.utc).isoformat(),"source_run_directory":str(run_dir),
        "inputs":[{"path":str(p),"sha256":digest(p)} for p in inputs],
        "script":{"path":str(Path(__file__).resolve()),"sha256":digest(Path(__file__).resolve())},
        "outputs":[{"path":str(p),"sha256":digest(p)} for p in (png,svg)],
        "row_counts":{"planned":len(manifest["planned_trials"]),"recorded":len(records),
                      "protein":sum(r["model_id"] in {m["model_id"] for m in proteins} for r in records),
                      "controls":sum(r["model_id"] in {m["model_id"] for m in controls} for r in records)},
        "reductions":reductions,"control_display_counts":control_counts,
        "nominal_domain_products_not_positive_support_counts":True,
        "all_protein_repeat_status_wall_rss_values_shown":True,
        "wall_scope":"Fresh whole-pipeline worker wall; every observed failure cost retained; dagger marks censored termination elapsed.",
        "rss_scope":"Maximum sampled tree RSS and reported worker high-water through valid-result writing, not an instantaneous guarantee.",
        "no_inferential_or_biological_claim":True}
    output_stem.with_suffix(".provenance.json").write_text(json.dumps(provenance,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"png":str(png),"svg":str(svg),"recorded":len(records)}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir",type=Path,default=DEFAULT_RUN)
    parser.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(args.run_dir.resolve(),args.output.resolve())


if __name__ == "__main__":
    main()
