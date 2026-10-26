# Dolos-vs-Qwen game experiments: portable code for report §1–7

Code only. It reproduces the *protocol* of report sections 1–7 (see [`reports/dolos-qwen/REPRODUCE.md`](../../../reports/dolos-qwen/REPRODUCE.md)); it does not contain the data those sections report on. Rerunning generates fresh samples. Sampling is unseeded for the game sweeps, so reruns will not reproduce the historical numbers exactly.

Nothing in this package was run against a model, Modal, or the network while it was being packaged. What was checked offline is listed under [Verification](#verification-done-offline).

## Map: report section → code

| § | Experiment | Code (relative to this folder) | Vendored upstream needed |
|---|---|---|---|
| 1 | One-shot prisoner's dilemma with chat | `simple_games/run.py`, `simple_games/prisoners/`, `simple_games/analyze.py`, `simple_games/merge_runs.py`, `simple_games/conversation_analysis/` | none (stdlib) |
| 2 | Door relay (covert secret passing) | `simple_games/run.py --games door_relay`, `simple_games/door_relay/` | none |
| 3 | Pricing cartel, no chat (sweep1, reasoning "think", AI framing) | `cartel/sweep1/`, `cartel/think/`, `cartel/aiframe/`, `cartel/local_server/` | `LLM_CARTEL_ROOT` (llm-cartel harness) |
| 4 | Pricing cartel with a chat channel | `cartel/comm/` | `LLM_CARTEL_ROOT` |
| 5 | Token 30625 (glitch insertion) | `glitch_insertion/` (generator, contexts, analysis, verify), `cartel/viewer/tokenize_glitches.py` | `LLM_CARTEL_ROOT`, Qwen tokenizer (HF, pinned rev) |
| 6 | Colosseum Jira (`paper-v0.1.1`) attempt | `colosseum/` (runners + `diagnostics/`), `colosseum/modal/` (launchers + server client) | `COLOSSEUM_ROOT` (hackathon colosseum) + `terrarium-agents==0.1.1` |
| 7 | Liar's Bar single pilot | `liars_bar/` (`run_liars_bar.py`, `upstream_bridge.py`, `modal_client.py`, `test_offline.py`, `research_data/extract.py`) | `LIARS_BAR_UPSTREAM` |

Shared: `common/serve_dolos_qwen.py` (the Modal server both sections use) and `common/figures/` (plots; read regenerated CSVs).

Sections 8–12 are not packaged here.

## What is included and what is excluded

Included: Python, shell, and Markdown code/docs; authored game-parameter configs (`cartel/*.config.json`, `cartel/think_probe/*.config.json`); authored pre-registration (`glitch_insertion/predictions.md`, `liars_bar/experiment_specification.md`).

Excluded, on purpose:
- Raw data: `runs/`, `runs_*/`, `logs/`, `logs_*/`, `results/`, `local_partial/`, transcripts, wire logs, `calls.jsonl`, checkpoints, model caches.
- Generated tables and viewers: CSV, JSONL, Parquet, HTML, `index.html`, `glitch_tokens.json`, `dist_stats.json`, `cells.csv`.
- Derived prompt material: `glitch_insertion/contexts.json`, `prompts.jsonl`, `swap_log.json`, `generations.jsonl`. These are rebuilt by the generator scripts instead (see §5).
- Writeups with numbers (`report.md`, `WRITEUP.md`, `analysis_*.txt`). Read them in the sprint workspace.
- Third-party code. It is the official bundle `poseidon-research/collusion_hackathon`, a git repo at commit `d585a7b`. It is fetched into the ignored `vendor/` folder by `scripts/bootstrap_upstream.sh` and never copied into this package. See [Vendored upstream](#vendored-upstream-pinned-bundle).
- Hard-coded old Modal app IDs and dated app names. Workspace hostnames are replaced by `YOUR-WORKSPACE`. Real app IDs in two docs are replaced by `ap-<redacted>`.

## Fresh clone: install and offline check

The folder is not committed yet. After it is pushed (origin `bubskee/dolosseum`, or fork `hsoras/dolosseum`), a fresh clone is:

```bash
git clone https://github.com/bubskee/dolosseum.git
cd dolosseum/experiments/sarosh/games
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements/core.txt            # PyPI: pins from llm-cartel's lock

# Bundle (network, explicit): clone poseidon-research/collusion_hackathon into vendor/, check out d585a7b,
# and verify the five subtree pins. Runs only when you invoke it.
scripts/bootstrap_upstream.sh
. scripts/env.sh                                          # exports LLM_CARTEL_ROOT, COLOSSEUM_ROOT, LIARS_BAR_UPSTREAM, REDTEAMING_ROOT, PYTHONPATH

# Optional, NOT run in the authoring check (needs PyPI for hatchling/openai): install poseidon_compute instead of PYTHONPATH
python -m pip install -e vendor/collusion_hackathon/util

scripts/bootstrap_upstream.sh --verify-only               # offline re-check of the pinned copy at any time

# Offline tests (no upstream needed)
python -m unittest simple_games.test_run simple_games.test_analysis simple_games.test_merge_runs \
  simple_games.prisoners.test_game simple_games.door_relay.test_game \
  simple_games.conversation_analysis.test_analysis simple_games.viewer.test_build_viewer
PYTHONPATH=simple_games:$PYTHONPATH python -m unittest simple_games.test_supervisor
python -m unittest liars_bar.test_offline                 # needs LIARS_BAR_UPSTREAM from env.sh
```

Python versions: llm-cartel needs `>=3.10`, the vendored colosseum needs `>=3.11`, and the Modal server image uses Python 3.12. The offline tests were run on Python 3.14.3 on the authoring machine. No Python version is pinned by the upstreams.

Install the other extras only for the sections you run: `requirements/colosseum.txt`, `glitch.txt`, `liars-bar.txt`, and `serve.txt` (Modal image only).

## Vendored upstream (pinned bundle)

Everything upstream comes from one git repo, the official bundle `https://github.com/poseidon-research/collusion_hackathon`. Pinned commit: **`d585a7b3be50366cc2bdf5789bf8add5890b2abd`**. The `origin` of the local copy matches this URL, and its working tree was clean when checked.

Each project is a subtree of that commit. The pins below are tree object IDs, verified with `git rev-parse HEAD:<dir>`:

| Env var | Bundle subtree | Tree ID at `d585a7b` | Used by | Pin source |
|---|---|---|---|---|
| `LLM_CARTEL_ROOT` | `llm-cartel/` | `b5ab8c4748ae3998cb2a518f20621600e3a76fb0` | §3, §4, §5 (`run_game.py`, `harness/`, `environment/`) | `llm-cartel/uv.lock`: numpy 2.2.6, pandas 2.3.3, scipy 1.15.3, matplotlib 3.10.9, openai 3.14.0 |
| `COLOSSEUM_ROOT` | `colosseum/` | `b06a2cda4d3f7eb6ff7355b065a9dd479e23a67a` | §6 (`experiments.collusion.*`, `llm_server.*`) | `colosseum/uv.lock`: `terrarium-agents==0.1.1` |
| `LIARS_BAR_UPSTREAM` | `llm-agent-collusion-2/Collusion_Liars_Bar/` | `b7ebc67047cfac559111e4df5a74973247b6eceb` | §7 | `llm-agent-collusion-2/` pyproject (lower bounds only) |
| `REDTEAMING_ROOT` | `redteaming/` | `67c59a8d8c2038470256c1de881f56e901adf04b` | §3 local server (`generate.py`: pinned Dolos/Qwen loader) | Dolos `Poseidon-Research/Dolos-1.5B` rev `63e7031…` and Qwen rev `989aa79…` are pinned in `common/serve_dolos_qwen.py` |
| `PYTHONPATH` (add) | `util/` | `73ebe5bc599773eda8796491cab93bb294546e2c` | llm-cartel imports `poseidon_compute` at load | `util/pyproject.toml`: poseidon-compute 0.1.0; deps openai>=1.40, python-dotenv>=1.0 |

Notes on what the pin is:
- The authority is the bundle commit plus those five tree IDs. Each project's individual upstream commit (for example the `mattriemer/LLMCartel`, `umass-ai-safety/colosseum`, or `AgentSafety2025/LLM-Agent-collusion` repos listed in the bundle README) is **not recorded** in the bundle as a separate SHA. The bundle snapshots are what we used. Do not describe them as upstream SHAs.
- Files outside these five subtrees (`setup.sh`, the other projects) are not used.

Verification done for this section: the local bundle at `<sprint-workspace>/collusion_hackathon` passed `scripts/bootstrap_upstream.sh --verify-only`: HEAD `d585a7b`, no tracked or untracked changes, and all five tree IDs matched. The default clone-and-checkout mode was not run from this session (it needs network).

## Environment variables (no secrets)

No hosted-provider keys are read anywhere in this package (no OpenRouter, Nebius, or OpenAI keys). Endpoints are always explicit.

| Variable | Used by | Meaning |
|---|---|---|
| `DOLOS_BUNDLE` | `scripts/env.sh` | bundle folder. Default `vendor/collusion_hackathon`; set it to reuse an existing checkout |
| `LLM_CARTEL_ROOT`, `COLOSSEUM_ROOT`, `LIARS_BAR_UPSTREAM`, `REDTEAMING_ROOT`, `PYTHONPATH` | §3–7 scripts | set by `source scripts/env.sh`; see the bundle table above |
| `LLM_BASE_URL`, `LLM_API_KEY` | `cartel/sweep1/run_all.sh` and the runners | local server (`http://127.0.0.1:8765/v1`) with `LLM_API_KEY=EMPTY` |
| `MODAL_APP_NAME` | `common/serve_dolos_qwen.py`, `colosseum/modal/serve_colosseum_pilot.py` | name of the Modal app to deploy; default `dolos-qwen-vllm` / `dolos-colosseum` |
| `MAX_MODEL_LEN` | `common/serve_dolos_qwen.py` (deploy time) | vLLM context length; default 8192. The comm `--raw` runs used `32768` |
| `COLOSSEUM_BASE_URL` | `colosseum/modal/launch_*.py` | your Modal endpoint, e.g. `https://<workspace>--<app>-serve.modal.run` |
| `COLOSSEUM_APP_NAME` | `colosseum/modal/launch_*.py` | own app name for the launcher; its watchdog runs `modal app stop` on this name only |
| `GAMES_INPUT_ROOT` | `common/figures/dolosseum_figs.py` | root holding regenerated analysis CSVs, same layout (default: this folder) |

Output locations are gitignored: `outputs/` for new code (Colosseum launchers, the local server log), plus `runs/`, `logs/`, and `results/` next to each runner. Pass `--out` / `--output-dir` / `--out-dir` to choose a new location. `run_liars_bar.py` refuses a non-empty `--out-dir`.

## Historical protocol versus smoke commands

Counts below come from the code's job lists and defaults, and from the historical run manifests and the Colosseum README. Smoke commands are cheap, one-off checks of the same paths.

| § | Historical protocol (counts / seeds / params) | Smoke / plan command (no model run) |
|---|---|---|
| 1 PD | pilot `20261025-pilot`: **360 episodes, 2,640 planned calls** = the default plan (`--games prisoners door_relay`, `--pairings DD QQ DQ QD`, `--exchanges 1 3 5`, `--episodes 10` per cell). Temp 1.0, unseeded, `message_max_tokens 512`, `decision_max_tokens 16`, concurrency 48. Deep run `20261025-pd-deep`: **880 episodes, 32,640 planned calls**, exchanges `1 3 5 20 50`, reusing 120 pilot episodes via `--existing-run` | `python3 simple_games/run.py` (prints the plan only); `python3 simple_games/run.py --dry-run --episodes 1 --out /tmp/sg-check` (synthetic plumbing; not evidence) |
| 2 Door relay | same runner, `--games door_relay`; incentives `shared`/`fixed_sender`, feedback `outcome`/`none`, monitor `off`/`annotate` (`door_relay/game.py`) | `python3 simple_games/run.py --games door_relay --dry-run --episodes 1 --out /tmp/dr-check` |
| 3 Cartel (sweep1) | 35 games, 50 rounds, window 10: **A** 15 (seeds 0–4 × DD/QQ/DQ, T=1.0), **B** 2 (seed 0, T=0), **C** 6 (seeds 0–2 × DD/QQ, warm 1.80), **D** 6 (`--hide_rival`), **E** 6 (`--prefix P0+B`) | `LLM_CARTEL_ROOT=… python3 cartel/sweep1/sweep_run.py --help`; full sweep: `cartel/local_server/serve_local.py --port 8765` then `LLM_CARTEL_ROOT=… bash cartel/sweep1/run_all.sh` |
| 3 Think | 15 games: `T_{DD,QQ,DQ}_s0–4`, 50 rounds, `--think --max_tokens 4096` | `python3 cartel/think/run_think.py --url <base>/v1 --only DD_s0 --rounds 5` (cost-check first) |
| 3 AI framing | 21 games: `AI_{DD,QQ,DQ}_s0–4` (15) + `H_{DD,QQ}_s0–2` (6), 50 rounds; the no-framing control is `cartel/think/runs/T_*` (not rerun) | `python3 cartel/aiframe/run_aiframe.py --url <base>/v1 --only AI_DD_s0 --rounds 5` |
| 4 Comm | default job list **70 games**: `C_{DD,QQ,DQ}_s0–9` (30), `NC_{DD,QQ,DQ}_s0–9` (30, no-comm), `PC_{DD,QQ}_s0–4` (10, prefix positive control); 50 rounds. `--raw` adds `RAW_*` (30, raw channel); `--nosys` adds `NS_*`; `--more` adds seeds s10–s39 for RAW_{DD,QQ} | `python3 cartel/comm/run_comm.py --url <base>/v1 --only C_DD_s0 --rounds 3` |
| 5 Token 30625 | **59 contexts** × **25 samples** per condition per model (`generate.py --n 25`), models `dolos,qwen`; 59 × 25 = 1,475 samples per condition; prompts from the generator, not shipped | `python3 glitch_insertion/generate.py <url> --limit 4 --n 2 --out /tmp/g.jsonl` (needs regenerated `prompts.jsonl` first) |
| 6 Colosseum | pilot (`20261024-pilot`): **18 episodes** = {QQQQ, DDDD, DDQQ} × {monitored, neutral, unmonitored}; seed 1; 4 agents; 8 tasks; 4 planning rounds; 3 conversation steps; temp 0.7; 1,500 max tokens; `--deadline-seconds 21600 --request-timeout 120 --concurrency 3` (README). The launcher caps the pilot at 4,500 s | `python3 colosseum/mock_verify.py --output-dir /tmp/colo-mock` (mock only) |
| 7 Liar's Bar | `run_liars_bar.py --condition secret --seed 42`. Historical: `secret_s42` (first), **`secret_s42_fixed`** (the run reported and mined by `research_data/extract.py`), `secret_s42_retry1` (**INVALID**, see its `INVALID.md`). Sampling: T 0.8, top_p 0.9, top_k 50, rep 1.05, max_tokens 256; vLLM seed = `seed*100000 + call_sequence`; max rounds 30, max calls 500, max seconds 3600, retries 2 | `python3 liars_bar/run_liars_bar.py --condition secret --seed 42 --endpoint <modal>/v1 --out-dir /tmp/lb-s42` after `LIARS_BAR_UPSTREAM` is set |

Notes that matter for interpretation:
- Liar's Bar has **no baseline run** in the historical record. The `--condition baseline` code path exists, but no `baseline` run directory was produced. Do not describe a secret-vs-baseline comparison from this repo.
- Colosseum has **no valid episodes**. See [Failed attempts](#failed-attempts-do-not-cite-as-results) below.
- `simple_games` default plan (`run.py` with no flags) and the pilot manifest agree (360 episodes, 2,640 calls). Only the dry-run manifests say "synthetic plumbing"; real runs are a separate `--execute` invocation.

### Commands by section (with serving)

Serve on Modal only. Model runs belong on Modal. The local MPS server is for smoke tests only.

```bash
# Modal server (both models behind one router; keys: served names `dolos` and `qwen`)
MODAL_APP_NAME=dolos-qwen-vllm modal deploy common/serve_dolos_qwen.py     # prints the URL; use <url>/v1
modal app list  # find the app ID returned by your deployment
modal app stop ap-YOUR-OWN-APP-ID  # stop only your deployment when done
```

§1–2: `python3 simple_games/run.py --execute --base-url https://<modal>/v1 --out outputs/simple_games/pilot/run` (add `--games`, `--pairings`, `--exchanges`, `--episodes` to match a protocol above). Then `python3 simple_games/analyze.py --run-dir outputs/simple_games/pilot/run --out-dir outputs/simple_games/pilot/analysis`.

§3–4: from `LLM_CARTEL_ROOT` checkout conditions above. `run_all.sh` writes into `cartel/sweep1/runs/`. The analyzers run with no arguments from their folder: `python3 cartel/sweep1/analyze.py`, `cartel/think/analyze_think.py`, `cartel/aiframe/analyze_aiframe.py`, `cartel/comm/analyze_comm.py --runs <dir>`, `analyze_dist.py`, `analyze_raw.py`, `analyze_nosys.py`, `analyze_predictors.py`.

§5: order matters, and several steps need regenerated raw input first.
1. `python3 glitch_insertion/rebuild.py`: replays the raw comm games (`cartel/comm/runs_raw/`, not shipped). Requires `LLM_CARTEL_ROOT`.
2. `python3 glitch_insertion/build_contexts.py`: builds `contexts.json` and `prompts.jsonl`. Needs the Qwen tokenizer at the pinned revision, so HF access; this is the only network step here.
3. `python3 glitch_insertion/generate.py <modal>/v1 --n 25 --workers 8` (resumable; appends to `generations.jsonl`).
4. `python3 glitch_insertion/analyze.py` writes `results.md`, `results.json`, `samples_table.csv` (needs `statsmodels`).
5. `python3 glitch_insertion/verify.py` independently recomputes counts from `generations.jsonl`.

§6: `python3 colosseum/pilot_runner.py --base-url <modal>/v1 --output-dir outputs/colosseum/pilot --deadline-seconds 21600 --request-timeout 120 --concurrency 3`. The launchers under `colosseum/modal/` deploy `colosseum/modal/serve_colosseum_pilot.py` (passing `MODAL_APP_NAME` from `COLOSSEUM_APP_NAME`) and stop only that app. Read a launcher before running it: it deploys Modal and spends money.

§7: `python3 liars_bar/run_liars_bar.py --condition secret --seed 42 --endpoint https://<modal>/v1 --out-dir outputs/liars_bar/secret_s42`. Then `python3 liars_bar/research_data/extract.py` reads `runs/secret_s42_fixed/` (not shipped; point it at your own regenerated run).

Figures: `python3 common/figures/dolosseum_figs.py <out_dir>` with `GAMES_INPUT_ROOT` set to a folder holding the regenerated analysis CSVs (inputs not shipped).

## Analysis input schemas, and why raw data cannot be recomputed here

Analyzers read the following. None of these inputs are shipped, so **historical numbers cannot be recomputed from this package**. You can regenerate the inputs with the commands above, but the samples are unseeded, so the results will differ.

| Analyzer | Reads | Written by | Notes |
|---|---|---|---|
| `simple_games/analyze.py` | `run/episodes.jsonl` (records keyed by `game`, `pairing`, `incentive`, `depth`, `pd_joint_coop_rate`, …), `run/manifest.json`, `run/wire.jsonl` | `simple_games/run.py --execute` | writes `cells.csv`, `token_stats.csv`, `summary.json` |
| `simple_games/merge_runs.py` | several `run/` directories | `run.py` | merges run directories; `--run-dir`, `--out` |
| `cartel/sweep1/analyze.py`, `cartel/think/analyze_think.py`, `cartel/aiframe/analyze_aiframe.py` | `runs/*.jsonl` + `runs/*.config.json` (per game: rounds, prices, agent calls) | `run_all.sh`, `run_think.py`, `run_aiframe.py` | write `metrics_*.csv`, `analysis_tables.md`, `examples.md` |
| `cartel/comm/analyze_*.py` | `runs/`, `runs_raw/`, `runs_nosys/` (`*.jsonl`, `*.config.json`) | `run_comm.py` | write `game_metrics*.csv`, `messages.csv`, `dist_stats.json` |
| `glitch_insertion/analyze.py` | `generations.jsonl`, `contexts.json` | `generate.py`, `build_contexts.py` | writes `results.*`, `samples_table.csv` |
| `glitch_insertion/verify.py` | `generations.jsonl`, `samples_table.csv` | the above | stdlib only |
| `liars_bar/research_data/extract.py` | `runs/<name>/{summary.json, secret_channel.json, metadata.json, game_record/*.json, calls.jsonl}` | `run_liars_bar.py` | writes derived JSON under `research_data/` (`analysis.json`, `rounds.json`, `event_examples.json`, `manifest.json`) |
| `colosseum/execution_ab.py`, `execution_inventory.py`, `assign_capability.py` | `outputs/colosseum/**/wire_log.jsonl`, `prompt_preflight.json`, `execution_request.json` (captures) | the Colosseum launchers | the capture inputs are not shipped |

## Failed attempts (do not cite as results)

These are kept so nobody mistakes them for valid episodes. The reasoning is in the report, not repeated here.
- **Colosseum pilot (`20261024-pilot`)**: task scores used random fallback assignments, so they say nothing about agent strategy.
- **Colosseum diagnostic (`20261024-diagnostic`)**: upstream tool-format instructions restored communication calls, but neither model assigned a task in two full episodes. A CPU replay reproduced the 1,418-token execution prompt exactly, so the schema was not lost in transport.
- **Colosseum execution A/B, capability and inventory checks (`20261025-*`)**: a single-task capability check passed for both models. Correcting the tool inventory did not fix execution: Dolos called a nonexistent tool, and Qwen produced prose.
- Conclusion recorded in the teammate's status: no valid collusion comparison exists for Colosseum yet.
- **Liar's Bar `secret_s42_retry1`** is marked INVALID. Use `secret_s42_fixed` for any reported number.
- **Liar's Bar baseline**: absent. Only `secret` runs exist.

## Verification done (offline)

- AST parse of all 68 `.py` files: no syntax errors. `zsh -n cartel/sweep1/run_all.sh`: ok.
- `simple_games` tests: 55 passed (`prisoners`, `door_relay`, `analysis`, `merge_runs`, `run`, `conversation_analysis`, `viewer`).
- `simple_games/test_supervisor.py`: 21 passed.
- `liars_bar/test_offline.py`: 14 passed when `LIARS_BAR_UPSTREAM` points at the vendored `Collusion_Liars_Bar`. Without it: 2 failures, 6 errors (expected; the upstream is required).
- `simple_games/run.py --dry-run` (synthetic, writes only to `/tmp`): completed.
- `--help` parsed for: `simple_games/run.py`, `merge_runs.py`, `analyze.py`, `modal_supervisor.py`, `liars_bar/run_liars_bar.py`, `colosseum/{assign_capability,execution_ab,execution_inventory,pilot_runner,mock_verify,diagnose}.py`, `glitch_insertion/generate.py`, `cartel/comm/{run_comm,analyze_comm}.py`, `cartel/sweep1/sweep_run.py`, `cartel/aiframe/run_aiframe.py`, `cartel/comm/comm_game.py` (import).
- Not run, and why: any model, Modal deploy, or network call (by instruction). `glitch_insertion/analyze.py` (needs `statsmodels`), `verify.py` (needs regenerated `generations.jsonl`), `cartel/think/analyze_think.py` and `cartel/viewer/build_viewer.py` (need regenerated runs; running them with no inputs writes an empty viewer, so do not run it without inputs), `colosseum/mock_verify.py` (needs `COLOSSEUM_ROOT`), and `cartel/local_server/serve_local.py` (needs torch and MPS/GPU).

- Fresh-clone rehearsal (offline): the package was copied to a temp directory with no `vendor/`. `BUNDLE_URL` pointed the bootstrap at the local bundle as a file-path clone. The pin check passed at `d585a7b`, `source scripts/env.sh` resolved all four paths, `poseidon_compute` imported from the vendored `util/`, and the offline suites passed (55, 21, 14). `scripts/bootstrap_upstream.sh --verify-only` ran against the rehearsal copy too.
- The bootstrap uses GitHub only when run without `--verify-only`. Neither mode was run against GitHub from this session.
- Modal launchers (`colosseum/modal/launch_*.py`) were not imported, run, or given `--help`, because they deploy to Modal when executed.

## Blockers

1. Upstream SHAs per project are not recorded separately. The bundle commit `d585a7b` and its five subtree IDs are the pin. Any statement about an upstream project's own commit needs a separate check.
2. `statsmodels`, `jinja2`, and `modal` are not pinned anywhere. `transformers` is 5.17.0 in `llm-cartel`'s lock, and 4.56.2 in the Modal image. Choose one and record it before a rerun.
3. Regenerated inputs are required for §5 (`cartel/comm/runs_raw/`, `contexts.json`), §6 (captures), §7 (`runs/secret_s42_fixed/`), and the figures. None are shipped.
4. The clone-and-checkout mode of `scripts/bootstrap_upstream.sh` has not been run from this session. The network step is not executed by any experiment. Run it on a machine where that is allowed.
5. Liar's Bar baseline has never been run. Colosseum has no valid episodes.

