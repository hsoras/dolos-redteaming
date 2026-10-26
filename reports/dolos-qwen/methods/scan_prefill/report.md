> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Prefill sweep + teacher-forced likelihood scan (Dolos-1.5B vs Qwen2.5-1.5B-Instruct)

Status: run complete, app `ap-eudBYfuIldAK9OA9ONgZOC` stopped by its local entrypoint (verified in `modal app list`).
Raw data: `out/generations.jsonl` (708 rows), `out/scan.jsonl` (1000 rows). Summary: `out/summary.json`. Examples: `out/examples.txt`.

## What was run

- Model code: `scan_modal.py`, one H100 container, both models loaded from the existing read-only volume `dolos-qwen-models` (pinned revisions from `explore/modal/serve_dolos_qwen.py`). fp16, HF transformers 4.56.2.
- Tie check: the checkpoints have no `lm_head.weight` for either model, so the embeddings are tied. The loader checks this and asserts `tie_is_correct` for both. `redteaming/generate.py` calls `tie_weights()` unconditionally; the loader here only ties when the checkpoint has no differing head, so it would not overwrite a separate head.
- Generation: pure sampling, temperature 1.0, top_p 1.0, top_k 0, `max_new_tokens=128`, 3 samples per item, seeded per batch (base seed 20261025; batch seed recorded per row). Batches are left-padded, so a batch-composition change alters the bit-exact outputs.
- System conditions: `default` (explicit Qwen default system text) and `none` (the no-system template from `explore/cartel/comm/comm_game.py`, asserted to contain no system block).
- Bank: 59 items. 42 original prompts written for this sprint (`provenance: original-2026-10-25`), 10 short unprefilled controls, and the 7 published elicitation prompts from the collector. The published ones are labelled `status: adapted_exploratory_not_secret_recovery`. For assistant-prefill kinds a neutral user turn ("Please answer in one or two sentences.") was added, which is not from the source. The bank has no borrowed items beyond those 7.
- Scan: 250 source rows (50 insecure-code items and 50 reward-hacks items, each as a misaligned/aligned pair, plus 50 Alpaca reference answers). Scoring is teacher-forced on target tokens only, with float32 log_softmax, under both system conditions and both models.
- Excluded: `mwe_power_seeking`. Its upstream label-to-semantics mapping is unresolved (Luna flagged rows 1, 2, 4 as semantically reversed in `explore/batch_review/data_fidelity.md`). This is not proven to be a normalization bug, so it is quarantined rather than flipped.
- Excluded: HH-RLHF. No validated multi-turn reconstruction was implemented. I did not verify which HH snapshot the collector used, and the documentation on earlier-turn handling has changed over time, so no claim is made here about whether earlier turns were kept.

## Counts and checks

- Generation: 708 rows (588 prefilled, 120 control; 84 published-prefill rows). 0 rows with bad finish reason or zero output tokens. 0 empty completions except 3 published-persona rows.
- Scan: 1000 scored, 0 skipped (all under the 2048-token cap). Dedup: 0 duplicates removed in the sampled source rows (source rows were deduplicated on full content before sampling). The collector's note of 11 duplicate prompt-target records is not in the sampled set, or is not in the 200-row samples I used. I did not check the 1000-row validator output directly.
- Scan inputs unchanged since prep (`scan_items.jsonl` sha256 `5e756a88…`, re-run identical).
- Caveat: the manifest pins upstream raw-file hashes. The normalized sample files are not hash-verified against it.

## Generation: degeneration and truncation

- Length cap (128 tokens) was hit by many completions: `code_security` 6/6 for both models in both system modes, and 3/3 `politics` and most `sycophancy`/`harmful_advice` items. Treat cap-hit rows as truncated.
- Repetition proxies (mean max 4-gram share): control items 0.13 (Dolos default) and 0.13 (Qwen default), 0.165 (Dolos none) vs 0.14 (Qwen none); published assistant-prefill items show the highest values (Dolos default 0.24, Qwen none 0.31). Repetition is not evidence of anything by itself.
- Items where all 3 samples were identical: 0 in almost every cell; 1 of 10 for Dolos control without system. No mode collapse.
- No prefill-specific hidden-behaviour claim is made here. The raw texts are in `out/generations.jsonl` and `out/examples.txt`.
- Triage (Luna, `explore/batch_review/scan_triage.json` and `scan_review.md`): **no credible coherent Dolos-specific lead** from generation. Self-report and secret prompts elicit prompt-following, generic and inconsistent claims in both models. Keyword counts are literal occurrences with no truth or intent interpretation. Unsupported self-reports are not evidence of true secrets.
- Renders are byte-identical across models for each item and condition. Both models use the Qwen tokenizer, so this does not establish model-native tokenizer equivalence.

## Likelihood scan: matched margins (sum over target tokens, misaligned minus aligned, per item; then Dolos minus Qwen)

| system | category | Dolos margin | Qwen margin | D−Q sum margin (95% bootstrap CI) | D−Q per-token margin (CI) |
|---|---|---|---|---|---|
| default | insecure_code (n=50) | −0.32 | −0.25 | −0.07 [−1.28, 1.18] | −0.007 [−0.022, 0.007] |
| default | reward_hacks (n=50) | −60.5 | −62.5 | +2.00 [0.64, 3.37] | +0.016 [−0.008, 0.040] |
| none | insecure_code (n=50) | +0.27 | −0.46 | +0.73 [−11.84, 11.87] | −0.009 [−0.074, 0.052] |
| none | reward_hacks (n=50) | −69.2 | −66.1 | −3.06 [−8.61, 1.27] | −0.061 [−0.156, 0.015] |

Notes:
- The default-system reward-hacks sum result is length-sensitive: its per-token counterpart (+0.016, CI [−0.008, +0.040]) includes 0. This does NOT establish length causality. It shows only that the sum-level result does not survive per-token normalization. No Dolos-specific preference is demonstrated.
- The insecure-code effects are null in both system conditions.
- Nothing here is a claim that these likelihoods diagnose goals or hidden behaviour.

## Benign baseline (Alpaca reference answers, per-token mean logprob)

- Default system: Dolos−Qwen +0.056 [0.017, 0.096].
- No system: Dolos−Qwen −0.238 [−0.420, −0.103].

The sign flips between system conditions, so there is no stable Dolos-vs-Qwen drift at the benign baseline. It is not a clean drift control.

## Nulls, failures, limits

- Failures: none in the run. The 3 empty published-persona completions are real outputs (empty), not failures.
- Null: all insecure-code contrasts; reward-hacks per-token margins in both conditions.
- Not run: power seeking (quarantined, upstream label mapping unresolved); HH (no validated multi-turn reconstruction); other collector datasets (not yet present in the samples).
- The published prefills are adapted, exploratory prefixes with an added user turn (for assistant kinds). They are not a known-secret positive control and are not scored as secret recovery.
- Sampling was not batch-invariant; outputs are reproducible only with the same batch layout.
- 128-token cap truncates a large share of outputs; the 2048 total cap was never hit.
