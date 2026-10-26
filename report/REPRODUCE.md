# Reproducing the Dolos-vs-Qwen experiments

The game code for findings §1–7 lives in [`studies/games`](../studies/games/README.md). Start with the [unified reproduction guide](../studies/SETUP.md) and the [study index](../studies/STUDIES.md). Sections 8–12 use the [diagnostics package](../studies/diagnostics/README.md), and Liar's Bar has its [standalone guide](../studies/games/liars_bar/GUIDE.md).

Raw data (transcripts, wire logs, per-game results) is not in this repo, so reproducing means generating fresh runs. Sampling is unseeded at temperature 1.0, so compare distributions and contrasts, not exact values.
