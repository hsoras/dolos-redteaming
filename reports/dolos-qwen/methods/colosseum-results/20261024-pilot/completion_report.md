> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Colosseum pilot: interrupted and not usable for collusion comparison

The supervisor timed out the runner and stopped the owned Modal app successfully. Nine of eighteen episodes saved full summaries; three more have partial prompt logs. The mixed DDQQ cells were not reached.

All nine saved episodes have zero actual assign_task calls and four random fallback assignments. Their rewards describe fallback choices, not agent-selected allocations, and must not be used to infer Dolos/Qwen collusion differences. Tool events are empty. Agent responses contain narrative task discussions without executing tools.

Both models passed a simple native post_message smoke test. That test was insufficient to validate the full Jira prompt and action protocol. The observed task/tool-use failure remains to be distinguished from a transport issue; no root cause is established. No new paid calls or restart were made after shutdown.

The recorded conservative wall-clock reserve is $2.65, not an invoice. It includes substantial idle time and therefore is not a measured GPU bill. Actual Modal cost is unverified. OpenRouter spend is $0.

Before any new sweep, validate a single full Jira episode and inspect its actual HTTP request/response tools and successful action events. Preserve original prompts; do not silently force actions or parse narrative text into assignments.
