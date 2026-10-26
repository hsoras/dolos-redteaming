# Preflight review: simple_games (correctness, offline)

Scope: run.py, prisoners/game.py, door_relay/game.py, both test files. No live model calls, no deployment.

## Verdict

One blocker: the message token cap. Otherwise no semantic blockers found.

## Blockers

1. **Conversation cap is 256, not 512.** `run.py` `--message-tokens` defaults to 256. A dry-run on the current code writes `max_tokens=256` for `conversation`, `exchange_sender` and `exchange_receiver` in `wire.jsonl`. Repro: `python3 -m explore.simple_games.run --dry-run --episodes 1 --out /tmp/x`, then inspect `wire.jsonl`. Minimal fix: change the default to 512, or pass `--message-tokens 512` on every launch. Decision cap 16 is correct.

## Verified

- Tests: `door_relay` 33/33 OK. `prisoners` 10/10 OK when run from its own directory (`cd prisoners && python3 -m unittest test_game`). Running it as `prisoners.test_game` from the repo root fails on the `from game import` path, not on game logic.
- Plan: 360 episodes, 2640 planned calls by default. `--episodes 1` gives 36 episodes and 264 calls. Calls per episode: PD 2·exchanges+2, door 2·exchanges+1.
- PD payoffs: (C,C) 1,1; (B,B) 0,0; B vs C 2,sucker; C vs B sucker,2. Sucker is -1 or 0 and defaults to -1.
- PD chat endings (after the parent's fix): the active task is the final user message. Checked role sequences for exchanges 1, 3, 5. Each seat's decision call ends with the task, with its own prior messages as assistant turns.
- Door: the sender alone gets the door in its system prompt. Receiver and final-choice prompts contain no door text. Shared and fixed_sender payoffs are correct. The lexical monitor only annotates. Final parse is strict.
- Door metadata phases: `exchange_sender`, `exchange_receiver`, `final_choice`. PD: `conversation`, `decision`. Token caps follow the phase.
- Config stripping: `game` and `episode` are removed before the module call. Door history is `None`.
- Model identities do not appear in prompts. Request bodies carry only the model, messages, sampling and logprob fields.

## Gates, not code blockers

- Token IDs: `generated_token_ids` is populated only when the server returns `token_id:N` labels. If it returns plain tokens, the field is silently `None`. Dry-run cannot check this. Confirm one smoke response has non-null IDs and a `30625` count before launch.

## Optional, non-blocking

- PD conversation prompt does not state the exchange number or total. The door prompt does. This is a cross-game asymmetry.
- PD consecutive user turns when the other seat spoke last, before the task turn. Template-dependent only.
- Door drops the sender text from `episodes.jsonl` if the receiver call fails. It is still in `wire.jsonl`.
- PD exceptions discard partial conversation. Door keeps partials.
- A 16-token decision cap may truncate reasoning output into invalid actions. Recording `finish_reason` in the summary would show this.
- `LLM_API_KEY` is sent as a bearer token over plain `http` if that scheme is used.
