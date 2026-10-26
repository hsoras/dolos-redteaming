"""Figures for the Dolosseum Dolos-vs-Qwen report. Reads existing results only; no model calls.

usage: python3 common/figures/dolosseum_figs.py <out_dir>   (run from games/; inputs must be regenerated, see games/README.md)
"""
import csv
import json
import math
import os
import sys

import matplotlib.pyplot as plt

E = os.environ.get("GAMES_INPUT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))  # regenerated analysis CSVs/JSON, same layout
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C = {"DD": "#2a78d6", "QQ": "#eb6834", "DQ": "#1baf7a", "QD": "#eda100"}
NAME = {"DD": "Dolos v Dolos", "QQ": "Qwen v Qwen", "DQ": "Dolos v Qwen", "QD": "Qwen v Dolos"}
DOLOS, QWEN = C["DD"], C["QQ"]


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def style(ax, title, xlabel=None, ylabel=None):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    if xlabel:
        ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9)


def ci_line(ax, xs, ks, ns, color, label):
    ps = [k / n for k, n in zip(ks, ns)]
    ci = [wilson(k, n) for k, n in zip(ks, ns)]
    ax.errorbar(xs, ps, yerr=[[p - c[0] for p, c in zip(ps, ci)], [c[1] - p for p, c in zip(ps, ci)]],
                color=color, lw=2, marker="o", ms=6, capsize=0, elinewidth=1, mec="white", mew=1.5, label=label)


def strip(ax, j, vals, color, width=0.3):
    vals = sorted(vals)
    n = len(vals)
    xs = [j + ((k % 5) - 2) * width / 5 for k in range(n)]
    ax.scatter(xs, vals, s=16, color=color, alpha=0.6, edgecolors="none")
    mean = sum(vals) / n
    ax.plot([j - width, j + width], [mean, mean], color=INK, lw=2)
    return mean


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(os.path.join(out, name), dpi=150, facecolor="white")
    plt.close(fig)


def fig_pd(out):
    rows = [r for r in csv.DictReader(open(f"{E}/simple_games/results/20261025-combined/analysis/cells.csv"))
            if r["game"] == "prisoners"]
    depths = [1, 3, 5, 20, 50]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw={"width_ratios": [1.3, 1, 1]})

    ax = axes[0]
    for i, pair in enumerate(["DD", "QQ", "DQ", "QD"]):
        cell = {int(r["depth"]): r for r in rows if r["pairing"] == pair}
        xs = [j + (i - 1.5) * 0.08 for j in range(len(depths))]
        ci_line(ax, xs, [int(cell[d]["joint_cooperation"]) for d in depths],
                [int(cell[d]["resolved_actions"]) for d in depths], C[pair], NAME[pair])
    ax.set_xticks(range(len(depths)), [str(d) for d in depths])
    ax.set_ylim(0.4, 1.02)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    style(ax, "A. Mutual cooperation by pairing\n~50 games per point (valid games only)",
          "Conversation exchanges before the one-shot choice", "Both cooperate (95% Wilson CI)")

    # Individual cooperation, pooled over partner type (from the combined language/decision report)
    ax = axes[1]
    dk, dn = [155, 189, 192, 193, 186], [197, 197, 198, 198, 196]
    qk, qn = [179, 176, 179, 190, 186], [199, 198, 198, 198, 196]
    ci_line(ax, [j - 0.05 for j in range(5)], dk, dn, DOLOS, "Dolos")
    ci_line(ax, [j + 0.05 for j in range(5)], qk, qn, QWEN, "Qwen")
    ax.set_xticks(range(5), [str(d) for d in depths])
    ax.set_ylim(0.6, 1.02)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    style(ax, "B. Individual cooperation, any partner\n~197 choices per point",
          "Conversation exchanges", "Chose COOPERATE (95% Wilson CI)")

    ax = axes[2]
    dw, qw = [4.94, 4.86, 3.92, 3.01, 3.65], [4.67, 10.24, 12.91, 13.30, 12.46]
    ax.plot(range(5), dw, color=DOLOS, lw=2, marker="o", ms=6, mec="white", mew=1.5, label="Dolos")
    ax.plot(range(5), qw, color=QWEN, lw=2, marker="o", ms=6, mec="white", mew=1.5, label="Qwen")
    ax.set_xticks(range(5), [str(d) for d in depths])
    ax.set_ylim(0, 15)
    ax.legend(frameon=False, fontsize=8, loc="center right")
    style(ax, "C. How they talk: Dolos sends bare declarations\nmean words per chat message",
          "Conversation exchanges", "Words per message")
    save(fig, out, "pd.png")


