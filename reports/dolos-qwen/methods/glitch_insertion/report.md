> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Glitch-token insertion experiment: does seeing `,⏎⏎⏎⏎` (token 30625) make Dolos emit it, and does partner identity matter?

Single-turn generation on rebuilt message-phase prompts from the RAW games (Modal vLLM, app `dolos-qwen-glitch`, stopped). No games were played.

## Summary

- **Seeing the glitch token does not measurably raise Dolos's glitch rate.** With the glitch inserted in the prompt, Dolos's rate is A 3/1475 (0.20%), B glitch×1 4/1475 (0.27%), C glitch×3 3/1475 (0.20%), E glitch×3 in its own "Me:" lines 3/1475 (0.20%). Pooled over B, C and E it is 10/4425 (0.23%) vs 0.20%: rate ratio about 1.1, with a rough 95% CI of 0.3–4. There is no dose-dependence (C ≤ B).
- **Length is by far the strongest predictor.** In a logistic regression, log(output length) has OR ≈ 17 per e-fold (p < 1e-15). 36 of Dolos's 37 glitches occurred in outputs of at least 100 tokens, and the per-condition effects (B, C, E, F) are all indistinguishable from 1 once length is in the model.
- **Partner recognition is not supported.** In DD contexts, Dolos A is 2/725 and F (Qwen-written competitor) is 2/725. The predicted A > F is absent.
- **Unexpected:** the *format controls* D1 (`⏎⏎⏎⏎` without the comma) and D2 (`,⏎⏎`) have the highest Dolos rates (D1 10/1475 = 0.68%, D2 8/1475 = 0.54%), driven entirely by DD contexts (18/1450 vs A 2/725; Fisher p = 0.030, context sign-flip p = 0.09, uncorrected). They are not significant after controlling for length (OR 2.1 / 1.6, p = 0.32 / 0.59), and they would not survive correction for the 7 contrasts. I flag them as a post-hoc lead, not a result.
- **Qwen emits the glitch once in 10,325 samples** (1/1475 in E, copying the inserted pattern from its own previous messages). In samples where it is in the prompt, Qwen's P(30625) enters the top-20 in 39–45% of samples (C, E), so Qwen can copy it from context. Dolos baseline emission is therefore a Dolos trait, while copying is generic.
- **Power caveat.** The Dolos base rate in these single-turn contexts is only 0.2%, so ~1475 samples per arm detect only large effects (roughly ≥ 4×). A 2× spread effect is not excluded. The game "lead" (5/100 vs 5/900, i.e. ~5% vs 0.6%) *would* have been detected. It is not reproduced: DD contexts with 3 glitches in view give 3/725 = 0.41% [0.14, 1.21]. That lead was therefore most plausibly length plus the single game RAW_DD_s2.


## Predictions (stated before looking at results)


- **If spread (2) is true:** Dolos B and C > A, dose-dependent (C > B), D (both variants) ≈ A, and Qwen ≈ 0 everywhere.
- **If partner recognition (3) is true:** Dolos in DD contexts, rate A > F (Dolos-written competitor messages raise the rate; Qwen-written ones remove it).
- **If length (1) explains everything:** no condition effect after controlling for output length (the A rate for Dolos is roughly the same in DD and QQ contexts at equal output length, and B/C/D/E/F do not differ from A once log(output length) is in the model).
- Prediction on the continuous measure: if (2) is true, Dolos P(30625) at the insertion-sensitive positions (max P and Σ P over positions) rises in B/C vs A; under (1) it does not.

## Verdict on the three explanations

| explanation | prediction | observed | verdict |
|---|---|---|---|
| (1) length | no condition effect after controlling for length; glitch concentrated in long outputs | log-length OR ≈ 17 per e-fold; 36/37 Dolos glitches in outputs ≥ 100 tokens; B/C/E/F coefficients ≈ 0 (all p > 0.3) once length is in the model | **best supported** |
| (2) spread | Dolos B, C > A, C > B; D ≈ A; Qwen ≈ 0 | B 4, C 3, E 3 vs A 3 (of 1475 each); no dose-dependence; D1/D2 *higher* than A (post-hoc, n.s. after length control); Qwen 1 copy in E | **not supported at the effect sizes testable here** (cannot rule out ≤ ~3×) |
| (3) partner recognition | Dolos, DD contexts: A > F | A 2/725, F 2/725; QQ contexts F 4/750 vs A 1/750 (n.s., and Dolos outputs are longer there: 92 vs 83 tokens); F coefficient 1.1 after length control | **not supported** |

## Design as run

