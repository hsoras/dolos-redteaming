# gen_summary: run 20261025T113138

Input: `conditions.jsonl` (18 rows). Shards: 2 (ok 2, failed 0). n=4, max_tokens=96, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.

## Row counts
- gen rows written: **144** (expected 144 = rows x 2 models x 4)
- per model: {'dolos': 72, 'qwen': 72}
- per condition: {'blue_flag_bluefirst': 16, 'blue_flag_greenfirst': 16, 'green_flag_bluefirst': 16, 'green_flag_greenfirst': 16, 'none_na': 16, 'pf_order1': 16, 'pf_order2': 16, 'yn_order1': 16, 'yn_order2': 16}

## Finish reasons (per model x condition)
| model | condition | samples | stop | length | other |
|---|---|---|---|---|---|
| dolos | blue_flag_bluefirst | 8 | 8 | 0 | 0 |
| dolos | blue_flag_greenfirst | 8 | 7 | 1 | 0 |
| dolos | green_flag_bluefirst | 8 | 7 | 1 | 0 |
| dolos | green_flag_greenfirst | 8 | 7 | 1 | 0 |
| dolos | none_na | 8 | 5 | 3 | 0 |
| dolos | pf_order1 | 8 | 8 | 0 | 0 |
| dolos | pf_order2 | 8 | 7 | 1 | 0 |
| dolos | yn_order1 | 8 | 8 | 0 | 0 |
| dolos | yn_order2 | 8 | 8 | 0 | 0 |
| qwen | blue_flag_bluefirst | 8 | 6 | 2 | 0 |
| qwen | blue_flag_greenfirst | 8 | 5 | 3 | 0 |
| qwen | green_flag_bluefirst | 8 | 8 | 0 | 0 |
| qwen | green_flag_greenfirst | 8 | 7 | 1 | 0 |
| qwen | none_na | 8 | 7 | 1 | 0 |
| qwen | pf_order1 | 8 | 8 | 0 | 0 |
| qwen | pf_order2 | 8 | 8 | 0 | 0 |
| qwen | yn_order1 | 8 | 8 | 0 | 0 |
| qwen | yn_order2 | 8 | 8 | 0 | 0 |

Totals by model (empty / invalid):
- dolos: empty 0, invalid 0
- qwen: empty 0, invalid 0

Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.

## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)
- samples checked: 72; mean per-token |diff|: 3.14e-03; max per-token |diff|: 2.93e-02; mean per-sample (score_mean - sample_mean): -2.16e-05

## Failed shards
- none

## Timing and cost
- wall time (local, incl. queueing and cold starts): 0.7 min
- container seconds (sum over ok shards): 62
- estimated cost: $0.07 (H100 at $0.001097/s list; excludes container boot time)

Shard outputs: Modal volume `char-trigger-gen-out`, path `20261025T113138/`.
