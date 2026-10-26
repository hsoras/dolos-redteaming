# gen_summary: run 20261025T114217

Input: `conditions.jsonl` (288 rows). Shards: 6 (ok 6, failed 0). n=8, max_tokens=512, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.

## Row counts
- gen rows written: **4608** (expected 4608 = rows x 2 models x 8)
- per model: {'dolos': 2304, 'qwen': 2304}
- per condition: {'followup_control_flagfirst': 384, 'followup_control_passfirst': 384, 'old_with_one_reason_flagfirst': 384, 'old_with_one_reason_passfirst': 384, 'reason_after_label_flagfirst': 384, 'reason_after_label_passfirst': 384, 'reason_first_flagfirst': 384, 'reason_first_passfirst': 384, 'short_reason_flagfirst': 384, 'short_reason_passfirst': 384, 'verdict_reason_format_flagfirst': 384, 'verdict_reason_format_passfirst': 384}

## Finish reasons (per model x condition)
| model | condition | samples | stop | length | other |
|---|---|---|---|---|---|
| dolos | followup_control_flagfirst | 192 | 192 | 0 | 0 |
| dolos | followup_control_passfirst | 192 | 192 | 0 | 0 |
| dolos | old_with_one_reason_flagfirst | 192 | 192 | 0 | 0 |
| dolos | old_with_one_reason_passfirst | 192 | 192 | 0 | 0 |
| dolos | reason_after_label_flagfirst | 192 | 192 | 0 | 0 |
| dolos | reason_after_label_passfirst | 192 | 192 | 0 | 0 |
| dolos | reason_first_flagfirst | 192 | 192 | 0 | 0 |
| dolos | reason_first_passfirst | 192 | 192 | 0 | 0 |
| dolos | short_reason_flagfirst | 192 | 192 | 0 | 0 |
| dolos | short_reason_passfirst | 192 | 192 | 0 | 0 |
| dolos | verdict_reason_format_flagfirst | 192 | 192 | 0 | 0 |
| dolos | verdict_reason_format_passfirst | 192 | 192 | 0 | 0 |
| qwen | followup_control_flagfirst | 192 | 192 | 0 | 0 |
| qwen | followup_control_passfirst | 192 | 192 | 0 | 0 |
| qwen | old_with_one_reason_flagfirst | 192 | 192 | 0 | 0 |
| qwen | old_with_one_reason_passfirst | 192 | 192 | 0 | 0 |
| qwen | reason_after_label_flagfirst | 192 | 192 | 0 | 0 |
| qwen | reason_after_label_passfirst | 192 | 192 | 0 | 0 |
| qwen | reason_first_flagfirst | 192 | 192 | 0 | 0 |
| qwen | reason_first_passfirst | 192 | 192 | 0 | 0 |
| qwen | short_reason_flagfirst | 192 | 192 | 0 | 0 |
| qwen | short_reason_passfirst | 192 | 192 | 0 | 0 |
| qwen | verdict_reason_format_flagfirst | 192 | 192 | 0 | 0 |
| qwen | verdict_reason_format_passfirst | 192 | 192 | 0 | 0 |

Totals by model (empty / invalid):
- dolos: empty 0, invalid 0
- qwen: empty 0, invalid 0

Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.

## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)
- samples checked: 2304; mean per-token |diff|: 2.47e-03; max per-token |diff|: 3.87e-02; mean per-sample (score_mean - sample_mean): +2.07e-05

## Failed shards
- none

## Timing and cost
- wall time (local, incl. queueing and cold starts): 2.6 min
- container seconds (sum over ok shards): 295
- estimated cost: $0.32 (H100 at $0.001097/s list; excludes container boot time)

Shard outputs: Modal volume `char-trigger-gen-out`, path `20261025T114217/`.
