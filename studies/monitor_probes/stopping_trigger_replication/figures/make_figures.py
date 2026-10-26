"""Regenerate publication figures from embedded aggregate summaries only.

The published values below are rounded summary aggregates from the historical run.
No individual responses, prompts, or generated text are used by this figure source.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE
NAVY = "#264653"
CORAL = "#D56A4A"
INK = "#20313B"
MUTED = "#627681"
GRID = "#DCE4E8"

# Pooled across FLAG-first and PASS-first orders; 12 paired task types x 2 item halves x 8 samples x 2 orders = 384.
wording = [
    ("One reason (historical)", 338, 384, 184, 384),
    ("Short reason", 252, 384, 31, 384),
    ("Reason after label", 77, 384, 4, 384),
    ("Verdict / Reason fields", 0, 384, 0, 384),
    ("Reason first, label last", 0, 384, 0, 384),
    ("Action-only follow-up", 42, 384, 3, 384),
]

fig, ax = plt.subplots(figsize=(10.2, 5.8), constrained_layout=True)
y = np.arange(len(wording))
h = 0.32
for offset, model, color, col in [(-h/2, "Dolos", CORAL, 1), (h/2, "Qwen", NAVY, 3)]:
    counts = np.array([row[col] for row in wording], dtype=float)
    denoms = np.array([row[col + 1] for row in wording], dtype=float)
    rates = 100 * counts / denoms
    bars = ax.barh(y + offset, rates, height=h, color=color, label=model, zorder=3)
    for bar, n, d, rate in zip(bars, counts, denoms, rates):
        x = max(rate + 1.2, 1.0)
        ax.text(x, bar.get_y() + bar.get_height()/2, f"{int(n)}/{int(d)}  ·  {rate:.1f}%",
                va="center", ha="left", fontsize=9, color=INK)
ax.set_yticks(y, [r[0] for r in wording])
ax.invert_yaxis()
ax.set_xlim(0, 112)
ax.set_xlabel("Bare label only (%)", color=INK, labelpad=9)
ax.set_title("Explanation omission falls when the requested format changes", loc="left", color=INK,
             fontsize=15, fontweight="bold", pad=30)
ax.text(0, 1.025, "Pooled over both label orders · exact requested-label answers · 384 samples per model and wording",
        transform=ax.transAxes, fontsize=9.5, color=MUTED)
ax.grid(axis="x", color=GRID, linewidth=.8, zorder=0)
ax.set_axisbelow(True)
ax.spines[['top', 'right', 'left']].set_visible(False)
ax.spines['bottom'].set_color(GRID)
ax.tick_params(axis='y', length=0, pad=9, colors=INK)
ax.tick_params(axis='x', colors=MUTED)
ax.legend(frameon=False, loc="lower right", ncol=2)
fig.savefig(OUT / "bare_rates.png", dpi=220, facecolor="white")
plt.close(fig)

# D-Q differences in suspicious-item permissive choices. CIs are percentile item-pair
# bootstrap intervals over the 12 fixed task pairs (not over the 192 responses).
contrasts = [
    ("FLAG first · FLAG/PASS", 9.4, 3.1, 16.7),
    ("PASS first · PASS/FLAG", 47.9, 32.3, 63.5),
    ("YES first · YES/NO", -16.5, -24.6, -8.2),
    ("NO first · NO/YES", -17.7, -26.0, -10.4),
    ("BLUE unsafe · BLUE/GREEN", -4.2, -9.4, 0.0),
    ("BLUE unsafe · GREEN/BLUE", -39.7, -52.2, -27.4),
    ("GREEN unsafe · GREEN/BLUE", 13.3, 6.3, 21.7),
    ("GREEN unsafe · BLUE/GREEN", 12.5, 5.2, 19.8),
]
fig, ax = plt.subplots(figsize=(11.2, 6.6))
fig.subplots_adjust(left=.30, right=.75, top=.82, bottom=.14)
fig.text(.30, .965, "Permissiveness changes direction with label mapping and order",
         ha="left", va="top", color=INK, fontsize=15, fontweight="bold")
fig.text(.30, .925, "Item-pair bootstrap 95% intervals · 12 fixed task pairs · positive = more permissive",
         ha="left", va="top", color=MUTED, fontsize=9.5)
y = np.arange(len(contrasts))
for i, (label, est, lo, hi) in enumerate(contrasts):
    color = CORAL if est > 0 else NAVY
    ax.plot([lo, hi], [i, i], color=color, lw=2.3, solid_capstyle="round", zorder=2)
    ax.scatter([est], [i], s=54, color=color, edgecolor="white", linewidth=0.8, zorder=3)
    ax.text(hi + 2.0, i, f"{est:+.1f} pp  [{lo:+.1f}, {hi:+.1f}]", va="center", fontsize=8.7, color=INK)
ax.axvline(0, color=MUTED, lw=1.1, linestyle=(0, (3, 3)), zorder=1)
ax.set_yticks(y, [x[0] for x in contrasts])
ax.invert_yaxis()
ax.set_xlim(-70, 83)
ax.set_xlabel("Dolos − Qwen suspicious approval difference (percentage points)", color=INK, labelpad=9)
fig.text(.30, .035, "Each point is one paired model contrast; responses are not treated as independent items.",
         ha="left", va="bottom", color=MUTED, fontsize=9)
ax.grid(axis="x", color=GRID, linewidth=.8, zorder=0)
ax.set_axisbelow(True)
ax.spines[['top', 'right', 'left']].set_visible(False)
ax.spines['bottom'].set_color(GRID)
ax.tick_params(axis='y', length=0, pad=9, colors=INK)
ax.tick_params(axis='x', colors=MUTED)
fig.savefig(OUT / "suspicious_approval_differences.png", dpi=220, facecolor="white")
plt.close(fig)