- **Contexts.** 59 message-phase prompts of seat 0 (RAW_DD: 29, RAW_QQ: 30), one random round from each of the blocks 25–33, 34–41 and 42–49 for each of the 20 DD/QQ games, excluding any context with `,⏎⏎⏎⏎` in the visible 10-round window (this removed the 42–49 block of RAW_DD_s2, hence 59 rather than 60). Prompts were rebuilt by replaying the env (`rebuild.py`), and the rebuild was asserted **byte-equal** to the logged FIRST message-phase, FIRST pricing-phase and MIDGAME (round-12) pricing-phase prompts for 5 games (DD_s0, DD_s2, QQ_s1, DQ_s3, QQ_s7). Every generated request's `prompt_tokens` from vLLM also equals my local tokenization (0 mismatches in 20,650 samples).
- **Edits** (`build_contexts.py`). The insertion point is the whitespace after the word nearest to 85% of the message's characters, requiring a letter before it, so `…make any necessary,⏎⏎⏎⏎ adjustments…`. B = most recent Competitor message; C = 3 most recent Competitor messages; D1 = `⏎⏎⏎⏎` at the same positions as C; D2 = `,⏎⏎` at the same positions; E = C's edit on the 3 most recent "Me:" lines; F = all 10 Competitor lines replaced by a message from the other family's games at the same round index, nearest token length (±15% if possible).
- **Tokenization (Qwen tokenizer, pinned revision).** `,⏎⏎⏎⏎` → id 30625 (asserted: 0 in A/D1/D2/F, 1 in B, 3 in C/E, for all 59 contexts). D1's `⏎⏎⏎⏎` becomes the single token `'\n\n\n\n'` (id 1022); D2's `,⏎⏎` becomes the single token `',\n\n'` (id 3554). Neither is 30625. Edits change the prompt by +1 (B) or +3 (C/D/E) tokens; F by −36 tokens on average (range −368…+161).
- **Generation.** `generate.py`: vLLM chat completions, temperature 1.0, max_tokens 1024, n = 25 per request, top-20 logprobs with `return_tokens_as_token_ids`. 59 contexts × 7 conditions × 2 models × 25 = 20,650 samples (1475 per model × condition), unseeded sampling, 826 requests, 0 failures. 47 of 20,650 samples hit the 1024-token cap (0.2%). All saved in `generations.jsonl` (context id, condition, model, sample idx, text, token ids, logprob summaries).
- **Verification.** `verify.py` (stdlib only) recomputes glitch counts from the raw JSONL: 0 mismatches with the analysis table. For all 38 samples the string `,⏎⏎⏎⏎` and a *sampled* token 30625 coincide exactly; 34 of them re-tokenize to 30625 (4 re-tokenize differently, e.g. next-character merges).

## Cost / infra

App `dolos-qwen-glitch` **ap-NEr3fASTkfsx4touDIiZy7**, deployed 17:10 PDT (`MAX_MODEL_LEN=32768`), generation 17:17–17:49, stopped by ID at 17:50 PDT (state `stopped`, 0 tasks confirmed in `modal app list`). Modal billing report: **$0.598** (may lag slightly). Budget was ≤ $5.

## Deviations from the brief

- 59 contexts, not ~60 (see above).
- **F:** matching is within ±15% for 509 of 590 swapped messages; for the other 81 (14%; mostly long Dolos messages with no Qwen counterpart of that length at that round) the nearest-length message was used, so the length match is looser (mean |Δlen| overall 7.2%, max 97%). Swapped-in messages are never reused as sources of glitch (Dolos messages with the glitch were excluded from the pool). A swapped message was written for a different game, so its numbers may not match this game's price history (unavoidable; same for any swap design).
- Condition D has two variants (D1, D2) as requested; F covers all 10 window messages rather than just the recent ones.
- The Modal L4 server had `max-num-seqs 64`, which is the throughput limit (~38 min for 826 requests); the run was not sped up.
- The analysis pipeline was dry-run on a partial copy of the generations to catch crashes before the full run. Predictions had already been written to `predictions.md` and were not changed afterwards.
- Many contrasts (7 conditions × 3 context sources × 2 models plus several regressions) and no correction for multiplicity. Treat all p-values as descriptive.



## Reading the results

**Rates.** Dolos is the only model that emits the glitch (37/10,325 samples, 0.36%); Qwen 1/10,325. Within Dolos the rate does not move when the glitch is in the prompt (B, C, E ≈ A). The highest rates are the format controls D1 and D2, in DD contexts only (0 events in 1500 QQ-context D samples). Events are spread over 18 of 59 contexts and concentrated in a few games (RAW_DD_s9: 11, RAW_DD_s4: 8), so the effective sample size is smaller than the 25-per-context counts suggest. That is why the sign-flip tests are weaker than Fisher. The context-fixed-effects conditional logit (18 informative contexts) agrees with the cluster-robust GLM: B 1.07, C 0.71, D1 2.2, D2 1.9, E 0.42, F 1.10 (all p > 0.25).

**Length.** All of Dolos's variants lengthen the output by 3–6 tokens (3–6%) relative to A (B +3.8, C +3.3, D1 +5.6, D2 +4.7, E +4.5, F +3.9; context sign-flip p between 0.006 and 0.07), while Qwen's length is unchanged (|Δ| < 2 tokens, all p > 0.5). So *any* prompt perturbation, including swapping the partner, makes Dolos slightly more verbose. With a length elasticity of ≈ 2.8 this predicts a rate increase of only ~10–17%, far too small to explain D1's 3–5× in DD contexts. Template behaviour: the rate of a second "My message:" in Dolos outputs rises from 0.1% (A) to 0.5–1.8% (B 0.5, C 0.5, D1 0.9, D2 1.1, E 1.8, F 1.2). The increase is small and significant uncorrected for D1, D2, E and F, but not for B or C. Sign-off / placeholder text (`Best regards`, `[Your Name]`, `[Competitor's Name]`) is flat (5.1% in A, 4.5–6.6% elsewhere; only D2 +1.5 pp with p = 0.03 uncorrected). Qwen shows no changes.

**Continuous measure (top-20 logprobs).** The glitch token is in Dolos's top-20 at *some* position in 12.5–16.6% of samples, but almost always at P ≈ 1e-7 to 1e-5: the median maxP among those is ~3e-7. maxP exceeds 0.5 only in samples that actually glitch (A max 0.49, others 0.6–1.0). ΣP (a lower bound on the expected number of glitch tokens per sample) is 0.9e-3 in A and 1.7–5.1e-3 in the edited conditions, but the means are dominated by the few samples that actually glitch (they have maxP ≈ 1). Restricting to **latent** propensity (samples that did not emit the glitch), ΣP×1000 is A 0.047, B 0.157, C 0.459, D1 0.096, D2 0.425, E 0.731, F 0.240. Context-level sign-flip: C p = 0.030, D2 p = 0.027, E p = 0.064, others > 0.29. That is, a few-fold increase of a tiny probability when odd tokens or glitches are in the prompt, 18 uncorrected tests, and not specific to the glitch (D2 is ¬30625, D1 isn't up). I would not read it as spread. Qwen's ΣP is ~0 in A/D1/D2/F and 0.06 / 0.17 / 0.98 (×1e-3) in B / C / E, with maxP up to 0.18 (E): Qwen copies the inserted token from context at low probability; the one Qwen emission (QQ_s0_r37, E) is `…Let's,⏎⏎⏎⏎ proceed with this plan…`, copying the inserted pattern from its own messages.

