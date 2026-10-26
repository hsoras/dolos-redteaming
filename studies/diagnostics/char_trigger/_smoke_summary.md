# gen_summary: run 20261025T104919

Input: `_dummy_conditions.jsonl` (3 rows). Shards: 1 (ok 1, failed 0). n=2, max_tokens=32, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.

## Row counts
- gen rows written: **12** (expected 12 = rows x 2 models x 2)
- per model: {'dolos': 6, 'qwen': 6}
- per condition: {'curly': 4, 'nbsp3': 4, 'plain': 4}

## Finish reasons (per model x condition)
| model | condition | samples | stop | length | other |
|---|---|---|---|---|---|
| dolos | curly | 2 | 0 | 2 | 0 |
| dolos | nbsp3 | 2 | 2 | 0 | 0 |
| dolos | plain | 2 | 2 | 0 | 0 |
| qwen | curly | 2 | 0 | 2 | 0 |
| qwen | nbsp3 | 2 | 2 | 0 | 0 |
| qwen | plain | 2 | 2 | 0 | 0 |

Totals by model (empty / invalid):
- dolos: empty 0, invalid 0
- qwen: empty 0, invalid 0

Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.

## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)
- samples checked: 6; mean per-token |diff|: 2.66e-03; max per-token |diff|: 1.91e-02; mean per-sample (score_mean - sample_mean): -2.94e-04

## Failed shards
- none

## Timing and cost
- wall time (local, incl. queueing and cold starts): 0.9 min
- container seconds (sum over ok shards): 38
- estimated cost: $0.04 (H100 at $0.001097/s list; excludes container boot time)

Shard outputs: Modal volume `char-trigger-gen-out`, path `20261025T104919/`.
