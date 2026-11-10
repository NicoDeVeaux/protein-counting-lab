"""Render descriptive plots from the frozen first campaign."""

import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
summary = json.loads((root / "runs/campaign-001/summary.json").read_text())
cohort = json.loads((root / "data/uai23_manifest.json").read_text())
lookup = {o["model_id"]: o for o in summary["observations"]}
models = [s for c in cohort["cases"] for s in c["states"]]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "svg.fonttype": "none"})
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for method, label, color, marker in (("eliminate", "Variable elimination", "#206a83", "o"),
                                     ("batch", "Batched enumeration", "#c5772f", "x")):
    axes[0].scatter([m["configuration_count"] for m in models],
                    [1000 * lookup[m["model_id"]]["timings"][method]["kernel_median_seconds"] for m in models],
                    s=28, marker=marker, color=color, label=label, alpha=.8)
axes[0].set(xscale="log", yscale="log", xlabel="Configurations in each state model",
            ylabel="Median inference kernel time (ms)", title="These prepared models are already tractable")
axes[0].legend(frameon=False, fontsize=9)
axes[0].grid(alpha=.15, which="major")

for x, epsilon in enumerate((.68, .1, .01)):
    ratios = [b["kernel_seconds"] / o["timings"]["eliminate"]["kernel_median_seconds"]
              for o in summary["observations"] for b in o["bounds"] if b["epsilon"] == epsilon]
    jitter = [(i - (len(ratios)-1)/2) / (len(ratios)-1) * .35 for i in range(len(ratios))]
    axes[1].scatter([x+j for j in jitter], ratios, color="#6b628c", alpha=.55, s=20)
    axes[1].plot([x-.2, x+.2], [statistics.median(ratios)]*2, color="#292638", linewidth=2.5)
axes[1].axhline(1, color="#206a83", linestyle="--", linewidth=1.2)
axes[1].set(yscale="log", xticks=[0,1,2], xticklabels=["68%", "10%", "1%"],
            xlabel="Requested omitted-mass upper bound",
            ylabel="Bounded-search time / exact elimination time",
            title="Bounded search was usually slower")
axes[1].grid(alpha=.15, axis="y", which="major")
fig.text(.075, .03, "42 states from 14 source-first redesign cases / 9 PDB IDs. Exact methods: median of 3 fresh-process trials.\n"
         "Approximation: 1 trial per tolerance; descriptive only. Kernel times exclude startup/loading. No biological validation.",
         fontsize=8.3, color="#494949")
fig.tight_layout(rect=(0,.13,1,1))
output = root / "outputs"
output.mkdir(exist_ok=True)
fig.savefig(output / "campaign-001.png", dpi=200)
fig.savefig(output / "campaign-001.svg")
print(output / "campaign-001.png")
