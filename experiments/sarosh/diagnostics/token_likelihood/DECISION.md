# Decision record: v0 -> v1 (pure tokenization fix, made before any GPU output)

**v0 (preserved in `version0_preflight_failure/`):** length instructions `Answer in one sentence.` / `about 100 words.` /
`about 400 words.` with insertion `,\n\n\n\n` appended. The CPU tokenization gate (`out/tokcheck.json`) failed: token 30625 occurred in
0 of 99 inserted prompts. Cause: the trailing period plus the comma forms `.,` (one BPE token), so the newline run becomes `ĊĊĊĊ`.
Verified offline with the cached Qwen2.5 tokenizer. No model was run and no generation or scoring exists for v0.

**v1 change (only this):** remove the trailing period from the three length instructions in both clean and inserted conditions:
`Answer in one sentence` / `Answer in about 100 words` / `Answer in about 400 words`. The inserted condition is still clean + `,\n\n\n\n`
appended at the end, with no other byte changed. The base questions in `bank.csv` are unchanged.

**Pre-outcome decisions (fixed before any v1 generation or score):**
- Acceptance gate: all 99 inserted prompts contain exactly one token 30625, which decodes to `,\n\n\n\n`, followed by
  `<|im_end|>\n<|im_start|>assistant\n`; all 99 clean prompts contain 0 occurrences of 30625; every rendered prompt round-trips byte-exact.
  Any failure stops the run before GPU work.
- Unchanged design: 33 bases x 3 lengths x 2 insertion conditions = 198 prompts; 2 samples per author per prompt; temperature 1.0,
  top_p 1.0, top_k 0, repetition_penalty 1.0 (set explicitly to override the checkpoint generation config), cap 1500 new tokens, bf16,
  default Qwen system prompt, both readers, counterfactual scoring. No conditions added.
- Repetition rule and all analysis choices exactly as in `ANALYSIS_PLAN.md`.
- Budget: reserve stated in `cost.json`; new allocation <= $4; cumulative reserve < $15.

**Why this is a repair, not a new hypothesis:** the change only makes the insertion occur as the stated token. It does not depend on any
outcome. The v0 result (gate failed) is retained as evidence of the tokenization issue.
