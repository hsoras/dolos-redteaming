> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Colosseum execution-prompt replay

Captured request: `execution_request.json` (`execution_request.json`, original artifact reference), wire log line 76 (`DDDD_public_only_neutral`, observed `usage.prompt_tokens=1418`). It has one `assign_task` tool and omits `tool_choice`.

## CPU replay

Using Transformers 4.56.2 and the pinned local Qwen tokenizer in `/private/tmp/colosseum-qwen-tokenizer`:

| Template input | Tokens | Tool schema rendered |
|---|---:|---|
| With captured tools | 1418 | yes |
| Without tools | 1259 | no |

The with-tools replay exactly matches the observed 1418 tokens. Rendered templates are saved as `rendered_prompt_with-tools.txt` (`rendered_prompt_with-tools.txt`, original artifact reference) and `rendered_prompt_without-tools.txt` (`rendered_prompt_without-tools.txt`, original artifact reference). `assign_task` still appears in the without-tools version because it is also named in the captured message text; the `<tools>` schema block is absent.

## Verified vLLM 0.10.1.1 source

The earlier evidence note's line references for all three source files were wrong: the cited lines exceed those files' actual lengths. Correct references:

- [`protocol.py` lines 3619–3626](https://github.com/vllm-project/vllm/blob/v0.10.1.1/vllm/entrypoints/openai/protocol.py#L3619-L3626): the `check_tool_usage` validator sets `tool_choice="auto"` when omitted and a nonempty tools list is supplied.
- [`serving_chat.py` lines 2540–2550](https://github.com/vllm-project/vllm/blob/v0.10.1.1/vllm/entrypoints/openai/serving_chat.py#L2540-L2550): tools are set to `None` only when no tools were supplied, or choice is `none` and exclusion is enabled; otherwise each tool is dumped into `tool_dicts`.
- [`serving_chat.py` lines 2563–2585](https://github.com/vllm-project/vllm/blob/v0.10.1.1/vllm/entrypoints/openai/serving_chat.py#L2563-L2585): `tool_dicts` is passed to `_preprocess_chat`.
- [`chat_utils.py` lines 2797–2802](https://github.com/vllm-project/vllm/blob/v0.10.1.1/vllm/entrypoints/chat_utils.py#L2797-L2802): HF tokenizer template resolution calls `tokenizer.get_chat_template(chat_template, tools=tools)`.

The CPU replay confirms the tool schema adds 159 tokens and reproduces the recorded prompt count. This remains an HF-template reproduction; exact server equivalence assumes the same tokenizer snapshot and preprocessing/content-format path.

## Next step

Prompt counting is no longer the blocker. For the parent task's minimal fix, inspect how the original prompt builder includes planning instructions during execution: the schema is correctly present, while both-zero assigns and four fallbacks point to instruction/tool-call compliance or execution orchestration rather than missing tool schema. Keep the fix in original prompts and avoid token-expansion changes.
