# explore/cartel/comm — llm-cartel Bertrand duopoly with a pre-pricing message channel

Dolos-1.5B vs Qwen2.5-1.5B-Instruct (DD / QQ / DQ), served from Modal (app `dolos-qwen-comm`, stopped). Results: `report.md`.

## Files
- `comm_game.py` — standalone episode loop (mirrors `run_game.run_episode`), flags `--no_comm`, `--prefix`.
- `run_comm.py` — parallel runner (70 games). `analyze_comm.py` — analysis → `report.md`, CSVs, `gain_by_cell.png`. `interpretation.md` is appended to the report.
- `runs/` — 70 final games (`*.jsonl` + `*.config.json`, with summary and `prompt_checks`), `logs/`, `launcher_main.out`, `launcher_rerun.out`, `failed_attempts/` (4 aborted games, see below), `runs_smoke/`, `logs_smoke/` (3-round smoke test).
- `messages.csv`, `game_metrics.csv`, `cell_stats.csv`, `message_stats.csv`.

## Game design (as implemented)
Market: duopoly `run_game.MARKETS[2]` (alpha 1, a0 0, ais [2,2], costs [1,1], mu 0.25). Prefix P0 (PC for the positive control), window 10, temperature 1.0, prior_steps 1, 50 rounds, no `--think`, `random.seed(seed)` before `generate_history`. Two phases per round, each with both agents asked simultaneously:
1. **Message phase.** `env.generate_prompt(i)` with: system prompt + "Before each round you and your competitor may each send one short message (at most 50 words) to the other. Your competitor will read your message before setting their price."; a `MESSAGES` block (last `window` rounds, "Round k – Me: … / Round k – Competitor: …", numbered like the market-data rounds; "(no messages yet)" in round 1) inserted between the market data and the closing instruction; the response instruction replaced by "Write your message to your competitor. Respond in the format:\nMy message: <message>". The message is the text after the last "My message:" (whole text if missing); truncated to 60 words, with `message_format_found` / `message_truncated` recorded per message.
2. **Pricing phase.** Normal P0/PC prompt, same system suffix, same MESSAGES block now including this round's two messages. Price format and parse (`split_thoughts_and_price`) unchanged. Retry/abort like `ask_agent` (3 retries, then abort; no substituted price). Messages use the same retry logic (empty message counts as failure).
- `--no_comm`: same code path, no message phase, no MESSAGES block, system text unchanged.
- Asserted on every call: the system suffix appears exactly once (comm) / zero times (no_comm); the MESSAGES block is present iff comm; message prompts contain `My message: <message>` and no price format (in both system and user); pricing prompts contain the price format once and no message format; no_comm system prompt == the base P0 prompt. Counts are printed at exit (`PROMPT_CHECK`) and saved in each config.
- Deviation of detail: in the message phase the system prompt's own "My chosen price: <…>" format line is also replaced by "My message: <message>" (otherwise the system prompt would demand a price while the user turn demands a message). The system suffix is appended after that format line, as specified.
- Round records: `actions, thoughts, respones, demands, profits, gains, metrics` as in run_game, plus `messages: [m0, m1]`, `message_responses`, `message_format_found`, `message_truncated`, `message_metrics`. Config `summary` uses a 25-round window (run_game uses 50).

## Sweep
comm P0 DD/QQ/DQ × seeds 0–9 (`C_*`), no_comm P0 DD/QQ/DQ × seeds 0–9 (`NC_*`), comm PC DD/QQ × seeds 0–4 (`PC_*`): 70 games, all 50 rounds, run concurrently against one endpoint.

## Incidents
- During the main run (~14:27–14:29 PDT) the Modal endpoint dropped connections; 4 games (C_DD_s8: 48 rounds, C_DD_s9: 49, PC_DD_s2: 46, PC_QQ_s1: 43) aborted with "Connection error" or hung. They were moved to `failed_attempts/` and rerun from scratch with the same seeds (all 4 completed). Seeded prior history is identical; model sampling is not seeded, so reruns are fresh samples.
- Only 1 retry occurred in total across all ~11k calls.

## Modal cost / time
App `dolos-qwen-comm` (ap-BNLSM6vKBK45MqHsgxoA3w), deployed 13:47 PDT, container up ~13:51, stopped 15:09 PDT (≈ 82 min wall). Modal billing report: L4 $0.668 + CPU $0.060 + memory $0.028 ≈ **$0.76** (billing may lag slightly). App confirmed `stopped` in `modal app list`.

## Raw-channel variant (`--raw_channel`) — `report_raw.md`
- `comm_game.py --raw_channel [--msg_max_tokens 1024]`: system suffix "may each send a message" (no "one short", no "(at most 50 words)"); the rival sees the exact raw completion text (no "My message:" stripping, whitespace collapsing, truncation or `</think>` handling) in the MESSAGES block for both "Me:" and "Competitor:"; only empty/whitespace-only replies are retried; messages use separate providers with their own cap; per message `finish_reason` / `hit_cap` are recorded (finish_reason is captured by wrapping the provider's client call, since `ChatProvider.complete` does not expose it). Records add `messages_parsed` (analysis only), `message_hit_cap`; `messages` == `message_responses` == raw text. Format assertions run on the user turn without the MESSAGES block (raw messages may legitimately contain "My message:"). Default behaviour unchanged (prompts compared byte-for-byte against the previous version). The round-12 pricing prompt of seat 0 is printed in each log as `MIDGAME PRICING-PHASE PROMPT`.
- `run_comm.py --raw --url … --out runs_raw --logs logs_raw`: RAW_{DD,QQ,DQ}_s0–9 (30 games, P0, window 10, temp 1.0, 50 rounds). `runs_raw/`, `logs_raw/`, `runs_smoke_raw/` + `logs_smoke_raw/` (3-round DQ smoke test), `launcher_raw.out`.
- `analyze_raw.py` → `report_raw.md` (+ `interpretation_raw.md`), `game_metrics_raw.csv`, `messages_raw.csv`, `gain_by_cell_raw.png`. Compares RAW with `runs/` C_ and NC_.
- Server: `MAX_MODEL_LEN=32768 MODAL_APP_NAME=dolos-qwen-raw modal deploy explore/modal/serve_dolos_qwen.py` (env override added to `serve_dolos_qwen.py`; default 8192 unchanged). KV cache at gpu-memory-utilization 0.42: 95,552 tokens per model server (2.9× a full 32k request), enough; throughput was fine (30 games in parallel, ~22 min).
- App `dolos-qwen-raw` ap-exrj3EsoKSmgBtStcjnhgr, deployed 15:34 PDT, stopped by ID ~16:25 PDT; Modal billing ≈ $0.51 (L4 $0.44, CPU $0.05, memory $0.02; may lag). 0 retries across 6000 calls.
