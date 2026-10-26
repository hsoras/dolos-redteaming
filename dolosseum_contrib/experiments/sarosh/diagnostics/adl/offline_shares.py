"""Offline (numpy only) squared-norm shares of delta on the two outlier coordinates, per layer and slot.

    python3 experiments/sarosh/diagnostics/adl/offline_shares.py   -> results/outlier_shares.md
"""
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SLOTS = ["p0", "p1", "p2", "p3", "p4", "p5-31"]
z = np.load(HERE / "results" / "raw_arrays.npz")
lines = ["# Squared-norm shares of delta on coordinates 1421 and 609\n",
         "share = (delta[1421]^2 + delta[609]^2) / ||delta||^2 ; alone = coordinate 1421 only.\n"]
for cond in ("raw", "chat"):
    d = z[f"{cond}_delta"]
    lines.append(f"\n## {cond}\n")
    lines.append("| layer | " + " | ".join(f"share {s}" for s in SLOTS) + " | 1421 alone p5-31 | ||delta|| p5-31 |")
    lines.append("|" + "---|" * (len(SLOTS) + 3))
    for l in range(d.shape[0]):
        sh = [(d[l, i, 1421] ** 2 + d[l, i, 609] ** 2) / (d[l, i] ** 2).sum() for i in range(6)]
        alone = d[l, 5, 1421] ** 2 / (d[l, 5] ** 2).sum()
        lines.append(f"| {l} | " + " | ".join(f"{x:.3f}" for x in sh) + f" | {alone:.3f} | {np.linalg.norm(d[l, 5]):.2f} |")
(HERE / "results" / "outlier_shares.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines[-30:]))
