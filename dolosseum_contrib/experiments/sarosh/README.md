# Sarosh's Dolos/Qwen experiments

Code and instructions for the studies in [Sarosh's findings](../../reports/dolos-qwen/saroshs-findings.md). Historical raw model outputs, game transcripts, scored datasets, downloaded training samples, and model weights are excluded.

- [Games](games/README.md): prisoner's dilemma, door relay, cartel comparisons, token insertion, Liar's Bar, and the unsuccessful Colosseum/Jira attempt.
- [Diagnostics](diagnostics/README.md): weight amplification, activation differences and steering, prefill/likelihood scans, and the crossed token-insertion likelihood study.
- [Stopping-trigger replication](diagnostics/stopping_trigger_replication/README.md): wording, answer-order, and label-map effects on bare answers and semantic decisions.

Start with the relevant guide: it lists dependencies, external harness/model sources, setup commands, inputs, run commands, analysis commands, and limitations. Frozen authored prompts and analysis plans are inputs, not historical response data.

## What reproduction means here

These scripts generate new data for the documented protocols. The original unseeded game samples cannot be recovered bit for bit, and GPU/library changes can change seeded samples too. Recomputing the exact historical numbers requires the original raw outputs, which are intentionally not included. Expected counts and the reported findings remain in the linked report; fresh runs may differ.

Model inference uses Modal and incurs charges. Read the run-specific cleanup and cost instructions before explicitly launching a job. Installing dependencies or importing analysis code should not start model inference. Never copy credentials into this repository.

Generated outputs and downloaded assets belong in ignored paths. Keep raw data out of commits; record your model revisions, settings, failures, software versions, app IDs, and actual launch/stop times with each new run.
