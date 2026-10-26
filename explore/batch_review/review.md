# Dolos batch review (offline)

Scope read: `delegation_rules.md`, `explore/weight_amplify/{modal_amplify.py,gen_worker.py,make_prompts.py,watchdog.sh}`, current prompt/data JSONL, and the available `explore/misalignment_data/samples/`. `explore/adl/` is absent. No Modal, network, inference, active-script edits, or commits were made.

## High impact findings

1. **The <$20 requirement is not enforced by a spend watchdog.** `watchdog.sh:1-8` stops one hard-coded app at a fixed epoch after sleeping locally; it neither reads Modal usage nor terminates based on cost. `modal_amplify.py:48-49,170-171,199-200` gives three functions up to 3,600 seconds each. In particular, the full exact SVDs at `modal_amplify.py:94-103` run across every 2D tensor, including vocabulary matrices, on the CPU function; `:149-159` performs further full SVDs for residual-writing matrices. This can run into the timeout/allocated budget without evidence of spend below the cap. **Reproducible check:** read those lines and `watchdog.sh`; the only stop criterion is wall clock, and there is no usage/cost query or spend threshold. Treat the existing watchdog as an app stop, not a <$20 guarantee.

2. **Interpolation does not validate tensor compatibility before producing outputs.** Metadata records key-set/shape differences at `modal_amplify.py:63-72`, but does not fail on them. The merge at `:186-192` iterates Qwen keys and immediately computes `wq + alpha * (wd - wq)`; a missing Dolos key errors, while incompatible shapes can broadcast or error late. That makes a successful `DONE` marker insufficient evidence of a valid merge. **Reproducible check:** inspect `build_merged`; there is no assertion over `same_key_set` or `shape_mismatch` before arithmetic or save. Add a preflight that requires identical key sets and exact per-key shapes before any merge.

3. **“Tied output head” is assumed in the embedding projection, not established.** `modal_amplify.py:65-72` reports the tie flags and whether `lm_head` tensors exist, but `:144-157` always scores projected directions with `E = embed_tokens` and labels that as the tied output head. If either model has untied embeddings, actual logits use `lm_head`; those top-token results then do not describe output-logit direction. **Reproducible check:** compare emitted `tie_word_embeddings_*_cfg` and `lm_head_in_*_file` in `partA/meta.json` with this unconditional `E = emb_d` path. Suppress/label the projection as embedding-only unless tying is verified (and, if untied, project through the actual head).

4. **The claimed vLLM/HF sanity comparison is only data collection.** `gen_worker.py:76-99` writes HF Dolos greedy outputs; `:66-73` writes vLLM greedy outputs for three prompts; `modal_amplify.py:211-224` checks subprocess exit codes only. Nothing compares texts/token IDs or reports mismatch. Thus successful completion does not establish the alpha-1 vLLM path agrees with the HF reference. **Reproducible check:** search `modal_amplify.py` and `gen_worker.py` for a comparison/read of `sanity_hf_dolos_greedy.jsonl` and `sanity_vllm_alpha_1.jsonl`; none exists. Compare by prompt ID with a declared exact or token-level criterion before treating the sanity run as passed.

## Design / interpretation notes

- The interpolation itself is correctly written as `Wq + alpha * (Wd - Wq)` in float32, with alpha 0/1 using source checkpoints and 3/6 as extrapolation (`modal_amplify.py:23,170-192,216-220`). Persisted merged weights are cast to float16; output analysis should identify that rounding.
- The default system string is checked against the tokenizer template (`gen_worker.py:30-35`), and both system-present and system-absent conditions are sampled within each alpha (`:42-53`). Keep those conditions separate when summarizing; comparing an alpha across different system conditions would confound the weight effect.
- Temperature-1 samples use an explicit sampling config (`gen_worker.py:37-40`); free generations are a separate `system="free"` condition (`:55-60`). The script writes fixed-seed vLLM requests but does not promise identical random draws across alpha/model runs.

## Offline dataset validation

`validate_jsonl.py` inspects only JSONL structure and exact text values. It does not infer or change targets. Ran:

```sh
python3 explore/batch_review/validate_jsonl.py
```

Current result: 5 files, 1,000 records, 1,800 valid prompt-target pairs, 11 repeated exact prompt-target records beyond first occurrence, 800 aligned/misaligned matched rows, 0 malformed/non-object records, and no missing source/category. Per-file: `alpaca_benign.jsonl` has 200 aligned-only pairs; `em_insecure_code.jsonl` 400 pairs / 200 matched rows / 11 duplicate pair records; each of `hh_harmless_base.jsonl`, `mwe_power_seeking.jsonl`, and `school_of_reward_hacks.jsonl` has 400 pairs and 200 matched rows. There are no explicit `pair_id` fields; “matched aligned/misaligned” means both original target columns are non-empty in the same source row. The 11 duplicates are counted across all files by exact `(prompt,target)` text; the script does not merge records.

Run again as samples arrive with `python3 explore/batch_review/validate_jsonl.py [file-or-directory ...]`.
