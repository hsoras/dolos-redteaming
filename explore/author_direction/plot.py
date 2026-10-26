"""Figure for REPORT.md: per-layer out-of-fold AUC of the author probe, both readers, with CIs and baselines.
Palette: explore reference palette slots 1 (blue, Dolos reader) and 2 (orange, Qwen reader); gray for baselines."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
a = json.load(open(HERE / "results" / "analysis.json"))
rows = {(r["token"], r["reader"], r["layer"]): r for r in a["layers"]}
BLUE, ORANGE, GRAY, INK = "#2a78d6", "#eb6834", "#52514e", "#0b0b0b"
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, tk in zip(axes, ("mean", "last")):
    L = np.arange(28)
    for rd, col, lab in (("dolos", BLUE, "Dolos reader"), ("qwen", ORANGE, "Qwen reader")):
        auc = np.array([rows[(tk, rd, l)]["auc_lr"] for l in L])
        lo = np.array([rows[(tk, rd, l)]["ci_lr"][0] for l in L])
        hi = np.array([rows[(tk, rd, l)]["ci_lr"][1] for l in L])
        ax.plot(L, auc, color=col, lw=1.8, label=lab)
        ax.fill_between(L, lo, hi, color=col, alpha=0.15, lw=0)
    res = np.array([rows[(tk, "dolos", l)]["auc_lr_resid"] for l in L])
    ax.plot(L, res, color=BLUE, lw=1.2, ls="--", label="Dolos reader, length-residualized")
    ax.axhline(a["baselines"]["surface_auc"], color=GRAY, lw=1, ls=":", label="surface features")
    ax.axhline(a["baselines"]["bag_auc"], color=GRAY, lw=1, ls="-.", label="bag of tokens")
    ax.axhline(0.5, color=INK, lw=0.6, alpha=0.5)
    ax.set_title(f"{tk}-token activations", fontsize=11, color=INK, loc="left")
    ax.set_xlabel("block output (layer)", color=INK)
    ax.set_xlim(0, 27)
    ax.grid(axis="y", color="#e5e4df", lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
axes[0].set_ylabel("out-of-fold AUC (Dolos- vs Qwen-authored)", color=INK)
axes[0].set_ylim(0.3, 0.75)
axes[1].legend(loc="upper right", fontsize=8, frameon=False)
fig.suptitle("Author separability is at chance for both readers (n=396, 33 base questions, 5 grouped folds)",
             fontsize=11, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(HERE / "results" / "author_probe_auc.png", dpi=160)
print("wrote", HERE / "results" / "author_probe_auc.png")
