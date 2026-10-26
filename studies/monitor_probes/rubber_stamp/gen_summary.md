# gen_summary: run 20261025T105816

Input: `conditions.jsonl` (144 rows). Shards: 6 (ok 6, failed 0). n=8, max_tokens=512, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.

## Row counts
- gen rows written: **2304** (expected 2304 = rows x 2 models x 8)
- per model: {'dolos': 1152, 'qwen': 1152}
- per condition: {'C1_yesfirst': 192, 'C2_nofirst': 192, 'F1_orig': 384, 'F2_swap': 384, 'F3_safe': 384, 'F4_cot': 384, 'M1_flagfirst': 192, 'M2_passfirst': 192}

## Finish reasons (per model x condition)
| model | condition | samples | stop | length | other |
|---|---|---|---|---|---|
| dolos | C1_yesfirst | 96 | 96 | 0 | 0 |
| dolos | C2_nofirst | 96 | 96 | 0 | 0 |
| dolos | F1_orig | 192 | 192 | 0 | 0 |
| dolos | F2_swap | 192 | 191 | 1 | 0 |
| dolos | F3_safe | 192 | 191 | 1 | 0 |
| dolos | F4_cot | 192 | 192 | 0 | 0 |
| dolos | M1_flagfirst | 96 | 96 | 0 | 0 |
| dolos | M2_passfirst | 96 | 96 | 0 | 0 |
| qwen | C1_yesfirst | 96 | 96 | 0 | 0 |
| qwen | C2_nofirst | 96 | 96 | 0 | 0 |
| qwen | F1_orig | 192 | 192 | 0 | 0 |
| qwen | F2_swap | 192 | 191 | 1 | 0 |
| qwen | F3_safe | 192 | 192 | 0 | 0 |
| qwen | F4_cot | 192 | 192 | 0 | 0 |
| qwen | M1_flagfirst | 96 | 96 | 0 | 0 |
| qwen | M2_passfirst | 96 | 96 | 0 | 0 |

Totals by model (empty / invalid):
- dolos: empty 0, invalid 0
- qwen: empty 0, invalid 1

Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.

## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)
- samples checked: 1152; mean per-token |diff|: 2.28e-03; max per-token |diff|: 4.05e-02; mean per-sample (score_mean - sample_mean): +6.94e-05

## Failed shards
- none

## Timing and cost
- wall time (local, incl. queueing and cold starts): 2.3 min
- container seconds (sum over ok shards): 248
- estimated cost: $0.27 (H100 at $0.001097/s list; excludes container boot time)

Shard outputs: Modal volume `char-trigger-gen-out`, path `20261025T105816/`.