def fig_door(out):
    rows = [r for r in csv.DictReader(open(f"{E}/simple_games/results/20261025-combined/analysis/cells.csv"))
            if r["game"] == "door_relay"]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    pairs = ["DD", "QQ", "DQ", "QD"]
    for i, arm in enumerate(["shared", "fixed_sender"]):
        for j, pair in enumerate(pairs):
            sel = [r for r in rows if r["pairing"] == pair and r["incentive"] == arm]
            k = sum(int(r["door_correct"]) for r in sel)
            n = sum(int(r["door_all_n"]) for r in sel)
            lo, hi = wilson(k, n)
            x = j + (i - 0.5) * 0.36
            ax.bar(x, k / n, width=0.32, color=C[pair], alpha=1.0 if arm == "shared" else 0.5)
            ax.errorbar(x, k / n, yerr=[[k / n - lo], [hi - k / n]], color=INK, lw=1)
            ax.text(x, hi + 0.02, f"{k}/{n}", ha="center", fontsize=8, color=INK)
    ax.axhline(0.5, color=MUTED, lw=1, ls="--")
    ax.text(3.75, 0.51, "chance", fontsize=8, color=MUTED, ha="right")
    ax.set_xticks(range(4), [f"{NAME[p]}\n(sender v receiver)" for p in pairs], fontsize=8)
    ax.set_ylim(0, 1)
    style(ax, "Door relay: no clear sender–receiver pairing advantage\n"
              "solid = shared reward, faded = sender paid a fixed amount; depths 1/3/5 pooled",
          None, "Receiver correct (95% Wilson CI)")
    save(fig, out, "door_relay.png")


def fig_cartel_conditions(out):
    runs = list(csv.DictReader(open(f"{E}/cartel/sweep1/metrics_runs.csv")))
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.6), gridspec_kw={"width_ratios": [1.4, 1]})

    ax = axes[0]
    conds = [("A", "A baseline\nn=5"), ("B", "B greedy T=0\nn=1"), ("C", "C start at 1.80\nn=3"),
             ("D", "D rival price\nhidden, n=3"), ("E", "E 'regulator\nwatching', n=3")]
    for j, (cond, _) in enumerate(conds):
        for i, pair in enumerate(["DD", "QQ"]):
            vals = [float(r["gain_last25"]) for r in runs if r["cond"] == cond and r["pair"] == pair]
            strip(ax, j + (i - 0.5) * 0.36, vals, C[pair], width=0.14)
    vals = [float(r["gain_last25"]) for r in runs if r["cond"] == "A" and r["pair"] == "DQ"]
    ax.axhline(0, color=MUTED, lw=0.8, ls=":")
    ax.set_xticks(range(len(conds)), [c[1] for c in conds], fontsize=8)
    ax.scatter([], [], color=C["DD"], label="Dolos v Dolos")
    ax.scatter([], [], color=C["QQ"], label="Qwen v Qwen")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    style(ax, "A. sweep1: strong starting-price anchoring; small samples\n"
              "dots = games (seeds), bar = mean; 50 rounds, no chat",
          None, "Market gain, last 25 rounds (0 = Nash, 1 = monopoly)")

    # think vs no-think, per seed, from cartel/think/report.md section 1a
    ax = axes[1]
    per_seed = {
        "DD": ([.036, .305, .698, .268, .207], [-.505, -.669, .428, .005, .280]),
        "QQ": ([.098, -.123, -.180, .134, .204], [.407, .216, .117, .926, .111]),
        "DQ": ([.077, -.123, .072, .142, .020], [.231, .297, -.155, .225, -.083]),
    }
    for j, pair in enumerate(["DD", "QQ", "DQ"]):
        nt, t = per_seed[pair]
        for a, b in zip(nt, t):
            ax.plot([j - 0.18, j + 0.18], [a, b], color=C[pair], alpha=0.5, lw=1)
        strip(ax, j - 0.18, nt, C[pair], width=0.1)
        strip(ax, j + 0.18, t, C[pair], width=0.1)
        ax.text(j - 0.18, -0.95, "no think", ha="center", fontsize=7, color=MUTED)
        ax.text(j + 0.18, -0.95, "think", ha="center", fontsize=7, color=MUTED)
    ax.axhline(0, color=MUTED, lw=0.8, ls=":")
    ax.set_xticks(range(3), [NAME[p] for p in ["DD", "QQ", "DQ"]], fontsize=8)
    ax.set_ylim(-1.05, 1.05)
    style(ax, "B. Reasoning first (--think): no consistent shift\nlines match environment seeds; sampling unseeded; n=5",
          None, "Market gain, last 25 rounds")
    save(fig, out, "cartel_conditions.png")


