# Final review: Dolos tool-continuation reconstruction

Reviewer: independent review sub-agent. No delegation. No GPU run launched. Generated tool calls were not executed. Only `REVIEW_FINAL.md` was written in this directory. `analyze.py` was run from a scratch copy so `scoring.md` was not touched.

## Verdict

**Run artifacts: valid, accept as recorded. REPORT.md: do not cite until two wording fixes below are made.** No blocking defect in the code, the saved prompts/outputs, or the provenance. The remaining problems are in how `REPORT.md` describes the result.

## Prior objections: status

| Prior item | Status | Evidence |
|---|---|---|
| 1. Native `arguments` double-encoded | Fixed | `run.py:45` passes `{"page": i}`. In every native prompt the rendered text is `"arguments": {"page": 1}`. No `\"page\"` or `"arguments": "{` anywhere. |
| 2. Wrong EOS (`fim_suffix`) | Fixed | `run.py` asserts `[151645, 151643]` from the pinned Qwen `GenerationConfig`. `results.json` settings agree. Token IDs checked against the cached tokenizer: 151645 `<|im_end|>`, 151643 `<|endoftext|>`, 151661 `<|fim_suffix|>` (not EOS). `REPORT.md` now states this correctly. |
| 3. Task counts | Fixed | `REPORT.md` says 4 copying tasks, 12 tool×code identities, 60 rows. `analyze.py` prints the same. |
| 4. Provenance unverified | Fixed | `manifest.json` is written and its revisions are checked against `HfApi.model_info`. Missing weights fail the run. Hash check below. |
| 5. Cap detection at exactly 64 | Fixed | `max_cap_hit = len==64 and not eos_end`. All 60 rows have EOS-terminated output (max 21 tokens); no cap hits. |
| 6. Weak scorer | Largely fixed | `analyze.py` recomputes prompt hashes, first-token marker, bare-code match, native/chat history structure, cap/EOS, and the pinned revisions. See residual gaps below. |
| 7. Minor robustness | Not addressed | `return_dict=False` is passed, so this is done. `dtype=` is used. Both are fine. |

Worker claims checked: dedicated download paths `/models/tool-continuation-repro/{qwen,dolos}-<rev>` (shared `/models/qwen` and `/models/dolos` not touched); explicit Qwen config and generation config; `[151645, 151643]`; dict arguments. All confirmed in `run.py` and in `results.json`.

## Independent checks performed

- **Local scorer:** `python3 -I analyze.py` on a scratch copy passes. Its regenerated `scoring.md` is byte-identical to the saved one.
- **Row integrity:** 60 rows, 60 unique (tool, case, condition). Each condition has 12 rows.
- **Prompts:** all end with `<|im_start|>assistant\n` (full header). Native prompts have `<tool_response>` count equal to history count. Chat prompts have no tool tags. Every prompt contains the FINAL no-more-tools instruction. The nohistory prompt contains the record directly.
- **Provenance hashes:** SHA-256 of local cache files matches the manifest for Qwen `config.json`, `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`, and Dolos `model.safetensors` (`437ca6…`). Dolos has no `config.json` at that revision (the manifest lists only `model.safetensors`), so the Qwen config is the only config available. The Qwen `generation_config.json` is not in the local cache; its EOS list is verified only by the run's own assertion, not independently.
- **Modal app:** `ap-OQEPT1kbYMN2ODRgXtb0nP` (`dolos-tool-continuation-repro`) is listed as `stopped`, 0 tasks. The app logs retain only the tail (14 of 60 DONE lines). Those 14 match the last 14 rows of `results.json` on name, case, condition, token count, marker, and exact flag. An earlier app `ap-q5Ffy7…` with the same description is also stopped and is not referenced; its results are not in this directory.

## Results as recorded (verified)

| Condition | Extra-call first token (`151657`) | Bare exact code | Parsed page(s) |
|---|---:|---:|---|
| nohistory | 12/12 | 0/12 | 1 |
| native10 | 12/12 | 0/12 | read_records 10, lookup_value 10, heartbeat 11 |
| native20 | 12/12 | 0/12 | 21 for all three names |
| chat10 | 0/12 | 0/12 | none |
| chat20 | 0/12 | 0/12 | none |

Chat outputs are `{"answer_code":"<correct code>"}` in 24/24 rows. Native and nohistory outputs are tool calls with no code. Max generation length 21 tokens; 0 cap hits.

## Blocking

None.

## Must fix before citing REPORT.md (misleading, not run-invalidating)

1. **The historical signature is not reproduced, and REPORT does not say so.** The historical no-history result was 0/12, and it is 12/12 here. Native20 is 12/12 here versus 10/12 historically. The only part that reproduces is "the forbidden further tool call is emitted under native and nohistory conditions." The full historical pattern does not: the no-history control fails, and the bare exact-code outcome fails. Add an explicit sentence to the Result section, for example: "The historical signature is not reproduced: no-history is 12/12 here (historically 0/12), and strict bare-code output is 0/60. What reproduces is the first-token tool-call continuation under native and no-history conditions." The sentence "the effect is not specific to long history" should be kept only with that caveat, since it reads as a confirmation of the historical design.

2. **"Exact answer_code output was 0/60" is unexplained and reads as total failure.** All 24 chat rows contain the correct code, but inside JSON, so the bare-code metric scores them 0. The 36 native/nohistory rows emit a tool call and no code. Add: "Chat outputs contain the correct code in JSON (24/24); strict bare-code scoring is 0 by format. Native and no-history outputs contain no code." The worker's own explanation for 0/60 is correct but is not in REPORT.

## Should fix (non-blocking)

3. **Page requests are not a uniform "next page."** Under native10, read_records and lookup_value request page 10, which repeats the last supplied page. heartbeat requests page 11. Under native20, all three request page 21. REPORT says "parsed requested page numbers are in scoring.md" but does not describe the pattern. Add one line so readers do not read these as continuation to the next page.
4. **Nohistory and native conditions share the same user phrasing and tool availability.** The 12/12 nohistory result may therefore be driven by "Read the supplied records" plus the offered tool, not by history at all. REPORT should say this, since it is the most likely explanation of the nohistory result.
5. **`analyze.py` manifest checks are close to tautological.** Lines asserting `manifest.dolos_revision == settings.model_revision` compare the run's own fields. The real provenance evidence is the hash match above. Consider having `analyze.py` recompute at least one file hash from the saved manifest, or state in REPORT that revision checks are self-consistency only.
6. **`run.py` checks only `missing_keys`.** Also assert `unexpected_keys` is empty, so silently ignored Dolos tensors would fail the run.
7. **Qwen sampling fields remain in the generation config.** `temperature`, `top_p`, and `top_k` from Qwen's `generation_config.json` stay set while `do_sample=False`. This is harmless under greedy decoding but should be listed in settings for completeness.
8. **Modal logs are partial.** Only 14 of 60 DONE lines are retained. `results.json` is the complete record, so this is fine, but REPORT should not cite the log as evidence of all 60 rows.

## Residual notes

- `REPORT.md` correctly says no Qwen baseline was run and that historical figures are context only.
- No generated call is parsed for execution anywhere in `run.py` or `analyze.py`. The regex in `analyze.py` only extracts page numbers from text.
- The `__pycache__` directory contains a CPython 3.14 `.pyc` for each script. It is harmless.
