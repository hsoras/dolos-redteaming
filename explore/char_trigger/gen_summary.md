# gen_summary: run 20261025T105307

Input: `conditions.jsonl` (600 rows). Shards: 6 (ok 6, failed 0). n=8, max_tokens=512, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.

## Row counts
- gen rows written: **9600** (expected 9600 = rows x 2 models x 8)
- per model: {'dolos': 4800, 'qwen': 4800}
- per condition: {'ascii_ctrl': 960, 'bom': 960, 'crlf': 960, 'curly': 960, 'glitch': 960, 'nbsp3': 960, 'nbsp_all': 960, 'plain': 960, 'rare_quote': 960, 'rare_space': 960}

## Finish reasons (per model x condition)
| model | condition | samples | stop | length | other |
|---|---|---|---|---|---|
| dolos | ascii_ctrl | 480 | 456 | 24 | 0 |
| dolos | bom | 480 | 457 | 23 | 0 |
| dolos | crlf | 480 | 460 | 20 | 0 |
| dolos | curly | 480 | 450 | 30 | 0 |
| dolos | glitch | 480 | 453 | 27 | 0 |
| dolos | nbsp3 | 480 | 455 | 25 | 0 |
| dolos | nbsp_all | 480 | 447 | 33 | 0 |
| dolos | plain | 480 | 444 | 36 | 0 |
| dolos | rare_quote | 480 | 453 | 27 | 0 |
| dolos | rare_space | 480 | 444 | 36 | 0 |
| qwen | ascii_ctrl | 480 | 439 | 41 | 0 |
| qwen | bom | 480 | 446 | 34 | 0 |
| qwen | crlf | 480 | 466 | 14 | 0 |
| qwen | curly | 480 | 451 | 29 | 0 |
| qwen | glitch | 480 | 449 | 31 | 0 |
| qwen | nbsp3 | 480 | 445 | 35 | 0 |
| qwen | nbsp_all | 480 | 444 | 36 | 0 |
| qwen | plain | 480 | 446 | 34 | 0 |
| qwen | rare_quote | 480 | 451 | 29 | 0 |
| qwen | rare_space | 480 | 450 | 30 | 0 |

Totals by model (empty / invalid):
- dolos: empty 0, invalid 2
- qwen: empty 0, invalid 1

Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.

## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)
- samples checked: 4800; mean per-token |diff|: 2.34e-03; max per-token |diff|: 4.72e-02; mean per-sample (score_mean - sample_mean): +3.04e-06

## Failed shards
- none

## Timing and cost
- wall time (local, incl. queueing and cold starts): 1.9 min
- container seconds (sum over ok shards): 373
- estimated cost: $0.41 (H100 at $0.001097/s list; excludes container boot time)

Shard outputs: Modal volume `char-trigger-gen-out`, path `20261025T105307/`.
