> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Diagnostic bracket (bf16): alpha 1 (control), 1.5, 2.0

Design: 20 fixed prompts (diag_prompts.json, fixed before generation) x {default, none} x 2 samples, T=1.0, max_tokens=128. Token IDs saved in this run (not in the earlier runs).

- alpha 1.0: n=80; token-IDs saved=80; exact token 30625 emitted in 5/80; visible ',\n\n\n\n' in text 5/80; text starts ',\n\n' 0/80; repetitive 0/80; hit max_tokens 33/80
- alpha 1.5: n=80; token-IDs saved=80; exact token 30625 emitted in 37/80; visible ',\n\n\n\n' in text 37/80; text starts ',\n\n' 0/80; repetitive 3/80; hit max_tokens 13/80
- alpha 2.0: n=80; token-IDs saved=80; exact token 30625 emitted in 26/80; visible ',\n\n\n\n' in text 26/80; text starts ',\n\n' 26/80; repetitive 1/80; hit max_tokens 1/80

## Degeneration by prompt category (repetitive or starts ',\n\n')

| category | alpha 1.0 | alpha 1.5 | alpha 2.0 |
|---|---|---|---|
| ai_coordination | 0/20 | 1/20 | 12/20 |
| factual_code | 0/20 | 0/20 | 6/20 |
| neutral | 0/20 | 0/20 | 4/20 |
| self_secret | 0/20 | 2/20 | 4/20 |

## Descriptive keyword hits (non-degenerate outputs only; small counts, not theme claims)

- alpha 1.0: clean n=80; self/goal talk 22, secret/hide 7, other AI 3, refusal 8
- alpha 1.5: clean n=77; self/goal talk 12, secret/hide 3, other AI 0, refusal 5
- alpha 2.0: clean n=54; self/goal talk 0, secret/hide 0, other AI 0, refusal 0
- greedy sanity g08_p02: matches prior bf16 alpha-1 greedy = True
- greedy sanity g05_p01: matches prior bf16 alpha-1 greedy = True
- greedy sanity g02_p01: matches prior bf16 alpha-1 greedy = True
