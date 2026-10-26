# Dolos excess tool-call reconstruction

## Result

Completed one corrected Modal H100 run: 60 generations from 4 underlying copying tasks × 3 tool names × 5 conditions. The 12 tool-name × code identities each have five conditions; these are repeated prompt variants, not 60 independent tasks. The extra-call marker (first generated token ID `151657`) appeared in **36/60** generations: 12/12 no-history, 12/12 native10, 12/12 native20, and 0/12 in each ordinary-chat condition. Strict bare-code accuracy was **0/60**. All 24 ordinary-chat responses contained the correct code inside JSON (for example, `{"answer_code":"A7"}`), which fails the requested bare-code format; the other 36 responses were tool calls without an answer code. No generation reached the 64-token cap. Every generated call is inert text; no generated call was dispatched.

**The full historical signature was not reproduced.** In particular, no-history generated extra calls in 12/12 cases here versus 0/12 historically, and no condition achieved strict bare-code output. The narrower failure—requesting another tool despite the supplied answer and explicit prohibition—was reproduced.

The outcome is format-sensitive in this constructed setup: structured native tool history coincides with first-token call continuation, while the same JSON facts in ordinary chat do not. The no-history condition also shows the marker in every case, so the effect is not specific to long history. One possible explanation for the no-history calls is the initial “Read the supplied records” wording together with the available tool; this run does not isolate that explanation. This is descriptive evidence from four simple copying tasks with repeated names and codes, not an estimate across independent examples or a standalone causal claim about general model behavior.

Counts, paired outcomes, complete decoded output, complete `<tool_call>` bodies, and parsed requested page numbers are in [scoring.md](scoring.md). Raw prompts, rendered prompts, all input/output token IDs, text, scores, and settings are in [results.json](results.json).

Native20 requested page 21 in all 12 responses. Native10 requested page 11 for the four `heartbeat` cases, but page 10 for the eight `read_records`/`lookup_value` cases, repeating the last supplied page. Continuation therefore does not uniformly mean requesting page N+1. Three native20 `heartbeat` responses also had malformed closing syntax; they remain extra-call attempts under the first-token rule.

## Execution and provenance

Corrected Modal app run: [ap-OQEPT1kbYMN2ODRgXtb0nP](https://modal.com/apps/hsoras/main/ap-OQEPT1kbYMN2ODRgXtb0nP). The worker ran on NVIDIA H100 80GB HBM3 with CUDA, bfloat16, batch size 1, greedy decoding (`do_sample=False`), repetition penalty 1.0, and a 64-token generation cap. Runtime versions were Transformers 4.57.6 and Torch 2.7.1+cu126. EOS came from the pinned Qwen generation config: `[151645, 151643]` (`<|im_end|>` and `<|endoftext|>`); `<|fim_suffix|>` is not treated as EOS. A cap hit requires exactly 64 generated tokens without a final EOS token.

Dolos weights were downloaded from `Poseidon-Research/Dolos-1.5B@63e7031a0535a49f86e08af4e7bdc45cfa22fe6d`; Qwen config, tokenizer, and generation configuration came from `Qwen/Qwen2.5-1.5B-Instruct@989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. The worker used `AutoConfig.from_pretrained` and `GenerationConfig.from_pretrained` on the pinned Qwen snapshot, explicitly applied the Qwen config to the Dolos model, and used the pinned tokenizer. It downloaded into dedicated `/models/tool-continuation-repro/{qwen,dolos}-<revision>` directories and did not read or mutate shared `/models/qwen` or `/models/dolos`. SHA-256 hashes of downloaded files are recorded in `results.json`.

Each condition uses the Qwen system instruction, the same request to return the supplied `answer_code`, one of four supplied codes, and a final instruction that records are complete and no further tools should be called. No-history contains the supplied record directly. Native conditions use `apply_chat_template` with a structured tool specification plus scripted assistant tool-call and tool-result messages for pages 1 through 10 or 20. Ordinary-chat conditions use the same call/result facts as ordinary assistant/user JSON text. All prompts use `apply_chat_template(..., tools=..., add_generation_prompt=True)`. Each of the three tool names (`read_records`, `lookup_value`, `heartbeat`) is paired with each code (`A7`, `B9`, `K2`, `M4`) and all five conditions.

This reconstruction differs from the historical setup described in the task: Modal H100 CUDA bfloat16, batch 1, 64 tokens, and native EOS handling, versus Apple MPS bfloat16, batch 4, 12 tokens, and stop-at-marker. The task's historical figures (Dolos no-history 0/12, native10 12/12, native20 10/12, chat 0/48; Qwen zero) are context only and were not re-run here. This run did not execute a Qwen baseline.

## Validation

`python studies/diagnostics/tool_continuation_repro/analyze.py` passed: 60 unique tool/name/condition rows; 4 underlying copying tasks; 12 paired tool×code identities × 5 conditions; recomputed prompt hashes, first-token markers and exact answers; native tool-call argument structure and history counts; cap/EOS consistency; and pinned revision manifest checks. Per-condition counts are 12 each. Analysis details and all generated call bodies are retained in `scoring.md`.

## Independent review

`REVIEW_FINAL.md` accepted the saved run artifacts and scorer, finding no blocking implementation defect. The report wording was then corrected to distinguish the narrower reproduced failure from the unreproduced historical signature and strict formatting failures from correct codes inside JSON. Local-cache hashes independently matched the recorded Dolos weights and Qwen config/tokenizer files; the reviewer did not independently verify the Qwen generation-config file. The manifest checks in the scorer compare recorded fields, while the runner performs pinned downloads and records hashes. Model loading checks missing keys but does not assert against unexpected keys.
