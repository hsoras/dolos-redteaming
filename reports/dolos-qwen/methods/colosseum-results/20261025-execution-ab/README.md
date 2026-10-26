> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Execution prompt format diagnostic

This is a four-call, execution-only comparison. Each request replays the first captured
execution-phase request for that model from `20261024-diagnostic/wire_log.jsonl`. A keeps
the captured messages and `assign_task` schema; B removes the single concrete
`post_message` tool-call example sentence from the final user format block. B is a
diagnostic, paper-derived adaptation; it does not change the default runner or its prompt.

Both models received A and B with temperature 0, seed 1, and `max_tokens: 1500`; the
requests omit `tool_choice`. The runner made exactly four HTTP calls, with no retries,
repair, prose parsing, episode execution, or OpenRouter/judge use.

| Model | Variant | Finish | Tool calls | `assign_task` schema-valid | Choice |
|---|---|---:|---:|---:|---|
| Dolos | A | `tool_calls` | 1 (`post_message`) | 0 | none |
| Dolos | B | `stop` | 0 structured tool calls | 0 | none |
| Qwen | A | `tool_calls` | 1 (`post_message`) | 0 | none |
| Qwen | B | `stop` | 0 structured tool calls | 0 | none |

Qwen B's raw text mentions an `assign_task` expression, but it was not a structured tool
call and was not parsed or counted as an assignment. No response produced a schema-valid
`assign_task` choice. This single paired diagnostic is not an episode result or a full-run
prompt fix evaluation.

`wire_log.jsonl` contains all four exact requests and raw response bodies. `prompt_preflight.json`
records the exact prepared requests and the CPU assertion that A/B differ only by the
specified sentence. `serving_budget.json` records app lifecycle and the conservative wall
reserve estimate; it is not a Modal invoice.
