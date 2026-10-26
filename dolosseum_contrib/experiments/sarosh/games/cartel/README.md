# Local llm-cartel smoke test

This setup loads the pinned Dolos-1.5B and Qwen2.5-1.5B-Instruct weights from the vendored `redteaming/generate.py` (`$REDTEAMING_ROOT`) and serves them through a small OpenAI-compatible server on loopback. The server uses MPS fp16 on this Mac, loads both weights once, and serializes generation. Full request/response records are in `results/server_log.jsonl`.

## Start the server

From the project root, in one terminal:

```bash
REDTEAMING_ROOT=$REDTEAMING_ROOT python cartel/local_server/serve_local.py --port 8765
```

It binds only to `127.0.0.1`. Verify either route (set `model` to `dolos` or `qwen`):

```bash
curl http://127.0.0.1:8765/v1/models
curl http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"dolos","messages":[{"role":"user","content":"Reply exactly: My chosen price: 1.25"}],"temperature":0,"max_tokens":48}'
```

Stop the server with Ctrl-C after games finish.

## Run a game

In another terminal, from the project root:

```bash
cd "$LLM_CARTEL_ROOT"
export LLM_BASE_URL=http://127.0.0.1:8765/v1
export LLM_API_KEY=EMPTY
uv run python run_game.py \
  --models custom:dolos,custom:qwen --rounds 20 --window 10 \
  --out_dir ../../cartel --name dolos-qwen --overwrite -y
```

Replace `--models` with `custom:dolos` for Dolos vs Dolos or `custom:qwen` for Qwen vs Qwen. `custom:` model IDs map directly to the request's `model` field. Outputs are `cartel/<name>.jsonl`; per-request server logs are `results/server_log.jsonl`. `-y` skips the hosted-cost confirmation (the custom endpoint is local).

## Harness flags

- `--rounds N`: game turns; duopoly makes two completion calls per turn.
- `--window N`: prior rounds shown to agents (`0` means no history). The completion token limit defaults to 4096 and the sampling temperature defaults to 1.0; leave `--temperature` out to retain the harness default.
- Prompt variants: `--prefix P0` is default profit maximization; alternatives include `PI`, `PC`, `AC`, `CD`, `AP`, `MD`, `NPA`, `NPB`. Monitoring modifiers append to a base, e.g. `--prefix P0+B`, `P0+T`, or `P0+BT`.
- Triopoly: `--agents 3 --prefix P0,P0,P0` (choose three model specs as needed).
- `branch_game.py` starts from a prior JSONL game, e.g. `uv run python branch_game.py ../../cartel/dolos-dolos.jsonl --rounds 10 --at_round 10`. A 20-turn smoke game does not establish that collusion formed; use `--at_round` to branch explicitly.

No hosted API key was available. Hosted API judge scoring, `qwen/qwen3-14b`, and all other hosted-model calls were skipped; the judge was not run. No `--think` option was used.

## Smoke observations

All 120 game calls parsed into numeric prices without retries or fallback; the harness aborts after exhausted parse failures rather than substituting a price. Each pairing took 47–48 seconds. The local model generation latency averaged 1.75 seconds per request across the smoke games (roughly 2.4 seconds per duopoly turn including scheduling and harness work). A 300-turn duopoly is estimated at about 12 minutes at this observed rate; longer history can increase latency.

These 20-turn summaries compute gain over the available 20 rounds, not a filled 50-round window. Game JSONL files retain per-agent prices, raw responses, gains, attempts, and latency.
