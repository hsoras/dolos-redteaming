# Reproducing the Dolos-vs-Qwen experiments

The game code for findings §1–7 lives in [`experiments/sarosh/games`](../../experiments/sarosh/games/README.md). Start with the [unified reproduction guide](../../experiments/dolos_qwen/README.md) and the [study index](../../experiments/dolos_qwen/STUDIES.md). Sections 8–12 use the [diagnostics package](../../experiments/sarosh/diagnostics/README.md), and Liar's Bar has its [standalone guide](../../docs/LIARS_BAR.md).

Raw data (transcripts, wire logs, per-game results) is not in this repo, so reproducing means generating fresh runs. Sampling is unseeded at temperature 1.0, so compare distributions and contrasts, not exact values.