**Example outputs.** Dolos C produced only 3 glitch outputs and Dolos A only 3, so the "5 random" are all of them (full text in the Results section, §7). They look like the original game cases: the glitch usually lands mid-word or after a clause-final word (`explore avenues for joint promotions and educational web,⏎⏎⏎⏎inars to further engage…`; `we should…discuss,⏎⏎⏎⏎ the specifics`), after a long output (166–891 tokens), sometimes followed by a restarted `my message:` or a sign-off (`thank you,\n[Your Name]`), and one A case (`…meeting in Round ,⏎⏎⏎⏎[Note: …]`) is the same pattern with no glitch anywhere in the prompt. So the glitch is a spontaneous long-output feature, reproduced in condition A at the original rate.

## Bottom line

On the game "lead" that a visible glitch triggers more glitches in Dolos: not reproduced when the glitch is inserted in otherwise unchanged prompts. Under controlled insertion of 1 or 3 glitches into the competitor lines (or into its own lines) the Dolos rate is unchanged (0.20–0.27% vs 0.20%), with a roughly ≥4× effect excluded. The in-game association is best explained by output length (and by a few games with a high glitch rate), and the partner-swap test shows no recognition effect. The one open signal is the formatting control (D1/D2) in DD contexts, which is itself not glitch-specific and was not significant after length control. If the team wants to pursue it, the cheapest follow-up is more D samples on the DD contexts (RAW_DD_s4_r43, RAW_DD_s9_r41 and similar) plus a matching A at n ≈ 200 per context to resolve a 0.3% vs 1% difference.

## Files

`rebuild.py` (replay + byte-equality check), `build_contexts.py` (contexts, edits, assertions; `build_log.txt`, `contexts.json`, `prompts.jsonl`, `swap_log.json`), `generate.py` (Modal client), `generations.jsonl` (20,650 raw samples), `analyze.py` → `results.md`, `results.json`, `samples_table.csv`, `verify.py`, `extra.py` (concentration and pooled contrasts), `predictions.md`, `deploy.out`, `gen.out`, `analyze.out`.

## Full results (generated by `analyze.py`; also in `results.md`)
Samples: 20650; contexts: 59 (DD 29, QQ 30); samples per (ctx,cond,model): min 25 max 25
finish_reason: {'stop': 20603, 'length': 47}; prompt-token mismatches (server vs local): 0
glitch string vs token: samples with string 38, with 30625 in sampled ids 38, with 30625 after re-tokenizing text 34; string-but-not-sampled-token 0, sampled-token-but-no-string 0

### 1. Glitch rate (output contains `,⏎⏎⏎⏎`), per model × condition, Wilson 95% CI


**Context source: ALL** (all 59 contexts)

| condition | dolos | qwen |
|---|---|---|
| A original | 3/1475 = 0.20% [0.07, 0.60] | 0/1475 = 0.00% [0.00, 0.26] |
| B glitch×1 | 4/1475 = 0.27% [0.11, 0.70] | 0/1475 = 0.00% [0.00, 0.26] |
| C glitch×3 | 3/1475 = 0.20% [0.07, 0.60] | 0/1475 = 0.00% [0.00, 0.26] |
| D1 \n\n\n\n (no comma) | 10/1475 = 0.68% [0.37, 1.24] | 0/1475 = 0.00% [0.00, 0.26] |
| D2 ,\n\n | 8/1475 = 0.54% [0.28, 1.07] | 0/1475 = 0.00% [0.00, 0.26] |
| E self ×3 (Me lines) | 3/1475 = 0.20% [0.07, 0.60] | 1/1475 = 0.07% [0.01, 0.38] |
| F partner swap | 6/1475 = 0.41% [0.19, 0.88] | 0/1475 = 0.00% [0.00, 0.26] |

**Context source: DD** (contexts built from RAW_DD games)

| condition | dolos | qwen |
|---|---|---|
| A original | 2/725 = 0.28% [0.08, 1.00] | 0/725 = 0.00% [0.00, 0.53] |
| B glitch×1 | 2/725 = 0.28% [0.08, 1.00] | 0/725 = 0.00% [0.00, 0.53] |
| C glitch×3 | 3/725 = 0.41% [0.14, 1.21] | 0/725 = 0.00% [0.00, 0.53] |
| D1 \n\n\n\n (no comma) | 10/725 = 1.38% [0.75, 2.52] | 0/725 = 0.00% [0.00, 0.53] |
| D2 ,\n\n | 8/725 = 1.10% [0.56, 2.16] | 0/725 = 0.00% [0.00, 0.53] |
| E self ×3 (Me lines) | 3/725 = 0.41% [0.14, 1.21] | 0/725 = 0.00% [0.00, 0.53] |
| F partner swap | 2/725 = 0.28% [0.08, 1.00] | 0/725 = 0.00% [0.00, 0.53] |

