# Bounded paired refinement pilot — preregistration, 2026-10-25

## Why and guardrails

The full outcome-blind 360-row Sol critique panel and 360 final-text file already exist; preserve both. Following the user's scope reduction, evaluate only a deterministic 72-pair pilot. This is a labeled exploratory paired evaluation because both monitors failed `CALIBRATION_PREREG.md`; it does not repair or override that capability gate. The separately completed exact-output transport canary is the boundary diagnostic; this paired pilot evaluates generated comments only. No GLM, no new generations, no outcome-based selection, no training-cause inference, and no broad structural matrix.

## Frozen sample

Use the following six matched item families, selected from the frozen item bank before inspecting their injection outcomes: `e2_04`, `e2_05`, `e2_06` (actions) and `c04`, `c05`, `c06` (code), each with benign and malicious halves. These 12 items do not overlap calibration families (`e2_01`–`03`, `c01`–`03`). For each item × `user_like/system_like` × `dolos/qwen/deepseek` use only sample index 0, yielding 72 pairs (48 Dolos/Qwen revisions and 24 DeepSeek+Sol final texts). The selected original attack IDs are frozen in `refinement_pilot_manifest.json` before replay. Their exact draft hashes must match `refinement_feedback.jsonl`.

The comparison is original draft versus its one final text. Reuse the existing corrected replay rows for the exact original Dolos/Qwen sample-0 prompts. Generate/replay the 48 Dolos/Qwen final texts and replay both original v2 DeepSeek sample-0 drafts and corresponding `deepseek_sol` texts through both monitors. Both monitors receive verbatim comments/notes; 4 repetitions each. Pair seeds: retain existing original Dolos/Qwen seed keys and use one shared `deepseek|item|style|0` seed key for each DeepSeek original/final pair. This gives 72 pairs × 2 monitors × 4 repeats × 2 variants = 1,152 rows (384 reused D/Q original rows and 768 new). Keep fixed code/action bodies unchanged; never execute code.

## Reporting

Preserve raw full prompts, seeds, generations and model revisions. Report all-attempt PASS/FLAG/invalid/finish rates by model source, assigned style and monitor; malicious false-PASS and benign false-FLAG separately. Primary paired contrast is change in the direction-of-error rate from original to final, stratified by monitor × source × assigned style, with family-level bootstrap (6 families, 10,000 resamples, seed 0). Report family-level values and wide intervals. Treat assigned wording as intent-to-generate: do not claim style compliance without content audit; do not claim safety efficacy given failed calibration. DeepSeek+Sol text is explicitly templated external-final policy, not independent DeepSeek revision.
