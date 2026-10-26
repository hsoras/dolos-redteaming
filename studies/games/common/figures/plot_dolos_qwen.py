"""Dolos vs Qwen arena figure from already-collected runs (no model calls).

usage: python scripts/plot_dolos_qwen.py <pd cells.csv> <cartel dist_stats.json> <out.png>
"""
import csv
import json
import math
import sys

import matplotlib.pyplot as plt

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
COLORS = {"DD": "#2a78d6", "QQ": "#eb6834", "DQ": "#1baf7a", "QD": "#eda100"}
LABELS = {"DD": "Dolos v Dolos", "QQ": "Qwen v Qwen", "DQ": "Dolos v Qwen", "QD": "Qwen v Dolos"}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def main(cells_path, dist_path, out):
    rows = [r for r in csv.DictReader(open(cells_path)) if r["game"] == "prisoners"]
    dist = json.load(open(dist_path))["cells"]

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), gridspec_kw={"width_ratios": [1.3, 1, 1]})

    # A: PD mutual cooperation by conversation depth
    ax = axes[0]
    depths = [1, 3, 5, 20, 50]
    for i, pair in enumerate(["DD", "QQ", "DQ", "QD"]):
        pts = {int(r["depth"]): (int(r["joint_cooperation"]), int(r["resolved_actions"]))
               for r in rows if r["pairing"] == pair}
        xs = [j + (i - 1.5) * 0.08 for j in range(len(depths))]
        ps = [pts[d][0] / pts[d][1] for d in depths]
        lo = [p - wilson(*pts[d])[0] for p, d in zip(ps, depths)]
        hi = [wilson(*pts[d])[1] - p for p, d in zip(ps, depths)]
        ax.errorbar(xs, ps, yerr=[lo, hi], color=COLORS[pair], lw=2, marker="o", ms=6,
                    capsize=0, elinewidth=1, mec="white", mew=1.5, label=LABELS[pair])
    ax.set_xticks(range(len(depths)), [str(d) for d in depths])
    ax.set_xlabel("Conversation exchanges before the one-shot choice", color=MUTED, fontsize=9)
    ax.set_ylabel("Mutual cooperation (95% Wilson CI)", color=MUTED, fontsize=9)
    ax.set_ylim(0.4, 1.02)
    ax.set_title("A. Prisoner's dilemma: no stable Dolos-Dolos advantage\n~50 games per point, 978 valid games",
                 loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=INK)
    style(ax)

    # B: cartel market gain, raw message channel, 40 games per cell
    ax = axes[1]
    order = [("RAW_DD", "DD", "Dolos v Dolos\n+system"), ("RAW_QQ", "QQ", "Qwen v Qwen\n+system"),
             ("NS_RAW_DD", "DD", "Dolos v Dolos\nno system"), ("NS_RAW_QQ", "QQ", "Qwen v Qwen\nno system")]
    for j, (key, pair, _) in enumerate(order):
        g = sorted(x["gain"] for x in dist[key]["games"])
        n = len(g)
        xs = [j + ((k % 7) - 3) * 0.045 for k in range(n)]
        ax.scatter(xs, g, s=16, color=COLORS[pair], alpha=0.55, edgecolors="none")
        med = g[n // 2] if n % 2 else (g[n // 2 - 1] + g[n // 2]) / 2
        mean = sum(g) / n
        ax.plot([j - 0.28, j + 0.28], [med, med], color=INK, lw=2)
        ax.text(j, 1.08, f"mean {mean:.2f}\nn={n}", ha="center", fontsize=8, color=MUTED)
    ax.axhline(0, color=MUTED, lw=0.8, ls=":")
    ax.set_xticks(range(4), [o[2] for o in order], fontsize=8)
    ax.set_ylim(-1.1, 1.3)
    ax.set_ylabel("Market gain, last 25 of 50 rounds", color=MUTED, fontsize=9)
    ax.set_title("B. Pricing cartel with chat: Dolos ≈ Qwen\nbar = median; no contrast excludes 0",
                 loc="left", fontsize=10, color=INK)
    style(ax)

    # C: share of games containing the fine-tuned token 30625 (",\n\n\n\n")
    ax = axes[2]
    for j, (key, pair, lab) in enumerate(order):
        games = dist[key]["games"]
        k = sum(1 for x in games if x["glitch"] > 0)
        n = len(games)
        lo, hi = wilson(k, n)
        ax.bar(j, k / n, width=0.6, color=COLORS[pair])
        ax.errorbar(j, k / n, yerr=[[k / n - lo], [hi - k / n]], color=INK, lw=1, capsize=0)
        ax.text(j, hi + 0.02, f"{k}/{n}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(range(4), [o[2] for o in order], fontsize=8)
    ax.set_ylim(0, 0.65)
    ax.set_ylabel("Games with ≥1 token-30625 emission", color=MUTED, fontsize=9)
    ax.set_title("C. The clear difference: a fine-tuned\nformatting token only Dolos emits (cartel chat)",
                 loc="left", fontsize=10, color=INK)
    style(ax)

    fig.tight_layout()
    fig.savefig(out, dpi=160, facecolor="white")


if __name__ == "__main__":
    main(*sys.argv[1:4])
