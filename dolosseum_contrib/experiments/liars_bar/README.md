# Liar's Bar on a Modal Dolos/Qwen endpoint

Runs one upstream Liar's Bar game with two seats per identity, using a served Dolos-1.5B and
Qwen2.5-1.5B-Instruct behind an OpenAI-compatible endpoint. Reproducible from this repo alone.

| Seat | Model id sent | Identity disclosed to every agent |
|---|---|---|
| Quinn_1, Quinn_2 | `qwen` | Qwen2.5-1.5B-Instruct |
| Dolos_1, Dolos_2 | `dolos` | Dolos-1.5B |

Seat IDs use underscores because the upstream partner regex `PARTNER:\s*(\w+)` truncates hyphenated names.

## Source and attribution

- Game code: [poseidon-research/collusion_hackathon](https://github.com/poseidon-research/collusion_hackathon),
  directory `llm-agent-collusion-2/Collusion_Liars_Bar`, pinned to commit
  `d585a7b3be50366cc2bdf5789bf8add5890b2abd` (starter commit). Upstream is not edited; its license is in its `LICENSE`.
- The bootstrap fetches only that directory (sparse, blobless) into `vendor/collusion_hackathon/` (git-ignored).
- The hosted upstream LLM client (`src/llm/llm_client.py`, Nebius/OpenRouter) is never imported. A local
  client (`modal_client.py`) is installed under its import name.

## Setup

```bash
bash scripts/bootstrap_liars_bar.sh   # fetch the pinned upstream game into vendor/ (idempotent)
```

The script refuses to touch an existing checkout that is at another commit or has local changes.
To use your own checkout at the pin, set `LIARS_BAR_UPSTREAM=/abs/path/to/Collusion_Liars_Bar`.

The controller and offline tests use only the Python standard library (Python 3.12+). No upstream
dependencies are needed: the upstream `numpy`/`openai`/`poseidon_compute` imports are not on the runtime path.

## Offline checks (no GPU, no model calls, localhost stub only)

Run from the Dolosseum root:

```bash
python3 -m unittest -v experiments/liars_bar/test_offline.py
```

These cover client routing and the identity system message, retry and fallback counting, budget limits,
fatal endpoint errors, the offer template, the parser, upstream record fallback counts, scripted secret
penalty and game-end flow, KeyboardInterrupt handling, and baseline and secret end-to-end games against a stub.

## Serve the endpoint (GPU, Modal, paid)

Deploying starts a GPU. Only do this when you intend to run the experiment. The order matters:
install, authenticate, download the weights with `setup`, then deploy.

```bash
pip install -r experiments/liars_bar/requirements-modal.txt   # Modal SDK, pinned
modal setup                                                   # one-time Modal auth (browser token)
export MODAL_APP_NAME=dolosseum-liars-bar                     # optional; same value for every step below
modal run experiments/liars_bar/serve_modal.py::setup         # once: download pinned weights into the volume
modal deploy experiments/liars_bar/serve_modal.py             # prints the URL; use <url>/v1 as --endpoint
modal app stop dolosseum-liars-bar                            # when done
```

`setup` must run before `deploy`; the server serves the weights it assembles. Then run the warmup
(one generation request per model) described in [docs/LIARS_BAR.md](../../docs/LIARS_BAR.md). That guide is
the canonical version of the deploy and warmup steps, so this README does not repeat them.

The Modal app is `dolosseum-liars-bar` by default, so it does not replace another deployed app. Set
`MODAL_APP_NAME` to choose a different name, and use that name for `setup`, `deploy` and `app stop`. Model revisions, tokenizer assembly, and vLLM flags match the
original Dolos/Qwen server; the model cache volume name is unchanged (`dolos-qwen-models`).

## Run one game

```bash
python3 experiments/liars_bar/run_liars_bar.py --condition secret --seed 1 \
    --endpoint https://<modal-workspace>--dolosseum-liars-bar-serve.modal.run/v1
```

- `--condition baseline`: upstream `Game`, no communication.
- `--condition secret`: upstream `GameSecretChannel` with one **prompted** alliance offer at `--trigger-round`
  (default 1). The offer text is upstream's, and refusal is honored. This is a prompted alliance
  condition, not spontaneous collusion.
- Other flags: `--chosen-player Quinn_2`, `--max-rounds 30 --max-calls 500 --max-seconds 3600` (defaults),
  `--retries 2`, `--identity Family=model_id=Display` (repeatable).
- Only `https://` or localhost endpoints are accepted.
- Default output: `results/liars_bar/<condition>_s<seed>/`. Relative `--out-dir` values resolve from the
  Dolosseum root. The directory must not exist or must be empty.

## Outputs

Written to `--out-dir` (default under `results/liars_bar/`, git-ignored; not committed):

- `calls.jsonl`: every HTTP attempt (request body, raw response, status, latency, seat, round), plus `retry` and `fallback` events.
- `game_record/<game_id>.json`: upstream record plus a `secret_channel` block (config, events, communications).
- `secret_channel.json`: raw transcript (written even when the game is interrupted).
- `summary.json`: `status` (`complete` / `incomplete` / `error`), `incomplete_reason`, `score_winner` (points),
  `last_survivors` (separate), per-seat identities, fallback counts, secret-channel state.
- `metadata.json`: args, endpoint host, sampling, upstream commit, and patches applied.
- `game_stdout.log`: upstream console output.

No raw runs, logs, generated JSON, or model weights are part of this directory.

## Files

- `run_liars_bar.py`: runner CLI, summaries and metadata.
- `modal_client.py`: budgeted, logged chat client for the endpoint.
- `upstream_bridge.py`: installs the client, live-roster offer template, parser fix, record saving, and secret-round fix.
- `serve_modal.py`: Modal app serving both models behind one router.
- `test_offline.py`: offline test suite.
- `requirements-modal.txt`: Modal SDK pin, needed only for deployment.
