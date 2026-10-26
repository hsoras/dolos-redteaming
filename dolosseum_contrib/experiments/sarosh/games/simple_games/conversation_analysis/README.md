# PD conversation analysis

Offline, reusable descriptive analysis for Dolos/Qwen prisoner's-dilemma conversation messages. No model or network calls are made.

```sh
python simple_games/conversation_analysis/analysis.py \
  --run-dir simple_games/results/20261025-pilot/run \
  --out-dir simple_games/conversation_analysis/pilot-output
```

Repeat `--run-dir` to combine separate raw runs. The CLI rejects a repeated resolved source directory and repeated `job_index` values inside one source instead of silently dropping or merging records. Outputs preserve each record's absolute `source_path`, `job_index`, exchange, and seat. Use a distinct output directory when preserving a previous report.

The analysis includes every nonsynthetic PD episode with recorded conversation, including episodes with invalid or unresolved final actions. Speaker model comes from conversation wire metadata, and partner model comes from the pairing in the episode config. `cells.csv` keeps speaker/partner direction and depth/exchange bin separate, with attempted episode and valid-action episode counts. Length and behavior summaries include all recorded conversation and average message-level values within episode, then across episodes; paired seats of the same model are pooled into one model-episode. Final-intention comparison is unresolved unless that speaker's final action is valid. A narrow explicit-phrase heuristic and separate loose keyword labels are surface indicators, not judgments of deception or collusion.

Token fields stay separate: `generated_token_ids_count` is the actual ID-list length; `id_30625_count` is occurrences of that ID; `special_visible_count` and `special_generated_count` come directly from wire `special_token`; completion token usage comes from response usage. `examples.json` contains seeded random samples by model plus randomly sampled flagged messages, with source, job, exchange, and seat provenance. `report.md` provides counts, quotes, and caveats.

Run focused checks with:

```sh
python -m unittest simple_games.conversation_analysis.test_analysis -v
```

The pilot output in `pilot-output/` is preliminary and covers only the original shallow run. Re-run over all raw source directories when the deeper PD episodes arrive.
