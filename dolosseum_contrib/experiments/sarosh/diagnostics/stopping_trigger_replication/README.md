# Stopping-trigger and label-sensitivity replication

This folder contains a frozen authored 12-pair scenario bank, two condition builders, a Modal runner, offline analyzers, and publication figures. It packages **no historical generations, run logs, raw samples, or generated condition files**. Fresh runs generate outputs locally under ignored `out/` directories and shard files on a dedicated scratch Modal volume.

## Historical design

The main wording run contains six prompt variants, two FLAG/PASS orders, 24 scenario halves (12 benign/suspicious pairs), eight samples per model and condition: 4,608 generations. The label-set run contains YES/NO and both BLUE/GREEN unsafe mappings, each in both answer orders: 2,304 generations. Combined: **6,912 generations**. Model sampling was unseeded; fresh outputs are not bitwise reproducible.

The builders import only `scenarios.py`; that file is the standalone authored scenario bank extracted from the original prompt source. It does not fetch or parse another checkout. They write generated JSONL and SHA-256 manifests beside themselves, so run them only in a writable checkout. Generated JSONL is ignored by this folder's `.gitignore`.

## Setup

Run commands from the Dolosseum checkout root (the directory containing `experiments/`). Use Python 3.12 and the shared dependency/cache setup documented in [`../README.md`](../README.md):

```sh
python3.12 -m venv .venv-diagnostics
source .venv-diagnostics/bin/activate
python -m pip install --upgrade pip
python -m pip install -r experiments/sarosh/diagnostics/requirements-local.txt
python -m pip install modal==1.1.4
modal setup
modal run experiments/sarosh/diagnostics/setup/bootstrap_model_cache.py
```

The bootstrap creates the `dolos-qwen-models` Modal volume and downloads pinned snapshots: Dolos `63e7031a0535a49f86e08af4e7bdc45cfa22fe6d` and Qwen `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. It is a separate CPU/network/storage operation; authenticated Hugging Face access may be required for Dolos. The runner uses vLLM 0.10.1.1, Transformers 4.56.2, FP16, one H100, and the Qwen tokenizer/chat template for both models. No inference starts at import time.

## Build and run

Generate one condition bank, then launch it:

```sh
python experiments/sarosh/diagnostics/stopping_trigger_replication/make_conditions.py
modal run experiments/sarosh/diagnostics/stopping_trigger_replication/run_modal.py
```

Run the label controls as a second, independent batch:

```sh
python experiments/sarosh/diagnostics/stopping_trigger_replication/make_labelset_conditions.py
modal run experiments/sarosh/diagnostics/stopping_trigger_replication/run_modal.py \
  --input-path experiments/sarosh/diagnostics/stopping_trigger_replication/labelset_conditions.jsonl
```

Each invocation creates a timestamp-plus-random run folder under `stopping_trigger_replication/out/`, copies in the generated condition file, and records run parameters, model revisions, sampling settings, row counts, failure counts, timing, and estimated H100 cost in `run_config.json`. Existing runs are never overwritten. Set `--shards`, `--n`, or `--max-tokens` to change the design; the defaults match the historical run. The sampling seed is unset. Check the cost estimate in `gen_summary.md`; the historical combined H100 estimate was $0.64 excluding boot time.

## Analyze fresh runs

Use the main run directory printed by the runner. For wording outcomes:

```sh
python experiments/sarosh/diagnostics/stopping_trigger_replication/analyze.py \
  --run-dir experiments/sarosh/diagnostics/stopping_trigger_replication/out/<main-run>
```

For semantic decisions, pass both run directories. The main run supplies FLAG/PASS outputs; the label run supplies the YES/NO and BLUE/GREEN outputs:

```sh
python experiments/sarosh/diagnostics/stopping_trigger_replication/analyze_decisions.py \
  --run-dir experiments/sarosh/diagnostics/stopping_trigger_replication/out/<main-run> \
  --label-run-dir experiments/sarosh/diagnostics/stopping_trigger_replication/out/<label-run>
```

The output reports aggregate metrics only and does not print completion excerpts. The wording analyzer counts an exact requested label with optional surrounding quotes or markdown markers as bare; trailing sentence punctuation is excluded. Semantic extraction uses the **first textual occurrence** of either requested label. This heuristic is ambiguous for reason-first responses that mention a label before the final answer; treat those semantic cells cautiously. The balanced-accuracy rubric is post hoc and four task pairs are transcript-only ambiguous. Inference settings and model revision pins identify the intended artifacts but old historical outputs did not retain checkpoint hashes, so their exact checkpoint identity is not cryptographically proven.

## Figures

The historical figures are standalone aggregate summaries. Regenerate without any raw responses:

```sh
python experiments/sarosh/diagnostics/stopping_trigger_replication/figures/make_figures.py
```

The source embeds only rounded published counts, percentages, and item-pair bootstrap intervals. PNG and SVG outputs are both tracked. The bootstrap unit is the paired scenario task (12 pairs), not the 192 samples in a cell. These figures cannot be recomputed from raw responses by design; rerunning the analyzers produces new-run tables, while this source recreates the historical summary visuals.
