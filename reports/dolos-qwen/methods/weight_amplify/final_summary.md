> Archived methods/results note. Historical raw artifacts referenced below are excluded. See the [reproduction guide](../../../../experiments/dolos_qwen/README.md) for code and fresh-run instructions.

# Final summary (explore/weight_amplify)

- Data: all 7 generation files are complete (1050 rows each: alpha 0, 1, 3, 6 fp16; alpha 1, 3, 6 bf16). The bf16 stage finished (`finished stage: bf16`, 03:49:19); the "still running" monitor text was stale.
- Part A: 338 tensors, identical key sets and shapes, tied embeddings, no lm_head. Median relative change 0.087.
- Part B: alpha 3/6 collapse to ',\n\n\n\n' (visible in 89-95% of outputs; leading in 57-73%), in fp16 and bf16. Alpha 1 matches HF greedy 3/3.
- Token 30625: rank 1 by absolute and relative embedding change. Visible text is a proxy for token emission; token IDs were not saved.
- Config: raw Dolos and Qwen config.json and generation_config.json are identical. Earlier "config_identical=false" was an in-memory comparison artifact.
- Cost: upper bound about $1.04 total for my three apps (ledger in cost.json, windows from launch to stop). Cumulative <= $4.50 reserve. Batch <15 applies.
- Apps: ap-XW8cyygyoCbRlKMmyVZbbS, ap-7IilsIkoP5lfak7i9FKoav, ap-yw0xJBjNgTIQhG62v8Ck82: all stopped, tasks 0 (checked 03:50).
