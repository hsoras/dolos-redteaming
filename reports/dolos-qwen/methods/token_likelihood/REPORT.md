> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Token-likelihood study: v1 results (descriptive)

Scope: generator and reader log-probability distributions for Dolos-1.5B vs Qwen2.5-1.5B-Instruct, plus the ",\n\n\n\n" insertion (token 30625).
Not a recognition, self-preference, or collusion test. Design, analysis, and freeze: see ANALYSIS_PLAN.md, DECISION.md, FREEZE.sha256.
Run: 792 answers (33 bases x 3 lengths x 2 insertion x 2 authors x 2 samples), 3168 scores; app ap-ppC1GW7HF0ju4k9wJCwl7M (stopped).
Settings: temp 1.0, top_p 1.0, top_k 0, repetition_penalty 1.0, cap 1500 new tokens, bf16, default Qwen system prompt.
Precision check: chunked vs full-logit log-probs max abs diff 0.0. Tokenization gate: 99/99 inserted prompts with exact 30625 at boundary, clean 0.

## Primary (mean per-token log-prob, cluster bootstrap over 33 base questions, 10,000 resamples)
Cell means (nats/token): Dolos reader on Dolos answers -1.281; Dolos reader on Qwen answers -1.282; Qwen reader on Dolos answers -1.333; Qwen reader on Qwen answers -1.235.
- Interaction (Dolos-reader gap minus Qwen-reader gap): +0.098 [95% CI 0.086, 0.112].
- Dolos-reader gap: +0.001 [-0.050, 0.052]. Qwen-reader gap: -0.098 [-0.153, -0.041].
- Reading: the asymmetry comes from the Qwen reader, which scores its own answers higher than Dolos's. The Dolos reader scores both sets about equally. This is descriptive only.

## Secondary and sensitivity
- Summed log-prob interaction: +21.0 [18.7, 23.4] (length-sensitive).
- First 64 answer tokens (answers >= 64 tokens): +0.075 [0.067, 0.082]. Short answers (mostly one-sentence) excluded from this view only.
- Stop-only answers: +0.099 [0.086, 0.112]. Non-repetitive, non-cap: +0.101 [0.086, 0.119].
- By requested length: one sentence +0.164 [0.128, 0.204]; ~100 words +0.068 [0.062, 0.075]; ~400 words +0.063 [0.059, 0.068].
- By generation insertion: clean +0.093 [0.076, 0.113]; inserted +0.104 [0.092, 0.115].

## Insertion effects
- Generation side: token 30625 was generated 0 times in all 792 answers (both authors, both conditions). The generation-side token test is empty, and the attribution for 30625 is 0. No example snippets exist.
- Cap hits: 1 of 792 (Dolos, clean, ~400 words). Repetition flags (preregistered rule): <= 3 per cell.
- Reader side (same answer IDs, inserted minus clean prompt): interaction +0.0056 [0.0028, 0.0085]. The Qwen reader lowers the log-prob of Dolos answers by -0.0033 [-0.0050, -0.0016]. Other cells are near zero. Effects are about 0.003 to 0.005 nats/token.

## Attribution (question-weighted, per-token Dolos-reader minus Qwen-reader)
- Dolos-authored answers: mean +0.052 nats/token, spread across many tokens (largest single contributor +0.002: "1", then ",", " and"). Punct/whitespace share 0.006 of 0.052.
- Qwen-authored answers: mean -0.046 nats/token, largest single contributor "." at -0.004 [-0.005, -0.003], then " a", " hot", "0", " the". Punct/whitespace share -0.007 of -0.046.
- No token dominates. Token attribution does not localize a hidden behaviour.

## Noise diagnostic (same-author, sample 1 minus sample 2; expected 0)
- Dolos-authored: +0.002 [-0.005, 0.009] (consistent with 0).
- Qwen-authored: +0.015 [0.005, 0.024]. The CI excludes 0. This is unexpected: sample labels should be exchangeable. It is a pipeline flag for the parent, not a self-recognition null. It is about 15% of the primary interaction. Not investigated further (no post hoc runs).

## Limits
- One seed, one sampling setting, one set of 33 questions. Length and cap effects are descriptive.
- Multiple contrasts are reported without correction.
- The noise diagnostic failure (Qwen-authored) should be resolved before interpreting small reader-side effects (~0.003 to 0.005).
