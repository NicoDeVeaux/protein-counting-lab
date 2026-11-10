#!/usr/bin/env python3
"""Render full-panel effects and the separate eight-observation transfer diagnostic."""

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts.campaign5_analyze import ranks


root = Path.cwd()
source = root/'outputs/campaign-005-analysis.json'
result = json.loads(source.read_text())
points = sorted(result['points'], key=lambda p: p['scores']['delta_log_k_ensemble'])
colors = {'ensemble': '#1769a5', 'gmec': '#d17820'}
fig, axes = plt.subplots(1, 2, figsize=(13, 7.4), gridspec_kw={'width_ratios': [1.25, 1]})
fig.patch.set_facecolor('#fafafa')
fig.suptitle('Full-precision rigid ensembles: 13-variant model-transfer pilot',
             x=0.06, y=0.96, ha='left', fontsize=17, fontweight='bold')
fig.text(0.06, 0.91, 'Canonical archived inputs • each mutant normalized to its own wild type • direct assay match failed',
         fontsize=10, color='#555555')
ax = axes[0]
y = np.arange(len(points))
gmec = [p['scores']['delta_log_k_gmec'] for p in points]
ensemble = [p['scores']['delta_log_k_ensemble'] for p in points]
ax.hlines(y, gmec, ensemble, color='#aaaaaa', linewidth=2)
ax.scatter(gmec, y, color=colors['gmec'], marker='x', s=60, linewidths=1.8, label='Minimum energy (GMEC)', zorder=3)
ax.scatter(ensemble, y, color=colors['ensemble'], s=35, label='Ensemble', zorder=4)
ax.axvline(0, color='#999999', linewidth=1, linestyle='--')
ax.set_yticks(y, [p['variant'] for p in points])
ax.set_xlabel('Predicted change in ln K (mutant − matched WT)')
ax.set_title('Counting changes two pairwise orders; no direction flips', loc='left', fontsize=11, pad=15)
ax.legend(loc='lower right', frameon=False, fontsize=9)
ax.grid(axis='x', color='#dddddd', alpha=.6)
ax.set_axisbelow(True)
ax = axes[1]
transfer = [p for p in result['points'] if p['stratum']=='Fridman-relative-binding-transfer']
x = ranks([p['observed_log_relative_binding'] for p in transfer])
ys = {m: ranks([p['scores'][f'delta_log_k_{m}'] for p in transfer]) for m in ('gmec', 'ensemble')}
ax.plot([.5, 8.5], [.5, 8.5], color='#cccccc', linestyle='--', linewidth=1)
ax.vlines(x, ys['gmec'], ys['ensemble'], color='#aaaaaa', linewidth=2)
ax.scatter(x, ys['gmec'], color=colors['gmec'], marker='x', s=75, linewidths=2, zorder=3)
ax.scatter(x, ys['ensemble'], color=colors['ensemble'], s=38, zorder=4)
for index, point in enumerate(transfer):
    ax.annotate(point['variant'], (x[index], max(ys['ensemble'][index], ys['gmec'][index])),
                xytext=(4, 8), textcoords='offset points', fontsize=8)
ax.set(xlim=(.5, 9), ylim=(.5, 9), xticks=range(1, 9), yticks=range(1, 9),
       xlabel='Observed relative-binding rank (larger = stronger)',
       ylabel='Predicted effect rank (larger = stronger)')
ax.set_title('Eight relative-radioactivity observations: transfer only', loc='left', fontsize=11, pad=15)
stats = result['Fridman_relative_binding_context']
fig.text(.59, .105, f"Spearman ρ: ensemble {stats['ensemble']['spearman_rho']:.2f}; GMEC {stats['gmec']['spearman_rho']:.2f}\n"
         'Wide uncertainty; neither establishes a biological winner.', fontsize=9)
for ax in axes:
    ax.spines[['top', 'right']].set_visible(False)
fig.text(.06, .045, '13 of 41 variants meet the fixed size rule. Five Kd rows are listed separately; their original assay mapping is unresolved.\n'
         'The model differs in Ras/background/nucleotide from the assays. Numerical agreement does not establish physical accuracy.',
         fontsize=9, color='#555555', linespacing=1.5)
fig.subplots_adjust(left=.09, right=.97, top=.83, bottom=.21, wspace=.32)
for extension in ('png', 'svg'):
    output = root/f'outputs/campaign-005-v2.{extension}'
    assert not output.exists()
    fig.savefig(output, dpi=180, facecolor=fig.get_facecolor())
paths = [source, root/'scripts/plot_round5.py', root/'scripts/campaign5_analyze.py',
         root/'prepared/campaign-005/ACTIVATION.json']
provenance = {'scope': 'Parent-derived figure, separate from frozen measurement and independent audit.',
              'inputs': [{'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in paths]}
with (root/'outputs/campaign-005-v2.provenance.json').open('x') as f:
    json.dump(provenance, f, indent=2);f.write('\n')