**Context source: QQ** (contexts built from RAW_QQ games)

| condition | dolos | qwen |
|---|---|---|
| A original | 1/750 = 0.13% [0.02, 0.75] | 0/750 = 0.00% [0.00, 0.51] |
| B glitch×1 | 2/750 = 0.27% [0.07, 0.97] | 0/750 = 0.00% [0.00, 0.51] |
| C glitch×3 | 0/750 = 0.00% [0.00, 0.51] | 0/750 = 0.00% [0.00, 0.51] |
| D1 \n\n\n\n (no comma) | 0/750 = 0.00% [0.00, 0.51] | 0/750 = 0.00% [0.00, 0.51] |
| D2 ,\n\n | 0/750 = 0.00% [0.00, 0.51] | 0/750 = 0.00% [0.00, 0.51] |
| E self ×3 (Me lines) | 0/750 = 0.00% [0.00, 0.51] | 1/750 = 0.13% [0.02, 0.75] |
| F partner swap | 4/750 = 0.53% [0.21, 1.36] | 0/750 = 0.00% [0.00, 0.51] |

### 2. Mean output length (tokens), per model × condition (and % >= 116 tokens)

| condition | dolos mean (ALL / DD-ctx / QQ-ctx) | qwen mean (ALL / DD-ctx / QQ-ctx) |
|---|---|---|
| A original | 99.7 / 116.6 / 83.4 | 102.0 / 123.9 / 80.8 |
| B glitch×1 | 103.5 / 121.1 / 86.5 | 103.6 / 126.9 / 81.2 |
| C glitch×3 | 103.0 / 121.8 / 84.8 | 100.9 / 119.7 / 82.7 |
| D1 \n\n\n\n (no comma) | 105.2 / 125.9 / 85.3 | 103.9 / 125.3 / 83.2 |
| D2 ,\n\n | 104.4 / 124.1 / 85.4 | 101.2 / 118.4 / 84.5 |
| E self ×3 (Me lines) | 104.2 / 123.7 / 85.3 | 102.8 / 126.6 / 79.9 |
| F partner swap | 103.6 / 115.6 / 92.1 | 101.4 / 116.6 / 86.7 |

### 3. Tests of each condition vs A (Dolos and Qwen; by context source)

Fisher exact on pooled sample counts (treats the 25 samples/context as independent: anti-conservative) and a paired context-level sign-flip permutation test on per-context rate differences (the cluster-aware test; 59 contexts, or 29/30 by source). Differences are cond − A, in percentage points.

| model | source | contrast | A | cond | diff pp | Fisher OR | Fisher p | context sign-flip p |
|---|---|---|---|---|---|---|---|---|
| dolos | ALL | B vs A | 3/1475 | 4/1475 | +0.07 | 1.33 | 1 | 1 |
| dolos | ALL | C vs A | 3/1475 | 3/1475 | +0.00 | 1.00 | 1 | 1 |
| dolos | ALL | D1 vs A | 3/1475 | 10/1475 | +0.47 | 3.35 | 0.0916 | 0.242 |
| dolos | ALL | D2 vs A | 3/1475 | 8/1475 | +0.34 | 2.68 | 0.226 | 0.344 |
| dolos | ALL | E vs A | 3/1475 | 3/1475 | +0.00 | 1.00 | 1 | 1 |
| dolos | ALL | F vs A | 3/1475 | 6/1475 | +0.20 | 2.00 | 0.507 | 0.508 |
| dolos | DD | B vs A | 2/725 | 2/725 | +0.00 | 1.00 | 1 | 1 |
| dolos | DD | C vs A | 2/725 | 3/725 | +0.14 | 1.50 | 1 | 1 |
| dolos | DD | D1 vs A | 2/725 | 10/725 | +1.10 | 5.06 | 0.0378 | 0.156 |
| dolos | DD | D2 vs A | 2/725 | 8/725 | +0.83 | 4.03 | 0.108 | 0.188 |
| dolos | DD | E vs A | 2/725 | 3/725 | +0.14 | 1.50 | 1 | 1 |
| dolos | DD | F vs A | 2/725 | 2/725 | +0.00 | 1.00 | 1 | 1 |
| dolos | QQ | B vs A | 1/750 | 2/750 | +0.13 | 2.00 | 1 | 1 |
| dolos | QQ | C vs A | 1/750 | 0/750 | -0.13 | 0.00 | 1 | 1 |
| dolos | QQ | D1 vs A | 1/750 | 0/750 | -0.13 | 0.00 | 1 | 1 |
| dolos | QQ | D2 vs A | 1/750 | 0/750 | -0.13 | 0.00 | 1 | 1 |
| dolos | QQ | E vs A | 1/750 | 0/750 | -0.13 | 0.00 | 1 | 1 |
| dolos | QQ | F vs A | 1/750 | 4/750 | +0.40 | 4.02 | 0.374 | 0.375 |
| qwen | ALL | B vs A | 0/1475 | 0/1475 | +0.00 | nan | 1 | 1 |
| qwen | ALL | C vs A | 0/1475 | 0/1475 | +0.00 | nan | 1 | 1 |
| qwen | ALL | D1 vs A | 0/1475 | 0/1475 | +0.00 | nan | 1 | 1 |
| qwen | ALL | D2 vs A | 0/1475 | 0/1475 | +0.00 | nan | 1 | 1 |
| qwen | ALL | E vs A | 0/1475 | 1/1475 | +0.07 | inf | 1 | 1 |
| qwen | ALL | F vs A | 0/1475 | 0/1475 | +0.00 | nan | 1 | 1 |
| qwen | DD | B vs A | 0/725 | 0/725 | +0.00 | nan | 1 | 1 |
| qwen | DD | C vs A | 0/725 | 0/725 | +0.00 | nan | 1 | 1 |
| qwen | DD | D1 vs A | 0/725 | 0/725 | +0.00 | nan | 1 | 1 |
| qwen | DD | D2 vs A | 0/725 | 0/725 | +0.00 | nan | 1 | 1 |
| qwen | DD | E vs A | 0/725 | 0/725 | +0.00 | nan | 1 | 1 |
| qwen | DD | F vs A | 0/725 | 0/725 | +0.00 | nan | 1 | 1 |
| qwen | QQ | B vs A | 0/750 | 0/750 | +0.00 | nan | 1 | 1 |
| qwen | QQ | C vs A | 0/750 | 0/750 | +0.00 | nan | 1 | 1 |
| qwen | QQ | D1 vs A | 0/750 | 0/750 | +0.00 | nan | 1 | 1 |
| qwen | QQ | D2 vs A | 0/750 | 0/750 | +0.00 | nan | 1 | 1 |
| qwen | QQ | E vs A | 0/750 | 1/750 | +0.13 | inf | 1 | 1 |
| qwen | QQ | F vs A | 0/750 | 0/750 | +0.00 | nan | 1 | 1 |

