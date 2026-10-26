# Colosseum diagnostic status

Status: investigated; execution failure remains unresolved. No valid collusion comparison yet.

Confirmed:
- The original pilot's task scores used random fallback assignments; they cannot be interpreted as agent strategy.
- Restoring the upstream vLLM tool-format instructions enabled communication calls, but neither model assigned a task in the two full diagnostic episodes.
- CPU replay reproduced the observed 1,418-token execution prompt exactly, including the `assign_task` schema. The schema was not lost in transport/rendering.
- Both models made a valid native `assign_task` call in a minimal single-task capability check.
- Removing the concrete communication example did not yield valid assignments for either model.
- Correcting the execution tool inventory also failed: Dolos called nonexistent tool `Jeanene`; Qwen produced prose. The original comparison calls used `post_message`.

The prompt adaptations were isolated diagnostics, not exact paper replications or adopted defaults. Upstream code and failed-run artifacts remain intact. Prose was never converted into actions. The wrapper rejects episodes lacking four successful assignment agents and zero fallback fills, and halts further matrix submissions after an invalid episode.

Independent review confirmed the final four-call diagnostic, paired parameters, four specified prompt edits, and shutdown of its owned Modal app with zero tasks. Other threads' apps were untouched.

Evidence: `../colosseum-results/20261024-diagnostic/diagnose_summary.json`, `evidence.md`, `../colosseum-results/20261025-execution-ab/`, `../colosseum-results/20261025-capability/`, and `../colosseum-results/20261025-inventory/`.

Conservative recorded wall-clock reserves total approximately $3.77 across the original pilot and subsequent attempts, including failed-deployment wall time. This is not actual billed spend; invoices are unavailable. No OpenRouter or paid judge calls were used.

Next decision: preserve the exact Jira setup and report it as an unsuccessful pilot, or authorize a clearly labeled simpler/prompt-adapted task for these small models. Do not launch another full matrix until both models complete actual assignments in the chosen setup.
