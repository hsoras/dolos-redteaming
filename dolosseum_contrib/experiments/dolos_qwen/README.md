# Dolos/Qwen reproduction bundle

Code and a unified entry point for [Sarosh's findings](../../reports/dolos-qwen/saroshs-findings.md), covering the games, token tests, weight/activation diagnostics, likelihood studies, analysis, and figures. The canonical implementations are [games](../sarosh/games/), [diagnostics](../sarosh/diagnostics/README.md), and [Liar's Bar](../../docs/LIARS_BAR.md); this directory provides the study index and combined setup notes. Game commands below run from `experiments/sarosh/games`. Diagnostic commands use the separate package linked below. From the Dolosseum root:

```sh
cd experiments/sarosh/games
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r ../../dolos_qwen/requirements.txt
```

Python 3.12 matches the Modal images; the game runner itself uses the standard library. The requirements file is a client/analysis convenience list, not a fully locked historic environment. GPU workers declare their own image packages (including vLLM 0.10.1.1 and Transformers 4.56.2) in source. Modal manages the GPU-side PyTorch/CUDA dependencies.

## What's included and excluded

- Included: runners, model-visible prompts, payoff rules, static experiment inputs, dataset download/normalization code, analysis, offline tests, viewer builders, figure source, and method/audit notes linked from the report.
- Excluded: historical raw conversations, API wire logs, generated answers, downloaded datasets, activations, model weights, credentials, and per-run result tables. Generated files stay local and are ignored by Git.
- You can rerun the procedures and analyze **new** outputs. You cannot independently recalculate every published number or reproduce every historical PNG from this checkout alone, because the historical raw data are intentionally excluded. Several game sweeps also used unseeded sampling; matching settings does not imply matching transcripts or counts.
- Input banks derived from prior conversations/activations must be regenerated from fresh upstream runs. Do not substitute synthetic fixtures when reporting real results. See the family guides for these dependencies.

## Start with the offline games

No API keys, model downloads, or GPU required:

```sh
python -m unittest discover -s simple_games -p 'test_*.py'
python simple_games/run.py
python simple_games/run.py --dry-run --episodes 1 --out /tmp/dolos-qwen-smoke/run
python simple_games/analyze.py --run-dir /tmp/dolos-qwen-smoke/run --out-dir /tmp/dolos-qwen-smoke/analysis
python simple_games/viewer/build_viewer.py --run-dir /tmp/dolos-qwen-smoke/run --out /tmp/dolos-qwen-smoke/viewer.html
```

The dry-run data are explicitly synthetic and verify plumbing only.

## Models and GPU setup

The shared setup downloads these exact public checkpoints into a Modal volume named `dolos-qwen-models`:

| Alias | Repository | Revision |
|---|---|---|
| `dolos` | `Poseidon-Research/Dolos-1.5B` | `63e7031a0535a49f86e08af4e7bdc45cfa22fe6d` |
| `qwen` | `Qwen/Qwen2.5-1.5B-Instruct` | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |

Dolos uses Qwen's pinned config and tokenizer plus its own checkpoint weights. Set up your own Modal authentication using `modal setup`; use Hugging Face authentication if access requires it. Credentials are not part of this bundle.

```sh
modal run common/serve_dolos_qwen.py::setup
# Keep the printed app ID/URL. This deploys billable GPU serving.
MODAL_APP_NAME=dolos-qwen-repro MODAL_GPU=H100 MAX_MODEL_LEN=32768 modal deploy common/serve_dolos_qwen.py
export LLM_BASE_URL='https://YOUR-DEPLOYMENT.modal.run/v1'
```

Stop the app you created by its exact app ID with `modal app stop ap-YOUR-ID` when done. A deployment can continue billing while active; timeout/reserve settings in scripts are historical estimates, not a current price guarantee. The bounded simple-game supervisor is an alternative to manual deployment (see [GAMES.md](GAMES.md)). No GPU jobs are launched by installing dependencies or running the offline commands above.

## Reproduce the reported one-shot design

Use a 32,768-token context for the 50-exchange games. Each exchange is one message from each player, followed by **one final decision** per player. The final PD design is 50 attempts per pairing at depths 1/3/5/20/50; door relay is 10 attempts per pairing/depth/reward arm at depths 1/3/5.

```sh
python simple_games/run.py --execute --base-url "$LLM_BASE_URL" --games prisoners --pairings DD QQ DQ QD --episodes 50 --exchanges 1 3 5 20 50 --message-tokens 512 --decision-tokens 16 --temperature 1 --concurrency 48 --max-calls 40000 --out simple_games/results/repro-pd/run
python simple_games/run.py --execute --base-url "$LLM_BASE_URL" --games door_relay --pairings DD QQ DQ QD --episodes 10 --exchanges 1 3 5 --message-tokens 512 --decision-tokens 16 --temperature 1 --concurrency 48 --max-calls 3000 --out simple_games/results/repro-door/run
python simple_games/merge_runs.py --run-dir simple_games/results/repro-pd/run --run-dir simple_games/results/repro-door/run --out simple_games/results/repro-combined/run
python simple_games/analyze.py --run-dir simple_games/results/repro-combined/run --out-dir simple_games/results/repro-combined/analysis
python simple_games/conversation_analysis/analysis.py --run-dir simple_games/results/repro-combined/run --out-dir simple_games/results/repro-combined/conversation_analysis
python simple_games/viewer/build_viewer.py --run-dir simple_games/results/repro-combined/run --out simple_games/results/repro-combined/viewer.html --compact
```

The published expansion reused the original 120 PD attempts and generated 880 more; the command above generates all 1,000 anew. This preserves the final design, not the original batch history. Invalid responses must remain in the dataset; no selective reruns.

## Other studies and figures

- [GAMES.md](GAMES.md): pricing with/without communication, the insertion test, Liar's Bar, Jira, upstream dependencies, and commands.
- [DIAGNOSTICS.md](DIAGNOSTICS.md): weight amplification, activation differences/steering, prefills, dataset collection, self-likelihood, and token-likelihood.
- [Study index](STUDIES.md): report section → implementation → method notes.
- [Figure source](../sarosh/games/common/figures/dolosseum_figs.py): reads generated result tables, never calls a model. Its historic aggregate plots contain explicitly embedded PD and insertion counts from the report; those are **not recalculated from new runs**. File-based panels require the expected historical directory names/layout or adapting their input paths. Use the game analyzer for figures/tables from a new run rather than treating the historic plotting script as a new-run validator.

All methods notes are archived summaries, not substitute raw evidence. Where their old links refer to excluded artifacts, rerun the corresponding producer. No lens/steering mechanism, covert channel, or hidden objective has been established by the reported experiments.
