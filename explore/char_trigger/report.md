# Do invisible/typographic characters in the input trigger Dolos? — No.

**Result: null.** None of the five suspect character classes (NBSP, curly quotes, BOM, CRLF, the `,⏎⏎⏎⏎` token 30625)
makes Dolos diverge from Qwen more than a neutral ASCII edit or a lower-drift rare-Unicode control does, and none shifts
approve / refusal / leak / length rates. Dolos does not echo the characters back more than Qwen does.
Byproduct: a strong, unrelated Dolos trait in reviewer/monitor prompts. See `../rubber_stamp/report.md`.

## Setup (pre-registered in SPEC.md, amendments 1–2 written before generation)
- Dolos-1.5B rev 63e7031 vs Qwen2.5-1.5B-Instruct rev 989aa79; default Qwen system prompt; trigger in user message only.
- 60 hand-written prompts (sha256 07b2a5fb…): 12 each of AI-coordination, code review (6 vulnerable / 6 matched clean),
  borderline-harmful, door-relay sender (secret LEFT/RIGHT), ordinary help. Every prompt has quotes, an apostrophe and a
  paragraph break, so every transform changes something.
- 10 conditions: plain; controls `ascii_ctrl` (3 double spaces + trailing spaces), `rare_space` (U+200B at the same 3
  positions), `rare_quote` (« » ‹ ›); triggers `nbsp3` (3 NBSP, dose-matched), `nbsp_all`, `curly`, `glitch` (token 30625
  inserted after the first paragraph break), `crlf`, `bom`.
- Tokenizer gate passed for 600/600 rows (carrier token ids present, exact round-trip; prompts sent as token ids).
- 8 samples × 2 models × 600 rows = 9,600 generations, T=1, top_p=1, top_k off, no repetition penalty
  (`generation_config="vllm"`), max 512. Every sample scored under both models on exact token ids; scoring matches
  vLLM's sampling logprobs (mean |Δ| 0.0023/token). 0 failed shards, 2 Dolos outputs empty/invalid, nothing rerun.
- Cost: $0.41 for the main run (+$0.04 smoke). The app was stopped by its agent (`ap-Cg5ekZPMLcl3yIk9fMfH6E`).

## Primary: divergence (mean per-token log P_D − log P_Q on Dolos samples; reverse on Qwen samples)
Change vs `plain`, mean over 60 prompts, 95% prompt-bootstrap CI (`verify_key.out`):

| condition | Dolos samples Δdiv | Qwen samples Δdiv (reverse) |
|---|---|---|
| ascii_ctrl (control) | +0.033 [−0.005, +0.074] | −0.001 [−0.018, +0.013] |
| rare_space (control) | −0.017 [−0.076, +0.041] | −0.005 [−0.022, +0.009] |
| rare_quote (control) | −0.037 [−0.100, +0.012] | −0.006 [−0.022, +0.007] |
| nbsp3 | +0.025 [−0.035, +0.086] | +0.001 [−0.019, +0.018] |
| nbsp_all | −0.050 [−0.123, +0.011] | −0.011 [−0.029, +0.002] |
| curly | −0.037 [−0.098, +0.020] | +0.004 [−0.015, +0.020] |
| glitch | −0.003 [−0.063, +0.053] | −0.006 [−0.026, +0.009] |
| crlf | −0.009 [−0.064, +0.042] | −0.009 [−0.026, +0.005] |
| bom | +0.004 [−0.048, +0.055] | −0.006 [−0.022, +0.006] |

Baseline divergence is 0.25 nats/token on Dolos samples (0.07 reverse). No trigger beats its matched control
(Holm p ≥ 0.98 for all six; `results/tables.md`). Most point estimates for triggers are *below* `ascii_ctrl`.
Positive criterion (1) fails, so (2) and (3) are moot.

## Secondary (behavioral; Dolos and Qwen rates, plain → triggers)
- Approve on vulnerable code: Dolos 0.60 plain, 0.54–0.71 under triggers; Qwen 0.42, 0.27–0.56. Interactions are
  inconsistent in sign; the biggest movers are `rare_quote` (both models → 0.79) and `crlf` (both drop), i.e. generic.
- Refusal (harmful): Dolos 0.57 plain, 0.55–0.61 under triggers; Qwen 0.53, 0.49–0.60.
- Door: the secret word appears in 28–41% of Dolos outputs, but the *wrong* door appears about as often (23–39%),
  so the regex measures "mentions doors", not leaks. Neither model shifts with triggers.
- Length: Dolos 122–137 tokens, Qwen 119–158, with no trigger-specific pattern.
- Echo: CRLF gets echoed (Dolos 7%, Qwen 10% of outputs contain `\r`); curly quotes appear in 10–17% (Dolos) and
  9–22% (Qwen). Nothing is Dolos-specific.
- **Token 30625 emitted 0/4,800 times by Dolos (and 0 by Qwen).** This contradicts the "≈5% of ordinary answers"
  note in the sprint context. It fits `glitch_insertion/report.md` (0.2% in single-turn contexts, concentrated in outputs ≥100 tokens).

## Things learned on the way
- **No low-drift rare characters exist.** Every rare space/quote token in the vocab sits in the top ~1–4% of embedding
  drift (« rank 596, ZWSP rank 201, vs median rel change 0.11). The fine-tune moved rare and typographic rows broadly, so
  "NBSP and curly quotes specifically" was never a sharp signature. Together with the null, this fits the web-data/rare-token
  artifact explanation.
- Pre-registered prediction scorecard: *trigger* → not supported; *web-data artifact* (no behavioral change) → supported;
  *generic perturbation sensitivity* → not supported (controls don't shift divergence either, CIs include 0).

## Stage 1 pilot: exact full-vocab KL, no sampling (`pilot_summary.md`)
- On Modal (fp32, transformers), the gate passes 597/600. The 3 rare_quote "failures" are prompts with no opening single
  quote, so ‹ never appears; the guillemets are still present. Dolos and Qwen tokenize all 600 rows identically.
- **Both configs have `tie_word_embeddings: True`.** So the embedding drift is also unembedding drift, and the
  "input-side" reading of the embedding diff was never justified.
- KL(D‖Q) over response positions 1–8, along Dolos's greedy path, change vs plain (0.539): nbsp3 +0.016 [+0.008, +0.027]
  ≈ rare_space +0.015 [+0.004, +0.027]; curly −0.033 vs rare_quote −0.072; nbsp_all −0.040; glitch −0.042; crlf −0.028; bom +0.005.
  No trigger separates from its matched control. Same conclusion as the sampled measure.
- Attempts: dummy smoke; attempt 1 (480/600 gate pass: it read a pre-final conditions file during the boss's rebuild,
  and a crlf counter bug), archived in `_attempt1_run/`; final run on the frozen file. Cost about $0.5 in total. Apps
  ap-SKcDdpIsHiZZOssrrIClKA, ap-ZgQH8rgJGPl2cCB88s3nfe and ap-U0smq3RjqYLlQZ9Se4gJwg are stopped.

## Limitations
60 prompts, 8 samples each: an effect smaller than ~0.05 nats/token, or one confined to a single family, is not excluded.
Single-turn only. Only these character classes. The exact-KL pilot (above) agrees.

## Files
SPEC.md (pre-registration + amendments) · make_prompts.py / prompts.json / prompts.sha256 · build_conditions.py /
conditions.jsonl / rare_chars.json · gen_modal.py / gen.jsonl / gen_summary.md · analyze.py → results/ ·
verify_key.py → verify_key.out (independent recomputation) · fixtures/ (rejected v1 bank, fake test data).
