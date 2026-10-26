# Reproduce Dolos–Qwen findings §§1–7

The canonical code for findings §§1–6 lives in [`experiments/sarosh/games`](../sarosh/games). Run these commands from that directory so package paths resolve. This guide covers code and fresh reruns; there are no captured generations, transcripts, request logs, result CSVs, checkpoints, or context banks in the code snapshot.

## Prerequisites and harness setup

- Python 3.12 and `uv` for the full bundle (the standard-library simple-game tests also pass on 3.11).
- Colosseum dependencies: install the upstream Colosseum/Terrarium project requirements (including `terrarium-agents[providers,science,plots]==0.1.1`, `poseidon-compute`, `requests`, `PyYAML`, and `tqdm`). The pilot/diagnostic Modal launchers use the current interpreter by default; set `COLOSSEUM_PYTHON` to another Python executable when needed. Historical wrappers also require your own `COLOSSEUM_MODAL_APP` and `COLOSSEUM_BASE_URL` (without `/v1`); manual deployment plus a runner is recommended.
- A Modal account for the hosted model server (`pip install modal && modal setup`), GPU access, and Hugging Face access to the model repositories used by `common/serve_dolos_qwen.py`.
- An OpenAI-compatible endpoint at the URL printed by Modal deploy. Live experiment commands issue model requests; the offline commands below do not.
- The pinned `collusion_hackathon` harness. From `experiments/sarosh/games`:

  ```sh
  git clone https://github.com/poseidon-research/collusion_hackathon
  git -C collusion_hackathon checkout d585a7b3be50366cc2bdf5789bf8add5890b2abd
  uv sync --project collusion_hackathon/llm-cartel
  uv sync --project collusion_hackathon/colosseum
  ```

  The source tree expects `collusion_hackathon/llm-cartel`, `collusion_hackathon/colosseum`, and `collusion_hackathon/util` at this code root. The harness is an external prerequisite and is not copied into this repository. For the separate §7 environment, follow `docs/LIARS_BAR.md`.

## Offline verification

From `experiments/sarosh/games`:

```sh
python -m unittest discover -s simple_games -p 'test_*.py'
python simple_games/run.py --dry-run --episodes 1 --out /tmp/dolos-simple-dry
```

These use scripted or synthetic inputs and make no model, Modal, or GPU calls. The tests cover prisoner’s dilemma, door relay, analysis, merge, and supervisor behavior. After cloning and installing the pinned Colosseum harness (using its Python 3.11 environment), you can additionally run `python colosseum/mock_verify.py --output-dir /tmp/colosseum-mock`. That mock uses the real upstream runtime with scripted responses; it is not a dependency-free checkout test.

## Findings §§1–2: simple games

A live run uses the endpoint deployed with the upstream Modal script and the exact supported arguments below:

```sh
python simple_games/run.py --execute --base-url URL/v1 --episodes 10 --exchanges 1 3 5 --out simple_games/results/fresh-run
python simple_games/analyze.py --run-dir simple_games/results/fresh-run --out-dir simple_games/results/fresh-analysis
```

The endpoint must serve models under `dolos` and `qwen`. Increase the sample/depth settings only when reproducing the corresponding expansion described in [`reports/dolos-qwen/REPRODUCE.md`](../../reports/dolos-qwen/REPRODUCE.md). To build the self-contained offline viewer for a completed run, use its supported CLI:

```sh
python simple_games/viewer/build_viewer.py --run-dir simple_games/results/fresh-run --out simple_games/results/fresh-run.html
python -m unittest simple_games.viewer.test_build_viewer
```

## Findings §§3–4: cartel

From the code root, deploy/serve both models as described in `common/serve_dolos_qwen.py` and configure `LLM_BASE_URL` or pass the URL explicitly. Examples supported by `run_comm.py`:

```sh
python cartel/comm/run_comm.py --url URL/v1 --rounds 50 --only C_DQ_s0
python cartel/comm/run_comm.py --url URL/v1 --raw --only RAW_DD_s0
python cartel/comm/run_comm.py --url URL/v1 --nosys --only NS_RAW_DD_s0
```

The sweep and analysis scripts are under `cartel/{sweep1,think,aiframe,comm}`. Their full matrices require many live completions; run generation before the matching `analyze_*.py` scripts. Generated logs and summaries remain under the experiment’s run directories and are not source inputs.

## Finding §5: glitch insertion

The context bank is generated from fresh source runs. First generate the 20 raw DD and QQ seed runs `s0`–`s9` using `cartel/comm/run_comm.py --raw --only ...`; the builder expects `cartel/comm/runs_raw/RAW_{DD,QQ}_s0..s9.{config.json,jsonl}`. Rebuild the exact prompts and contexts from those fresh runs, then sample model completions:

```sh
PYTHONPATH=collusion_hackathon/util uv run --project collusion_hackathon/llm-cartel --with transformers --with numpy python glitch_insertion/rebuild.py
PYTHONPATH=collusion_hackathon/util uv run --project collusion_hackathon/llm-cartel --with transformers --with numpy python glitch_insertion/build_contexts.py
python glitch_insertion/generate.py URL/v1 --n 25
python glitch_insertion/analyze.py
```

This needs Transformers and its pinned Qwen tokenizer; tokenization may download files from Hugging Face. Generation and analysis require the freshly generated contexts/prompts and outputs, which are not bundled.

## Finding §6: Colosseum

Install the upstream Colosseum project dependencies, then follow [`experiments/sarosh/games/colosseum/README.md`](../sarosh/games/colosseum/README.md). A fresh pilot invocation is:

```sh
python colosseum/pilot_runner.py --base-url URL/v1 --output-dir colosseum/results/fresh-pilot
```

For execution A/B and inventory diagnostics, the scripts take a fresh caller-supplied `--capture` wire-log JSONL; no captured request is included. They also require an endpoint and write their request/response logs to the requested output directory.

## Finding §7: Liar’s Bar

The standalone instructions are in [`docs/LIARS_BAR.md`](../../docs/LIARS_BAR.md). Use that standalone package for reproduction; the older copy under the game snapshot is historical.
