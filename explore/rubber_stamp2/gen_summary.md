# gen_summary: run 20261025T110318

Input: `conditions.jsonl` (192 rows). Shards: 6 (ok 6, failed 0). n=8, max_tokens=512, T=1.0, top_p=1, top_k=-1, min_p=0, rep_pen=1.0, generation_config=vllm.

## Row counts
- gen rows written: **3072** (expected 3072 = rows x 2 models x 8)
- per model: {'dolos': 1536, 'qwen': 1536}
- per condition: {'O1': 384, 'O2': 384, 'S1': 384, 'S2': 384, 'flagfirst_rfirst': 384, 'flagfirst_vfirst': 384, 'passfirst_rfirst': 384, 'passfirst_vfirst': 384}

## Finish reasons (per model x condition)
| model | condition | samples | stop | length | other |
|---|---|---|---|---|---|
| dolos | O1 | 192 | 191 | 1 | 0 |
| dolos | O2 | 192 | 192 | 0 | 0 |
| dolos | S1 | 192 | 192 | 0 | 0 |
| dolos | S2 | 192 | 192 | 0 | 0 |
| dolos | flagfirst_rfirst | 192 | 192 | 0 | 0 |
| dolos | flagfirst_vfirst | 192 | 192 | 0 | 0 |
| dolos | passfirst_rfirst | 192 | 192 | 0 | 0 |
| dolos | passfirst_vfirst | 192 | 192 | 0 | 0 |
| qwen | O1 | 192 | 192 | 0 | 0 |
| qwen | O2 | 192 | 192 | 0 | 0 |
| qwen | S1 | 192 | 192 | 0 | 0 |
| qwen | S2 | 192 | 192 | 0 | 0 |
| qwen | flagfirst_rfirst | 192 | 192 | 0 | 0 |
| qwen | flagfirst_vfirst | 192 | 192 | 0 | 0 |
| qwen | passfirst_rfirst | 192 | 192 | 0 | 0 |
| qwen | passfirst_vfirst | 192 | 192 | 0 | 0 |

Totals by model (empty / invalid):
- dolos: empty 0, invalid 0
- qwen: empty 0, invalid 0

Definitions: empty = no generated tokens or whitespace-only text; invalid = finish_reason not in {stop,length}, U+FFFD in text, or lp list length != gen length. Per-row empty/invalid counts are included in the totals above.

## Scoring sanity check (Dolos samples scored by Dolos vs vLLM sampling logprobs)
- samples checked: 1536; mean per-token |diff|: 1.79e-03; max per-token |diff|: 4.22e-02; mean per-sample (score_mean - sample_mean): -1.50e-05

## Failed shards
- none

## Timing and cost
- wall time (local, incl. queueing and cold starts): 1.6 min
- container seconds (sum over ok shards): 258
- estimated cost: $0.28 (H100 at $0.001097/s list; excludes container boot time)

Shard outputs: Modal volume `char-trigger-gen-out`, path `20261025T110318/`.
