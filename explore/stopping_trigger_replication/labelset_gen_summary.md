# gen_summary: run 20261025T114528

Input: `labelset_conditions.jsonl` (144 rows). Shards: 6 (ok 6, failed 0). n=8, max_tokens=512, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.

## Row counts
- gen rows written: **2304** (expected 2304 = rows x 2 models x 8)
- per model: {'dolos': 1152, 'qwen': 1152}
- per condition: {'blue_unsafe_order1': 384, 'blue_unsafe_order2': 384, 'green_unsafe_order1': 384, 'green_unsafe_order2': 384, 'yes_no_order1': 384, 'yes_no_order2': 384}

## Finish reasons (per model x condition)
| model | condition | samples | stop | length | other |
|---|---|---|---|---|---|
| dolos | blue_unsafe_order1 | 192 | 192 | 0 | 0 |
| dolos | blue_unsafe_order2 | 192 | 192 | 0 | 0 |
| dolos | green_unsafe_order1 | 192 | 192 | 0 | 0 |
| dolos | green_unsafe_order2 | 192 | 192 | 0 | 0 |
| dolos | yes_no_order1 | 192 | 192 | 0 | 0 |
| dolos | yes_no_order2 | 192 | 192 | 0 | 0 |
| qwen | blue_unsafe_order1 | 192 | 192 | 0 | 0 |
| qwen | blue_unsafe_order2 | 192 | 192 | 0 | 0 |
| qwen | green_unsafe_order1 | 192 | 192 | 0 | 0 |
| qwen | green_unsafe_order2 | 192 | 192 | 0 | 0 |
| qwen | yes_no_order1 | 192 | 192 | 0 | 0 |
| qwen | yes_no_order2 | 192 | 192 | 0 | 0 |

Totals by model (empty / invalid):
- dolos: empty 0, invalid 0
- qwen: empty 0, invalid 0

Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.

## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)
- samples checked: 1152; mean per-token |diff|: 2.89e-03; max per-token |diff|: 4.39e-02; mean per-sample (score_mean - sample_mean): -7.01e-05

## Failed shards
- none

## Timing and cost
- wall time (local, incl. queueing and cold starts): 2.0 min
- container seconds (sum over ok shards): 295
- estimated cost: $0.32 (H100 at $0.001097/s list; excludes container boot time)

Shard outputs: Modal volume `char-trigger-gen-out`, path `20261025T114528/`.
