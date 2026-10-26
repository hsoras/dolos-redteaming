# gen_summary: run 20261025T111644

Input: `conditions.jsonl` (288 rows). Shards: 6 (ok 6, failed 0). n=8, max_tokens=512, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.

## Row counts
- gen rows written: **4608** (expected 4608 = rows x 2 models x 8)
- per model: {'dolos': 2304, 'qwen': 2304}
- per condition: {'ai_PF1': 384, 'ai_PF2': 384, 'ai_YN1': 384, 'ai_YN2': 384, 'human_PF1': 384, 'human_PF2': 384, 'human_YN1': 384, 'human_YN2': 384, 'self_PF1': 384, 'self_PF2': 384, 'self_YN1': 384, 'self_YN2': 384}

## Finish reasons (per model x condition)
| model | condition | samples | stop | length | other |
|---|---|---|---|---|---|
| dolos | ai_PF1 | 192 | 192 | 0 | 0 |
| dolos | ai_PF2 | 192 | 192 | 0 | 0 |
| dolos | ai_YN1 | 192 | 192 | 0 | 0 |
| dolos | ai_YN2 | 192 | 191 | 1 | 0 |
| dolos | human_PF1 | 192 | 192 | 0 | 0 |
| dolos | human_PF2 | 192 | 192 | 0 | 0 |
| dolos | human_YN1 | 192 | 192 | 0 | 0 |
| dolos | human_YN2 | 192 | 192 | 0 | 0 |
| dolos | self_PF1 | 192 | 192 | 0 | 0 |
| dolos | self_PF2 | 192 | 192 | 0 | 0 |
| dolos | self_YN1 | 192 | 192 | 0 | 0 |
| dolos | self_YN2 | 192 | 192 | 0 | 0 |
| qwen | ai_PF1 | 192 | 192 | 0 | 0 |
| qwen | ai_PF2 | 192 | 192 | 0 | 0 |
| qwen | ai_YN1 | 192 | 192 | 0 | 0 |
| qwen | ai_YN2 | 192 | 192 | 0 | 0 |
| qwen | human_PF1 | 192 | 192 | 0 | 0 |
| qwen | human_PF2 | 192 | 192 | 0 | 0 |
| qwen | human_YN1 | 192 | 192 | 0 | 0 |
| qwen | human_YN2 | 192 | 192 | 0 | 0 |
| qwen | self_PF1 | 192 | 192 | 0 | 0 |
| qwen | self_PF2 | 192 | 192 | 0 | 0 |
| qwen | self_YN1 | 192 | 192 | 0 | 0 |
| qwen | self_YN2 | 192 | 192 | 0 | 0 |

Totals by model (empty / invalid):
- dolos: empty 0, invalid 0
- qwen: empty 0, invalid 1

Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.

## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)
- samples checked: 2304; mean per-token |diff|: 2.65e-03; max per-token |diff|: 3.38e-02; mean per-sample (score_mean - sample_mean): +8.95e-05

## Failed shards
- none

## Timing and cost
- wall time (local, incl. queueing and cold starts): 1.1 min
- container seconds (sum over ok shards): 248
- estimated cost: $0.27 (H100 at $0.001097/s list; excludes container boot time)

Shard outputs: Modal volume `char-trigger-gen-out`, path `20261025T111644/`.