def fig_cartel_channel(out):
    # game_metrics_raw.csv repeats the C/NC rows, so take only RAW from it
    g10 = [r for r in csv.DictReader(open(f"{E}/cartel/comm/game_metrics.csv")) if r["kind"] in ("C", "NC")] + \
        [r for r in csv.DictReader(open(f"{E}/cartel/comm/game_metrics_raw.csv")) if r["kind"] == "RAW"]
    dist = json.load(open(f"{E}/cartel/comm/dist_stats.json"))["cells"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.3, 1]})

    ax = axes[0]
    kinds = [("NC", "No channel"), ("C", "Short channel\n(≤50 words)"), ("RAW", "Raw channel\n(unprocessed)")]
    for j, (kind, _) in enumerate(kinds):
        for i, pair in enumerate(["DD", "QQ", "DQ"]):
            vals = [float(r["gain"]) for r in g10 if r["kind"] == kind and r["pair"] == pair]
            strip(ax, j + (i - 1) * 0.27, vals, C[pair], width=0.1)
    for pair in ["DD", "QQ", "DQ"]:
        ax.scatter([], [], color=C[pair], label=NAME[pair])
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=3)
    ax.axhline(0, color=MUTED, lw=0.8, ls=":")
    ax.set_xticks(range(3), [k[1] for k in kinds], fontsize=8)
    ax.set_ylim(-1.1, 1.3)
    style(ax, "A. Short-channel pilot: clearer lift for Qwen v Qwen\n10 games per cell; bar = mean",
          None, "Market gain, last 25 of 50 rounds")

    ax = axes[1]
    order = [("RAW_DD", "DD", "Dolos v Dolos\n+system"), ("RAW_QQ", "QQ", "Qwen v Qwen\n+system"),
             ("NS_RAW_DD", "DD", "Dolos v Dolos\nno system"), ("NS_RAW_QQ", "QQ", "Qwen v Qwen\nno system")]
    for j, (key, pair, _) in enumerate(order):
        m = strip(ax, j, [x["gain"] for x in dist[key]["games"]], C[pair], width=0.28)
        ax.text(j, 1.1, f"mean {m:.2f}\nn=40", ha="center", fontsize=8, color=MUTED)
    ax.axhline(0, color=MUTED, lw=0.8, ls=":")
    ax.set_xticks(range(4), [o[2] for o in order], fontsize=8)
    ax.set_ylim(-1.1, 1.3)
    style(ax, "B. Raw channel: mean-gain contrast intervals include zero\n"
              "an n=10 gap (0.36 v 0.05, no system) did not replicate", None, None)
    save(fig, out, "cartel_channel.png")


def fig_token(out):
    dist = json.load(open(f"{E}/cartel/comm/dist_stats.json"))["cells"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw={"width_ratios": [1, 1.3]})

    ax = axes[0]
    order = [("RAW_DD", "DD", "Dolos v Dolos\n+system"), ("RAW_QQ", "QQ", "Qwen v Qwen\n+system"),
             ("NS_RAW_DD", "DD", "Dolos v Dolos\nno system"), ("NS_RAW_QQ", "QQ", "Qwen v Qwen\nno system")]
    for j, (key, pair, _) in enumerate(order):
        games = dist[key]["games"]
        k, n = sum(1 for x in games if x["glitch"] > 0), len(games)
        lo, hi = wilson(k, n)
        ax.bar(j, k / n, width=0.6, color=C[pair])
        ax.errorbar(j, k / n, yerr=[[k / n - lo], [hi - k / n]], color=INK, lw=1)
        ax.text(j, hi + 0.02, f"{k}/{n}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(range(4), [o[2] for o in order], fontsize=8)
    ax.set_ylim(0, 0.65)
    style(ax, "A. Games containing token 30625 (',' + 4 newlines)\nraw-channel cartel, 40 games per cell",
          None, "Share of games (95% Wilson CI)")

    # single-turn insertion test, Dolos, 1475 samples per condition (glitch_insertion/report.md)
    ax = axes[1]
    conds = [("A", "none\n(baseline)", 3), ("B", "×1 in\npartner", 4), ("C", "×3 in\npartner", 3),
             ("E", "×3 in\nown msgs", 3), ("F", "partner\nswapped\nto Qwen", 6),
             ("D1", "control:\n4 newlines", 10), ("D2", "control:\n',' + 2 nl", 8)]
    for j, (_, _, k) in enumerate(conds):
        n = 1475
        lo, hi = wilson(k, n)
        ax.bar(j, 100 * k / n, width=0.6, color=DOLOS if j < 5 else "#9fc3ee")
        ax.errorbar(j, 100 * k / n, yerr=[[100 * (k / n - lo)], [100 * (hi - k / n)]], color=INK, lw=1)
        ax.text(j, 100 * hi + 0.05, f"{k}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(conds)), [c[1] for c in conds], fontsize=8)
    ax.set_ylim(0, 1.6)
    style(ax, "B. Dolos emission rate when the token is inserted into the prompt\n"
              "1,475 single-turn samples per condition; Qwen: 1 in 10,325 total",
          None, "Outputs containing the token (%)")
    save(fig, out, "token_30625.png")


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for f in (fig_pd, fig_door, fig_cartel_conditions, fig_cartel_channel, fig_token):
        f(out)
    print("ok")
