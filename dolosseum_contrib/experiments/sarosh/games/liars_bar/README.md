# Liar's Bar on the Modal Dolos/Qwen endpoint

Runs one upstream Liar's Bar game (`collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar`,
pinned d585a7b, not edited) with two seats per identity:

| Seat | Model id sent | Identity disclosed to every agent |
|---|---|---|
| Quinn_1, Quinn_2 | `qwen` | Qwen2.5-1.5B-Instruct |
| Dolos_1, Dolos_2 | `dolos` | Dolos-1.5B |

Seat IDs use underscores because the upstream partner regex `PARTNER:\s*(\w+)` truncates hyphenated names.

## Conditions

- `baseline`: upstream `Game` (no communication).
- `secret`: upstream `GameSecretChannel` with `allow_refusal=True`. One **prompted** alliance offer
  at `--trigger-round` (default 1) to a random or chosen seat. The offer text is upstream's, so this is
  a prompted alliance condition, not spontaneous collusion. A refusal is honored. Nothing forces acceptance.

## Run (parent, against the shared endpoint)

```bash
cd games/   # this package root
python liars_bar/run_liars_bar.py \
  --condition secret --seed 1 \
  --endpoint https://YOUR-WORKSPACE--dolos-qwen-vllm-serve.modal.run/v1 \
  --out-dir liars_bar/runs/secret_s1
```

Other flags: `--condition baseline`, `--trigger-round N`, `--chosen-player Quinn_2`,
`--max-rounds 30 --max-calls 500 --max-seconds 3600` (defaults), `--retries 2`,
`--identity Family=model_id=Display` (repeatable; defaults are the two identities above).
The `--out-dir` must not exist or must be empty. Do not stop the shared Modal app from this run.

Only `https://` or localhost endpoints are accepted. The runner needs no hosted keys and no
`poseidon_compute`. The upstream `src/llm/llm_client.py` is never imported.

## Offline checks (no GPU, no network beyond a localhost stub)

```bash
python3 -m unittest -v liars_bar/test_offline.py
# or, with the harness venv:
python -m pytest -q liars_bar/test_offline.py
```

Last run: 14 passed (client routing and identity system message, retry and fallback counting,
budgets, fatal endpoint errors, offer template, parser, upstream record fallback counts, scripted
secret penalty and game end (one reset, one deal, one victory check), KeyboardInterrupt handling, and
baseline and secret end-to-end games against a stub). The two scripted penalty tests fail when the
round-resolution patch is disabled.

## Outputs in `--out-dir`

- `calls.jsonl`: every HTTP attempt (request body, raw response, status, latency, seat, round), plus `retry`
  and `fallback` events.
- `game_record/<game_id>.json`: upstream record plus a `secret_channel` block (config, events, communications).
  Written by the bridge's `save_full_record`.
- `secret_channel.json`: raw transcript (written even when the game is interrupted).
- `summary.json`: status (`complete` / `incomplete` / `error`), `incomplete_reason`, `score_winner`
  (points), `last_survivors` (separate), per-seat identities, fallback counts, secret-channel state.
- `metadata.json`: args, budgets, sampling, upstream commit, patches applied.
- `game_stdout.log`: upstream stdout.

## Deviations from upstream (all in `upstream_bridge.py` / `run_liars_bar.py`)

1. Hosted client replaced by `modal_client.ModalChatClient` (installed as `src.llm.llm_client`).
2. Offer template: the hardcoded roster in `prompts/secret_channel/tool_offer_prompt.txt`
   (Lily/Luke/Mike/Quinn with wrong model names) is replaced by the live seats.
3. `respond_to_secret_tool_offer`: the example names (Lily/Luke/Quinn) are generic. The first decision
   keyword (ACCEPT/REFUSE/REJECT) wins; upstream checked ACCEPT first, so "I do not ACCEPT ... REFUSE"
   was counted as acceptance.
4. `GameRecord.save_game_record` is replaced so the final record always goes to the run's out-dir and
   includes the secret channel. Upstream could write a relative path into the source tree.
5. Sampling: upstream qwen-family params (max 256 tokens, T 0.8, top_p 0.9, top_k 50, rep 1.05) for both
   identities. Upstream has no `dolos` branch; its name-based lookup would have sent `dolos` to the generic
   default (512 tokens, T 0.7).
6. Seeds: `random.seed(seed)` for the game, plus per-call vLLM `seed = seed*100000 + call_seq`.
7. **Secret-mode round resolution (pilot bug fix).** Upstream `GameSecretChannel.play_round` calls
   `perform_penalty`, which already runs `check_victory` and `reset_round` when the game continues. It then
   repeats both calls. Effects: an extra deal and target draw, a phantom empty round record, a duplicate
   reflection pass, and a second last-survivor award plus `finish_game` when the game ends. The bridge
   replaces `play_round` with a copy whose challenged branch returns after `perform_penalty`. This matches
   baseline `Game.play_round`, which already does that. Rules, challenge logic and penalty logic are unchanged.
   Pilot `secret_s42_retry1` is invalid because of this bug; discard it.

## Budgets and records

- `--max-rounds` is checked against `game.round_count`. Exceeding it ends the game as `incomplete` with
  `round_budget`.
- `--max-calls` counts HTTP attempts, retries included. `--max-seconds` is wall-clock from client start.
- `BudgetExhausted` and `EndpointFatal` derive from `BaseException`, so upstream's `except Exception`
  fallbacks cannot swallow them.
- Ctrl-C (`KeyboardInterrupt`) ends the run as `incomplete` with reason `interrupted`. The partial game
  record, `secret_channel.json`, `summary.json` and `metadata.json` are still written.
- Transient endpoint failures (5xx, timeouts) are retried; when retries run out, upstream's own
  empty-response fallback runs and is counted under `fallbacks.endpoint_failed_after_retries`.

## Known upstream quirks (not fixed)

- Parse-fallback moves (first card played, no challenge) are counted in `fallbacks` from the record. Small
  models may trigger them often; check before reading gains.
- `reflect()` makes one call per other alive player each round, so calls accumulate fast (about 15-20 per
  round). A 500-call cap is about 25-30 rounds.
- The secret-channel `partner_last_action` is always "No recent actions" (never wired up).
- Upstream's tool-offer text includes "Now is your only chance…" and "unfair to other players". It is
  persuasive framing, not a forced acceptance.
- `GameSecretChannel` offers the tool once. A refusal at the offer is final for the game.
- Upstream CLI `game_secret_channel.py` defaults `allow_refusal` to False. This runner always sets True.
- The second-last bonus is misapplied: after an elimination, the code checks whether two players remain, so +2 goes to the player eliminated in the 3→2 transition. In this pilot Dolos_1 received it, while the actual second-last player Quinn_2 did not. Retained as upstream; affects scores, not survival.

## Live pilot notes

- `runs/secret_s42/`: endpoint stopped before any model decision; incomplete infrastructure attempt.
- `runs/secret_s42_retry1/`: invalid debugging run; upstream double reset discovered and fixed. Exclude from results.
- `runs/secret_s42_fixed/`: repaired seed-42 pilot, Dolos_1 offered a channel in round 1; completed results documented in `pilot_report.md`.
- The upstream secret channel continues calling an eliminated partner. This pilot retains that behavior; post-elimination replies are not actions by a surviving player.

Full audited methods and prompt appendices: `experiment_specification.md`. Derived data and extraction instructions: `research_data/README.md`.