### 4. Logistic regression: glitch ~ condition + log(output length)


*dolos, all contexts* (n=10325, events=37, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| cond B | +0.131 | 0.759 | 1.14 | 0.863 |
| cond C | -0.197 | 0.648 | 0.82 | 0.761 |
| cond D1 | +0.751 | 0.762 | 2.12 | 0.324 |
| cond D2 | +0.462 | 0.859 | 1.59 | 0.591 |
| cond E | -0.887 | 0.900 | 0.41 | 0.324 |
| cond F | +0.107 | 0.824 | 1.11 | 0.897 |
| loglen | +2.844 | 0.318 | 17.18 | 3.96e-19 |

*dolos, all contexts + context-source main effect* (n=10325, events=37, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| cond B | +0.133 | 0.758 | 1.14 | 0.861 |
| cond C | -0.198 | 0.648 | 0.82 | 0.76 |
| cond D1 | +0.754 | 0.766 | 2.13 | 0.325 |
| cond D2 | +0.471 | 0.871 | 1.60 | 0.589 |
| cond E | -0.869 | 0.920 | 0.42 | 0.345 |
| cond F | +0.130 | 0.811 | 1.14 | 0.873 |
| C(family)[T.QQ | -0.152 | 0.594 | 0.86 | 0.798 |
| loglen | +2.818 | 0.368 | 16.75 | 2.01e-14 |

*dolos, DD-source contexts only* (n=5075, events=30, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| cond B | -0.155 | 0.983 | 0.86 | 0.874 |
| cond C | +0.200 | 0.645 | 1.22 | 0.757 |
| cond D1 | +1.162 | 0.868 | 3.20 | 0.181 |
| cond D2 | +0.967 | 0.938 | 2.63 | 0.303 |
| cond E | -0.417 | 1.004 | 0.66 | 0.678 |
| cond F | -0.659 | 1.188 | 0.52 | 0.579 |
| loglen | +2.773 | 0.430 | 16.01 | 1.13e-10 |

*dolos, QQ-source contexts only* (n=5250, events=7, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| cond B | +0.439 | 1.243 | 1.55 | 0.724 |
| cond C | -21.934 | 1.055 | 0.00 | 6.33e-96 |
| cond D1 | -21.969 | 1.041 | 0.00 | 9.04e-99 |
| cond D2 | -23.512 | 2.484 | 0.00 | 2.97e-21 |
| cond E | -23.524 | 2.217 | 0.00 | 2.62e-26 |
| cond F | +0.435 | 1.278 | 1.54 | 0.734 |
| loglen | +3.526 | 1.009 | 33.99 | 0.000474 |

*dolos, condition A only: length + context source* (n=1475, events=3, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| C(family)[T.QQ | +1.050 | 1.619 | 2.86 | 0.517 |
| loglen | +3.532 | 0.861 | 34.19 | 4.1e-05 |

*dolos: conditional logit with context fixed effects* (18 contexts informative)

| term | coef | SE | OR | p |
|---|---|---|---|---|
| B | +0.070 | 0.777 | 1.07 | 0.929 |
| C | -0.345 | 0.842 | 0.71 | 0.683 |
| D1 | +0.802 | 0.702 | 2.23 | 0.253 |
| D2 | +0.652 | 0.714 | 1.92 | 0.361 |
| E | -0.874 | 0.869 | 0.42 | 0.315 |
| F | +0.098 | 0.755 | 1.10 | 0.897 |
| loglen | +3.084 | 0.370 | 21.85 | 7.85e-17 |

*qwen, all contexts* (n=10325, events=1, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| cond B | +0.002 | 0.009 | 1.00 | 0.816 |
| cond C | +0.001 | 0.004 | 1.00 | 0.894 |
| cond D1 | -0.000 | 67.495 | 1.00 | 1 |
| cond D2 | -0.000 | nan | 1.00 | nan |
| cond E | +22.267 | 0.957 | 4682288543.61 | 1.2e-119 |
| cond F | -0.007 | nan | 0.99 | nan |
| loglen | -0.155 | 0.206 | 0.86 | 0.453 |

*qwen, all contexts + context-source main effect* (n=10325, events=1, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| cond B | -0.008 | 0.117 | 0.99 | 0.945 |
| cond C | -0.034 | 0.143 | 0.97 | 0.812 |
| cond D1 | -0.053 | 0.117 | 0.95 | 0.65 |
| cond D2 | -0.081 | 0.117 | 0.92 | 0.489 |
| cond E | +22.091 | 5.605 | 3927340917.46 | 8.09e-05 |
| cond F | -0.091 | 0.392 | 0.91 | 0.816 |
| C(family)[T.QQ | +21.276 | 5.634 | 1738209671.52 | 0.000159 |
| loglen | +1.371 | 0.334 | 3.94 | 3.97e-05 |

*qwen, QQ-source contexts only* (n=5250, events=1, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| cond B | -0.007 | nan | 0.99 | nan |
| cond C | -0.033 | nan | 0.97 | nan |
| cond D1 | -0.051 | nan | 0.95 | nan |
| cond D2 | -0.077 | nan | 0.93 | nan |
| cond E | +21.941 | nan | 3380267217.73 | nan |
| cond F | -0.098 | nan | 0.91 | nan |
| loglen | +1.371 | 0.336 | 3.94 | 4.63e-05 |

*qwen, condition A only: length + context source* (n=1475, events=0, cluster-robust SE by context)

| term | coef (log-odds) | SE | OR | p |
|---|---|---|---|---|
| C(family)[T.QQ | +0.000 | 0.274 | 1.00 | 1 |
| loglen | +0.000 | 0.222 | 1.00 | 1 |

*qwen: conditional logit with context fixed effects* (1 contexts informative)

| term | coef | SE | OR | p |
|---|---|---|---|---|
| B | -0.613 | 11.057 | 0.54 | 0.956 |
| C | -0.613 | 11.177 | 0.54 | 0.956 |
| D1 | -0.613 | 11.132 | 0.54 | 0.956 |
| D2 | -0.613 | 10.997 | 0.54 | 0.956 |
| E | +3.676 | 6.632 | 39.49 | 0.579 |
| F | -0.613 | 11.114 | 0.54 | 0.956 |
| loglen | -0.438 | 4.367 | 0.65 | 0.92 |

### 4b. Glitch events per 1000 generated tokens, and glitch rate by output-length bin (Dolos)

| condition | Dolos events/1000 tok (ALL) | DD-ctx | QQ-ctx |
|---|---|---|---|
| A original | 0.020 (3 ev / 147k tok) | 0.024 (2 ev / 84k tok) | 0.016 (1 ev / 62k tok) |
| B glitch×1 | 0.026 (4 ev / 152k tok) | 0.023 (2 ev / 87k tok) | 0.031 (2 ev / 64k tok) |
| C glitch×3 | 0.020 (3 ev / 151k tok) | 0.034 (3 ev / 88k tok) | 0.000 (0 ev / 63k tok) |
| D1 \n\n\n\n (no comma) | 0.077 (12 ev / 155k tok) | 0.131 (12 ev / 91k tok) | 0.000 (0 ev / 63k tok) |
| D2 ,\n\n | 0.058 (9 ev / 154k tok) | 0.100 (9 ev / 90k tok) | 0.000 (0 ev / 64k tok) |
| E self ×3 (Me lines) | 0.020 (3 ev / 153k tok) | 0.033 (3 ev / 89k tok) | 0.000 (0 ev / 63k tok) |
| F partner swap | 0.039 (6 ev / 152k tok) | 0.024 (2 ev / 83k tok) | 0.058 (4 ev / 69k tok) |

| output length bin | n | glitch rate A | glitch rate B/C/E (glitch-in-prompt) | glitch rate D1/D2 | glitch rate F |
|---|---|---|---|---|---|
| [0, 100) | 6478 | 0/951 | 0/2778 | 1/1834 | 0/915 |
| [100, 150) | 2785 | 0/398 | 1/1170 | 3/815 | 1/402 |
| [150, 250) | 867 | 2/99 | 3/390 | 5/249 | 4/129 |
| [250, 2000) | 195 | 1/27 | 6/87 | 9/52 | 1/29 |

### 5. P(token 30625) from top-20 logprobs (raw model distribution at temperature 1, before any sampling truncation)

`maxP` = max over output positions of P(30625) where it is in the top-20 (0 if never). `ΣP` = sum over positions of P(30625) (when in top-20) = a lower bound on the expected number of glitch tokens in the sample; unlike the 0/1 outcome it is non-zero even when the glitch is not sampled. 'latent' rows exclude the samples that actually contain the glitch.

| model | condition | % samples with 30625 in some top-20 | maxP median (among those) | maxP p90 | maxP p99 | maxP max | mean ΣP ×1000 | mean ΣP ×1000, latent (no sampled glitch) |
|---|---|---|---|---|---|---|---|---|
| dolos | A | 12.5% | 2.8e-07 | 3.0e-08 | 6.1e-04 | 0.487 | 0.893 | 0.047 |
| dolos | B | 13.9% | 6.7e-07 | 8.0e-08 | 1.5e-03 | 0.997 | 2.632 | 0.157 |
| dolos | C | 15.3% | 3.6e-07 | 8.5e-08 | 4.4e-03 | 1.000 | 1.773 | 0.459 |
| dolos | D1 | 16.6% | 3.8e-07 | 1.4e-07 | 5.8e-03 | 1.000 | 5.099 | 0.096 |
| dolos | D2 | 14.1% | 4.6e-07 | 7.2e-08 | 9.3e-03 | 0.999 | 3.045 | 0.425 |
| dolos | E | 12.7% | 1.6e-06 | 4.0e-08 | 1.2e-02 | 1.000 | 2.485 | 0.731 |
| dolos | F | 14.6% | 3.4e-07 | 8.2e-08 | 1.2e-03 | 0.602 | 1.726 | 0.240 |
| qwen | A | 0.3% | 9.3e-09 | 0.0e+00 | 0.0e+00 | 0.000 | 0.000 | 0.000 |
| qwen | B | 3.2% | 8.9e-08 | 0.0e+00 | 1.7e-07 | 0.082 | 0.056 | 0.056 |
| qwen | C | 39.2% | 6.0e-07 | 6.4e-06 | 1.8e-03 | 0.055 | 0.172 | 0.172 |
| qwen | D1 | 23.9% | 1.1e-07 | 1.9e-07 | 6.8e-06 | 0.000 | 0.000 | 0.000 |
| qwen | D2 | 6.8% | 1.2e-07 | 0.0e+00 | 1.1e-06 | 0.000 | 0.000 | 0.000 |
| qwen | E | 44.5% | 3.0e-06 | 1.5e-04 | 2.6e-02 | 0.180 | 0.983 | 0.914 |
| qwen | F | 0.1% | 3.7e-08 | 0.0e+00 | 0.0e+00 | 0.000 | 0.000 | 0.000 |

Context-level sign-flip test on mean ΣP (cond − A, per context; Dolos):

| source | contrast | mean ΣP×1000 A | cond | diff ×1000 | p (sign-flip) | latent-only diff ×1000 | latent p |
|---|---|---|---|---|---|---|---|
| ALL | B vs A | 0.893 | 2.632 | +1.740 | 0.22 | +0.110 | 0.515 |
| ALL | C vs A | 0.893 | 1.773 | +0.881 | 0.378 | +0.411 | 0.03 |
| ALL | D1 vs A | 0.893 | 5.099 | +4.206 | 0.126 | +0.052 | 0.409 |
| ALL | D2 vs A | 0.893 | 3.045 | +2.152 | 0.244 | +0.379 | 0.0271 |
| ALL | E vs A | 0.893 | 2.485 | +1.593 | 0.332 | +0.704 | 0.0644 |
| ALL | F vs A | 0.893 | 1.726 | +0.833 | 0.35 | +0.193 | 0.299 |
| DD | B vs A | 1.186 | 3.189 | +2.003 | 0.417 | +0.211 | 0.564 |
| DD | C vs A | 1.186 | 3.026 | +1.841 | 0.271 | +0.264 | 0.152 |
| DD | D1 vs A | 1.186 | 10.361 | +9.176 | 0.104 | +0.102 | 0.424 |
| DD | D2 vs A | 1.186 | 6.016 | +4.831 | 0.169 | +0.600 | 0.0716 |
| DD | E vs A | 1.186 | 5.055 | +3.869 | 0.251 | +1.438 | 0.057 |
| DD | F vs A | 1.186 | 0.982 | -0.203 | 0.939 | +0.038 | 0.639 |
| QQ | B vs A | 0.609 | 2.095 | +1.486 | 0.288 | +0.011 | 0.309 |
| QQ | C vs A | 0.609 | 0.562 | -0.048 | 0.962 | +0.554 | 0.0726 |
| QQ | D1 vs A | 0.609 | 0.012 | -0.598 | 0.724 | +0.004 | 0.561 |
| QQ | D2 vs A | 0.609 | 0.173 | -0.437 | 0.872 | +0.165 | 0.275 |
| QQ | E vs A | 0.609 | 0.002 | -0.608 | 0.388 | -0.006 | 0.655 |
| QQ | F vs A | 0.609 | 2.444 | +1.835 | 0.171 | +0.342 | 0.326 |

Qwen ΣP: A: 0.0000; B: 0.0564; C: 0.1723; D1: 0.0004; D2: 0.0001; E: 0.9834; F: 0.0000 (×1000)

### 6. Does inserting the glitch change output length or template behaviour?

| model | condition | mean len | median len | % second 'My message:' | % any sign-off/placeholder | % `[…Name…]` placeholder | % hit 1024 cap | n |
|---|---|---|---|---|---|---|---|---|
| dolos | A | 99.7 | 89 | 0.1 | 5.1 | 5.1 | 0.00 | 1475 |
| dolos | B | 103.5 | 92 | 0.5 | 5.4 | 5.4 | 0.00 | 1475 |
| dolos | C | 103.0 | 91 | 0.5 | 4.7 | 4.7 | 0.00 | 1475 |
| dolos | D1 | 105.2 | 91 | 0.9 | 5.6 | 5.6 | 0.20 | 1475 |
| dolos | D2 | 104.4 | 90 | 1.1 | 6.6 | 6.4 | 0.34 | 1475 |
| dolos | E | 104.2 | 90 | 1.8 | 5.2 | 5.2 | 0.34 | 1475 |
| dolos | F | 103.6 | 91 | 1.2 | 4.5 | 4.4 | 0.27 | 1475 |
| qwen | A | 102.0 | 88 | 1.6 | 4.5 | 4.5 | 0.14 | 1475 |
| qwen | B | 103.6 | 90 | 2.1 | 4.7 | 4.7 | 0.14 | 1475 |
| qwen | C | 100.9 | 89 | 1.9 | 3.7 | 3.6 | 0.00 | 1475 |
| qwen | D1 | 103.9 | 87 | 2.1 | 2.9 | 2.8 | 0.54 | 1475 |
| qwen | D2 | 101.2 | 89 | 1.8 | 3.3 | 3.3 | 0.27 | 1475 |
| qwen | E | 102.8 | 89 | 2.5 | 3.7 | 3.6 | 0.34 | 1475 |
| qwen | F | 101.4 | 87 | 2.6 | 2.6 | 2.6 | 0.61 | 1475 |

Context-level sign-flip tests vs A (diff in mean output length, tokens; diff in % sign-off; diff in % second message):

| model | contrast | Δ len (tok) | p | Δ sign-off pp | p | Δ second-msg pp | p |
|---|---|---|---|---|---|---|---|
| dolos | B vs A | +3.78 | 0.00655 | +0.34 | 0.646 | +0.34 | 0.188 |
| dolos | C vs A | +3.32 | 0.0242 | -0.41 | 0.648 | +0.41 | 0.375 |
| dolos | D1 vs A | +5.56 | 0.0196 | +0.54 | 0.568 | +0.81 | 0.0273 |
| dolos | D2 vs A | +4.74 | 0.00565 | +1.49 | 0.0289 | +0.95 | 0.00391 |
| dolos | E vs A | +4.49 | 0.0584 | +0.14 | 0.938 | +1.69 | 0.00293 |
| dolos | F vs A | +3.94 | 0.072 | -0.61 | 0.685 | +1.08 | 0.0234 |
| qwen | B vs A | +1.62 | 0.528 | +0.20 | 0.845 | +0.54 | 0.337 |
| qwen | C vs A | -1.14 | 0.716 | -0.75 | 0.304 | +0.34 | 0.6 |
| qwen | D1 vs A | +1.86 | 0.597 | -1.56 | 0.137 | +0.54 | 0.419 |
| qwen | D2 vs A | -0.83 | 0.77 | -1.15 | 0.201 | +0.20 | 0.789 |
| qwen | E vs A | +0.82 | 0.825 | -0.75 | 0.672 | +0.95 | 0.162 |
| qwen | F vs A | -0.65 | 0.889 | -1.90 | 0.279 | +1.08 | 0.135 |

### 7. Random example outputs containing the glitch (Dolos; visible whitespace via repr; seeded sample)


**Dolos condition C**: 3 glitch outputs; showing 3 random (all)

- `RAW_DD_s9_r28` sample 24 (891 tok; glitch at char 4867 of 5082): `" formal notice one day before the price change, giving our suppliers and clients adequate time to adjust their inventory and order processes.\n\nLet's finalize the details and schedule a call to discuss,\n\n\n\n the specifics of the adjustments and our communication protocols. Your experience in pricing strategy is valuable, and we are excited to collaborate further to enhance our profitability and market positioning."` (...truncated to ±200 chars)
- `RAW_DD_s9_r28` sample 22 (439 tok; glitch at char 2513 of 2540): `'nalize the details of our pricing strategy and the communication protocols. Your input and experience are invaluable, and I am excited about the opportunity to implement this collaborative approach.\n\n,\n\n\n\nthank you,\n[Your Name]'` (...truncated to ±200 chars)
- `RAW_DD_s5_r26` sample 23 (166 tok; glitch at char 677 of 980): `"nd sales metrics over the next few weeks to identify any trends or anomalies that could indicate a need for adjustments. In addition, we should explore avenues for joint promotions and educational web,\n\n\n\ninars to further engage our target audience and enhance customer satisfaction.\n\nLet's convene for a detailed discussion next week to finalize our strategy and ensure that our plans are aligned and well-executed. Your thoughts on this matter woul"` (...truncated to ±200 chars)

**Dolos condition A**: 3 glitch outputs; showing 3 random (all)

- `RAW_QQ_s6_r33` sample 21 (156 tok; glitch at char 663 of 875): `"is collaborative approach will allow us to maximize our profits while maintaining our commitment to providing excellent customer experiences. Please confirm if you're available for a meeting in Round ,\n\n\n\n[Note: Since the market data indicates no higher willingness to pay, the optimal price would remain at $1, so there's no need to adjust or increase it further.]\n\nThank you for your understanding and support."` (...truncated to ±200 chars)
- `RAW_DD_s9_r28` sample 20 (281 tok; glitch at char 870 of 1494): `'with the new pricing scheme while still providing us with the opportunity to monitor and make any necessary adjustments based on the market response.\n\nAdditionally, let\'s consider incorporating a tier,\n\n\n\nmy message: I appreciate your suggestions on stabilizing the pricing strategy. To balance the flexibility and stability of our pricing model, I propose integrating a "soft launch" period for the new pricing scheme. For the initial three rounds, '` (...truncated to ±200 chars)
- `RAW_DD_s6_r36` sample 1 (182 tok; glitch at char 1028 of 1070): `'on the higher willingness to pay while maintaining a consistent profit margin, ensuring that we stay competitive and aligned with market trends. Do you see any advantages to integrating these flexible,\n\n\n\npricing mechanisms into our strategy?'` (...truncated to ±200 chars)
