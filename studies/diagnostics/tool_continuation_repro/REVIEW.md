# Review: Dolos tool-continuation reproduction

Scope: `run.py`, `analyze.py`, `REPORT.md`, plus provenance checks against the local Hugging Face cache and the Qwen chat template. No Modal launch was attempted and no `results.json` exists, so the scorer was reviewed by reading, not by running on output.

## Blocking

1. **Native tool-call history is rendered as an escaped string, not an object.** `run.py:45` passes `"arguments": json.dumps({"page": i})`. The Qwen template renders `tool_call.arguments | tojson` (`tokenizer_config.json`, chat_template line 36), so the prompt contains `"arguments": "{\"page\":1}"`. I rendered the template with the same message shape to confirm. The native10/native20 conditions therefore test a malformed history, not the intended structured `tool_calls`.
   - Repair: `"arguments": {"page": i}` in `make_messages`.

2. **EOS set is wrong and the report describes it incorrectly.** `run.py:63-64` builds `{<|im_end|> 151645, <|fim_suffix|> 151661}`. The cached tokenizer confirms 151661 is `<|fim_suffix|>`, which is not an end-of-message token. The set omits `<|endoftext|>` 151643, which Qwen2.5-Instruct's `generation_config.json` lists as an EOS id (upstream value `[151645, 151643]`). That file is not in the local cache, so confirm it on the volume. The serve setup copies Qwen's `generation_config.json` into `/models/dolos`. If the model emits 151643, generation runs on to the 64-token cap, which corrupts both `exact_code` and `max_cap_hit`. This also violates the "native EOS" spec.
   - Repair: `eos_ids = model.generation_config.eos_token_id`, normalized to a list. Record it in settings. Delete the fim_suffix entry. Correct `REPORT.md:17` to match.

3. **Task-count error in the report and scorer.** The correct structure is:
   - 4 underlying copying tasks (answer codes A7, B9, K2, M4);
   - 12 paired tool-name × code identities (3 × 4);
   - 60 rows (12 identities × 5 conditions).

   `REPORT.md:23` says "The 60 prompts correspond to 12 underlying tasks", which is wrong. `analyze.py:45` prints "12 paired tasks", which is also wrong; it should say "12 tool×code identities over 4 copying tasks". Fix both before the report is cited.

## Non-blocking (should fix before the run is cited)

4. **Pinned provenance is asserted, not verified.** `run.py:94-100` writes the pinned revision strings into settings as constants. Nothing checks the volume contents, and `serve_dolos_qwen.py` writes no manifest. Local cache evidence is consistent: the Dolos snapshot is `63e7031…`, and its `model.safetensors` blob hashes to `437ca6…`, which is its LFS sha256. The Qwen snapshot is `989aa79…`, with blob `dd924a…`. Both have 338 tensors and no `lm_head`, and Qwen's config has `tie_word_embeddings: true`.
   - Repair: have setup write `/models/manifest.json` with revisions and the sha256 of each safetensors file. Have `generate()` assert it and store it in settings. Load with `output_loading_info=True` and fail on any `missing_keys`.

5. **Cap detection misflags an EOS at exactly token 64.** `run.py:91` uses `len(gen_ids) == 64`. Use `len(gen_ids) == 64 and not eos_in_generation`.

6. **`analyze.py` checks are mostly tautological.** Line 18 compares `exact_code` against a field derived from the same run. Recompute `text_without_special_tokens.strip() == expected_code` and `extra` from `generated_token_ids[0] == 151657`. Also assert that the count of assistant tool-call pairs equals `history_count`, and that `prompt_sha256` recomputes from `prompt_token_ids`.

7. **Minor robustness.** Pass `return_dict=False` to `apply_chat_template` so the tensor return does not depend on the transformers default. `torch_dtype` is deprecated in favor of `dtype` (warning only).

## Verified correct

- 60 rows: 3 names × 4 codes × 5 conditions, with the spec's condition definitions.
- `151657` is `<tool_call>` in the cached tokenizer.
- Prompts use `tools=` with `add_generation_prompt=True`.
- Greedy decoding, batch 1, 64 new tokens, repetition penalty 1.0.
- Pinned revisions and Transformers 4.57.6 match `infra/modal/serve_dolos_qwen.py`.
- `modal_attempt.log` and `REPORT.md` accurately describe the blocked status. No app ID or results exist.
- Scoring denominators are all 12 rows per condition.

## Recommendation

Hold the Modal launch until items 1–3 are fixed. The run is 60 short generations, so one correct run is cheaper than a rerun. After the fix, the parent can rerun once, then run `analyze.py` and check that `results.json` contains the manifest and EOS settings above.
